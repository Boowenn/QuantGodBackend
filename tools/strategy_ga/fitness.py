from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

GENERIC_STRATEGY_FAMILIES = {"MA_Cross", "BB_Triple", "MACD_Divergence", "SR_Breakout"}


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _variant_metrics(report: Dict[str, Any], group: str, index: int) -> Dict[str, Any]:
    section = report.get(group) if isinstance(report.get(group), dict) else {}
    variants = section.get("variants") if isinstance(section.get("variants"), list) else []
    if len(variants) <= index or not isinstance(variants[index], dict):
        return {}
    metrics = variants[index].get("metrics")
    return metrics if isinstance(metrics, dict) else variants[index]


def evidence_metrics(runtime_dir: Path, seed: Dict[str, Any] | None = None) -> Dict[str, Any]:
    replay = _load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYBarReplayReport.json")
    walk_forward = _load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYWalkForwardReport.json")
    strategy_backtest = _strategy_backtest_metrics(runtime_dir, seed)
    seed_walk_forward = _seed_walk_forward_metrics(runtime_dir, seed)
    strategy_backtest_quality = _load_json(runtime_dir / "backtest" / "QuantGod_StrategyBacktestQualityReport.json")
    history_production_status = _load_json(runtime_dir / "backtest" / "QuantGod_USDJPYHistoryProductionStatus.json")
    backtest_required = seed is not None
    parity = _load_json(runtime_dir / "evidence_os" / "QuantGod_StrategyParityReport.json")
    execution = _load_json(runtime_dir / "evidence_os" / "QuantGod_LiveExecutionQualityReport.json")
    cases = _load_json(runtime_dir / "evidence_os" / "QuantGod_CaseMemorySummary.json")
    strategy_contract_shadow = _strategy_contract_shadow_metrics(cases, seed)
    entry_relaxed = _variant_metrics(replay, "entryComparison", 1)
    exit_let_run = _variant_metrics(replay, "exitComparison", 1)
    summary = replay.get("summary") if isinstance(replay.get("summary"), dict) else {}
    wf_summary = walk_forward.get("summary") if isinstance(walk_forward.get("summary"), dict) else {}
    seed_wf_summary = seed_walk_forward.get("summary") if isinstance(seed_walk_forward.get("summary"), dict) else {}
    backtest_metrics = strategy_backtest.get("metrics") if isinstance(strategy_backtest.get("metrics"), dict) else {}
    backtest_quality_status = str(strategy_backtest_quality.get("status") or "MISSING")
    backtest_quality_penalty = _backtest_quality_penalty(backtest_quality_status, strategy_backtest_quality)
    history_production = _history_production_metrics(history_production_status, strategy_backtest_quality)
    history_production_penalty = _history_production_penalty(history_production)
    execution_metrics = execution.get("metrics") if isinstance(execution.get("metrics"), dict) else {}
    execution_gate = execution.get("promotionGate") if isinstance(execution.get("promotionGate"), dict) else {}
    execution_blocker_codes = _execution_blocker_codes(execution_gate)
    has_seed_backtest = bool(seed and strategy_backtest)
    backtest_ok = bool(strategy_backtest.get("ok")) if strategy_backtest else False
    backtest_net_r = _num(backtest_metrics.get("netR"), 0)
    backtest_trade_count = int(_num(backtest_metrics.get("tradeCount"), 0))
    backtest_profit_factor = _num(backtest_metrics.get("profitFactor"), 0)
    backtest_win_rate = _num(backtest_metrics.get("winRate"), 0)
    backtest_max_drawdown = _num(backtest_metrics.get("maxDrawdownR"), 0)
    backtest_sharpe = _num(backtest_metrics.get("sharpe"), 0)
    backtest_sortino = _num(backtest_metrics.get("sortino"), 0)
    replay_net_r = _num(entry_relaxed.get("netRDelta") or summary.get("relaxedNetRDelta") or wf_summary.get("netRDelta"), 0)
    backtest_penalty = min(1.0, _num(backtest_metrics.get("maxDrawdownR"), 0) * 0.2)
    promotion_gate = parity.get("promotionGate") if isinstance(parity.get("promotionGate"), dict) else {}
    parity_status = parity.get("status") or "MISSING"
    parity_penalty = _parity_penalty(parity_status, promotion_gate)
    execution_penalty = _execution_penalty(execution_metrics)
    case_penalty = _case_penalty(cases)
    seed_wf_sample_count = int(_num(seed_wf_summary.get("sampleCount"), 0))
    sample_count = max(backtest_trade_count, seed_wf_sample_count) if has_seed_backtest else int(
        _num(summary.get("sampleCount") or wf_summary.get("sampleCount") or backtest_trade_count, 0)
    )
    net_r = backtest_net_r if has_seed_backtest else replay_net_r + min(1.0, backtest_net_r * 0.15)
    max_adverse_r = _num(backtest_metrics.get("maxAdverseR"), 0) if has_seed_backtest else (
        _num(entry_relaxed.get("maxAdverseR") or summary.get("maxAdverseR"), 0) - backtest_penalty
    )
    profit_capture = _num(backtest_metrics.get("profitCaptureRatio"), 0) if has_seed_backtest else _num(
        exit_let_run.get("profitCaptureRatio")
        or summary.get("profitCaptureRatio")
        or backtest_metrics.get("profitCaptureRatio"),
        0,
    )
    return {
        "sampleCount": sample_count,
        "netR": net_r,
        "maxAdverseR": max_adverse_r,
        "profitCaptureRatio": profit_capture,
        "missedOpportunityReduction": _num(entry_relaxed.get("missedOpportunityReduction") or summary.get("entryCountDelta"), 0),
        "validationNetRDelta": _num(seed_wf_summary.get("validationNetRDelta"), _num(wf_summary.get("validationNetRDelta"), 0)),
        "forwardNetRDelta": _num(seed_wf_summary.get("forwardNetRDelta"), _num(wf_summary.get("forwardNetRDelta"), 0)),
        "walkForward": seed_walk_forward,
        "strategyBacktest": {
            "required": backtest_required,
            "present": bool(strategy_backtest),
            "ok": backtest_ok,
            "runId": strategy_backtest.get("runId"),
            "strategyId": strategy_backtest.get("strategyId"),
            "seedId": strategy_backtest.get("seedId"),
            "strategyFamily": strategy_backtest.get("strategyFamily"),
            "direction": strategy_backtest.get("direction"),
            "engine": strategy_backtest.get("engine") if isinstance(strategy_backtest.get("engine"), dict) else {},
            "netR": _num(backtest_metrics.get("netR"), 0),
            "profitFactor": backtest_profit_factor,
            "winRate": backtest_win_rate,
            "maxDrawdownR": backtest_max_drawdown,
            "sharpe": backtest_sharpe,
            "sortino": backtest_sortino,
            "tradeCount": int(_num(backtest_metrics.get("tradeCount"), 0)),
            "evidenceQuality": strategy_backtest.get("evidenceQuality") or "LOW",
            "reasonZh": strategy_backtest.get("reasonZh") or "",
        },
        "parity": {
            "present": bool(parity),
            "status": parity_status,
            "promotionGateStatus": promotion_gate.get("status") or "MISSING",
            "promotionAllowed": bool(promotion_gate.get("promotionAllowed")) if promotion_gate else False,
            "blockerCount": int(_num(promotion_gate.get("blockerCount"), 0)) if promotion_gate else 0,
            "penalty": parity_penalty,
        },
        "executionFeedback": {
            "present": bool(execution),
            "sampleCount": int(_num(execution.get("sampleCount"), 0)),
            "promotionGateStatus": execution_gate.get("status") or ("MISSING" if not execution else "UNKNOWN"),
            "promotionAllowed": bool(execution_gate.get("promotionAllowed")) if execution_gate else False,
            "blockerCodes": execution_blocker_codes,
            "caseMemoryTriggerCount": len(execution.get("caseMemoryTriggers", [])) if isinstance(execution.get("caseMemoryTriggers"), list) else 0,
            "rejectCount": int(_num(execution_metrics.get("rejectCount"), 0)),
            "rejectRatePct": _num(execution_metrics.get("rejectRatePct"), 0),
            "dominantRejectReason": execution_metrics.get("dominantRejectReason") or "",
            "avgAbsSlippagePips": _num(execution_metrics.get("avgAbsSlippagePips"), 0),
            "maxAbsSlippagePips": _num(execution_metrics.get("maxAbsSlippagePips"), 0),
            "avgLatencyMs": _num(execution_metrics.get("avgLatencyMs"), 0),
            "acceptedWithoutFillCount": int(_num(execution_metrics.get("acceptedWithoutFillCount"), 0)),
            "policyMismatchCount": int(_num(execution_metrics.get("policyMismatchCount"), 0)),
            "fieldCompletenessStatus": execution_metrics.get("fieldCompletenessStatus") or "",
            "fieldCoveragePct": _num(execution_metrics.get("fieldCoveragePct"), 0),
            "coreMissingFieldCount": int(_num(execution_metrics.get("coreMissingFieldCount"), 0)),
            "conditionalMissingFieldCount": int(_num(execution_metrics.get("conditionalMissingFieldCount"), 0)),
            "penalty": execution_penalty,
        },
        "caseMemory": {
            "present": bool(cases),
            "caseCount": int(_num(cases.get("caseCount"), 0)),
            "queuedForGA": int(_num(cases.get("queuedForGA"), 0)),
            "caseTypeCounts": cases.get("caseTypeCounts") if isinstance(cases.get("caseTypeCounts"), dict) else {},
            "penalty": case_penalty,
            "strategyContractShadow": strategy_contract_shadow,
        },
        "strategyContractShadow": strategy_contract_shadow,
        "evidencePenalty": parity_penalty
        + execution_penalty
        + case_penalty
        + backtest_quality_penalty
        + history_production_penalty,
        "backtestQuality": {
            "present": bool(strategy_backtest_quality),
            "status": backtest_quality_status,
            "failedCount": int(_num(strategy_backtest_quality.get("failedCount"), 0)),
            "historyTargetSatisfied": bool(strategy_backtest_quality.get("historyTargetSatisfied")),
            "penalty": backtest_quality_penalty,
            "reasonZh": strategy_backtest_quality.get("reasonZh") or "",
        },
        "historyProductionStatus": history_production,
        "evidenceQuality": (
            seed_wf_summary.get("evidenceQuality")
            or entry_relaxed.get("evidenceQuality")
            or wf_summary.get("evidenceQuality")
            or strategy_backtest.get("evidenceQuality")
            or "LOW"
        ),
    }


