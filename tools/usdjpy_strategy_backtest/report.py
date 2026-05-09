from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.strategy_json.schema import ALLOWED_STRATEGY_FAMILIES, base_strategy_seed
    from tools.strategy_json.fingerprint import strategy_fingerprint
    from tools.strategy_json.normalizer import normalize_strategy_json
except ModuleNotFoundError:  # pragma: no cover
    from strategy_json.schema import ALLOWED_STRATEGY_FAMILIES, base_strategy_seed
    from strategy_json.fingerprint import strategy_fingerprint
    from strategy_json.normalizer import normalize_strategy_json

from .historical_news import load_historical_news_events
from .quality import build_quality_report, write_quality_report
from .schema import (
    AGENT_VERSION,
    FOCUS_SYMBOL,
    SAFETY_BOUNDARY,
    backtest_cache_path,
    equity_path,
    history_sync_report_path,
    ingest_report_path,
    production_status_path,
    quality_report_path,
    report_path,
    trades_path,
)
from .sqlite_store import (
    bar_coverage_summary,
    connect,
    count_bars,
    ingest_runtime_snapshot,
    load_bars,
    latest_bar_time,
    write_sample_bars,
    write_strategy_run,
)
from .strategy_runner import SUPPORTED_BACKTEST_FAMILIES, run_strategy


def status(runtime_dir: Path) -> Dict[str, Any]:
    with connect(runtime_dir) as conn:
        bar_counts = {timeframe: count_bars(conn, timeframe) for timeframe in ("M1", "M5", "M15", "H1", "H4", "D1")}
        latest_bars = {timeframe: latest_bar_time(conn, timeframe) for timeframe in ("M1", "M5", "M15", "H1", "H4", "D1")}
        history_coverage = bar_coverage_summary(conn)
    report = _load_json(report_path(runtime_dir))
    ingest_report = _load_json(ingest_report_path(runtime_dir))
    history_sync_report = _load_json(history_sync_report_path(runtime_dir))
    production_status = _load_json(production_status_path(runtime_dir))
    quality_report = _load_json(quality_report_path(runtime_dir))
    return {
        "ok": True,
        "schema": "quantgod.strategy_backtest.status.v1",
        "agentVersion": AGENT_VERSION,
        "symbol": FOCUS_SYMBOL,
        "barCounts": bar_counts,
        "latestBars": latest_bars,
        "historyCoverage": history_coverage,
        "ingestReport": ingest_report,
        "historySyncReport": history_sync_report,
        "historyProductionStatus": production_status,
        "qualityReport": quality_report,
        "latestReport": report,
        "paths": {
            "sqlite": str((runtime_dir / "backtest" / "usdjpy.sqlite").resolve()),
            "report": str(report_path(runtime_dir).resolve()),
            "trades": str(trades_path(runtime_dir).resolve()),
            "equity": str(equity_path(runtime_dir).resolve()),
            "historyProductionStatus": str(production_status_path(runtime_dir).resolve()),
        },
        "safety": dict(SAFETY_BOUNDARY),
    }


def build_sample(runtime_dir: Path, overwrite: bool = False) -> Dict[str, Any]:
    result = write_sample_bars(runtime_dir, overwrite=overwrite)
    return {
        "ok": True,
        "schema": "quantgod.strategy_backtest.sample.v1",
        "agentVersion": AGENT_VERSION,
        **result,
        "safety": dict(SAFETY_BOUNDARY),
    }


