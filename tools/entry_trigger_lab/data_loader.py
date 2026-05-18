from __future__ import annotations
import csv, json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            mtime = path.stat().st_mtime
            payload.setdefault("_filePath", str(path))
            payload.setdefault("_fileMtimeIso", datetime.fromtimestamp(mtime, timezone.utc).isoformat())
            payload.setdefault("_fileAgeSeconds", max(0.0, time.time() - mtime))
        return payload
    except Exception:
        return None

def read_csv_rows(path: Path, limit: int = 5000) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    rows: List[Dict[str, str]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append({str(k): str(v) for k, v in row.items()})
                if len(rows) >= limit:
                    break
    except Exception:
        return []
    return rows

def discover_runtime_snapshot(runtime_dir: Path, symbol: str) -> Optional[Dict[str, Any]]:
    for candidate in [runtime_dir / f"QuantGod_MT5RuntimeSnapshot_{symbol}.json", runtime_dir / f"QuantGod_RuntimeSnapshot_{symbol}.json", runtime_dir / "QuantGod_Dashboard.json"]:
        payload = read_json(candidate)
        if payload:
            if candidate.name == "QuantGod_Dashboard.json":
                runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
                market = payload.get("market") if isinstance(payload.get("market"), dict) else {}
                payload = dict(payload)
                payload.setdefault("symbol", payload.get("watchlist") or symbol)
                payload.setdefault("fallback", False)
                payload.setdefault("runtimeAgeSeconds", payload.get("_fileAgeSeconds", 9999))
                tick_age = runtime.get("tickAgeSeconds")
                try:
                    tick_fresh = tick_age is not None and float(tick_age) <= 30
                except Exception:
                    tick_fresh = False
                payload.setdefault("runtimeFresh", float(payload.get("runtimeAgeSeconds", 9999)) <= 300 or tick_fresh)
                payload.setdefault("current_price", {"bid": market.get("bid"), "ask": market.get("ask"), "spread": market.get("spread")})
                payload.setdefault("tradeStatus", runtime.get("tradeStatus"))
                payload.setdefault("executionEnabled", runtime.get("executionEnabled"))
                payload.setdefault("readOnlyMode", runtime.get("readOnlyMode"))
            return payload
    return None

def _fresh_dashboard_fallback(runtime_dir: Path, symbol: str) -> Dict[str, Any]:
    dashboard = discover_runtime_snapshot(runtime_dir, symbol) or {}
    if not dashboard:
        return {}
    runtime = dashboard.get("runtime") if isinstance(dashboard.get("runtime"), dict) else {}
    age = dashboard.get("runtimeAgeSeconds", dashboard.get("_fileAgeSeconds", 9999))
    try:
        age_ok = float(age) <= 300
    except Exception:
        age_ok = False
    try:
        tick_ok = runtime.get("tickAgeSeconds") is not None and float(runtime.get("tickAgeSeconds")) <= 30
    except Exception:
        tick_ok = False
    if not (dashboard.get("runtimeFresh") is True or age_ok or tick_ok):
        return {}
    return {
        "found": True,
        "focusSymbolFound": True,
        "symbol": symbol,
        "quality": "EA_DASHBOARD_OK",
        "state": "EA_DASHBOARD_OK",
        "source": "QuantGod_Dashboard.json",
        "note": "独立快通道未给出可用心跳，使用 HFM EA Dashboard 新鲜快照作为降级证据。",
    }

def _empty_fastlane_exporter(payload: Dict[str, Any], item: Optional[Dict[str, Any]]) -> bool:
    if payload.get("heartbeatFound") is not False:
        return False
    row = item if isinstance(item, dict) else {}
    try:
        tick_rows = float(row.get("tickRows") or 0)
    except Exception:
        tick_rows = 0.0
    return tick_rows <= 0 and row.get("tickAgeSeconds") in (None, "", "null") and row.get("indicatorAgeSeconds") in (None, "", "null")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _degraded_by_stale_fastlane_exporter(payload: Dict[str, Any], item: Optional[Dict[str, Any]]) -> bool:
    row = item if isinstance(item, dict) else {}
    quality = str(row.get("quality") or row.get("state") or payload.get("quality") or "MISSING").upper()
    if quality in {"OK", "PASS", "PASSED", "GOOD", "HEALTHY", "FAST", "EA_DASHBOARD_OK"}:
        return False
    failed_checks = {
        str(check.get("name") or "")
        for check in row.get("checks", [])
        if isinstance(check, dict) and check.get("passed") is False
    }
    stale_exporter_checks = {"indicator_lane", "tick_fast_lane"}
    if failed_checks and not failed_checks.issubset(stale_exporter_checks):
        return False
    tick_age = _as_float(row.get("tickAgeSeconds"), 9999.0)
    tick_rows = _as_float(row.get("tickRows"), 0.0)
    heartbeat_limit = _as_float(payload.get("heartbeatFreshLimitSeconds"), 90.0)
    heartbeat_age = _as_float(payload.get("heartbeatAgeSeconds"), 0.0)
    heartbeat_stale = payload.get("heartbeatFresh") is False or heartbeat_age > heartbeat_limit
    indicator_stale = "indicator_lane" in failed_checks or _as_float(row.get("indicatorAgeSeconds"), 0.0) > 30
    tick_lane_stale = "tick_fast_lane" in failed_checks and tick_age <= 30
    return tick_age <= 30 and tick_rows >= 1 and (heartbeat_stale or indicator_stale or tick_lane_stale)


def discover_fastlane_quality(runtime_dir: Path, symbol: str) -> Dict[str, Any]:
    for candidate in [runtime_dir / "quality" / "QuantGod_MT5FastLaneQuality.json", runtime_dir / "QuantGod_MT5FastLaneQuality.json"]:
        payload = read_json(candidate)
        if not payload:
            continue
        symbols = payload.get("symbols")
        if isinstance(symbols, dict):
            for row_symbol, row_payload in symbols.items():
                if not isinstance(row_payload, dict):
                    continue
                key = str(row_symbol or "")
                if key == symbol or key.upper().startswith("USDJPY"):
                    item = dict(row_payload)
                    item.setdefault("symbol", key or symbol)
                    item.setdefault("found", True)
                    item.setdefault("focusSymbolFound", True)
                    if _empty_fastlane_exporter(payload, item):
                        fallback = _fresh_dashboard_fallback(runtime_dir, symbol)
                        if fallback:
                            return fallback
                    if _degraded_by_stale_fastlane_exporter(payload, item):
                        fallback = _fresh_dashboard_fallback(runtime_dir, symbol)
                        if fallback:
                            return fallback
                    return item
            return {}
        if isinstance(symbols, list):
            for item in symbols:
                if not isinstance(item, dict):
                    continue
                row_symbol = str(item.get("symbol") or "")
                if row_symbol == symbol or row_symbol.upper().startswith("USDJPY"):
                    result = dict(item)
                    result.setdefault("found", True)
                    result.setdefault("focusSymbolFound", True)
                    result.setdefault("sourceQuality", payload.get("quality"))
                    if _empty_fastlane_exporter(payload, result):
                        fallback = _fresh_dashboard_fallback(runtime_dir, symbol)
                        if fallback:
                            return fallback
                    if _degraded_by_stale_fastlane_exporter(payload, result):
                        fallback = _fresh_dashboard_fallback(runtime_dir, symbol)
                        if fallback:
                            return fallback
                    return result
            return {}
        if _empty_fastlane_exporter(payload, None):
            fallback = _fresh_dashboard_fallback(runtime_dir, symbol)
            if fallback:
                return fallback
        return payload
    return {}

def discover_adaptive_gate(runtime_dir: Path, symbol: str) -> Dict[str, Any]:
    for candidate in [runtime_dir / "adaptive" / "QuantGod_DynamicEntryGate.json", runtime_dir / "QuantGod_DynamicEntryGate.json"]:
        payload = read_json(candidate)
        if not payload:
            continue
        items = payload.get("entryGates") or payload.get("gates") or payload.get("items")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("symbol") == symbol:
                    return item
        if payload.get("symbol") == symbol:
            return payload
    return {}

def load_shadow_rows(runtime_dir: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for candidate in [runtime_dir / "ShadowCandidateOutcomeLedger.csv", runtime_dir / "QuantGod_ShadowCandidateOutcomeLedger.csv", runtime_dir / "adaptive" / "QuantGod_AdaptivePolicyLedger.csv", runtime_dir / "QuantGod_AdaptivePolicyLedger.csv"]:
        rows.extend(read_csv_rows(candidate))
    return rows

def sample_runtime(runtime_dir: Path, symbols: Iterable[str], overwrite: bool = False) -> None:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "quality").mkdir(parents=True, exist_ok=True)
    (runtime_dir / "adaptive").mkdir(parents=True, exist_ok=True)
    for symbol in symbols:
        snapshot = {
            "schema": "quantgod.mt5.runtime_snapshot.sample.v1",
            "symbol": symbol,
            "runtimeFresh": True,
            "fallback": False,
            "safety": {
                "readOnlyDataPlane": True,
                "orderSendAllowed": False,
                "brokerExecutionAllowed": False,
                "livePresetMutationAllowed": False,
            },
        }
        snapshot_target = runtime_dir / f"QuantGod_MT5RuntimeSnapshot_{symbol}.json"
        if overwrite or not snapshot_target.exists():
            snapshot_target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    quality = {"schema":"quantgod.mt5.fastlane.quality.v1","quality":"OK","symbols":{symbol:{"quality":"OK","heartbeatFresh":True,"tickFresh":True,"indicatorFresh":True,"spreadOk":True} for symbol in symbols},"safety":{"readOnlyDataPlane":True,"orderSendAllowed":False,"brokerExecutionAllowed":False}}
    target = runtime_dir / "quality" / "QuantGod_MT5FastLaneQuality.json"
    if overwrite or not target.exists():
        target.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    gate = {"schema":"quantgod.dynamic_entry_gate.v1","entryGates":[{"symbol":symbol,"direction":"LONG","passed":True,"state":"PASS","reasons":["sample runtime gate passed"]} for symbol in symbols],"safety":{"readOnlyDataPlane":True,"orderSendAllowed":False,"brokerExecutionAllowed":False}}
    target = runtime_dir / "adaptive" / "QuantGod_DynamicEntryGate.json"
    if overwrite or not target.exists():
        target.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [
        {"symbol":"USDJPYc","direction":"LONG","horizonMinutes":"15","pips":"4.2","scoreR":"0.42"},
        {"symbol":"USDJPYc","direction":"LONG","horizonMinutes":"15","pips":"2.7","scoreR":"0.27"},
        {"symbol":"USDJPYc","direction":"LONG","horizonMinutes":"15","pips":"1.3","scoreR":"0.13"},
        {"symbol":"USDJPYc","direction":"SHORT","horizonMinutes":"15","pips":"-3.1","scoreR":"-0.31"},
    ]
    ledger = runtime_dir / "ShadowCandidateOutcomeLedger.csv"
    if overwrite or not ledger.exists():
        with ledger.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader(); writer.writerows(rows)