def score_seed(seed: Dict[str, Any], runtime_dir: Path) -> Dict[str, Any]:
    metrics = evidence_metrics(runtime_dir, seed)
    backtest = metrics.get("strategyBacktest", {})
    backtest_trade_count = int(_num(backtest.get("tradeCount"), 0))
    family = seed.get("strategyFamily", "")
    direction = seed.get("direction", "")
    sample_count = metrics["sampleCount"]
    family_bonus = 0.25 if family == "RSI_Reversal" and direction == "LONG" else -0.15
    low_sample_penalty = max(0.0, (20 - sample_count) / 20.0)
    max_adverse_penalty = max(0.0, abs(min(0.0, metrics["maxAdverseR"])) - 0.5)
    max_drawdown_penalty = min(1.5, _num(backtest.get("maxDrawdownR"), 0) * 0.35)
    walk_forward = metrics.get("walkForward") if isinstance(metrics.get("walkForward"), dict) else {}
    walk_forward_summary = walk_forward.get("summary") if isinstance(walk_forward.get("summary"), dict) else {}
    walk_forward_penalty = _walk_forward_penalty(walk_forward_summary)
    walk_forward_stability_bonus = _walk_forward_stability_bonus(walk_forward_summary)
    overfit_penalty = max(
        _num(walk_forward_summary.get("overfitPenalty"), 0),
        0.25 if metrics["validationNetRDelta"] < 0 or metrics["forwardNetRDelta"] < 0 else 0.0,
    )
    backtest_no_trade_penalty = 2.0 if backtest.get("present") and backtest.get("ok") and backtest_trade_count == 0 else 0.0
    trade_frequency_penalty = 0.15 if sample_count == 0 else 0.0
    rsi_overfit_sample_penalty = _rsi_overfit_sample_penalty(family, direction, sample_count, overfit_penalty)
    rsi_min_trade_gate_penalty = _rsi_min_trade_gate_penalty(
        family,
        direction,
        sample_count,
        backtest_trade_count,
        metrics["netR"],
    )
    evidence_penalty = float(metrics.get("evidencePenalty", 0.0))
    strategy_contract_shadow_bonus = _strategy_contract_shadow_bonus(metrics.get("strategyContractShadow", {}))
    profit_factor_bonus = _profit_factor_bonus(_num(backtest.get("profitFactor"), 0))
    win_rate_bonus = _win_rate_bonus(_num(backtest.get("winRate"), 0))
    sharpe_bonus = _bounded_bonus(_num(backtest.get("sharpe"), 0), scale=0.12, cap=0.45)
    sortino_bonus = _bounded_bonus(_num(backtest.get("sortino"), 0), scale=0.08, cap=0.35)
    fitness = (
        metrics["netR"]
        + metrics["profitCaptureRatio"] * 0.5
        + metrics["missedOpportunityReduction"] * 0.2
        + profit_factor_bonus
        + win_rate_bonus
        + sharpe_bonus
        + sortino_bonus
        + walk_forward_stability_bonus
        + strategy_contract_shadow_bonus
        + family_bonus
        - max_drawdown_penalty
        - max_adverse_penalty
        - overfit_penalty
        - rsi_overfit_sample_penalty
        - rsi_min_trade_gate_penalty
        - backtest_no_trade_penalty
        - walk_forward_penalty
        - low_sample_penalty
        - trade_frequency_penalty
        - evidence_penalty
    )
    blocker = None
    history_production = metrics.get("historyProductionStatus", {})
    if not backtest.get("present"):
        blocker = "STRATEGY_BACKTEST_MISSING"
    elif not backtest.get("ok"):
        blocker = "STRATEGY_BACKTEST_FAILED"
    elif history_production.get("promotionGateStatus") == "BLOCKED":
        blocker = "HISTORY_PRODUCTION_NOT_READY"
    elif backtest_trade_count == 0:
        blocker = "STRATEGY_BACKTEST_NO_TRADES"
    elif sample_count < 5:
        blocker = "INSUFFICIENT_SAMPLES"
    elif _rsi_min_trade_gate_blocks(family, direction, sample_count, backtest_trade_count, metrics["netR"]):
        blocker = "RSI_MIN_TRADE_GATE"
    elif walk_forward_summary.get("promotionGateStatus") == "BLOCKED":
        blocker = walk_forward_summary.get("blockerCode") or "WALK_FORWARD_FAILED"
    elif overfit_penalty:
        blocker = "OVERFIT_RISK"
    elif metrics.get("parity", {}).get("promotionGateStatus") in {"BLOCKED", "MISSING"}:
        blocker = "PARITY_PROMOTION_GATE_BLOCKED"
    elif _execution_blocks_strategy_ranking(metrics.get("executionFeedback", {})):
        blocker = "PARITY_OR_EXECUTION_EVIDENCE_FAILED"
    elif evidence_penalty >= 1.0:
        blocker = "PARITY_OR_EXECUTION_EVIDENCE_FAILED"
    elif max_adverse_penalty > 0.5:
        blocker = "MAX_ADVERSE_TOO_HIGH"
    elif fitness < 0:
        blocker = "FITNESS_TOO_LOW"
    return {
        **metrics,
        "fitness": round(fitness, 4),
        "overfitPenalty": round(overfit_penalty, 4),
        "backtestNoTradePenalty": round(backtest_no_trade_penalty, 4),
        "walkForwardPenalty": round(walk_forward_penalty, 4),
        "walkForwardStabilityBonus": round(walk_forward_stability_bonus, 4),
        "lowSamplePenalty": round(low_sample_penalty, 4),
        "maxAdversePenalty": round(max_adverse_penalty, 4),
        "maxDrawdownPenalty": round(max_drawdown_penalty, 4),
        "tradeFrequencyPenalty": round(trade_frequency_penalty, 4),
        "rsiOverfitSamplePenalty": round(rsi_overfit_sample_penalty, 4),
        "rsiMinTradeGatePenalty": round(rsi_min_trade_gate_penalty, 4),
        "evidencePenalty": round(evidence_penalty, 4),
        "profitFactorBonus": round(profit_factor_bonus, 4),
        "winRateBonus": round(win_rate_bonus, 4),
        "sharpeBonus": round(sharpe_bonus, 4),
        "sortinoBonus": round(sortino_bonus, 4),
        "strategyContractShadowBonus": round(strategy_contract_shadow_bonus, 4),
        "blockerCode": blocker,
        "strategyBacktest": metrics.get("strategyBacktest", {}),
        "parity": metrics.get("parity", {}),
        "executionFeedback": metrics.get("executionFeedback", {}),
        "caseMemory": metrics.get("caseMemory", {}),
        "strategyContractShadow": metrics.get("strategyContractShadow", {}),
        "backtestQuality": metrics.get("backtestQuality", {}),
        "historyProductionStatus": metrics.get("historyProductionStatus", {}),
        "walkForward": metrics.get("walkForward", {}),
    }


