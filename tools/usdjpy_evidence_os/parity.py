from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .io_utils import load_json, utc_now_iso, write_json
from .schema import AGENT_VERSION, FOCUS_SYMBOL, SAFETY_BOUNDARY, parity_path

PROMOTION_HARD_CHECKS = {
    "strategy_json_backtest_engine_v2",
    "strategy_json_vs_live_loop_policy",
    "strategy_json_vs_mql5_rsi_diagnostics",
    "strategy_json_python_replay_mql5_gate_matrix",
    "backtest_no_execution",
    "live_loop_no_frontend_execution",
}


def build_parity_report(runtime_dir: Path, write: bool = True) -> Dict[str, Any]:
    backtest = load_json(runtime_dir / "backtest" / "QuantGod_StrategyBacktestReport.json")
    replay = load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYBarReplayReport.json")
    live_loop = load_json(runtime_dir / "live" / "QuantGod_USDJPYLiveLoopStatus.json")
    diagnostics = load_json(runtime_dir / "QuantGod_USDJPYRsiEntryDiagnostics.json")

    deep_gate_check = _check_deep_gate_matrix(backtest, replay, diagnostics)
    checks: List[Dict[str, Any]] = [
        _check_equal("symbol", backtest.get("symbol"), FOCUS_SYMBOL, required=True),
        _check_equal("strategy_family", backtest.get("strategyFamily"), "RSI_Reversal", required=False),
        _check_equal("direction", backtest.get("direction"), "LONG", required=False),
        _check_backtest_engine(backtest.get("engine")),
        _check_sqlite_persistence(backtest),
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
        "singleSourceOfTruth": "STRATEGY_JSON_PYTHON_REPLAY_MQL5_EA_PARITY",
        "safety": dict(SAFETY_BOUNDARY),
    }
    if write:
        write_json(parity_path(runtime_dir), report)
    return report


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
    expected_direction = str(top_policy.get("direction") or "").upper()
    mismatches = []
    if expected_family and vector.get("strategyFamily") != expected_family:
        mismatches.append("strategyFamily")
    if expected_direction and str(vector.get("direction") or "").upper() != expected_direction:
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
        return {
            "name": "strategy_json_vs_mql5_rsi_diagnostics",
            "status": "MISSING",
            "required": False,
            "promotionCritical": True,
            "reasonZh": "等待 EA 输出 QuantGod_USDJPYRsiEntryDiagnostics.json 后做逐字段对账；同步前不能晋级。",
        }
    diag_strategy = diagnostics.get("strategy") or diagnostics.get("strategyFamily") or "RSI_Reversal"
    diag_direction = str(diagnostics.get("direction") or "LONG").upper()
    diag_route = diagnostics.get("route") if isinstance(diagnostics.get("route"), dict) else {}
    diag_guards = diagnostics.get("guards") if isinstance(diagnostics.get("guards"), dict) else {}
    diag_rsi = diagnostics.get("rsi") if isinstance(diagnostics.get("rsi"), dict) else {}
    vector_rsi = vector.get("rsi") if isinstance(vector.get("rsi"), dict) else {}
    mismatches = []
    if vector.get("strategyFamily") != diag_strategy:
        mismatches.append("strategyFamily")
    if str(vector.get("direction") or "").upper() != diag_direction:
        mismatches.append("direction")
    if _present(vector_rsi.get("period")) and _present(diag_rsi.get("period")) and int(float(vector_rsi.get("period"))) != int(float(diag_rsi.get("period"))):
        mismatches.append("rsi.period")
    if _present(vector_rsi.get("timeframe")) and _present(diag_route.get("timeframe")) and str(vector_rsi.get("timeframe")).upper() != str(diag_route.get("timeframe")).upper():
        mismatches.append("rsi.timeframe")
    if _present(vector_rsi.get("buyBand")) and _present(diag_rsi.get("oversold")) and abs(float(vector_rsi.get("buyBand")) - float(diag_rsi.get("oversold"))) > 5.0:
        mismatches.append("rsi.buyBand/oversold")
    if str(diag_rsi.get("signalDirection") or "").upper() not in {"", "NONE", str(vector.get("direction") or "").upper()}:
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
    if str(vector.get("direction") or "").upper() != str(diagnostics.get("direction") or "LONG").upper():
        hard_mismatches.append("direction")
    _compare_number("rsi.period", vector_rsi.get("period"), diag_rsi.get("period"), hard_mismatches, missing_optional, tolerance=0.0)
    _compare_text("rsi.timeframe", vector_rsi.get("timeframe"), diag_route.get("timeframe"), hard_mismatches, missing_optional)
    _compare_number("rsi.buyBand", vector_rsi.get("buyBand"), diag_rsi.get("oversold"), hard_mismatches, missing_optional, tolerance=0.01)
    if _present(vector_rsi.get("crossbackThreshold")) and not _present(diag_rsi.get("crossbackThreshold")):
        missing_optional.append("mql5.rsi.crossbackThreshold")
    signal_direction = str(diag_rsi.get("signalDirection") or "").upper()
    if signal_direction not in {"", "NONE", str(vector.get("direction") or "").upper()}:
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
