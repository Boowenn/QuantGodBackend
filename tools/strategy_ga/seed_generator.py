from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.strategy_json.schema import base_strategy_seed
except ModuleNotFoundError:  # pragma: no cover
    from strategy_json.schema import base_strategy_seed


def initial_seed_pool(population_size: int = 16) -> List[Dict[str, Any]]:
    """Create deterministic Strategy JSON seeds for the first GA generation."""
    families = [
        "RSI_Reversal",
        "MA_Cross",
        "BB_Triple",
        "MACD_Divergence",
        "SR_Breakout",
        "USDJPY_TOKYO_RANGE_BREAKOUT",
        "USDJPY_NIGHT_REVERSION_SAFE",
        "USDJPY_H4_TREND_PULLBACK",
    ]
    seeds: List[Dict[str, Any]] = []
    for index in range(population_size):
        family = families[index % len(families)]
        direction = "LONG" if index % 3 != 1 else "SHORT"
        seed = base_strategy_seed(f"GA-USDJPY-{index + 1:04d}", family=family, direction=direction)
        seed["source"] = "LLM_SEED" if index < 4 else "MANUAL_ARCHIVE_IMPORT"
        seed["strategyId"] = f"USDJPY_{family.upper()}_{direction}_SEED_{index + 1:03d}"
        rsi = seed["indicators"]["rsi"]
        rsi["buyBand"] = 30 + (index % 7)
        rsi["crossbackThreshold"] = round(0.4 + (index % 5) * 0.2, 2)
        seed["exit"]["breakevenDelayR"] = round(0.8 + (index % 4) * 0.1, 2)
        seed["exit"]["mfeGivebackPct"] = round(0.52 + (index % 5) * 0.03, 2)
        seeds.append(seed)
    return seeds


def clone_seed(seed: Dict[str, Any], seed_id: str, source: str) -> Dict[str, Any]:
    cloned = deepcopy(seed)
    cloned["seedId"] = seed_id
    cloned["source"] = source
    return cloned


def case_memory_seed_pool(runtime_dir: Path, limit: int = 6) -> List[Dict[str, Any]]:
    """Turn Case Memory into safe Strategy JSON seeds for GA shadow research."""
    cases = _load_case_memory(runtime_dir)
    seeds: List[Dict[str, Any]] = []
    for index, case in enumerate(cases[:limit], start=1):
        action = case.get("proposedAction") if isinstance(case.get("proposedAction"), dict) else {}
        hint = str(case.get("mutationHint") or action.get("mutationHint") or "case_memory_observe")
        seed = base_strategy_seed(f"GA-USDJPY-CASE-{index:04d}", family="RSI_Reversal", direction="LONG")
        seed["source"] = "CASE_MEMORY"
        seed["caseId"] = case.get("caseId")
        seed["caseType"] = case.get("caseType") or case.get("type")
        seed["casePriority"] = case.get("priority") or action.get("priority") or "MEDIUM"
        seed["caseReasonZh"] = case.get("reasonZh") or case.get("rootCause")
        seed["mutationHint"] = hint
        seed["strategyId"] = f"USDJPY_RSI_REVERSAL_LONG_CASE_{hint.upper()}_{index:03d}"
        _apply_case_hint(seed, hint)
        seeds.append(seed)
    return seeds


def _load_case_memory(runtime_dir: Path) -> List[Dict[str, Any]]:
    summary = runtime_dir / "evidence_os" / "QuantGod_CaseMemorySummary.json"
    try:
        if summary.exists():
            data = json.loads(summary.read_text(encoding="utf-8"))
            hints = data.get("gaSeedHints") if isinstance(data.get("gaSeedHints"), list) else []
            if hints:
                return [
                    row
                    for row in hints
                    if isinstance(row, dict)
                    and row.get("status", "QUEUED_FOR_GA") == "QUEUED_FOR_GA"
                ]
            rows = data.get("cases") if isinstance(data.get("cases"), list) else []
            return [row for row in rows if isinstance(row, dict) and row.get("status") == "QUEUED_FOR_GA"]
    except Exception:
        pass
    return []


def _apply_case_hint(seed: Dict[str, Any], hint: str) -> None:
    rsi = seed.setdefault("indicators", {}).setdefault("rsi", {})
    exit_cfg = seed.setdefault("exit", {})
    risk = seed.setdefault("risk", {})
    if hint in {"relax_rsi_crossback", "keep_soft_news_gate"}:
        rsi["buyBand"] = min(38, float(rsi.get("buyBand", 34)) + 1)
        rsi["crossbackThreshold"] = max(0.3, round(float(rsi.get("crossbackThreshold", 0.8)) - 0.2, 2))
    elif hint == "let_profit_run":
        exit_cfg["breakevenDelayR"] = max(1.0, float(exit_cfg.get("breakevenDelayR", 1.0)))
        exit_cfg["trailStartR"] = max(1.5, float(exit_cfg.get("trailStartR", 1.5)))
        exit_cfg["mfeGivebackPct"] = min(0.68, max(0.6, float(exit_cfg.get("mfeGivebackPct", 0.6)) + 0.05))
    elif hint in {"tighten_entry_filter", "tighten_execution_filter"}:
        rsi["buyBand"] = max(30, float(rsi.get("buyBand", 34)) - 1)
        rsi["crossbackThreshold"] = min(1.2, round(float(rsi.get("crossbackThreshold", 0.8)) + 0.2, 2))
        risk["opportunityLotMultiplier"] = min(0.35, float(risk.get("opportunityLotMultiplier", 0.35)))
    elif hint in {"inspect_execution_quality", "reduce_execution_latency", "verify_execution_ack_fill_sync", "verify_ea_policy_sync"}:
        risk["opportunityLotMultiplier"] = min(0.25, float(risk.get("opportunityLotMultiplier", 0.35)))
        seed.setdefault("entry", {}).setdefault("conditions", []).append("executionQuality != DEGRADED")
    elif hint == "promote_contract_candidate_to_tester":
        rsi["buyBand"] = min(37, float(rsi.get("buyBand", 34)) + 0.5)
        seed.setdefault("entry", {}).setdefault("conditions", []).append("strategyContractShadowSignal == true")
    elif hint in {"add_ea_contract_adapter_family", "repair_strategy_json_contract_safety"}:
        risk["opportunityLotMultiplier"] = min(0.20, float(risk.get("opportunityLotMultiplier", 0.35)))
        seed.setdefault("entry", {}).setdefault("conditions", []).append("strategyContractAdapterReady == true")
    risk["stage"] = "SHADOW"
    risk["maxLot"] = min(2.0, float(risk.get("maxLot", 2.0)))