def run_backtest(
    runtime_dir: Path,
    strategy_json: Dict[str, Any] | None = None,
    write: bool = True,
    include_coverage_matrix: bool = True,
) -> Dict[str, Any]:
    seed = strategy_json or base_strategy_seed("STRATEGY-BACKTEST-USDJPY-RSI-LONG")
    ingest_report = ingest_runtime_snapshot(runtime_dir)
    historical_news = load_historical_news_events(runtime_dir)
    with connect(runtime_dir) as conn:
        if count_bars(conn, "H1") < 40:
            write_sample_bars(runtime_dir, overwrite=False)
        bars_by_timeframe = {
            timeframe: load_bars(conn, timeframe, limit=5000)
            for timeframe in ("M1", "M5", "M15", "H1", "H4", "D1")
        }
        multi_timeframe = {
            timeframe: {
                "barCount": count_bars(conn, timeframe),
                "latestBar": latest_bar_time(conn, timeframe),
            }
            for timeframe in ("M1", "M5", "M15", "H1", "H4", "D1")
        }
        history_coverage = bar_coverage_summary(conn)
    cache_key = _backtest_cache_key(seed, history_coverage, historical_news, include_coverage_matrix)
    cached = _get_cached_backtest(runtime_dir, cache_key) if _cache_enabled() else None
    if cached:
        cached["cache"] = {
            "enabled": True,
            "hit": True,
            "cacheKey": cache_key,
            "reasonZh": "命中 Strategy JSON 回测缓存；历史窗口、策略指纹、成本和新闻证据未变化。",
        }
        if write:
            write_outputs(runtime_dir, cached, cached.get("trades", []), cached.get("equityCurve", []))
            quality = build_quality_report(status(runtime_dir), cached)
            write_quality_report(runtime_dir, quality)
        return cached

    result = run_strategy(seed, bars_by_timeframe, historical_news=historical_news)
    strategy_coverage = (
        _multi_strategy_coverage_matrix(bars_by_timeframe)
        if include_coverage_matrix
        else _coverage_matrix_skipped("per-seed GA scoring skips full multi-strategy matrix to keep evolution fast")
    )
    report = _report_payload(
        seed,
        result,
        bars_by_timeframe,
        ingest_report,
        multi_timeframe,
        history_coverage,
        strategy_coverage,
        historical_news,
    )
    report["cache"] = {
        "enabled": _cache_enabled(),
        "hit": False,
        "cacheKey": cache_key,
        "reasonZh": "本次重新计算 Strategy JSON 回测，并写入缓存供 GA 重复评分使用。",
    }
    if _cache_enabled() and report.get("ok"):
        _put_cached_backtest(runtime_dir, cache_key, report)
    if write:
        write_outputs(runtime_dir, report, result.get("trades", []), result.get("equityCurve", []))
        quality = build_quality_report(status(runtime_dir), report)
        write_quality_report(runtime_dir, quality)
    return report


def write_outputs(runtime_dir: Path, report: Dict[str, Any], trades: List[Dict[str, Any]], equity: List[float]) -> None:
    root = runtime_dir / "backtest"
    root.mkdir(parents=True, exist_ok=True)
    report_path(runtime_dir).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    trade_fields = [
        "tradeId",
        "symbol",
        "direction",
        "entryTime",
        "exitTime",
        "entryPrice",
        "exitPrice",
        "exitReason",
        "riskPips",
        "grossProfitPips",
        "costPips",
        "spreadPoints",
        "spreadPips",
        "profitPips",
        "rawProfitR",
        "profitR",
        "mfeR",
        "maeR",
        "newsRiskLevel",
        "newsLotMultiplier",
        "newsReasonZh",
    ]
    with trades_path(runtime_dir).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=trade_fields)
        writer.writeheader()
        for row in trades:
            writer.writerow({field: row.get(field, "") for field in trade_fields})

    with equity_path(runtime_dir).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["index", "equityR"])
        writer.writeheader()
        for index, value in enumerate(equity, start=1):
            writer.writerow({"index": index, "equityR": value})
    with connect(runtime_dir) as conn:
        write_strategy_run(conn, report)


def ingest_klines(runtime_dir: Path) -> Dict[str, Any]:
    return ingest_runtime_snapshot(runtime_dir)