def _rsi_overfit_sample_penalty(family: Any, direction: Any, sample_count: int, overfit_penalty: float) -> float:
    if family != "RSI_Reversal" or str(direction or "").upper() != "LONG" or overfit_penalty <= 0:
        return 0.0
    if sample_count >= 24:
        return 0.0
    return round(min(1.2, (24 - max(0, sample_count)) / 12.0), 4)


def _rsi_min_trade_gate_blocks(
    family: Any,
    direction: Any,
    sample_count: int,
    trade_count: int,
    net_r: float,
) -> bool:
    if family != "RSI_Reversal" or str(direction or "").upper() != "LONG":
        return False
    return net_r > 0 and max(sample_count, trade_count) < 20


def _rsi_min_trade_gate_penalty(
    family: Any,
    direction: Any,
    sample_count: int,
    trade_count: int,
    net_r: float,
) -> float:
    if not _rsi_min_trade_gate_blocks(family, direction, sample_count, trade_count, net_r):
        return 0.0
    effective_count = max(0, max(sample_count, trade_count))
    sample_gap = max(0, 20 - effective_count)
    return round(min(7.0, 1.0 + sample_gap * 0.32 + max(0.0, net_r) * 0.25), 4)


def _execution_penalty(metrics: Dict[str, Any]) -> float:
    if not metrics:
        return 0.0
    reject_penalty = min(0.45, _num(metrics.get("rejectRatePct"), 0) / 100.0 * 1.5)
    reject_count_penalty = min(0.25, _num(metrics.get("rejectCount"), 0) * 0.05)
    slippage_penalty = max(0.0, _num(metrics.get("avgAbsSlippagePips"), 0) - 0.8) * 0.35
    latency_penalty = max(0.0, _num(metrics.get("avgLatencyMs"), 0) - 1500.0) / 3000.0
    mismatch_penalty = min(0.5, _num(metrics.get("policyMismatchCount"), 0) * 0.25)
    ack_fill_penalty = min(0.25, max(0.0, _num(metrics.get("acceptedWithoutFillCount"), 0) - 2.0) * 0.05)
    field_gap_penalty = min(
        0.75,
        _num(metrics.get("coreMissingFieldCount"), 0) * 0.2
        + _num(metrics.get("conditionalMissingFieldCount"), 0) * 0.08,
    )
    return round(
        min(
            1.25,
            reject_penalty
            + reject_count_penalty
            + slippage_penalty
            + latency_penalty
            + mismatch_penalty
            + ack_fill_penalty
            + field_gap_penalty,
        ),
        4,
    )


