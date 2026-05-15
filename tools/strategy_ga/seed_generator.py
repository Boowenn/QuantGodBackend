from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.strategy_json.schema import base_strategy_seed
except ModuleNotFoundError:  # pragma: no cover
    from strategy_json.schema import base_strategy_seed

SUPPORTED_CASE_MEMORY_FAMILIES = {
    "RSI_Reversal",
    "MA_Cross",
    "BB_Triple",
    "MACD_Divergence",
    "SR_Breakout",
    "USDJPY_TOKYO_RANGE_BREAKOUT",
    "USDJPY_NIGHT_REVERSION_SAFE",
    "USDJPY_H4_TREND_PULLBACK",
}
GOVERNANCE_ONLY_HINTS = {"verify_live_lane_strategy_lock"}


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


def exploration_seed_pool(generation_number: int, population_size: int = 16) -> List[Dict[str, Any]]:
    """Create deterministic wide-search seeds when no elite survived.

    The point of this pool is to avoid repeatedly scoring the same weak first
    population. It stays inside Strategy JSON safety limits, but fans out RSI,
    exit, and risk-pip parameters across all MT5 shadow families.
    """
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
    periods = [7, 9, 14, 21, 28, 34]
    buy_bands = [24, 28, 30, 32, 34, 36, 38, 40, 42]
    crossbacks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5]
    breakevens = [0.4, 0.7, 1.0, 1.3, 1.6]
    trails = [0.8, 1.1, 1.5, 2.0, 2.5]
    givebacks = [0.4, 0.5, 0.6, 0.7, 0.8]
    hold_bars = [3, 4, 6, 8, 10, 12]
    risk_pips = [5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
    opportunity_multipliers = [0.2, 0.35, 0.5, 0.75]
    ma_fast_periods = [5, 8, 9, 13, 21]
    ma_slow_periods = [18, 21, 34, 55, 89]
    bb_periods = [14, 18, 20, 24, 30]
    bb_deviations = [1.6, 1.8, 2.0, 2.2, 2.5]
    macd_fast_periods = [8, 10, 12, 15]
    macd_slow_periods = [21, 26, 34, 45]
    macd_signal_periods = [5, 7, 9, 12]
    sr_lookbacks = [12, 18, 24, 36, 48, 72]
    breakout_buffers = [0.0, 1.0, 2.0, 3.5, 5.0]
    tokyo_trade_windows = [(2, 5), (3, 6), (4, 7)]
    night_windows = [(20, 2), (21, 3), (22, 4)]
    h4_fast_periods = [13, 20, 34]
    h4_slow_periods = [50, 89, 144]
    h4_pullback_periods = [13, 20, 34]

    seeds: List[Dict[str, Any]] = []
    phase_base = max(0, generation_number - 2) * max(1, population_size)
    for index in range(population_size):
        phase = phase_base + index
        family = families[phase % len(families)]
        direction = "LONG" if (phase // len(families)) % 2 == 0 else "SHORT"
        seed = base_strategy_seed(f"GA-USDJPY-G{generation_number:04d}-X{index + 1:04d}", family=family, direction=direction)
        seed["source"] = "EXPLORATION_GRID"
        seed["explorationMode"] = "NO_ELITE_EXPAND_SEARCH"
        seed["explorationReasonZh"] = "上一代没有 elite，Agent 自动扩大 Strategy JSON 参数搜索空间。"
        seed["strategyId"] = f"USDJPY_{family.upper()}_{direction}_EXPLORE_{generation_number:03d}_{index + 1:03d}"

        rsi = seed.setdefault("indicators", {}).setdefault("rsi", {})
        indicators = seed.setdefault("indicators", {})
        exit_cfg = seed.setdefault("exit", {})
        risk = seed.setdefault("risk", {})
        rsi["period"] = periods[phase % len(periods)]
        rsi["buyBand"] = buy_bands[(phase // len(periods)) % len(buy_bands)]
        rsi["crossbackThreshold"] = crossbacks[(phase // (len(periods) * len(buy_bands))) % len(crossbacks)]
        rsi["timeframe"] = ["M15", "H1", "M5"][phase % 3]
        ma = indicators.setdefault("ma", {})
        ma_fast = ma_fast_periods[phase % len(ma_fast_periods)]
        ma_slow = ma_slow_periods[(phase // 2) % len(ma_slow_periods)]
        ma["fastPeriod"] = min(ma_fast, ma_slow - 1)
        ma["slowPeriod"] = ma_slow
        ma["timeframe"] = ["M15", "H1", "M5"][phase % 3]
        bollinger = indicators.setdefault("bollinger", {})
        bollinger["period"] = bb_periods[phase % len(bb_periods)]
        bollinger["deviations"] = bb_deviations[(phase // 2) % len(bb_deviations)]
        bollinger["reclaimBufferPips"] = breakout_buffers[(phase // 3) % len(breakout_buffers)]
        bollinger["timeframe"] = ["M15", "H1", "M5"][phase % 3]
        macd = indicators.setdefault("macd", {})
        macd_fast = macd_fast_periods[phase % len(macd_fast_periods)]
        macd_slow = macd_slow_periods[(phase // 2) % len(macd_slow_periods)]
        macd["fastPeriod"] = min(macd_fast, macd_slow - 1)
        macd["slowPeriod"] = macd_slow
        macd["signalPeriod"] = macd_signal_periods[(phase // 3) % len(macd_signal_periods)]
        macd["minHistogramAbs"] = [0.0, 0.0005, 0.001, 0.002][phase % 4]
        macd["timeframe"] = ["M15", "H1", "M5"][phase % 3]
        support_resistance = indicators.setdefault("supportResistance", {})
        support_resistance["lookbackBars"] = sr_lookbacks[phase % len(sr_lookbacks)]
        support_resistance["breakoutBufferPips"] = breakout_buffers[(phase // 2) % len(breakout_buffers)]
        support_resistance["timeframe"] = ["M15", "H1", "M5"][phase % 3]
        tokyo = indicators.setdefault("tokyoRange", {})
        tokyo_start, tokyo_end = tokyo_trade_windows[phase % len(tokyo_trade_windows)]
        tokyo["tradeStartHourUtc"] = tokyo_start
        tokyo["tradeEndHourUtc"] = tokyo_end
        tokyo["rangeStartHourUtc"] = max(0, tokyo_start - 3)
        tokyo["rangeEndHourUtc"] = max(0, tokyo_start - 1)
        tokyo["lookbackBars"] = [6, 8, 12, 16][phase % 4]
        tokyo["bufferPips"] = breakout_buffers[(phase // 4) % len(breakout_buffers)]
        tokyo["timeframe"] = "M15"
        night = indicators.setdefault("nightReversion", {})
        night_start, night_end = night_windows[phase % len(night_windows)]
        night["startHourUtc"] = night_start
        night["endHourUtc"] = night_end
        night["bollingerPeriod"] = bb_periods[(phase // 2) % len(bb_periods)]
        night["deviations"] = [1.4, 1.6, 1.8, 2.0, 2.2][phase % 5]
        night["entryBufferPips"] = [0.0, 0.5, 1.0, 1.5][phase % 4]
        night["timeframe"] = "M15"
        h4 = indicators.setdefault("h4Pullback", {})
        h4_fast = h4_fast_periods[phase % len(h4_fast_periods)]
        h4_slow = h4_slow_periods[(phase // 2) % len(h4_slow_periods)]
        h4["fastEmaPeriod"] = min(h4_fast, h4_slow - 1)
        h4["slowEmaPeriod"] = h4_slow
        h4["pullbackEmaPeriod"] = h4_pullback_periods[(phase // 3) % len(h4_pullback_periods)]
        h4["rsiPeriod"] = periods[(phase // 4) % len(periods)]
        h4["longRsiMin"] = [35, 38, 42, 46][phase % 4]
        h4["shortRsiMax"] = [54, 58, 62, 66][phase % 4]
        h4["timeframe"] = "H4"
        exit_cfg["breakevenDelayR"] = breakevens[(phase // 2) % len(breakevens)]
        exit_cfg["trailStartR"] = trails[(phase // 3) % len(trails)]
        exit_cfg["mfeGivebackPct"] = givebacks[(phase // 5) % len(givebacks)]
        exit_cfg["timeStopBars"] = {
            "M15": hold_bars[phase % len(hold_bars)],
            "H1": hold_bars[(phase // 2) % len(hold_bars)],
        }
        risk["riskPips"] = risk_pips[(phase // 3) % len(risk_pips)]
        risk["opportunityLotMultiplier"] = opportunity_multipliers[(phase // 4) % len(opportunity_multipliers)]
        risk["stage"] = "SHADOW"
        risk["maxLot"] = min(2.0, float(risk.get("maxLot", 2.0)))
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
    strategy_cases = [case for case in cases if _is_strategy_seed_case(case)]
    for index, case in enumerate(strategy_cases[:limit], start=1):
        action = case.get("proposedAction") if isinstance(case.get("proposedAction"), dict) else {}
        hint = str(case.get("mutationHint") or action.get("mutationHint") or "case_memory_observe")
        family = _case_strategy_family(case)
        direction = _case_direction(case)
        seed = base_strategy_seed(f"GA-USDJPY-CASE-{index:04d}", family=family, direction=direction)
        seed["source"] = "CASE_MEMORY"
        seed["caseId"] = case.get("caseId")
        seed["caseType"] = case.get("caseType") or case.get("type")
        seed["casePriority"] = case.get("priority") or action.get("priority") or "MEDIUM"
        seed["caseReasonZh"] = case.get("reasonZh") or case.get("rootCause")
        seed["mutationHint"] = hint
        seed["strategyId"] = f"USDJPY_{_strategy_id_token(family)}_{direction}_CASE_{_strategy_id_token(hint)}_{index:03d}"
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


def _is_strategy_seed_case(case: Dict[str, Any]) -> bool:
    action = case.get("proposedAction") if isinstance(case.get("proposedAction"), dict) else {}
    hint = str(case.get("mutationHint") or action.get("mutationHint") or "")
    if action.get("generateStrategyJsonCandidate") is False or case.get("generateStrategyJsonCandidate") is False:
        return False
    return hint not in GOVERNANCE_ONLY_HINTS


def _case_strategy_family(case: Dict[str, Any]) -> str:
    action = case.get("proposedAction") if isinstance(case.get("proposedAction"), dict) else {}
    raw = (
        case.get("strategyFamily")
        or case.get("strategy")
        or action.get("strategyFamily")
        or action.get("strategy")
        or "RSI_Reversal"
    )
    family = str(raw or "RSI_Reversal")
    return family if family in SUPPORTED_CASE_MEMORY_FAMILIES else "RSI_Reversal"


def _case_direction(case: Dict[str, Any]) -> str:
    action = case.get("proposedAction") if isinstance(case.get("proposedAction"), dict) else {}
    raw = str(case.get("direction") or action.get("direction") or "LONG").upper()
    return raw if raw in {"LONG", "SHORT"} else "LONG"


def _strategy_id_token(value: str) -> str:
    return (
        str(value or "")
        .upper()
        .replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
    )


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
