from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .io_utils import candidate_mt5_files_dirs, load_json, utc_now_iso, write_json
from .schema import (
    AGENT_VERSION,
    FOCUS_SYMBOL,
    SAFETY_BOUNDARY,
    parity_ledger_path,
    parity_path,
    parity_public_path,
)

try:
    from tools.strategy_json.schema import base_strategy_seed
    from tools.usdjpy_bar_replay.replay_engine import build_bar_replay_report
    from tools.usdjpy_strategy_backtest.report import run_backtest
except ModuleNotFoundError:  # pragma: no cover
    from strategy_json.schema import base_strategy_seed
    from usdjpy_bar_replay.replay_engine import build_bar_replay_report
    from usdjpy_strategy_backtest.report import run_backtest

PROMOTION_HARD_CHECKS = {
    "strategy_json_backtest_engine_v2",
    "strategy_json_vs_live_loop_policy",
    "strategy_json_vs_mql5_rsi_diagnostics",
    "strategy_json_python_replay_mql5_gate_matrix",
    "backtest_no_execution",
    "live_loop_no_frontend_execution",
}

RSI_DIAGNOSTICS_FILE = "QuantGod_USDJPYRsiEntryDiagnostics.json"
MT5_DASHBOARD_FILE = "QuantGod_Dashboard.json"


def build_parity_report(runtime_dir: Path, write: bool = True) -> Dict[str, Any]:
    sync = _sync_strategy_json_python_evidence(runtime_dir)
    backtest = load_json(runtime_dir / "backtest" / "QuantGod_StrategyBacktestReport.json")
    replay = load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYBarReplayReport.json")
    live_loop = load_json(runtime_dir / "live" / "QuantGod_USDJPYLiveLoopStatus.json")
    diagnostics, diagnostics_source = _load_rsi_diagnostics(runtime_dir)

    deep_gate_check = _check_deep_gate_matrix(backtest, replay, diagnostics)
    checks: List[Dict[str, Any]] = [
        _check_equal("symbol", backtest.get("symbol"), FOCUS_SYMBOL, required=True),
        _check_equal("strategy_family", backtest.get("strategyFamily"), "RSI_Reversal", required=False),
        _check_equal("direction", backtest.get("direction"), "LONG", required=False),
        _check_backtest_engine(backtest.get("engine")),
        _check_sqlite_persistence(backtest),
        _check_multi_strategy_coverage(backtest.get("strategyCoverageMatrix")),
        _check_parity_vector_vs_live(backtest, live_loop),
        _check_parity_vector_vs_ea(backtest, diagnostics),
        deep_gate_check,
        _check_present("bar_replay_report", replay),
        _check_present("live_loop_status", live_loop),
        _check_present("ea_rsi_diagnostics", diagnostics),
        _check_safety("backtest_no_execution", backtest.get("safety")),
        _check_safety("live_loop_no_frontend_execution", live_loop.get("safety")),
    ]
    failed_required = [row for row in checks if row["status"] == "FAIL" and row.get("required")]
    warnings = [row for row in checks if row["status"] in {"WARN", "MISSING"}]
    status = "PARITY_FAIL" if failed_required else ("PARITY_WARN" if warnings else "PARITY_PASS")
    promotion_gate = _promotion_gate(checks)
    report = {
        "ok": status != "PARITY_FAIL",
        "schema": "quantgod.strategy_parity_report.v1",
        "agentVersion": AGENT_VERSION,
        "createdAt": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "status": status,
        "checks": checks,
        "promotionGate": promotion_gate,
        "deepParity": deep_gate_check.get("actual") if isinstance(deep_gate_check.get("actual"), dict) else {},
        "parityDimensions": _parity_dimensions(backtest, live_loop, diagnostics),
        "summary": _summary(checks),
        "reasonZh": _reason_zh(status),
        "evidenceSync": sync,
        "rsiDiagnosticsSource": diagnostics_source,
        "singleSourceOfTruth": "STRATEGY_JSON_PYTHON_REPLAY_MQL5_EA_PARITY",
        "safety": dict(SAFETY_BOUNDARY),
    }
    if write:
        write_json(parity_path(runtime_dir), report)
        _write_public_parity_outputs(runtime_dir, report)
    return report


def _sync_strategy_json_python_evidence(runtime_dir: Path) -> Dict[str, Any]:
    """Keep Strategy JSON parity vector and Python replay evidence in the active runtime.

    Evidence OS is often pointed directly at the live MT5 MQL5/Files directory. In
    that mode the EA diagnostics are fresh, but the Strategy JSON backtest report
    and Python replay report can be absent. Build read-only evidence from the EA
    inputs so deep parity compares the same live RSI contract instead of the
    generic GA seed defaults.
    """
    runtime_dir = Path(runtime_dir)
    diagnostics, diagnostics_source = _load_rsi_diagnostics(runtime_dir)
    sync: Dict[str, Any] = {
        "schema": "quantgod.strategy_python_parity_sync.v1",
        "createdAt": utc_now_iso(),
        "strategyJsonBacktest": "SKIPPED",
        "pythonReplay": "SKIPPED",
        "source": "MQL5_EA_DIAGNOSTICS" if diagnostics else "DEFAULT_STRATEGY_JSON",
        "rsiDiagnosticsSource": diagnostics_source,
        "safety": dict(SAFETY_BOUNDARY),
    }

    try:
        seed = _strategy_seed_from_ea_diagnostics(diagnostics)
        backtest = run_backtest(runtime_dir, seed, write=True)
        sync["strategyJsonBacktest"] = "WRITTEN" if backtest.get("engine", {}).get("parityVector") else "WRITTEN_WITHOUT_VECTOR"
        sync["strategyId"] = seed.get("strategyId")
        sync["rsi"] = ((seed.get("indicators") or {}).get("rsi") or {})
    except Exception as exc:  # pragma: no cover - defensive runtime sync path
        sync["strategyJsonBacktest"] = "FAILED"
        sync["strategyJsonBacktestError"] = str(exc)

    try:
        replay = build_bar_replay_report(runtime_dir, write=True)
        sync["pythonReplay"] = "WRITTEN" if replay else "FAILED_EMPTY"
        sync["pythonReplayStatus"] = replay.get("status") if isinstance(replay, dict) else None
    except Exception as exc:  # pragma: no cover - defensive runtime sync path
        sync["pythonReplay"] = "FAILED"
        sync["pythonReplayError"] = str(exc)
    return sync