def _parity_penalty(status: str, promotion_gate: Dict[str, Any]) -> float:
    if status == "PARITY_FAIL":
        return 1.0
    if not promotion_gate or promotion_gate.get("status") == "MISSING":
        return 0.65
    if promotion_gate.get("status") == "BLOCKED":
        # Missing EA/live evidence should not be confused with a proven
        # strategy failure, but it must still prevent promotion.
        return 0.65
    if status == "PARITY_WARN":
        return 0.2
    return 0.0


def _case_penalty(cases: Dict[str, Any]) -> float:
    type_counts = cases.get("caseTypeCounts") if isinstance(cases.get("caseTypeCounts"), dict) else {}
    if not type_counts:
        return 0.0
    execution_types = {
        "EXECUTION_REJECT",
        "EXECUTION_SLIPPAGE",
        "EXECUTION_LATENCY",
    }
    severe_count = sum(int(_num(type_counts.get(name), 0)) for name in execution_types)
    overfit_count = int(_num(type_counts.get("GA_OVERFIT"), 0))
    return round(min(0.5, severe_count * 0.08 + overfit_count * 0.05), 4)


def _execution_blocker_codes(execution_gate: Dict[str, Any]) -> List[str]:
    blockers = execution_gate.get("blockers") if isinstance(execution_gate.get("blockers"), list) else []
    return [str(row.get("code") or "") for row in blockers if isinstance(row, dict) and row.get("code")]