def _report_payload(
    seed: Dict[str, Any],
    result: Dict[str, Any],
    bars_by_timeframe: Dict[str, List[Any]],
    ingest_report: Dict[str, Any],
    multi_timeframe: Dict[str, Any],
    history_coverage: Dict[str, Any],
    strategy_coverage: Dict[str, Any],
    historical_news: Dict[str, Any],
) -> Dict[str, Any]:
    strategy = result.get("strategyJson") if isinstance(result.get("strategyJson"), dict) else seed
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    engine = result.get("engine") if isinstance(result.get("engine"), dict) else {}
    primary_timeframe = str(engine.get("primaryTimeframe") or "H1")
    primary_bars = bars_by_timeframe.get(primary_timeframe, [])
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_id = _run_id(strategy, now)
    return {
        "ok": bool(result.get("ok")),
        "schema": "quantgod.strategy_backtest.report.v1",
        "agentVersion": AGENT_VERSION,
        "runId": run_id,
        "createdAt": now,
        "symbol": FOCUS_SYMBOL,
        "timeframe": primary_timeframe,
        "strategyId": strategy.get("strategyId"),
        "seedId": strategy.get("seedId"),
        "strategyFamily": strategy.get("strategyFamily"),
        "direction": strategy.get("direction"),
        "barCount": len(primary_bars),
        "multiTimeframe": {
            "primaryTimeframe": primary_timeframe,
            "confirmationTimeframes": [
                item
                for item in ("M1", "M5", "M15", "H1", "H4", "D1")
                if item != primary_timeframe
            ],
            "contexts": multi_timeframe,
            "runnerZh": "Strategy JSON runner 会读取 USDJPY 多周期 SQLite K线，并按策略族选择主执行周期。",
        },
        "engine": engine,
        "historicalNews": {
            "schema": historical_news.get("schema"),
            "sourceAvailable": bool(historical_news.get("sourceAvailable")),
            "eventCount": int(historical_news.get("eventCount") or 0),
            "digest": historical_news.get("digest"),
            "reasonZh": historical_news.get("reasonZh"),
        },
        "klineIngest": ingest_report,
        "historyCoverage": history_coverage,
        "strategyCoverageMatrix": strategy_coverage,
        "tradeCount": int(metrics.get("tradeCount", 0)),
        "metrics": metrics,
        "trades": result.get("trades", []),
        "equityCurve": result.get("equityCurve", []),
        "validation": result.get("validation", {}),
        "reasonZh": result.get("reasonZh"),
        "evidenceQuality": _evidence_quality(len(primary_bars), int(metrics.get("tradeCount", 0))),
        "singleSourceOfTruth": "STRATEGY_JSON_USDJPY_SQLITE_BACKTEST",
        "safety": dict(SAFETY_BOUNDARY),
    }


def _evidence_quality(bar_count: int, trade_count: int) -> str:
    if bar_count >= 720 and trade_count >= 20:
        return "HIGH"
    if bar_count >= 160 and trade_count >= 3:
        return "MEDIUM"
    return "LOW"


def _cache_enabled() -> bool:
    value = os.environ.get("QG_BACKTEST_CACHE_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _backtest_cache_key(
    seed: Dict[str, Any],
    history_coverage: Dict[str, Any],
    historical_news: Dict[str, Any],
    include_coverage_matrix: bool,
) -> str:
    normalized_seed = normalize_strategy_json(seed)
    if not isinstance(normalized_seed, dict):
        normalized_seed = seed
    cost_env = {
        "spreadPips": os.environ.get("QG_BACKTEST_SPREAD_PIPS", ""),
        "slippagePips": os.environ.get("QG_BACKTEST_SLIPPAGE_PIPS", ""),
        "commissionPips": os.environ.get("QG_BACKTEST_COMMISSION_PIPS", ""),
        "dynamicSpread": os.environ.get("QG_BACKTEST_DYNAMIC_SPREAD", ""),
        "maxSpreadPips": os.environ.get("QG_BACKTEST_MAX_SPREAD_PIPS", ""),
    }
    raw = {
        "schema": "quantgod.strategy_backtest_cache_key.v1",
        "strategyFingerprint": strategy_fingerprint(normalized_seed),
        "historyCoverage": history_coverage,
        "historicalNewsDigest": historical_news.get("digest"),
        "historicalNewsEventCount": historical_news.get("eventCount"),
        "includeCoverageMatrix": include_coverage_matrix,
        "costEnv": cost_env,
    }
    return hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _get_cached_backtest(runtime_dir: Path, cache_key: str) -> Dict[str, Any] | None:
    cache = _load_json(backtest_cache_path(runtime_dir))
    entries = cache.get("entries") if isinstance(cache.get("entries"), dict) else {}
    cached = entries.get(cache_key)
    if isinstance(cached, dict):
        return json.loads(json.dumps(cached))
    return None


