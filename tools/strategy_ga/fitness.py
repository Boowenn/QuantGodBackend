from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


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
    parity = _load_json(runtime_dir / "evidence_os" / "QuantGod_StrategyParityReport.json")
    execution = _load_json(runtime_dir / "evidence_os" / "QuantGod_LiveExecutionQualityReport.json")
    cases = _load_json(runtime_dir / "evidence_os" / "QuantGod_CaseMemorySummary.json")
    entry_relaxed = _variant_metrics(replay, "entryComparison", 1)
    exit_let_run = _variant_metrics(replay, "exitComparison", 1)
    summary = replay.get("summary") if isinstance(replay.get("summary"), dict) else {}
    wf_summary = walk_forward.get("summary") if isinstance(walk_forward.get("summary"), dict) else {}
    backtest_metrics = strategy_backtest.get("metrics") if isinstance(strategy_backtest.get("metrics"), dict) else {}
    execution_metrics = execution.get("metrics") if isinstance(execution.get("metrics"), dict) else {}
    execution_gate = execution.get("promotionGate") if isinstance(execution.get("promotionGate"), dict) else {}
    has_seed_backtest = bool(seed and strategy_backtest)
    backtest_net_r = _num(backtest_metrics.get("netR"), 0)
    backtest_trade_count = int(_num(backtest_metrics.get("tradeCount"), 0))
    replay_net_r = _num(entry_relaxed.get("netRDelta") or summary.get("relaxedNetRDelta") or wf_summary.get("netRDelta"), 0)
    backtest_penalty = min(1.0, _num(backtest_metrics.get("maxDrawdownR"), 0) * 0.2)
    promotion_gate = parity.get("promotionGate") if isinstance(parity.get("promotionGate"), dict) else {}
    parity_status = parity.get("status") or "MISSING"
    parity_penalty = _parity_penalty(parity_status, promotion_gate)
    execution_penalty = _execution_penalty(execution_metrics)
    case_penalty = _case_penalty(cases)
    sample_count = backtest_trade_count if has_seed_backtest else int(
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
        "validationNetRDelta": _num(wf_summary.get("validationNetRDelta"), 0),
        "forwardNetRDelta": _num(wf_summary.get("forwardNetRDelta"), 0),
        "strategyBacktest": {
            "present": bool(strategy_backtest),
            "runId": strategy_backtest.get("runId"),
            "strategyId": strategy_backtest.get("strategyId"),
            "seedId": strategy_backtest.get("seedId"),
            "strategyFamily": strategy_backtest.get("strategyFamily"),
            "direction": strategy_backtest.get("direction"),
            "engine": strategy_backtest.get("engine") if isinstance(strategy_backtest.get("engine"), dict) else {},
            "netR": _num(backtest_metrics.get("netR"), 0),
            "profitFactor": _num(backtest_metrics.get("profitFactor"), 0),
            "winRate": _num(backtest_metrics.get("winRate"), 0),
            "maxDrawdownR": _num(backtest_metrics.get("maxDrawdownR"), 0),
            "sharpe": _num(backtest_metrics.get("sharpe"), 0),
            "tradeCount": int(_num(backtest_metrics.get("tradeCount"), 0)),
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
        },
        "evidencePenalty": parity_penalty + execution_penalty + case_penalty,
        "evidenceQuality": entry_relaxed.get("evidenceQuality") or wf_summary.get("evidenceQuality") or strategy_backtest.get("evidenceQuality") or "LOW",
    }


def score_seed(seed: Dict[str, Any], runtime_dir: Path) -> Dict[str, Any]:
    metrics = evidence_metrics(runtime_dir, seed)
    family = seed.get("strategyFamily", "")
    direction = seed.get("direction", "")
    sample_count = metrics["sampleCount"]
    family_bonus = 0.25 if family == "RSI_Reversal" and direction == "LONG" else -0.15
    low_sample_penalty = max(0.0, (20 - sample_count) / 20.0)
    max_adverse_penalty = max(0.0, abs(min(0.0, metrics["maxAdverseR"])) - 0.5)
    overfit_penalty = 0.25 if metrics["validationNetRDelta"] < 0 or metrics["forwardNetRDelta"] < 0 else 0.0
    trade_frequency_penalty = 0.15 if sample_count == 0 else 0.0
    evidence_penalty = float(metrics.get("evidencePenalty", 0.0))
    fitness = (
        metrics["netR"]
        + metrics["profitCaptureRatio"] * 0.5
        + metrics["missedOpportunityReduction"] * 0.2
        + family_bonus
        - max_adverse_penalty
        - overfit_penalty
        - low_sample_penalty
        - trade_frequency_penalty
        - evidence_penalty
    )
    blocker = None
    if sample_count < 5:
        blocker = "INSUFFICIENT_SAMPLES"
    elif overfit_penalty:
        blocker = "OVERFIT_RISK"
    elif metrics.get("parity", {}).get("promotionGateStatus") in {"BLOCKED", "MISSING"}:
        blocker = "PARITY_PROMOTION_GATE_BLOCKED"
    elif metrics.get("executionFeedback", {}).get("promotionGateStatus") == "BLOCKED":
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
        "lowSamplePenalty": round(low_sample_penalty, 4),
        "maxAdversePenalty": round(max_adverse_penalty, 4),
        "tradeFrequencyPenalty": round(trade_frequency_penalty, 4),
        "evidencePenalty": round(evidence_penalty, 4),
        "blockerCode": blocker,
        "strategyBacktest": metrics.get("strategyBacktest", {}),
        "parity": metrics.get("parity", {}),
        "executionFeedback": metrics.get("executionFeedback", {}),
        "caseMemory": metrics.get("caseMemory", {}),
    }


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
        "POLICY_MISMATCH",
    }
    severe_count = sum(int(_num(type_counts.get(name), 0)) for name in execution_types)
    overfit_count = int(_num(type_counts.get("GA_OVERFIT"), 0))
    return round(min(0.5, severe_count * 0.08 + overfit_count * 0.05), 4)


def _strategy_backtest_metrics(runtime_dir: Path, seed: Dict[str, Any] | None) -> Dict[str, Any]:
    if seed is None:
        return _load_json(runtime_dir / "backtest" / "QuantGod_StrategyBacktestReport.json")
    try:
        from tools.usdjpy_strategy_backtest.report import run_backtest
    except ModuleNotFoundError:  # pragma: no cover
        from usdjpy_strategy_backtest.report import run_backtest

    report = run_backtest(runtime_dir, seed, write=False)
    return report if isinstance(report, dict) else {}