def _execution_blocks_strategy_ranking(execution_feedback: Dict[str, Any]) -> bool:
    if execution_feedback.get("promotionGateStatus") != "BLOCKED":
        return False
    blocker_codes = set(execution_feedback.get("blockerCodes") or [])
    if blocker_codes and blocker_codes <= {"LIVE_LANE_STRATEGY_LOCK_MISMATCH"}:
        return False
    return True


def _strategy_contract_shadow_metrics(cases: Dict[str, Any], seed: Dict[str, Any] | None) -> Dict[str, Any]:
    shadow = cases.get("strategyContractShadowEvaluation") if isinstance(cases.get("strategyContractShadowEvaluation"), dict) else {}
    generic_summary = shadow.get("genericAdapterSummary") if isinstance(shadow.get("genericAdapterSummary"), dict) else {}
    stable_families = shadow.get("genericAdapterStableFamilies") if isinstance(shadow.get("genericAdapterStableFamilies"), list) else []
    family = str((seed or {}).get("strategyFamily") or "")
    family_summary = generic_summary.get(family) if isinstance(generic_summary.get(family), dict) else {}
    return {
        "present": bool(shadow),
        "strategyFamily": family,
        "isGenericFamily": family in GENERIC_STRATEGY_FAMILIES,
        "adapterStable": family in stable_families,
        "stableFamilyCount": len(stable_families),
        "familyCount": int(_num(family_summary.get("count"), 0)),
        "implementedRows": int(_num(family_summary.get("implementedRows"), 0)),
        "shadowObserveCount": int(_num(family_summary.get("shadowObserveCount"), 0)),
        "shadowWouldEnterCount": int(_num(family_summary.get("shadowWouldEnterCount"), 0)),
        "guardBlockedCount": int(_num(family_summary.get("guardBlockedCount"), 0)),
        "adapterGapCount": int(_num(family_summary.get("adapterGapCount"), 0)),
        "latest": family_summary.get("latest") if isinstance(family_summary.get("latest"), dict) else {},
    }


