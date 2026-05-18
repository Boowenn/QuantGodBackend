from __future__ import annotations

import csv
import importlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .schema import AGENT_VERSION, FOCUS_SYMBOL, SAFETY_BOUNDARY, history_sync_report_path, production_status_path
from .sqlite_store import (
    Bar,
    bar_coverage_summary,
    connect,
    count_bars,
    earliest_bar_time,
    ingest_runtime_snapshot,
    latest_bar_time,
    upsert_bars,
)

DEFAULT_HISTORY_TIMEFRAMES = ("M1", "M5", "M15", "H1")
SUPPORTED_HISTORY_TIMEFRAMES = ("M1", "M5", "M15", "H1", "H4")
TIMEFRAME_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400}
MT5_TIMEFRAME_ATTRS = {
    "M1": "TIMEFRAME_M1",
    "M5": "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "H1": "TIMEFRAME_H1",
    "H4": "TIMEFRAME_H4",
}
CHUNK_DAYS = {"M1": 21, "M5": 60, "M15": 120, "H1": 180, "H4": 372}
MQL5_EXPORT_SOURCE = "MQL5_COPYRATES_EXPORT_FALLBACK"
DEFAULT_MAX_LATEST_LAG_HOURS = 96
MAX_FUTURE_BAR_SKEW_HOURS = 24.0