def _load_rsi_diagnostics(runtime_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    runtime_dir = Path(runtime_dir)
    runtime_file = runtime_dir / RSI_DIAGNOSTICS_FILE
    candidates = _prefer_live_dirs(candidate_mt5_files_dirs(runtime_dir), runtime_dir)
    live_candidates = [path for path in candidates if not _same_path(path, runtime_dir)]
    runtime_candidates = [path for path in candidates if _same_path(path, runtime_dir)]

    for directory in live_candidates:
        path = directory / RSI_DIAGNOSTICS_FILE
        diagnostics = load_json(path)
        if diagnostics:
            source = _diagnostics_source("standalone_file", path, runtime_file)
            _sync_runtime_diagnostics(runtime_file, diagnostics, source)
            return diagnostics, source

    for directory in live_candidates:
        path = directory / MT5_DASHBOARD_FILE
        dashboard = load_json(path)
        embedded = dashboard.get("usdJpyRsiEntryDiagnostics")
        if isinstance(embedded, dict) and embedded:
            source = _diagnostics_source("dashboard_embedded", path, runtime_file)
            _sync_runtime_diagnostics(runtime_file, embedded, source)
            return embedded, source

    for directory in runtime_candidates:
        path = directory / RSI_DIAGNOSTICS_FILE
        diagnostics = load_json(path)
        if diagnostics:
            source = _diagnostics_source("standalone_file", path, runtime_file)
            _sync_runtime_diagnostics(runtime_file, diagnostics, source)
            return diagnostics, source

    for directory in runtime_candidates:
        path = directory / MT5_DASHBOARD_FILE
        dashboard = load_json(path)
        embedded = dashboard.get("usdJpyRsiEntryDiagnostics")
        if isinstance(embedded, dict) and embedded:
            source = _diagnostics_source("dashboard_embedded", path, runtime_file)
            _sync_runtime_diagnostics(runtime_file, embedded, source)
            return embedded, source

    return {}, {
        "type": "missing",
        "searchedDirs": [str(path) for path in candidates],
        "expectedFile": RSI_DIAGNOSTICS_FILE,
    }


def _prefer_live_dirs(candidates: List[Path], runtime_dir: Path) -> List[Path]:
    try:
        runtime_resolved = runtime_dir.resolve()
    except Exception:
        runtime_resolved = runtime_dir
    return sorted(
        candidates,
        key=lambda path: 1 if _same_path(path, runtime_resolved) else 0,
    )


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except Exception:
        return left == right


def _diagnostics_source(source_type: str, path: Path, runtime_file: Path) -> Dict[str, Any]:
    try:
        resolved_path = path.resolve()
    except Exception:
        resolved_path = path
    try:
        resolved_runtime = runtime_file.resolve()
    except Exception:
        resolved_runtime = runtime_file
    return {
        "type": source_type,
        "path": str(resolved_path),
        "runtimePath": str(resolved_runtime),
        "runtimeSynced": str(resolved_path) != str(resolved_runtime),
    }


def _sync_runtime_diagnostics(runtime_file: Path, diagnostics: Dict[str, Any], source: Dict[str, Any]) -> None:
    if not source.get("runtimeSynced"):
        return
    try:
        write_json(runtime_file, diagnostics)
    except Exception:
        source["runtimeSyncError"] = True


def _strategy_seed_from_ea_diagnostics(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    seed = base_strategy_seed("PARITY-LIVE-EA-RSI", family="RSI_Reversal", direction="LONG")
    seed["strategyId"] = "USDJPY_RSI_REVERSAL_LONG_LIVE_PARITY"
    seed["lane"] = "MT5_SHADOW"
    seed["source"] = "MQL5_EA_DIAGNOSTICS"
    inputs = diagnostics.get("inputs") if isinstance(diagnostics.get("inputs"), dict) else {}
    route = diagnostics.get("route") if isinstance(diagnostics.get("route"), dict) else {}
    rsi = diagnostics.get("rsi") if isinstance(diagnostics.get("rsi"), dict) else {}
    indicators = seed.get("indicators") if isinstance(seed.get("indicators"), dict) else {}
    rsi_cfg = indicators.get("rsi") if isinstance(indicators.get("rsi"), dict) else {}
    rsi_cfg.update({
        "period": _first_number(inputs.get("PilotRsiPeriod"), rsi.get("period"), rsi_cfg.get("period")),
        "timeframe": str(inputs.get("PilotRsiTimeframe") or rsi.get("timeframe") or route.get("timeframe") or rsi_cfg.get("timeframe") or "H1").upper(),
        "buyBand": _first_number(inputs.get("PilotRsiOversold"), rsi.get("buyBandLevel"), rsi.get("oversold"), rsi_cfg.get("buyBand")),
        "sellBand": _first_number(inputs.get("PilotRsiOverbought"), rsi.get("sellBandLevel"), rsi.get("overbought"), rsi_cfg.get("sellBand"), 85),
        "crossbackThreshold": _first_number(inputs.get("PilotRsiCrossbackThreshold"), rsi.get("crossbackThreshold"), rsi_cfg.get("crossbackThreshold"), 0),
    })
    indicators["rsi"] = rsi_cfg
    seed["indicators"] = indicators
    return seed


def _first_number(*values: Any) -> float:
    for value in values:
        try:
            if value not in {None, ""}:
                return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _check_equal(name: str, actual: Any, expected: Any, required: bool) -> Dict[str, Any]:
    if actual == expected:
        status = "PASS"
    elif actual in {None, ""} and not required:
        status = "MISSING"
    else:
        status = "FAIL" if required else "WARN"
    return {
        "name": name,
        "status": status,
        "required": required,
        "actual": actual,
        "expected": expected,
        "reasonZh": "一致" if status == "PASS" else "证据缺失或口径不一致",
    }


def _check_present(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    present = bool(payload)
    return {
        "name": name,
        "status": "PASS" if present else "MISSING",
        "required": False,
        "reasonZh": "已读取" if present else "尚未生成，保留为审计提醒，不阻断实盘",
    }


def _check_sqlite_persistence(backtest: Dict[str, Any]) -> Dict[str, Any]:
    run_id = backtest.get("runId")
    has_engine = isinstance(backtest.get("engine"), dict)
    has_trades = int(backtest.get("tradeCount") or 0) >= 0
    status = "PASS" if run_id and has_engine and has_trades else "WARN"
    return {
        "name": "strategy_backtest_sqlite_persistence",
        "status": status,
        "required": False,
        "actual": {
            "runId": run_id,
            "tradeCount": backtest.get("tradeCount"),
            "hasEngine": has_engine,
        },
        "reasonZh": "Strategy run 可落入 SQLite 审计表" if status == "PASS" else "尚未看到完整 SQLite run 证据",
    }


def _check_multi_strategy_coverage(matrix: Any) -> Dict[str, Any]:
    data = matrix if isinstance(matrix, dict) else {}
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    expected_routes = 16
    ok_routes = int(float(summary.get("okRouteCount") or 0))
    covered_families = int(float(summary.get("coveredFamilyCount") or 0))
    parity_routes = int(float(summary.get("parityVectorRouteCount") or 0))
    missing = []
    if data.get("schema") != "quantgod.strategy_backtest_coverage_matrix.v1":
        missing.append("schema")
    if len(rows) < expected_routes:
        missing.append("routes")
    if ok_routes < expected_routes:
        missing.append("okRouteCount")
    if covered_families < 8:
        missing.append("coveredFamilyCount")
    if parity_routes < expected_routes:
        missing.append("parityVectorRouteCount")
    status = "PASS" if not missing else "WARN"
    return {
        "name": "strategy_json_multi_strategy_coverage_matrix",
        "status": status,
        "required": False,
        "promotionCritical": True,
        "actual": {
            "routeCount": len(rows),
            "okRouteCount": ok_routes,
            "coveredFamilyCount": covered_families,
            "parityVectorRouteCount": parity_routes,
        },
        "expected": {
            "routeCount": expected_routes,
            "coveredFamilyCount": 8,
            "parityVectorRouteCount": expected_routes,
        },
        "reasonZh": "8 个 USDJPY MT5 Shadow 策略族、双方向回测与 parityVector 覆盖已接入"
        if status == "PASS"
        else "多策略 Strategy JSON 回测覆盖矩阵不完整：" + ", ".join(missing),
    }


def _check_parity_vector_vs_live(backtest: Dict[str, Any], live_loop: Dict[str, Any]) -> Dict[str, Any]:
    vector = ((backtest.get("engine") or {}).get("parityVector") or {}) if isinstance(backtest.get("engine"), dict) else {}
    top_policy = live_loop.get("topLiveEligiblePolicy") or live_loop.get("topPolicy") or {}
    if not vector or not top_policy:
        return {
            "name": "strategy_json_vs_live_loop_policy",
            "status": "MISSING",
            "required": False,
            "promotionCritical": True,
            "reasonZh": "等待 Live Loop policy 与 Strategy JSON parity vector 同步；同步前不能晋级。",
        }
    expected_family = _policy_strategy(top_policy)
    expected_direction = _normalize_direction(top_policy.get("direction"))
    mismatches = []
    if expected_family and vector.get("strategyFamily") != expected_family:
        mismatches.append("strategyFamily")
    if expected_direction and _normalize_direction(vector.get("direction")) != expected_direction:
        mismatches.append("direction")
    status = "PASS" if not mismatches else "FAIL"
    return {
        "name": "strategy_json_vs_live_loop_policy",
        "status": status,
        "required": bool(mismatches),
        "promotionCritical": True,
        "actual": {
            "vectorFamily": vector.get("strategyFamily"),
            "vectorDirection": vector.get("direction"),
            "policyFamily": expected_family,
            "policyDirection": expected_direction,
        },
        "reasonZh": "Strategy JSON 与 Live Loop 候选策略方向一致" if status == "PASS" else f"Strategy JSON 与 Live Loop 存在硬口径差异：{', '.join(mismatches)}",
    }


def _check_parity_vector_vs_ea(backtest: Dict[str, Any], diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    vector = ((backtest.get("engine") or {}).get("parityVector") or {}) if isinstance(backtest.get("engine"), dict) else {}
    if not vector or not diagnostics:
        missing_reason = (
            "等待 Strategy JSON parity vector 与 EA 诊断同步；EA 诊断已读取，但缺 Strategy JSON parity vector。"
            if diagnostics
            else "等待 EA 输出 QuantGod_USDJPYRsiEntryDiagnostics.json 后做逐字段对账；同步前不能晋级。"
        )
        return {
            "name": "strategy_json_vs_mql5_rsi_diagnostics",
            "status": "MISSING",
            "required": False,
            "promotionCritical": True,
            "actual": {
                "hasParityVector": bool(vector),
                "hasEaDiagnostics": bool(diagnostics),
            },
            "reasonZh": missing_reason,
        }
    diag_strategy = diagnostics.get("strategy") or diagnostics.get("strategyFamily") or "RSI_Reversal"
    diag_direction = _normalize_direction(diagnostics.get("direction") or "LONG")
    diag_route = diagnostics.get("route") if isinstance(diagnostics.get("route"), dict) else {}
    diag_guards = diagnostics.get("guards") if isinstance(diagnostics.get("guards"), dict) else {}
    diag_rsi = diagnostics.get("rsi") if isinstance(diagnostics.get("rsi"), dict) else {}
    vector_rsi = vector.get("rsi") if isinstance(vector.get("rsi"), dict) else {}
    mismatches = []
    if vector.get("strategyFamily") != diag_strategy:
        mismatches.append("strategyFamily")
    if _normalize_direction(vector.get("direction")) != diag_direction:
        mismatches.append("direction")
    if _present(vector_rsi.get("period")) and _present(diag_rsi.get("period")) and int(float(vector_rsi.get("period"))) != int(float(diag_rsi.get("period"))):
        mismatches.append("rsi.period")
    if _present(vector_rsi.get("timeframe")) and _present(diag_route.get("timeframe")) and str(vector_rsi.get("timeframe")).upper() != str(diag_route.get("timeframe")).upper():
        mismatches.append("rsi.timeframe")
    if _present(vector_rsi.get("buyBand")) and _present(diag_rsi.get("oversold")) and abs(float(vector_rsi.get("buyBand")) - float(diag_rsi.get("oversold"))) > 5.0:
        mismatches.append("rsi.buyBand/oversold")
    if _normalize_direction(diag_rsi.get("signalDirection")) not in {"", "NONE", _normalize_direction(vector.get("direction"))}:
        mismatches.append("signalDirection")
    status = "PASS" if not mismatches else "FAIL"
    return {
        "name": "strategy_json_vs_mql5_rsi_diagnostics",
        "status": status,
        "required": bool(mismatches),
        "promotionCritical": True,
        "actual": {
            "vectorFamily": vector.get("strategyFamily"),
            "vectorDirection": vector.get("direction"),
            "vectorRsi": vector_rsi,
            "eaFamily": diag_strategy,
            "eaDirection": diag_direction,
            "eaStatus": diagnostics.get("status") or diagnostics.get("state"),
            "eaRoute": {
                "timeframe": diag_route.get("timeframe"),
                "candidateEnabled": diag_route.get("candidateEnabled"),
                "liveEnabled": diag_route.get("liveEnabled"),
                "lastStatus": diag_route.get("lastStatus"),
                "lastReason": diag_route.get("lastReason"),
            },
            "eaGuards": {
                "sessionOpen": diag_guards.get("sessionOpen"),
                "spreadAllowed": diag_guards.get("spreadAllowed"),
                "newsBlocked": diag_guards.get("newsBlocked"),
                "cooldownActive": diag_guards.get("cooldownActive"),
                "startupGuardActive": diag_guards.get("startupGuardActive"),
                "symbolPositions": diag_guards.get("symbolPositions"),
                "maxPositionsPerSymbol": diag_guards.get("maxPositionsPerSymbol"),
            },
            "eaRsi": {
                "period": diag_rsi.get("period"),
                "oversold": diag_rsi.get("oversold"),
                "signalReady": diag_rsi.get("signalReady"),
                "signalDirection": diag_rsi.get("signalDirection"),
                "evalCode": diag_rsi.get("evalCode"),
                "evalReason": diag_rsi.get("evalReason"),
            },
        },
        "reasonZh": "Strategy JSON 与 MQL5 RSI 诊断关键口径一致" if status == "PASS" else f"Strategy JSON 与 MQL5 诊断存在硬口径差异：{', '.join(mismatches)}",
    }


def _check_deep_gate_matrix(backtest: Dict[str, Any], replay: Dict[str, Any], diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    vector = ((backtest.get("engine") or {}).get("parityVector") or {}) if isinstance(backtest.get("engine"), dict) else {}
    missing_sources = []
    if not vector:
        missing_sources.append("Strategy JSON parityVector")
    if not replay:
        missing_sources.append("Python bar replay report")
    if not diagnostics:
        missing_sources.append("MQL5 RSI diagnostics")

    matrix = _deep_gate_matrix(vector, replay, diagnostics)
    if missing_sources:
        matrix["missingSources"] = missing_sources
        return {
            "name": "strategy_json_python_replay_mql5_gate_matrix",
            "status": "MISSING",
            "required": False,
            "promotionCritical": True,
            "actual": matrix,
            "reasonZh": "等待 Strategy JSON、Python 回放和 MQL5 EA 三方证据同时可用；同步前不能晋级。",
        }

    mismatches = matrix.get("hardMismatches") if isinstance(matrix.get("hardMismatches"), list) else []
    status = "PASS" if not mismatches else "FAIL"
    return {
        "name": "strategy_json_python_replay_mql5_gate_matrix",
        "status": status,
        "required": bool(mismatches),
        "promotionCritical": True,
        "actual": matrix,
        "reasonZh": "Strategy JSON / Python Replay / MQL5 EA 深度门禁矩阵一致"
        if status == "PASS"
        else "Strategy JSON / Python Replay / MQL5 EA 深度门禁矩阵存在硬差异：" + ", ".join(mismatches),
    }


def _deep_gate_matrix(vector: Dict[str, Any], replay: Dict[str, Any], diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    vector_rsi = vector.get("rsi") if isinstance(vector.get("rsi"), dict) else {}
    entry_conditions = vector.get("entryConditions") if isinstance(vector.get("entryConditions"), list) else []
    diag_route = diagnostics.get("route") if isinstance(diagnostics.get("route"), dict) else {}
    diag_guards = diagnostics.get("guards") if isinstance(diagnostics.get("guards"), dict) else {}
    diag_permissions = diagnostics.get("permissions") if isinstance(diagnostics.get("permissions"), dict) else {}
    diag_rsi = diagnostics.get("rsi") if isinstance(diagnostics.get("rsi"), dict) else {}
    replay_causal = replay.get("causalReplay") if isinstance(replay.get("causalReplay"), dict) else {}
    replay_entry = replay.get("entryComparison") if isinstance(replay.get("entryComparison"), dict) else {}
    replay_entry_causal = replay_entry.get("causalReplay") if isinstance(replay_entry.get("causalReplay"), dict) else {}
    replay_events = replay_entry.get("events") if isinstance(replay_entry.get("events"), dict) else {}
    replay_current_events = replay_events.get("current") if isinstance(replay_events.get("current"), list) else []
    sample_event = replay_current_events[0] if replay_current_events and isinstance(replay_current_events[0], dict) else {}

    missing_optional: List[str] = []
    hard_mismatches: List[str] = []
    if vector.get("strategyFamily") and vector.get("strategyFamily") != (diagnostics.get("strategy") or diagnostics.get("strategyFamily") or "RSI_Reversal"):
        hard_mismatches.append("strategyFamily")
    if _present(vector.get("direction")) and _normalize_direction(vector.get("direction")) != _normalize_direction(diagnostics.get("direction") or "LONG"):
        hard_mismatches.append("direction")
    if vector_rsi:
        _compare_number("rsi.period", vector_rsi.get("period"), diag_rsi.get("period"), hard_mismatches, missing_optional, tolerance=0.0)
        _compare_text("rsi.timeframe", vector_rsi.get("timeframe"), diag_route.get("timeframe"), hard_mismatches, missing_optional)
        _compare_number("rsi.buyBand", vector_rsi.get("buyBand"), diag_rsi.get("oversold"), hard_mismatches, missing_optional, tolerance=0.01)
    if _present(vector_rsi.get("crossbackThreshold")) and not _present(diag_rsi.get("crossbackThreshold")):
        missing_optional.append("mql5.rsi.crossbackThreshold")
    signal_direction = _normalize_direction(diag_rsi.get("signalDirection"))
    if _present(vector.get("direction")) and signal_direction not in {"", "NONE", _normalize_direction(vector.get("direction"))}:
        hard_mismatches.append("mql5.rsi.signalDirection")

    if replay_causal.get("posteriorMayAffectTrigger") is True or replay_entry_causal.get("posteriorMayAffectTrigger") is True:
        hard_mismatches.append("pythonReplay.posteriorLeakage")
    if replay_causal.get("posteriorUsedForScoringOnly") is False:
        hard_mismatches.append("pythonReplay.posteriorScoringOnly")
    hard_gates = _lower_set(replay_entry_causal.get("hardGatesNeverRelaxed") or [])
    required_replay_hard_gates = {"runtime", "fastlane", "spread", "highimpactnews"}
    missing_hard_gates = sorted(required_replay_hard_gates - hard_gates)
    if missing_hard_gates:
        hard_mismatches.append("pythonReplay.hardGatesNeverRelaxed:" + "/".join(missing_hard_gates))
    if replay_entry_causal.get("ordinaryNewsBlocksLive") is True:
        hard_mismatches.append("pythonReplay.ordinaryNewsStillHardBlocks")

    for key in ("sessionOpen", "spreadAllowed", "newsBlocked", "cooldownActive", "startupGuardActive", "symbolPositions", "maxPositionsPerSymbol"):
        if key not in diag_guards:
            missing_optional.append("mql5.guards." + key)
    for key in ("liveMode", "tradeAllowed", "readOnlyMode"):
        if key not in diag_permissions:
            missing_optional.append("mql5.permissions." + key)

    return {
        "schema": "quantgod.strategy_deep_parity_matrix.v1",
        "status": "FAIL" if hard_mismatches else "PASS",
        "strategyJson": {
            "strategyId": vector.get("strategyId"),
            "seedId": vector.get("seedId"),
            "symbol": vector.get("symbol") or FOCUS_SYMBOL,
            "strategyFamily": vector.get("strategyFamily"),
            "direction": vector.get("direction"),
            "entryMode": vector.get("entryMode"),
            "entryGateExpectations": _entry_gate_expectations(entry_conditions),
            "rsi": {
                "period": vector_rsi.get("period"),
                "timeframe": vector_rsi.get("timeframe"),
                "buyBand": vector_rsi.get("buyBand"),
                "crossbackThreshold": vector_rsi.get("crossbackThreshold"),
            },
            "exit": vector.get("exit") if isinstance(vector.get("exit"), dict) else {},
            "risk": vector.get("risk") if isinstance(vector.get("risk"), dict) else {},
        },
        "pythonReplay": {
            "causalInputsOnly": replay_causal.get("posteriorMayAffectTrigger") is False,
            "posteriorMayAffectTrigger": replay_causal.get("posteriorMayAffectTrigger"),
            "posteriorUsedForScoringOnly": replay_causal.get("posteriorUsedForScoringOnly"),
            "hardGatesNeverRelaxed": sorted(hard_gates),
            "ordinaryNewsBlocksLive": replay_entry_causal.get("ordinaryNewsBlocksLive"),
            "currentSample": {
                "allowed": sample_event.get("allowed"),
                "hardGatePass": sample_event.get("hardGatePass"),
                "tacticalGatePass": sample_event.get("tacticalGatePass"),
                "hardBlockers": sample_event.get("hardBlockers"),
                "tacticalBlockers": sample_event.get("tacticalBlockers"),
                "posteriorUsedForTrigger": sample_event.get("posteriorUsedForTrigger"),
            },
        },
        "mql5Ea": {
            "state": diagnostics.get("state") or diagnostics.get("status"),
            "route": {
                "timeframe": diag_route.get("timeframe"),
                "candidateEnabled": diag_route.get("candidateEnabled"),
                "liveEnabled": diag_route.get("liveEnabled"),
                "inScope": diag_route.get("inScope"),
                "lastStatus": diag_route.get("lastStatus"),
            },
            "permissions": {
                "liveMode": diag_permissions.get("liveMode"),
                "tradeAllowed": diag_permissions.get("tradeAllowed"),
                "readOnlyMode": diag_permissions.get("readOnlyMode"),
            },
            "guards": {
                "killSwitch": diag_guards.get("killSwitch"),
                "sessionOpen": diag_guards.get("sessionOpen"),
                "spreadAllowed": diag_guards.get("spreadAllowed"),
                "newsBlocked": diag_guards.get("newsBlocked"),
                "cooldownActive": diag_guards.get("cooldownActive"),
                "startupGuardActive": diag_guards.get("startupGuardActive"),
                "manualPositionBlock": diag_guards.get("manualPositionBlock"),
                "symbolPositions": diag_guards.get("symbolPositions"),
                "maxPositionsPerSymbol": diag_guards.get("maxPositionsPerSymbol"),
            },
            "rsi": {
                "period": diag_rsi.get("period"),
                "timeframe": diag_route.get("timeframe"),
                "oversold": diag_rsi.get("oversold"),
                "buyBandLevel": diag_rsi.get("buyBandLevel"),
                "buyBand": diag_rsi.get("buyBand"),
                "crossbackThreshold": diag_rsi.get("crossbackThreshold"),
                "crossbackRule": diag_rsi.get("crossbackRule"),
                "signalReady": diag_rsi.get("signalReady"),
                "signalDirection": diag_rsi.get("signalDirection"),
                "evalCode": diag_rsi.get("evalCode"),
                "evalReason": diag_rsi.get("evalReason"),
            },
        },
        "missingOptionalFields": sorted(set(missing_optional)),
        "hardMismatches": sorted(set(hard_mismatches)),
        "reasonZh": "三方关键门禁一致；可选字段缺失只作为审计提醒。"
        if not hard_mismatches
        else "三方关键门禁存在硬差异，禁止晋级。",
    }


PARITY_LEDGER_FIELDS = [
    "createdAt",
    "symbol",
    "strategyId",
    "timeframe",
    "barTime",
    "rsiValue",
    "rsiCrossback",
    "sessionAllowed",
    "spreadAllowed",
    "newsRisk",
    "runtimeFresh",
    "fastlaneState",
    "entryAllowed",
    "entryMode",
    "exitMode",
    "lotSuggestion",
    "parityStatus",
    "promotionGateStatus",
    "hardMismatchCount",
    "hardMismatches",
    "missingOptionalFields",
    "reasonZh",
]


def _write_public_parity_outputs(runtime_dir: Path, report: Dict[str, Any]) -> None:
    write_json(parity_public_path(runtime_dir), report)
    row = _parity_ledger_row(report)
    path = parity_ledger_path(runtime_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PARITY_LEDGER_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in PARITY_LEDGER_FIELDS})


def _parity_ledger_row(report: Dict[str, Any]) -> Dict[str, Any]:
    deep = report.get("deepParity") if isinstance(report.get("deepParity"), dict) else {}
    strategy = deep.get("strategyJson") if isinstance(deep.get("strategyJson"), dict) else {}
    replay = deep.get("pythonReplay") if isinstance(deep.get("pythonReplay"), dict) else {}
    replay_sample = replay.get("currentSample") if isinstance(replay.get("currentSample"), dict) else {}
    ea = deep.get("mql5Ea") if isinstance(deep.get("mql5Ea"), dict) else {}
    ea_route = ea.get("route") if isinstance(ea.get("route"), dict) else {}
    ea_guards = ea.get("guards") if isinstance(ea.get("guards"), dict) else {}
    ea_rsi = ea.get("rsi") if isinstance(ea.get("rsi"), dict) else {}
    gate = report.get("promotionGate") if isinstance(report.get("promotionGate"), dict) else {}
    sync = report.get("evidenceSync") if isinstance(report.get("evidenceSync"), dict) else {}
    dimensions = report.get("parityDimensions") if isinstance(report.get("parityDimensions"), dict) else {}
    dim_strategy = dimensions.get("strategyJson") if isinstance(dimensions.get("strategyJson"), dict) else {}
    hard_mismatches = deep.get("hardMismatches") if isinstance(deep.get("hardMismatches"), list) else []
    missing_optional = deep.get("missingOptionalFields") if isinstance(deep.get("missingOptionalFields"), list) else []
    entry_allowed = _first_present(
        replay_sample.get("allowed"),
        ea_rsi.get("signalReady") if ea_guards.get("sessionOpen") and ea_guards.get("spreadAllowed") else None,
    )
    rsi_crossback = _first_present(
        ea_rsi.get("buyReversal"),
        ea_rsi.get("crossback"),
        "rsi.crossback" in " ".join(str(item).lower() for item in strategy.get("entryGateExpectations", {})),
    )
    news_risk = "HARD" if ea_guards.get("newsBlocked") is True else ("OK" if ea_guards.get("newsBlocked") is False else "")
    return {
        "createdAt": report.get("createdAt") or utc_now_iso(),
        "symbol": report.get("symbol") or strategy.get("symbol") or FOCUS_SYMBOL,
        "strategyId": strategy.get("strategyId") or sync.get("strategyId") or "",
        "timeframe": _first_present(ea_route.get("timeframe"), (strategy.get("rsi") or {}).get("timeframe")),
        "barTime": _first_present(ea_route.get("lastSignalTime"), ea_route.get("lastEvalTime"), dim_strategy.get("lastSignalTime")),
        "rsiValue": _first_present(ea_rsi.get("rsiClosed1"), ea_rsi.get("value"), ea_rsi.get("currentValue")),
        "rsiCrossback": rsi_crossback,
        "sessionAllowed": ea_guards.get("sessionOpen"),
        "spreadAllowed": ea_guards.get("spreadAllowed"),
        "newsRisk": news_risk,
        "runtimeFresh": not bool(ea_guards.get("startupGuardActive")) if "startupGuardActive" in ea_guards else "",
        "fastlaneState": _first_present(ea_route.get("lastStatus"), ea.get("state")),
        "entryAllowed": entry_allowed,
        "entryMode": strategy.get("entryMode") or "",
        "exitMode": _exit_mode(strategy.get("exit") if isinstance(strategy.get("exit"), dict) else {}),
        "lotSuggestion": (strategy.get("risk") or {}).get("opportunityLotMultiplier") if isinstance(strategy.get("risk"), dict) else "",
        "parityStatus": report.get("status") or deep.get("status") or "",
        "promotionGateStatus": gate.get("status") or "",
        "hardMismatchCount": len(hard_mismatches),
        "hardMismatches": ";".join(str(item) for item in hard_mismatches),
        "missingOptionalFields": ";".join(str(item) for item in missing_optional),
        "reasonZh": report.get("reasonZh") or deep.get("reasonZh") or "",
    }


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in {None, ""}:
            return value
    return ""


def _exit_mode(exit_cfg: Dict[str, Any]) -> str:
    if not exit_cfg:
        return ""
    labels = []
    if exit_cfg.get("trailStartR") is not None:
        labels.append("TRAILING_STOP")
    if exit_cfg.get("mfeGivebackPct") is not None:
        labels.append("MFE_GIVEBACK")
    if exit_cfg.get("timeStopBars"):
        labels.append("TIME_STOP")
    if exit_cfg.get("breakevenDelayR") is not None:
        labels.append("BREAKEVEN")
    return "+".join(labels) or "CUSTOM_EXIT"


def _check_backtest_engine(engine: Any) -> Dict[str, Any]:
    data = engine if isinstance(engine, dict) else {}
    required_markers = {
        "schema": "quantgod.strategy_backtest_engine.v2",
        "coverage": "ALL_SUPPORTED_USDJPY_SHADOW_FAMILIES",
    }
    missing = [
        key
        for key, expected in required_markers.items()
        if data.get(key) != expected
    ]
    if not isinstance(data.get("costModel"), dict):
        missing.append("costModel")
    if not isinstance(data.get("parityVector"), dict):
        missing.append("parityVector")
    status = "PASS" if not missing else "FAIL"
    return {
        "name": "strategy_json_backtest_engine_v2",
        "status": status,
        "required": bool(missing),
        "promotionCritical": True,
        "actual": {
            "schema": data.get("schema"),
            "coverage": data.get("coverage"),
            "hasCostModel": isinstance(data.get("costModel"), dict),
            "hasParityVector": isinstance(data.get("parityVector"), dict),
        },
        "expected": required_markers,
        "reasonZh": "全策略 Strategy JSON runner 已接入 parity 审计"
        if status == "PASS"
        else f"Strategy JSON runner 晋级证据不完整：{', '.join(missing)}",
    }


def _check_safety(name: str, safety: Any) -> Dict[str, Any]:
    data = safety if isinstance(safety, dict) else {}
    execution_allowed = any(bool(data.get(key)) for key in ("orderSendAllowed", "closeAllowed", "cancelAllowed", "livePresetMutationAllowed"))
    return {
        "name": name,
        "status": "FAIL" if execution_allowed else "PASS",
        "required": True,
        "reasonZh": "安全边界保持只读" if not execution_allowed else "发现越权执行字段",
    }


def _policy_strategy(policy: Dict[str, Any]) -> str:
    return str(policy.get("strategy") or policy.get("strategyFamily") or "")


def _summary(checks: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"PASS": 0, "WARN": 0, "MISSING": 0, "FAIL": 0}
    for row in checks:
        status = str(row.get("status") or "WARN")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _promotion_gate(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = [
        {
            "name": str(row.get("name") or ""),
            "status": str(row.get("status") or ""),
            "reasonZh": str(row.get("reasonZh") or "晋级关键证据未通过"),
        }
        for row in checks
        if row.get("name") in PROMOTION_HARD_CHECKS and row.get("status") != "PASS"
    ]
    return {
        "schema": "quantgod.strategy_parity_promotion_gate.v1",
        "status": "BLOCKED" if blockers else "PASS",
        "promotionAllowed": not blockers,
        "blockerCount": len(blockers),
        "blockers": blockers,
        "reasonZh": "Strategy JSON / Python Replay / MQL5 EA 关键口径一致，可进入后续 shadow/tester 晋级评估。"
        if not blockers
        else "Strategy JSON / Python Replay / MQL5 EA 关键口径未完全一致，禁止晋级。",
    }


def _parity_dimensions(backtest: Dict[str, Any], live_loop: Dict[str, Any], diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    vector = ((backtest.get("engine") or {}).get("parityVector") or {}) if isinstance(backtest.get("engine"), dict) else {}
    diag_route = diagnostics.get("route") if isinstance(diagnostics.get("route"), dict) else {}
    diag_guards = diagnostics.get("guards") if isinstance(diagnostics.get("guards"), dict) else {}
    diag_rsi = diagnostics.get("rsi") if isinstance(diagnostics.get("rsi"), dict) else {}
    top_policy = live_loop.get("topLiveEligiblePolicy") or live_loop.get("topPolicy") or {}
    return {
        "strategyJson": {
            "strategyId": vector.get("strategyId"),
            "seedId": vector.get("seedId"),
            "symbol": vector.get("symbol") or FOCUS_SYMBOL,
            "strategyFamily": vector.get("strategyFamily"),
            "direction": vector.get("direction"),
            "entryMode": vector.get("entryMode"),
            "rsi": vector.get("rsi") if isinstance(vector.get("rsi"), dict) else {},
            "exit": vector.get("exit") if isinstance(vector.get("exit"), dict) else {},
            "risk": vector.get("risk") if isinstance(vector.get("risk"), dict) else {},
            "signalCount": vector.get("signalCount"),
            "lastSignalTime": vector.get("lastSignalTime"),
        },
        "liveLoop": {
            "status": live_loop.get("status") or live_loop.get("state"),
            "topLiveEligiblePolicy": {
                "strategy": _policy_strategy(top_policy),
                "direction": top_policy.get("direction"),
                "entryMode": top_policy.get("entryMode") or top_policy.get("mode"),
                "recommendedLot": top_policy.get("recommendedLot"),
            },
        },
        "mql5Ea": {
            "state": diagnostics.get("state") or diagnostics.get("status"),
            "route": {
                "timeframe": diag_route.get("timeframe"),
                "candidateEnabled": diag_route.get("candidateEnabled"),
                "liveEnabled": diag_route.get("liveEnabled"),
                "lastStatus": diag_route.get("lastStatus"),
            },
            "guards": {
                "sessionOpen": diag_guards.get("sessionOpen"),
                "spreadAllowed": diag_guards.get("spreadAllowed"),
                "newsBlocked": diag_guards.get("newsBlocked"),
                "cooldownActive": diag_guards.get("cooldownActive"),
                "startupGuardActive": diag_guards.get("startupGuardActive"),
                "manualPositionBlock": diag_guards.get("manualPositionBlock"),
            },
            "rsi": {
                "period": diag_rsi.get("period"),
                "oversold": diag_rsi.get("oversold"),
                "signalReady": diag_rsi.get("signalReady"),
                "signalDirection": diag_rsi.get("signalDirection"),
                "evalCode": diag_rsi.get("evalCode"),
            },
        },
    }


def _present(value: Any) -> bool:
    return value not in {None, ""}


def _normalize_direction(value: Any) -> str:
    text = str(value or "").upper()
    if text == "BUY":
        return "LONG"
    if text == "SELL":
        return "SHORT"
    return text


def _compare_number(name: str, left: Any, right: Any, mismatches: List[str], missing: List[str], tolerance: float) -> None:
    if not _present(left) or not _present(right):
        missing.append(name)
        return
    try:
        left_num = float(left)
        right_num = float(right)
    except (TypeError, ValueError):
        mismatches.append(name)
        return
    if abs(left_num - right_num) > tolerance:
        mismatches.append(name)


def _compare_text(name: str, left: Any, right: Any, mismatches: List[str], missing: List[str]) -> None:
    if not _present(left) or not _present(right):
        missing.append(name)
        return
    if str(left).upper() != str(right).upper():
        mismatches.append(name)


def _lower_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(item).replace("_", "").lower() for item in values}


def _entry_gate_expectations(entry_conditions: List[Any]) -> Dict[str, bool]:
    text = " ".join(str(item or "") for item in entry_conditions).lower()
    return {
        "runtimeFresh": "runtimefresh" in text,
        "fastlanePass": "fastlane" in text,
        "spreadSafe": "spread" in text,
        "newsNotHard": "news" in text,
        "rsiCrossback": "rsi.crossback" in text or "crossback" in text,
    }


def _reason_zh(status: str) -> str:
    if status == "PARITY_PASS":
        return "Strategy JSON、Python 回放和 EA 证据口径当前一致。"
    if status == "PARITY_WARN":
        return "部分 EA 或回放证据尚未同步；不影响只读研究，但不能把该证据当完整 parity。"
    return "发现必需口径不一致，策略不能晋级。"