def _strategy_contract_shadow_bonus(metrics: Dict[str, Any]) -> float:
    if not metrics or not metrics.get("isGenericFamily") or not metrics.get("adapterStable"):
        return 0.0
    if int(_num(metrics.get("adapterGapCount"), 0)) > 0:
        return 0.0
    observe_bonus = min(0.12, int(_num(metrics.get("shadowObserveCount"), 0)) * 0.03)
    signal_bonus = min(0.20, int(_num(metrics.get("shadowWouldEnterCount"), 0)) * 0.10)
    return round(min(0.35, 0.05 + observe_bonus + signal_bonus), 4)


def _backtest_quality_penalty(status: str, quality: Dict[str, Any]) -> float:
    if not quality:
        return 0.15
    if status == "PASS":
        return 0.0
    failed_count = int(_num(quality.get("failedCount"), 0))
    return round(min(0.6, 0.2 + failed_count * 0.08), 4)


def _history_production_metrics(production: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
    nested = quality.get("historyProductionStatus") if isinstance(quality.get("historyProductionStatus"), dict) else {}
    source = production if production else nested
    status = str(source.get("status") or "MISSING")
    target_satisfied = bool(source.get("historyTargetSatisfied"))
    failed_count = int(_num(source.get("failedCount"), 0))
    timeframe_rows = source.get("timeframes") if isinstance(source.get("timeframes"), dict) else {}
    source_meta = source.get("source") if isinstance(source.get("source"), dict) else {}
    promotion_blocked = status != "PASS" or not target_satisfied
    return {
        "present": bool(source),
        "status": status,
        "historyTargetSatisfied": target_satisfied,
        "promotionGateStatus": "BLOCKED" if promotion_blocked else "PASS",
        "promotionAllowed": not promotion_blocked,
        "failedCount": failed_count,
        "source": source_meta,
        "timeframes": timeframe_rows,
        "penalty": _history_production_penalty(
            {
                "present": bool(source),
                "status": status,
                "historyTargetSatisfied": target_satisfied,
                "failedCount": failed_count,
            }
        ),
        "reasonZh": source.get("reasonZh")
        or (
            "USDJPY 历史样本已达到生产级深度，GA 可使用完整 SQLite 回测评分。"
            if not promotion_blocked
            else "USDJPY 历史样本未达到生产级 PASS，GA 候选只能停留在 shadow/tester 证据。"
        ),
    }


def _history_production_penalty(production: Dict[str, Any]) -> float:
    if not production or not production.get("present"):
        return 0.5
    if production.get("status") == "PASS" and production.get("historyTargetSatisfied"):
        return 0.0
    failed_count = int(_num(production.get("failedCount"), 0))
    return round(min(0.9, 0.35 + failed_count * 0.1), 4)


def _profit_factor_bonus(value: float) -> float:
    if value <= 1.0:
        return -min(0.5, (1.0 - value) * 0.35)
    return min(0.75, (value - 1.0) * 0.45)


def _win_rate_bonus(value: float) -> float:
    if value <= 0:
        return 0.0
    return max(-0.35, min(0.35, (value - 50.0) / 100.0 * 0.7))


def _bounded_bonus(value: float, scale: float, cap: float) -> float:
    return max(-cap, min(cap, value * scale))


def _strategy_backtest_metrics(runtime_dir: Path, seed: Dict[str, Any] | None) -> Dict[str, Any]:
    if seed is None:
        return _load_json(runtime_dir / "backtest" / "QuantGod_StrategyBacktestReport.json")
    try:
        from tools.usdjpy_strategy_backtest.report import run_backtest
    except ModuleNotFoundError:  # pragma: no cover
        from usdjpy_strategy_backtest.report import run_backtest

    report = run_backtest(runtime_dir, seed, write=False, include_coverage_matrix=False)
    return report if isinstance(report, dict) else {}


def _seed_walk_forward_metrics(runtime_dir: Path, seed: Dict[str, Any] | None) -> Dict[str, Any]:
    if seed is None:
        return _load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYSeedWalkForwardReport.json")
    try:
        from tools.usdjpy_strategy_backtest.walk_forward import build_seed_walk_forward
    except ModuleNotFoundError:  # pragma: no cover
        from usdjpy_strategy_backtest.walk_forward import build_seed_walk_forward

    report = build_seed_walk_forward(runtime_dir, seed, write=False)
    return report if isinstance(report, dict) else {}


def _walk_forward_penalty(summary: Dict[str, Any]) -> float:
    if not summary:
        return 0.35
    penalty = 0.0
    if summary.get("promotionGateStatus") == "BLOCKED":
        penalty += 0.45
    penalty += _num(summary.get("overfitPenalty"), 0) * 0.65
    if _num(summary.get("validationNetR"), 0) < 0:
        penalty += 0.2
    if _num(summary.get("forwardNetR"), 0) < 0:
        penalty += 0.3
    if int(_num(summary.get("validSegmentCount"), 0)) < 3:
        penalty += 0.25
    return round(min(1.25, penalty), 4)


def _walk_forward_stability_bonus(summary: Dict[str, Any]) -> float:
    if not summary:
        return 0.0
    stability = _num(summary.get("stabilityScore"), 0)
    validation_net = _num(summary.get("validationNetR"), 0)
    forward_net = _num(summary.get("forwardNetR"), 0)
    sample_count = int(_num(summary.get("sampleCount"), 0))
    if validation_net < 0 or forward_net < 0 or sample_count < 5:
        return 0.0
    return round(min(0.6, stability * 0.35 + min(0.25, sample_count / 80.0)), 4)