def _put_cached_backtest(runtime_dir: Path, cache_key: str, report: Dict[str, Any]) -> None:
    path = backtest_cache_path(runtime_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    cache = _load_json(path)
    entries = cache.get("entries") if isinstance(cache.get("entries"), dict) else {}
    entries[cache_key] = report
    max_entries = int(os.environ.get("QG_BACKTEST_CACHE_MAX_ENTRIES", "24"))
    if len(entries) > max_entries:
        for key in list(entries.keys())[: len(entries) - max_entries]:
            entries.pop(key, None)
    payload = {
        "schema": "quantgod.strategy_backtest_cache.v1",
        "agentVersion": AGENT_VERSION,
        "updatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "entryCount": len(entries),
        "maxEntries": max_entries,
        "entries": entries,
        "reasonZh": "Strategy JSON 回测缓存按策略指纹、历史覆盖、成本模型和历史新闻证据失效。",
        "safety": dict(SAFETY_BOUNDARY),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _coverage_matrix_skipped(reason: str) -> Dict[str, Any]:
    return {
        "schema": "quantgod.strategy_backtest_coverage_matrix.v1",
        "status": "SKIPPED",
        "reasonZh": reason,
        "families": sorted(ALLOWED_STRATEGY_FAMILIES),
        "rows": [],
        "summary": {
            "familyCount": len(ALLOWED_STRATEGY_FAMILIES),
            "routeCount": 0,
            "coveredFamilyCount": len(SUPPORTED_BACKTEST_FAMILIES),
            "okRouteCount": 0,
            "tradeRouteCount": 0,
        },
    }


def _multi_strategy_coverage_matrix(bars_by_timeframe: Dict[str, List[Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for family in sorted(ALLOWED_STRATEGY_FAMILIES):
        for direction in ("LONG", "SHORT"):
            seed = base_strategy_seed(f"COVERAGE-{family}-{direction}", family=family, direction=direction)
            try:
                result = run_strategy(seed, bars_by_timeframe)
            except Exception as exc:  # pragma: no cover - defensive audit path
                result = {
                    "ok": False,
                    "metrics": {},
                    "engine": {},
                    "reasonZh": f"coverage runner failed: {exc}",
                }
            metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
            engine = result.get("engine") if isinstance(result.get("engine"), dict) else {}
            trade_count = int(float(metrics.get("tradeCount") or 0))
            ok = bool(result.get("ok"))
            rows.append(
                {
                    "strategyFamily": family,
                    "direction": direction,
                    "runnerCovered": family in SUPPORTED_BACKTEST_FAMILIES,
                    "ok": ok,
                    "status": "PASS" if ok else "FAILED",
                    "tradeCount": trade_count,
                    "netR": metrics.get("netR", 0),
                    "profitFactor": metrics.get("profitFactor", 0),
                    "winRate": metrics.get("winRate", 0),
                    "maxDrawdownR": metrics.get("maxDrawdownR", 0),
                    "sharpe": metrics.get("sharpe", 0),
                    "sortino": metrics.get("sortino", 0),
                    "parityVectorPresent": isinstance(engine.get("parityVector"), dict),
                    "signalCount": engine.get("signalCount", 0),
                    "reasonZh": result.get("reasonZh") or ("covered" if ok else "runner failed"),
                }
            )
    ok_routes = [row for row in rows if row["ok"]]
    trade_routes = [row for row in rows if int(row.get("tradeCount") or 0) > 0]
    return {
        "schema": "quantgod.strategy_backtest_coverage_matrix.v1",
        "status": "PASS" if len(ok_routes) == len(rows) else "WARN",
        "families": sorted(ALLOWED_STRATEGY_FAMILIES),
        "directions": ["LONG", "SHORT"],
        "rows": rows,
        "summary": {
            "familyCount": len(ALLOWED_STRATEGY_FAMILIES),
            "routeCount": len(rows),
            "coveredFamilyCount": len({row["strategyFamily"] for row in ok_routes}),
            "okRouteCount": len(ok_routes),
            "tradeRouteCount": len(trade_routes),
            "parityVectorRouteCount": sum(1 for row in rows if row.get("parityVectorPresent")),
        },
        "reasonZh": "全部 USDJPY Strategy JSON 策略族已进入多策略回测覆盖矩阵；实盘仍只允许 RSI_Reversal LONG。",
    }


def _run_id(strategy: Dict[str, Any], created_at: str) -> str:
    raw = json.dumps(
        {
            "strategyId": strategy.get("strategyId"),
            "seedId": strategy.get("seedId"),
            "createdAt": created_at,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"BT-{digest}"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}
