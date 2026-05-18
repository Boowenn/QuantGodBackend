from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .schema import DEFAULT_STRATEGIES, FOCUS_SYMBOL, is_focus_symbol, normalize_strategy_name, normalize_symbol


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists() and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                mtime = path.stat().st_mtime
                payload.setdefault("_filePath", str(path))
                payload.setdefault("_fileMtimeIso", datetime.fromtimestamp(mtime, timezone.utc).isoformat())
                payload.setdefault("_fileAgeSeconds", max(0.0, time.time() - mtime))
            return payload
    except Exception:
        return None
    return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    for encoding in ("utf-8-sig", "utf-8", "shift_jis", "cp932"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except Exception:
            continue
    return []


def _candidate_paths(runtime_dir: Path, *names: str) -> List[Path]:
    bases = [
        runtime_dir,
        runtime_dir / "adaptive",
        runtime_dir / "quality",
        runtime_dir / "journal",
        runtime_dir / "reports",
        runtime_dir / "history",
        runtime_dir / "datasets" / "usdjpy",
        runtime_dir / "replay" / "usdjpy",
    ]
    paths: List[Path] = []
    for base in bases:
        for name in names:
            paths.append(base / name)
    return paths


def first_json(runtime_dir: Path, *names: str) -> Optional[Dict[str, Any]]:
    for path in _candidate_paths(runtime_dir, *names):
        payload = _read_json(path)
        if payload is not None:
            payload.setdefault("_filePath", str(path))
            return payload
    return None


def _dashboard_fastlane_fallback(runtime_dir: Path) -> Optional[Dict[str, Any]]:
    dashboard = focus_runtime_snapshot(runtime_dir)
    if not dashboard:
        return None
    runtime = dashboard.get("runtime") if isinstance(dashboard.get("runtime"), dict) else {}
    age = to_float(dashboard.get("runtimeAgeSeconds"), 9999.0)
    tick_age = to_float(runtime.get("tickAgeSeconds"), 9999.0)
    fresh_limit = runtime_fresh_limit_seconds()
    if not (bool(dashboard.get("runtimeFresh")) or age <= fresh_limit or tick_age <= 30):
        return None
    return {
        "found": True,
        "quality": "EA_DASHBOARD_OK",
        "focusSymbolFound": True,
        "source": "QuantGod_Dashboard.json",
        "payload": {
            "quality": "EA_DASHBOARD_OK",
            "runtimeAgeSeconds": dashboard.get("runtimeAgeSeconds"),
            "tickAgeSeconds": runtime.get("tickAgeSeconds"),
            "tradeStatus": runtime.get("tradeStatus"),
            "executionEnabled": runtime.get("executionEnabled"),
            "note": "独立快通道未给出可用心跳，已使用 HFM EA Dashboard 新鲜快照作为降级证据。",
        },
    }


def _empty_fastlane_exporter(payload: Dict[str, Any], focus: Optional[Dict[str, Any]]) -> bool:
    if payload.get("heartbeatFound") is not False:
        return False
    row = focus if isinstance(focus, dict) else {}
    tick_rows = to_float(row.get("tickRows"), 0.0)
    return tick_rows <= 0 and row.get("tickAgeSeconds") in (None, "", "null") and row.get("indicatorAgeSeconds") in (None, "", "null")


def _degraded_by_stale_fastlane_exporter(payload: Dict[str, Any], focus: Optional[Dict[str, Any]], quality: str) -> bool:
    """Allow fresh EA Dashboard evidence to replace stale auxiliary fastlane output."""
    pass_states = {"OK", "PASS", "PASSED", "GOOD", "HEALTHY", "FAST", "EA_DASHBOARD_OK"}
    if quality in pass_states:
        return False
    row = focus if isinstance(focus, dict) else {}
    if not row:
        return False
    failed_checks = {
        str(check.get("name") or "")
        for check in row.get("checks", [])
        if isinstance(check, dict) and check.get("passed") is False
    }
    stale_exporter_checks = {"indicator_lane", "tick_fast_lane"}
    if failed_checks and not failed_checks.issubset(stale_exporter_checks):
        return False
    tick_age = to_float(row.get("tickAgeSeconds"), 9999.0)
    tick_rows = to_float(row.get("tickRows"), 0.0)
    heartbeat_limit = to_float(payload.get("heartbeatFreshLimitSeconds"), 90.0)
    heartbeat_age = to_float(payload.get("heartbeatAgeSeconds"), 0.0)
    heartbeat_stale = payload.get("heartbeatFresh") is False or heartbeat_age > heartbeat_limit
    indicator_stale = "indicator_lane" in failed_checks or to_float(row.get("indicatorAgeSeconds"), 0.0) > 30
    tick_lane_stale = "tick_fast_lane" in failed_checks and tick_age <= 30
    return tick_age <= 30 and tick_rows >= 1 and (heartbeat_stale or indicator_stale or tick_lane_stale)


def read_all_csv(runtime_dir: Path, *names: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in _candidate_paths(runtime_dir, *names):
        rows.extend(_read_csv_rows(path))
    return rows


def _get(row: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    if not row:
        return default
    lower = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
        lower_key = key.lower()
        if lower_key in lower and lower[lower_key] not in (None, ""):
            return lower[lower_key]
    return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip().replace("%", "")
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def runtime_fresh_limit_seconds(default: float = 180.0) -> float:
    return max(30.0, to_float(os.environ.get("QG_USDJPY_RUNTIME_FRESH_SECONDS"), default))


def to_direction(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG", "1", "多", "买", "买入"}:
        return "LONG"
    if text in {"SELL", "SHORT", "-1", "空", "卖", "卖出"}:
        return "SHORT"
    return "UNKNOWN"


def normalize_strategy(value: Any) -> str:
    return normalize_strategy_name(value)


def focus_runtime_snapshot(runtime_dir: Path, symbol: str = FOCUS_SYMBOL) -> Optional[Dict[str, Any]]:
    aliases = [symbol, "USDJPY", FOCUS_SYMBOL]
    names = []
    for alias in aliases:
        names.append(f"QuantGod_MT5RuntimeSnapshot_{alias}.json")
    names.append("QuantGod_Dashboard.json")
    payload = first_json(runtime_dir, *names)
    if payload and ("symbol" not in payload or is_focus_symbol(payload.get("symbol") or symbol)):
        if "runtime" in payload and "watchlist" in payload:
            runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
            market = payload.get("market") if isinstance(payload.get("market"), dict) else {}
            payload = dict(payload)
            payload.setdefault("schema", "quantgod.hfm_ea_dashboard_snapshot.v1")
            payload.setdefault("symbol", payload.get("watchlist") or symbol)
            payload.setdefault("fallback", False)
            payload.setdefault("runtimeAgeSeconds", payload.get("_fileAgeSeconds", 9999))
            payload.setdefault("runtimeFresh", float(payload.get("runtimeAgeSeconds", 9999)) <= runtime_fresh_limit_seconds())
            payload.setdefault("current_price", {
                "bid": market.get("bid"),
                "ask": market.get("ask"),
                "spread": market.get("spread"),
            })
            payload.setdefault("tradeStatus", runtime.get("tradeStatus"))
            payload.setdefault("executionEnabled", runtime.get("executionEnabled"))
            payload.setdefault("readOnlyMode", runtime.get("readOnlyMode"))
        return payload
    return None


def fastlane_quality(runtime_dir: Path) -> Dict[str, Any]:
    payload = first_json(runtime_dir, "QuantGod_MT5FastLaneQuality.json") or {}
    quality = str(payload.get("quality") or payload.get("status") or "MISSING").upper()
    symbols = payload.get("symbols")
    focus = None
    if isinstance(symbols, list):
        for item in symbols:
            if isinstance(item, dict) and is_focus_symbol(item.get("symbol")):
                focus = item
                break
    elif isinstance(symbols, dict):
        for row_symbol, item in symbols.items():
            if isinstance(item, dict) and is_focus_symbol(row_symbol):
                focus = dict(item)
                focus.setdefault("symbol", row_symbol)
                break
    if focus:
        quality = str(focus.get("quality") or focus.get("status") or quality).upper()
    if not payload:
        fallback = _dashboard_fastlane_fallback(runtime_dir)
        if fallback:
            return fallback
    elif _empty_fastlane_exporter(payload, focus):
        fallback = _dashboard_fastlane_fallback(runtime_dir)
        if fallback:
            return fallback
    elif _degraded_by_stale_fastlane_exporter(payload, focus, quality):
        fallback = _dashboard_fastlane_fallback(runtime_dir)
        if fallback:
            return fallback
    return {
        "found": bool(payload),
        "quality": quality,
        "focusSymbolFound": bool(focus) or not isinstance(symbols, (list, dict)),
        "payload": payload,
    }


def dynamic_sltp(runtime_dir: Path) -> Dict[str, Any]:
    calibration = first_json(runtime_dir, "QuantGod_DynamicSLTPCalibration.json") or {}
    direction_plan = first_json(runtime_dir, "QuantGod_DynamicSLTPPlan.json") or {}
    if calibration and direction_plan:
        merged = dict(calibration)
        if "dynamicSltpPlans" in direction_plan:
            merged["dynamicSltpPlans"] = direction_plan.get("dynamicSltpPlans") or []
        merged.setdefault("directionPlan", direction_plan)
        return merged
    return calibration or direction_plan or {}


def entry_trigger_plan(runtime_dir: Path) -> Dict[str, Any]:
    return first_json(runtime_dir, "QuantGod_EntryTriggerPlan.json") or {}


def adaptive_policy(runtime_dir: Path) -> Dict[str, Any]:
    return first_json(runtime_dir, "QuantGod_AdaptivePolicy.json", "QuantGod_DynamicEntryGate.json") or {}


def existing_auto_policy(runtime_dir: Path) -> Dict[str, Any]:
    return first_json(runtime_dir, "QuantGod_AutoExecutionPolicy.json") or {}


def load_evidence_rows(runtime_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in read_all_csv(
        runtime_dir,
        "ShadowCandidateOutcomeLedger.csv",
        "QuantGod_ShadowCandidateOutcomeLedger.csv",
        "QuantGod_CloseHistory.csv",
        "QuantGod_CloseHistoryLedger.csv",
        "QuantGod_StrategyEvaluationReport.csv",
        "QuantGod_DynamicSLTPCalibrationLedger.csv",
        "QuantGod_AutoExecutionPolicyLedger.csv",
    ):
        symbol = normalize_symbol(_get(row, "symbol", "Symbol", "SYMBOL", default=FOCUS_SYMBOL))
        if not is_focus_symbol(symbol):
            continue
        direction = to_direction(_get(row, "direction", "side", "Side", "Type", "orderType", "cmd", "signalDirection", "CandidateDirection", "SignalDirection", default="UNKNOWN"))
        strategy = normalize_strategy(_get(row, "strategy", "strategyName", "route", "name", "magicName", "CandidateRoute", "Strategy", default="UNKNOWN_STRATEGY"))
        regime = str(_get(row, "regime", "marketRegime", "state", "Regime", default="UNKNOWN") or "UNKNOWN").strip() or "UNKNOWN"
        timeframe = str(_get(row, "timeframe", "tf", "horizon", "Timeframe", default="UNKNOWN") or "UNKNOWN").strip() or "UNKNOWN"
        pnl = to_float(_get(row, "scoreR", "r", "R", "profitR", "pnlR", default="nan"), default=float("nan"))
        if pnl != pnl:
            pnl = to_float(_get(
                row,
                "DirectionalOutcomePips",
                "DirectionalOutcome",
                "pips",
                "profitPips",
                "netPips",
                "outcomePips",
                "profit",
                "pnl",
                "netProfit",
                default=0.0,
            ))
        mfe = to_float(_get(row, "mfe", "mfePips", "LongMFEPips", "ShortMFEPips", "maxFavorableMove", "maxFavorablePips", default=0.0))
        mae = abs(to_float(_get(row, "mae", "maePips", "LongMAEPips", "ShortMAEPips", "maxAdverseMove", "maxAdversePips", default=0.0)))
        rows.append({
            "symbol": FOCUS_SYMBOL,
            "strategy": strategy if strategy != "UNKNOWN_STRATEGY" else infer_strategy_from_row(row),
            "direction": direction,
            "regime": regime,
            "timeframe": timeframe,
            "pnl": pnl,
            "mfe": mfe,
            "mae": mae,
            "raw": row,
        })
    return rows


def infer_strategy_from_row(row: Dict[str, Any]) -> str:
    text = " ".join(str(v) for v in row.values() if v is not None)
    for strategy in DEFAULT_STRATEGIES:
        if strategy.lower() in text.lower():
            return strategy
    return "UNKNOWN_STRATEGY"


def sample_runtime(runtime_dir: Path, overwrite: bool = False) -> Dict[str, Any]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    adaptive = runtime_dir / "adaptive"
    adaptive.mkdir(parents=True, exist_ok=True)
    snapshot = runtime_dir / f"QuantGod_MT5RuntimeSnapshot_{FOCUS_SYMBOL}.json"
    if overwrite or not snapshot.exists():
        _write_json(snapshot, {
            "schema": "quantgod.mt5.runtime_snapshot.v1",
            "symbol": FOCUS_SYMBOL,
            "source": "hfm_ea_runtime",
            "fallback": False,
            "runtimeFresh": True,
            "runtimeAgeSeconds": 3,
            "current_price": {"bid": 155.12, "ask": 155.14, "spread": 0.02},
            "safety": {"readOnly": True, "orderSendAllowed": False},
        })
    quality = runtime_dir / "quality" / "QuantGod_MT5FastLaneQuality.json"
    quality.parent.mkdir(parents=True, exist_ok=True)
    if overwrite or not quality.exists():
        _write_json(quality, {
            "schema": "quantgod.mt5.fastlane_quality.v1",
            "quality": "OK",
            "symbols": [{"symbol": FOCUS_SYMBOL, "quality": "OK", "tickAgeSeconds": 1, "spreadOk": True}],
        })
    gate = adaptive / "QuantGod_EntryTriggerPlan.json"
    if overwrite or not gate.exists():
        _write_json(gate, {
            "schema": "quantgod.entry_trigger_lab.v1",
            "plans": [
                {"symbol": FOCUS_SYMBOL, "direction": "LONG", "status": "READY_FOR_CONFIRMATION", "triggerScore": 0.86, "missingConfirmations": []},
                {"symbol": FOCUS_SYMBOL, "direction": "SHORT", "status": "BLOCKED", "triggerScore": 0.25, "missingConfirmations": ["方向近期负期望"]},
            ],
        })
    sltp = adaptive / "QuantGod_DynamicSLTPCalibration.json"
    if overwrite or not sltp.exists():
        _write_json(sltp, {
            "schema": "quantgod.dynamic_sltp_calibration.v1",
            "plans": [
                {"symbol": FOCUS_SYMBOL, "strategy": "RSI_Reversal", "direction": "LONG", "status": "CALIBRATED", "initialStopPips": 3.2, "target1Pips": 4.8, "target2Pips": 6.1},
            ],
        })
    ledger = runtime_dir / "ShadowCandidateOutcomeLedger.csv"
    if overwrite or not ledger.exists():
        ledger.write_text(
            "symbol,strategy,direction,regime,timeframe,pips,mfePips,maePips\n"
            "USDJPYc,RSI_Reversal,LONG,TREND_EXP_DOWN,M15,3.2,6.4,1.8\n"
            "USDJPYc,RSI_Reversal,LONG,TREND_EXP_DOWN,M15,2.5,5.1,1.1\n"
            "USDJPYc,RSI_Reversal,LONG,TREND_EXP_DOWN,M15,4.1,7.2,2.0\n"
            "USDJPYc,RSI_Reversal,LONG,TREND_EXP_DOWN,M15,1.7,3.8,1.5\n"
            "USDJPYc,RSI_Reversal,LONG,TREND_EXP_DOWN,M15,2.1,5.0,1.7\n"
            "USDJPYc,RSI_Reversal,SHORT,RANGE,M15,-3.0,1.2,5.2\n"
            "USDJPYc,RSI_Reversal,SHORT,RANGE,M15,-2.2,1.0,4.0\n"
            "USDJPYc,MA_Cross,LONG,TREND_EXP_UP,M15,1.0,2.0,1.5\n"
            "USDJPYc,MA_Cross,LONG,TREND_EXP_UP,M15,0.8,1.9,1.1\n"
            "USDJPYc,MA_Cross,LONG,TREND_EXP_UP,M15,-0.4,1.0,1.7\n",
            encoding="utf-8",
        )
    candidate_outcomes = runtime_dir / "QuantGod_ShadowCandidateOutcomeLedger.csv"
    if overwrite or not candidate_outcomes.exists():
        candidate_outcomes.write_text(
            "EventId,Symbol,CandidateRoute,Timeframe,CandidateDirection,CandidateScore,Regime,DirectionalOutcomePips,LongMFEPips,LongMAEPips,ShortMFEPips,ShortMAEPips\n"
            "TOKYO-1,USDJPYc,USDJPY_TOKYO_RANGE_BREAKOUT,M15,LONG,74,TREND_EXP_UP,5.8,8.6,2.1,1.2,7.2\n"
            "TOKYO-2,USDJPYc,USDJPY_TOKYO_RANGE_BREAKOUT,M15,LONG,72,TREND_EXP_UP,4.1,6.5,1.9,1.0,5.4\n"
            "TOKYO-3,USDJPYc,USDJPY_TOKYO_RANGE_BREAKOUT,M15,LONG,70,TREND_EXP_UP,-1.2,2.0,3.4,3.4,2.0\n"
            "TOKYO-4,USDJPYc,USDJPY_TOKYO_RANGE_BREAKOUT,M15,LONG,73,TREND_EXP_UP,3.7,5.0,1.5,1.1,4.3\n"
            "TOKYO-5,USDJPYc,USDJPY_TOKYO_RANGE_BREAKOUT,M15,LONG,76,TREND_EXP_UP,6.2,8.0,2.4,1.3,7.1\n"
            "NIGHT-1,USDJPYc,USDJPY_NIGHT_REVERSION_SAFE,M15,SHORT,64,RANGE,1.2,1.4,1.1,4.0,1.2\n"
            "NIGHT-2,USDJPYc,USDJPY_NIGHT_REVERSION_SAFE,M15,SHORT,63,RANGE,-0.8,0.9,1.6,2.1,1.8\n"
            "NIGHT-3,USDJPYc,USDJPY_NIGHT_REVERSION_SAFE,M15,SHORT,60,RANGE,0.9,1.1,1.0,2.0,1.4\n"
            "NIGHT-4,USDJPYc,USDJPY_NIGHT_REVERSION_SAFE,M15,SHORT,61,RANGE,1.0,1.0,1.2,2.4,1.1\n"
            "NIGHT-5,USDJPYc,USDJPY_NIGHT_REVERSION_SAFE,M15,SHORT,62,RANGE,-1.4,0.6,2.4,1.0,2.8\n"
            "H4-1,USDJPYc,USDJPY_H4_TREND_PULLBACK,M15,LONG,70,TREND_EXP_UP,3.0,4.2,1.6,1.0,3.9\n"
            "H4-2,USDJPYc,USDJPY_H4_TREND_PULLBACK,M15,LONG,71,TREND_EXP_UP,2.4,3.8,1.4,0.9,3.5\n"
            "H4-3,USDJPYc,USDJPY_H4_TREND_PULLBACK,M15,LONG,69,TREND_EXP_UP,1.9,3.1,1.3,0.8,2.7\n"
            "H4-4,USDJPYc,USDJPY_H4_TREND_PULLBACK,M15,LONG,70,TREND_EXP_UP,-0.6,1.2,2.0,2.0,1.1\n"
            "H4-5,USDJPYc,USDJPY_H4_TREND_PULLBACK,M15,LONG,72,TREND_EXP_UP,3.5,4.7,1.5,0.8,4.1\n",
            encoding="utf-8",
        )
    candidate_ledger = runtime_dir / "QuantGod_ShadowCandidateLedger.csv"
    if overwrite or not candidate_ledger.exists():
        candidate_ledger.write_text(
            "EventId,LabelTimeLocal,EventBarTime,Symbol,CandidateRoute,Timeframe,CandidateDirection,CandidateScore,Regime,ReferencePrice,SpreadPips,Trigger,Reason\n"
            "SIG-TOKYO,2026.05.05 12:15,2026.05.05 12:15,USDJPYc,USDJPY_TOKYO_RANGE_BREAKOUT,M15,BUY,74,TREND_EXP_UP,155.12,0.8,JST box breakout,shadow-only Tokyo range breakout\n"
            "SIG-NIGHT,2026.05.05 23:45,2026.05.05 23:45,USDJPYc,USDJPY_NIGHT_REVERSION_SAFE,M15,SELL,64,RANGE,155.40,0.7,night band reversion,shadow-only night reversion\n"
            "SIG-H4,2026.05.05 14:30,2026.05.05 14:30,USDJPYc,USDJPY_H4_TREND_PULLBACK,M15,BUY,70,TREND_EXP_UP,155.18,0.8,H4 trend pullback,shadow-only H4 pullback\n",
            encoding="utf-8",
        )
    return {"ok": True, "runtimeDir": str(runtime_dir), "focusSymbol": FOCUS_SYMBOL}