def sync_historical_klines(
    runtime_dir: Path,
    *,
    months: int = 12,
    lookback_days: int | None = None,
    timeframes: Iterable[str] | None = None,
    symbol: str | None = None,
    terminal_path: str | None = None,
    full_refresh: bool = False,
    max_bars_per_timeframe: int = 700000,
    max_latest_lag_hours: float | None = None,
    write: bool = True,
) -> Dict[str, Any]:
    """Incrementally sync real USDJPY bars from the local MT5 terminal into SQLite."""
    runtime_dir = Path(runtime_dir)
    selected_timeframes = _normalize_timeframes(timeframes)
    target_days = int(lookback_days or max(180, int(months) * 31))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    target_start = now - timedelta(days=target_days)
    allowed_lag_hours = float(
        max_latest_lag_hours
        if max_latest_lag_hours is not None
        else os.environ.get("QG_USDJPY_HISTORY_MAX_LAG_HOURS", DEFAULT_MAX_LATEST_LAG_HOURS)
    )
    mt5_symbol = symbol or os.environ.get("QG_USDJPY_MT5_SYMBOL") or FOCUS_SYMBOL
    terminal = terminal_path or os.environ.get("QG_MT5_TERMINAL_PATH") or ""
    mt5, mt5_status = _load_mt5(terminal)
    report: Dict[str, Any] = {
        "ok": False,
        "schema": "quantgod.usdjpy_historical_kline_sync_report.v1",
        "agentVersion": "perfect-v1.0",
        "symbol": FOCUS_SYMBOL,
        "sourceSymbol": mt5_symbol,
        "source": "MT5_COPY_RATES_RANGE",
        "timeframes": selected_timeframes,
        "targetLookbackDays": target_days,
        "targetStart": _iso(target_start),
        "targetEnd": _iso(now),
        "fullRefresh": bool(full_refresh),
        "maxBarsPerTimeframe": int(max_bars_per_timeframe),
        "maxLatestLagHours": allowed_lag_hours,
        "mt5": mt5_status,
        "sync": {},
        "fallback": {},
        "safety": dict(SAFETY_BOUNDARY),
    }
    try:
        if mt5 is not None:
            _select_symbol(mt5, mt5_symbol)
            with connect(runtime_dir) as conn:
                report["sync"] = _sync_from_mt5(
                    conn=conn,
                    mt5=mt5,
                    symbol=mt5_symbol,
                    timeframes=selected_timeframes,
                    target_start=target_start,
                    target_end=now,
                    full_refresh=full_refresh,
                    max_bars_per_timeframe=max_bars_per_timeframe,
                )
                report["historyCoverage"] = bar_coverage_summary(conn)
            report["ok"] = any(item.get("receivedBars", 0) > 0 for item in report["sync"].values())
            report["historyTargetSatisfied"] = _target_satisfied(report.get("historyCoverage", {}), target_days)
            report["productionStatus"] = build_history_production_status(
                runtime_dir,
                sync_report=report,
                target_days=target_days,
                max_latest_lag_hours=allowed_lag_hours,
                now=now,
            )
            report["reasonZh"] = _reason(report)
        else:
            export_report = ingest_mql5_exported_klines(
                runtime_dir,
                timeframes=selected_timeframes,
                symbol=mt5_symbol,
            )
            if export_report.get("ok"):
                report["source"] = MQL5_EXPORT_SOURCE
                report["fallback"] = {"mql5Export": export_report}
                with connect(runtime_dir) as conn:
                    report["historyCoverage"] = bar_coverage_summary(conn)
                report["ok"] = True
                report["historyTargetSatisfied"] = _target_satisfied(report.get("historyCoverage", {}), target_days)
                report["productionStatus"] = build_history_production_status(
                    runtime_dir,
                    sync_report=report,
                    target_days=target_days,
                    max_latest_lag_hours=allowed_lag_hours,
                    now=now,
                )
                report["reasonZh"] = _reason(report)
            else:
                report["source"] = "RUNTIME_SNAPSHOT_FALLBACK"
                report["fallback"] = {
                    "mql5Export": export_report,
                    "runtimeSnapshot": ingest_runtime_snapshot(runtime_dir),
                }
                with connect(runtime_dir) as conn:
                    report["historyCoverage"] = bar_coverage_summary(conn)
                report["ok"] = bool(report["fallback"]["runtimeSnapshot"].get("ok"))
                report["historyTargetSatisfied"] = False
                report["productionStatus"] = build_history_production_status(
                    runtime_dir,
                    sync_report=report,
                    target_days=target_days,
                    max_latest_lag_hours=allowed_lag_hours,
                    now=now,
                )
                report["reasonZh"] = (
                    "未连接到本机 MT5 Python 历史数据源，也未发现 MQL5 CopyRates 导出；"
                    "已回退到运行快照增量写入，GA 历史样本仍不足。"
                )
    finally:
        _shutdown_mt5(mt5)
    if write:
        history_sync_report_path(runtime_dir).parent.mkdir(parents=True, exist_ok=True)
        history_sync_report_path(runtime_dir).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        production_status_path(runtime_dir).write_text(
            json.dumps(report.get("productionStatus") or {}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


def ingest_mql5_exported_klines(
    runtime_dir: Path,
    *,
    timeframes: Iterable[str] | None = None,
    symbol: str | None = None,
) -> Dict[str, Any]:
    """Ingest read-only MQL5 CopyRates CSV exports into the USDJPY SQLite store."""
    runtime_dir = Path(runtime_dir)
    selected_timeframes = _normalize_timeframes(timeframes)
    source_symbol = symbol or os.environ.get("QG_USDJPY_MT5_SYMBOL") or FOCUS_SYMBOL
    export_dir_candidates = _candidate_export_dirs(runtime_dir)
    export_dir = _select_export_dir(export_dir_candidates)
    manifest = _load_export_manifest(runtime_dir, export_dir) if export_dir else {}
    report: Dict[str, Any] = {
        "ok": False,
        "schema": "quantgod.mql5_copyrates_export_ingest_report.v1",
        "source": "MQL5_COPYRATES_EXPORT",
        "symbol": FOCUS_SYMBOL,
        "sourceSymbol": source_symbol,
        "exportDir": str(export_dir) if export_dir else "",
        "exportDirCandidates": [str(item) for item in export_dir_candidates],
        "manifest": manifest,
        "timeframes": {},
        "safety": dict(SAFETY_BOUNDARY),
    }
    if export_dir is None or not export_dir.exists():
        report["reasonZh"] = "未发现 MQL5 CopyRates 导出目录，等待 EA/脚本写入 K 线 CSV。"
        return report

    any_rows = False
    with connect(runtime_dir) as conn:
        for timeframe in selected_timeframes:
            file_path = _find_mql5_export_file(export_dir, source_symbol, timeframe)
            before_count = count_bars(conn, timeframe)
            bars: List[Bar] = []
            errors: List[str] = []
            if file_path is None:
                errors.append(f"missing export csv for {timeframe}")
            else:
                bars, errors = _read_mql5_export_csv(file_path)
                if bars:
                    upsert_bars(conn, timeframe, bars)
                    any_rows = True
            after_count = count_bars(conn, timeframe)
            report["timeframes"][timeframe] = {
                "timeframe": timeframe,
                "file": str(file_path) if file_path else "",
                "rowsRead": len(bars),
                "barCountBefore": before_count,
                "barCountAfter": after_count,
                "newBarDelta": max(0, after_count - before_count),
                "earliestBar": earliest_bar_time(conn, timeframe),
                "latestBar": latest_bar_time(conn, timeframe),
                "errors": errors[:5],
            }
        report["historyCoverage"] = bar_coverage_summary(conn)
    report["ok"] = any_rows
    report["reasonZh"] = (
        "已从 MQL5/Files 的 CopyRates CSV 导出增量写入 USDJPY SQLite。"
        if any_rows
        else "发现 MQL5 导出目录，但没有可用 USDJPY K 线 CSV。"
    )
    return report


def build_history_production_status(
    runtime_dir: Path,
    *,
    sync_report: Dict[str, Any] | None = None,
    target_days: int = 372,
    max_latest_lag_hours: float = DEFAULT_MAX_LATEST_LAG_HOURS,
    now: datetime | None = None,
) -> Dict[str, Any]:
    """Build a verifiable production readiness snapshot for USDJPY SQLite history."""
    runtime_dir = Path(runtime_dir)
    sync_report = sync_report if isinstance(sync_report, dict) else {}
    checked_at = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    required_span_days = max(1.0, float(target_days) * 0.85)
    with connect(runtime_dir) as conn:
        coverage = bar_coverage_summary(conn)
    rows: Dict[str, Any] = {}
    failed: List[Dict[str, Any]] = []
    for timeframe in DEFAULT_HISTORY_TIMEFRAMES:
        row = coverage.get("timeframes", {}).get(timeframe, {})
        latest = _parse_iso(row.get("latestBar"))
        latest_lag_hours, future_skew_hours = _latest_lag_and_future_skew(
            checked_at,
            latest,
        )
        expected_bars = _expected_min_bars(required_span_days, timeframe)
        bar_count = int(row.get("barCount") or 0)
        span_days = float(row.get("spanDays") or 0.0)
        span_ok = span_days >= required_span_days
        density_ok = bar_count >= expected_bars
        freshness_ok = latest_lag_hours is not None and latest_lag_hours <= float(max_latest_lag_hours)
        passed = span_ok and density_ok and freshness_ok
        rows[timeframe] = {
            "timeframe": timeframe,
            "barCount": bar_count,
            "expectedMinBars": expected_bars,
            "earliestBar": row.get("earliestBar"),
            "latestBar": row.get("latestBar"),
            "spanDays": span_days,
            "requiredSpanDays": round(required_span_days, 3),
            "latestLagHours": latest_lag_hours,
            "futureSkewHours": future_skew_hours,
            "maxLatestLagHours": float(max_latest_lag_hours),
            "spanOk": span_ok,
            "densityOk": density_ok,
            "freshnessOk": freshness_ok,
            "passed": passed,
            "reasonZh": _timeframe_production_reason(timeframe, span_ok, density_ok, freshness_ok, span_days, bar_count, expected_bars),
        }
        if not passed:
            failed.append(rows[timeframe])
    source = str(sync_report.get("source") or "UNKNOWN")
    mql5_export = {}
    fallback = sync_report.get("fallback") if isinstance(sync_report.get("fallback"), dict) else {}
    if isinstance(fallback.get("mql5Export"), dict):
        mql5_export = fallback["mql5Export"]
    status = "PASS" if not failed and bool(sync_report.get("ok", True)) else "WARN"
    return {
        "ok": status == "PASS",
        "schema": "quantgod.usdjpy_history_production_status.v1",
        "agentVersion": AGENT_VERSION,
        "generatedAt": _iso(checked_at),
        "symbol": FOCUS_SYMBOL,
        "targetLookbackDays": int(target_days),
        "requiredSpanDays": round(required_span_days, 3),
        "maxLatestLagHours": float(max_latest_lag_hours),
        "status": status,
        "historyTargetSatisfied": status == "PASS",
        "failedCount": len(failed),
        "timeframes": rows,
        "source": {
            "syncSource": source,
            "sqlite": str((runtime_dir / "backtest" / "usdjpy.sqlite").resolve()),
            "runtimeDir": str(runtime_dir.resolve()),
            "mql5ExportDir": mql5_export.get("exportDir") or "",
            "mt5PythonStatus": (sync_report.get("mt5") if isinstance(sync_report.get("mt5"), dict) else {}).get("status"),
            "mql5ExportOk": bool(mql5_export.get("ok")),
        },
        "continuousSync": {
            "expected": True,
            "intervalSeconds": int(float(os.environ.get("QG_USDJPY_HISTORY_INTERVAL_SECONDS", "3600"))),
            "script": "tools/run_mac_usdjpy_history_sync_loop.sh --loop",
            "launchdService": "com.quantgod.usdjpy-history-sync",
            "reasonZh": "后台应每小时刷新 sync-klines 与 quality，保持 SQLite 和 MT5 CopyRates 导出同步。",
        },
        "reasonZh": (
            "USDJPY SQLite 历史数据生产状态通过：M1/M5/M15/H1 覆盖、密度和最新延迟均满足目标。"
            if status == "PASS"
            else "USDJPY SQLite 历史数据仍未达到生产验收；请继续运行 MQL5 CopyRates exporter 与后台 sync-klines。"
        ),
        "safety": dict(SAFETY_BOUNDARY),
    }


def _sync_from_mt5(
    *,
    conn: Any,
    mt5: Any,
    symbol: str,
    timeframes: List[str],
    target_start: datetime,
    target_end: datetime,
    full_refresh: bool,
    max_bars_per_timeframe: int,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for timeframe in timeframes:
        before_count = count_bars(conn, timeframe)
        start = _sync_start(conn, timeframe, target_start, full_refresh)
        received = 0
        chunks = 0
        errors: List[str] = []
        cursor = start
        while cursor < target_end and received < max_bars_per_timeframe:
            chunk_end = min(target_end, cursor + timedelta(days=CHUNK_DAYS.get(timeframe, 90)))
            bars, error = _copy_rates(mt5, symbol, timeframe, cursor, chunk_end)
            chunks += 1
            if error:
                errors.append(error)
            if bars:
                remaining = max_bars_per_timeframe - received
                selected = bars[:remaining]
                upsert_bars(conn, timeframe, selected)
                received += len(selected)
            cursor = chunk_end + timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
        after_count = count_bars(conn, timeframe)
        result[timeframe] = {
            "timeframe": timeframe,
            "requestedStart": _iso(start),
            "requestedEnd": _iso(target_end),
            "chunkCount": chunks,
            "receivedBars": received,
            "barCountBefore": before_count,
            "barCountAfter": after_count,
            "newBarDelta": max(0, after_count - before_count),
            "earliestBar": earliest_bar_time(conn, timeframe),
            "latestBar": latest_bar_time(conn, timeframe),
            "errors": errors[:5],
        }
    return result


def _sync_start(conn: Any, timeframe: str, target_start: datetime, full_refresh: bool) -> datetime:
    if full_refresh:
        return target_start
    earliest = _parse_iso(earliest_bar_time(conn, timeframe))
    latest = _parse_iso(latest_bar_time(conn, timeframe))
    if earliest is None or latest is None:
        return target_start
    if earliest > target_start + timedelta(days=2):
        return target_start
    overlap = timedelta(seconds=TIMEFRAME_SECONDS[timeframe] * 2)
    return max(target_start, latest - overlap)


def _copy_rates(mt5: Any, symbol: str, timeframe: str, start: datetime, end: datetime) -> Tuple[List[Bar], str | None]:
    try:
        rates = mt5.copy_rates_range(symbol, _mt5_timeframe(mt5, timeframe), start, end)
    except Exception as exc:
        return [], f"copy_rates_range failed: {exc}"
    if rates is None:
        return [], f"copy_rates_range returned no data: {_last_error(mt5)}"
    bars = _rates_to_bars(rates)
    return bars, None


def _rates_to_bars(rates: Any) -> List[Bar]:
    bars: List[Bar] = []
    for row in list(rates):
        timestamp = _row_value(row, "time")
        if timestamp is None:
            continue
        try:
            bars.append(
                Bar(
                    timestamp=_epoch_to_iso(timestamp),
                    open=float(_row_value(row, "open")),
                    high=float(_row_value(row, "high")),
                    low=float(_row_value(row, "low")),
                    close=float(_row_value(row, "close")),
                    volume=float(_row_value(row, "tick_volume", _row_value(row, "real_volume", 0)) or 0),
                    spread=float(_row_value(row, "spread", 0) or 0),
                    real_volume=float(_row_value(row, "real_volume", 0) or 0),
                )
            )
        except Exception:
            continue
    return sorted(bars, key=lambda item: item.timestamp)


def _load_export_manifest(runtime_dir: Path, export_dir: Path) -> Dict[str, Any]:
    for path in (
        export_dir / "QuantGod_USDJPY_KlineExportManifest.json",
        runtime_dir / "QuantGod_USDJPYKlineExportManifest.json",
    ):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {"unreadablePath": str(path)}
    return {}


def _candidate_export_dirs(runtime_dir: Path) -> List[Path]:
    candidates: List[Path] = []
    roots: List[Path] = [Path(runtime_dir)]
    env_mt5_files = os.environ.get("QG_MT5_FILES_DIR") or ""
    if env_mt5_files:
        roots.append(Path(env_mt5_files).expanduser())
    roots.append(_default_mac_mt5_files_dir())
    seen: set[str] = set()
    for root in roots:
        export_dir = (root / "backtest" / "exported_klines").resolve()
        key = str(export_dir)
        if key not in seen:
            candidates.append(export_dir)
            seen.add(key)
    return candidates


def _select_export_dir(candidates: List[Path]) -> Path | None:
    existing = [item for item in candidates if item.exists()]
    if not existing:
        return None
    for item in existing:
        if (item / "QuantGod_USDJPY_KlineExportManifest.json").exists() or list(item.glob("QuantGod_*USDJPY*_*_rates.csv")):
            return item
    return existing[0]


def _default_mac_mt5_files_dir() -> Path:
    return (
        Path.home()
        / "Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/MQL5/Files"
    )


def _find_mql5_export_file(export_dir: Path, source_symbol: str, timeframe: str) -> Path | None:
    candidates = [
        export_dir / f"QuantGod_{_safe_export_symbol(source_symbol)}_{timeframe}_rates.csv",
        export_dir / f"QuantGod_{_safe_export_symbol(FOCUS_SYMBOL)}_{timeframe}_rates.csv",
        export_dir / f"QuantGod_USDJPY_{timeframe}_rates.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(export_dir.glob(f"QuantGod_*USDJPY*_{timeframe}_rates.csv"))
    return matches[-1] if matches else None


def _safe_export_symbol(symbol: str) -> str:
    value = str(symbol or FOCUS_SYMBOL)
    for old in ("\\", "/", ":", " "):
        value = value.replace(old, "_")
    return value


def _read_mql5_export_csv(path: Path) -> Tuple[List[Bar], List[str]]:
    bars: List[Bar] = []
    errors: List[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_index, row in enumerate(reader, start=2):
                try:
                    timestamp = _export_row_timestamp(row)
                    if not timestamp:
                        continue
                    bars.append(
                        Bar(
                            timestamp=timestamp,
                            open=float(row.get("open") or 0),
                            high=float(row.get("high") or 0),
                            low=float(row.get("low") or 0),
                            close=float(row.get("close") or 0),
                            volume=float(row.get("tick_volume") or row.get("volume") or row.get("real_volume") or 0),
                            spread=float(row.get("spread") or 0),
                            real_volume=float(row.get("real_volume") or 0),
                        )
                    )
                except Exception as exc:
                    if len(errors) < 5:
                        errors.append(f"{path.name}:{row_index}: {exc}")
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
    except Exception as exc:
        errors.append(f"read failed: {exc}")
    return sorted(bars, key=lambda item: item.timestamp), errors


def _export_row_timestamp(row: Dict[str, Any]) -> str | None:
    epoch = row.get("epoch") or row.get("time")
    if epoch not in (None, ""):
        return _epoch_to_iso(epoch)
    raw = str(row.get("timestamp") or "").strip()
    if not raw:
        return None
    parsed = _parse_iso(raw)
    if parsed is not None:
        return _iso(parsed)
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return _iso(datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc))
        except Exception:
            continue
    return None


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, default)


def _load_mt5(terminal_path: str) -> Tuple[Any | None, Dict[str, Any]]:
    try:
        mt5 = importlib.import_module("MetaTrader5")
    except Exception as exc:
        return None, {"ok": False, "status": "PACKAGE_UNAVAILABLE", "detail": str(exc)}
    try:
        initialized = bool(mt5.initialize(path=terminal_path)) if terminal_path else bool(mt5.initialize())
    except Exception as exc:
        return None, {"ok": False, "status": "INITIALIZE_FAILED", "detail": str(exc)}
    if not initialized:
        return None, {"ok": False, "status": "INITIALIZE_FAILED", "detail": _last_error(mt5)}
    return mt5, {"ok": True, "status": "INITIALIZED", "terminalPath": terminal_path or "default"}


def _shutdown_mt5(mt5: Any | None) -> None:
    if mt5 is None:
        return
    try:
        mt5.shutdown()
    except Exception:
        return


def _select_symbol(mt5: Any, symbol: str) -> None:
    try:
        mt5.symbol_select(symbol, True)
    except Exception:
        return


def _mt5_timeframe(mt5: Any, timeframe: str) -> Any:
    return getattr(mt5, MT5_TIMEFRAME_ATTRS[timeframe])


def _last_error(mt5: Any) -> str:
    try:
        return str(mt5.last_error())
    except Exception:
        return ""


def _normalize_timeframes(timeframes: Iterable[str] | None) -> List[str]:
    raw = list(timeframes or DEFAULT_HISTORY_TIMEFRAMES)
    selected: List[str] = []
    for item in raw:
        value = str(item).strip().upper()
        if value in SUPPORTED_HISTORY_TIMEFRAMES and value not in selected:
            selected.append(value)
    return selected or list(DEFAULT_HISTORY_TIMEFRAMES)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _latest_lag_and_future_skew(
    checked_at: datetime,
    latest: datetime | None,
) -> tuple[float | None, float | None]:
    if latest is None:
        return None, None
    lag_hours = (checked_at - latest).total_seconds() / 3600.0
    if lag_hours >= 0:
        return round(lag_hours, 3), 0.0
    future_skew_hours = round(abs(lag_hours), 3)
    if future_skew_hours <= MAX_FUTURE_BAR_SKEW_HOURS:
        return 0.0, future_skew_hours
    return None, future_skew_hours


def _epoch_to_iso(value: Any) -> str:
    timestamp = float(value)
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _target_satisfied(history_coverage: Dict[str, Any], target_days: int) -> bool:
    timeframes = history_coverage.get("timeframes") if isinstance(history_coverage.get("timeframes"), dict) else {}
    required_days = min(float(target_days) * 0.85, float(target_days) - 7)
    if required_days < 150:
        required_days = 150
    for timeframe in DEFAULT_HISTORY_TIMEFRAMES:
        data = timeframes.get(timeframe) if isinstance(timeframes.get(timeframe), dict) else {}
        if float(data.get("spanDays") or 0) < required_days:
            return False
        if int(data.get("barCount") or 0) <= 0:
            return False
    return True


def _expected_min_bars(required_span_days: float, timeframe: str) -> int:
    # FX has weekend gaps and broker maintenance gaps; 45% of wall-clock bars is
    # conservative enough for a 6-12 month production-history readiness check.
    seconds = TIMEFRAME_SECONDS[timeframe]
    return max(1, int((float(required_span_days) * 86400.0 / float(seconds)) * 0.45))


def _timeframe_production_reason(
    timeframe: str,
    span_ok: bool,
    density_ok: bool,
    freshness_ok: bool,
    span_days: float,
    bar_count: int,
    expected_bars: int,
) -> str:
    if span_ok and density_ok and freshness_ok:
        return f"{timeframe} 历史覆盖、K线密度和最新延迟均通过。"
    parts: List[str] = []
    if not span_ok:
        parts.append(f"覆盖天数不足：{span_days} 天")
    if not density_ok:
        parts.append(f"K线数量不足：{bar_count}/{expected_bars}")
    if not freshness_ok:
        parts.append("最新 K 线延迟超出阈值")
    return "；".join(parts) or f"{timeframe} 未通过生产验收。"


def _reason(report: Dict[str, Any]) -> str:
    if report.get("historyTargetSatisfied"):
        return "USDJPY M1/M5/M15/H1 历史 K 线已完成 6-12 个月级别增量同步，可用于更可信 GA 回测。"
    if report.get("ok"):
        return "USDJPY 历史 K 线已增量同步，但覆盖窗口还未达到目标；后续定时同步会继续补齐。"
    return "未从 MT5 拉取到 USDJPY 历史 K 线；请确认本机 MT5/HFM 终端已登录并允许 Python copy_rates_range。"
