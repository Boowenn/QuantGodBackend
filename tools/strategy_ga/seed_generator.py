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
QUALITY_REPAIR_BLOCKERS = {
    "WALK_FORWARD_UNSTABLE",
    "WALK_FORWARD_INSUFFICIENT",
    "MAX_ADVERSE_TOO_HIGH",
    "INSUFFICIENT_SAMPLES",
    "STRATEGY_BACKTEST_NO_TRADES",
    "OVERFIT_RISK",
    "OVERFIT_RISK_HIGH",
    "FITNESS_NOT_POSITIVE",
}
P4_10D_RSI_FOCUS_BLOCKERS = {
    "OVERFIT_RISK",
    "OVERFIT_RISK_HIGH",
    "WALK_FORWARD_UNSTABLE",
    "WALK_FORWARD_INSUFFICIENT",
    "INSUFFICIENT_SAMPLES",
}
DANGEROUS_REPAIR_BLOCKERS = {
    "SAFETY_REJECTED",
    "DUPLICATE_STRATEGY",
    "HISTORY_PRODUCTION_NOT_READY",
    "NON_USDJPY_REJECTED",
}
FAMILY_CONFIG_KEYS = {
    "RSI_Reversal": "rsi",
    "MA_Cross": "ma",
    "BB_Triple": "bollinger",
    "MACD_Divergence": "macd",
    "SR_Breakout": "supportResistance",
    "USDJPY_TOKYO_RANGE_BREAKOUT": "tokyoRange",
    "USDJPY_NIGHT_REVERSION_SAFE": "nightReversion",
    "USDJPY_H4_TREND_PULLBACK": "h4Pullback",
}


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


def quality_repair_seed_pool(runtime_dir: Path, generation_number: int, limit: int = 8) -> List[Dict[str, Any]]:
    """Create blocker-aware search seeds from the best rejected candidates.

    P4-10 deliberately expands candidate quality instead of making more of the
    same grid. Each repair keeps the Strategy JSON in shadow mode and targets
    the blocker that stopped a promising parent.
    """
    if limit <= 0:
        return []
    rows = _quality_repair_candidate_rows(runtime_dir)
    parent_limit = min(len(rows), max(4, min(limit, 6)))
    rows = rows[:parent_limit]
    seeds: List[Dict[str, Any]] = []
    offset = 1
    max_profile_count = max((len(_repair_profiles_for_row(row)) for row in rows), default=0)
    for profile_index in range(max_profile_count):
        for row in rows:
            profiles = _repair_profiles_for_row(row)
            if profile_index >= len(profiles):
                continue
            seed = _build_quality_repair_seed(row, generation_number, offset, profiles[profile_index])
            if not seed:
                continue
            seeds.append(seed)
            offset += 1
            if len(seeds) >= limit:
                return seeds
    return seeds


def _quality_repair_candidate_rows(runtime_dir: Path) -> List[Dict[str, Any]]:
    candidate_file = runtime_dir / "ga" / "QuantGod_GACandidateRuns.jsonl"
    if not candidate_file.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in candidate_file.read_text(encoding="utf-8").splitlines()[-4096:]:
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
        blocker = str(row.get("blockerCode") or "")
        if not seed or blocker in DANGEROUS_REPAIR_BLOCKERS:
            continue
        if blocker not in QUALITY_REPAIR_BLOCKERS and _num(row.get("fitness"), -99.0) < -15:
            continue
        rows.append(row)
    best_by_parent: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
        parent_id = str(seed.get("seedId") or row.get("seedId") or "")
        if not parent_id:
            continue
        current = best_by_parent.get(parent_id)
        if current is None or _quality_repair_sort_key(row) > _quality_repair_sort_key(current):
            best_by_parent[parent_id] = row
    deduped = list(best_by_parent.values())
    deduped.sort(key=_quality_repair_sort_key, reverse=True)
    return _balanced_quality_repair_rows(deduped, limit=24)


def _balanced_quality_repair_rows(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    rsi_focus_limit = max(1, min(3, limit // 2))
    for row in sorted((row for row in rows if _is_p4_10d_rsi_focus_row(row)), key=_rsi_focus_sort_key, reverse=True):
        if _selected_family_count(selected, "RSI_Reversal") >= rsi_focus_limit:
            break
        _append_balanced_row(selected, seen, row, limit)
    family_priority = [
        "RSI_Reversal",
        "MACD_Divergence",
        "USDJPY_H4_TREND_PULLBACK",
    ]
    for family in family_priority:
        for row in rows:
            seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
            row_family = str(seed.get("strategyFamily") or row.get("strategyFamily") or "")
            if row_family != family:
                continue
            if _append_balanced_row(selected, seen, row, limit):
                break
    blocker_priority = [
        "WALK_FORWARD_UNSTABLE",
        "OVERFIT_RISK",
        "MAX_ADVERSE_TOO_HIGH",
        "INSUFFICIENT_SAMPLES",
        "STRATEGY_BACKTEST_NO_TRADES",
        "WALK_FORWARD_INSUFFICIENT",
        "OVERFIT_RISK_HIGH",
        "FITNESS_NOT_POSITIVE",
    ]
    for blocker in blocker_priority:
        for row in rows:
            if str(row.get("blockerCode") or "") != blocker:
                continue
            if _row_family(row) == "RSI_Reversal" and _selected_family_count(selected, "RSI_Reversal") >= rsi_focus_limit:
                continue
            if _append_balanced_row(selected, seen, row, limit):
                break
    for row in rows:
        if len(selected) >= limit:
            break
        _append_balanced_row(selected, seen, row, limit)
    return selected


def _selected_family_count(rows: List[Dict[str, Any]], family: str) -> int:
    return sum(1 for row in rows if _row_family(row) == family)


def _row_family(row: Dict[str, Any]) -> str:
    seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
    return str(seed.get("strategyFamily") or row.get("strategyFamily") or "")


def _is_p4_10d_rsi_focus_row(row: Dict[str, Any]) -> bool:
    if _row_family(row) != "RSI_Reversal":
        return False
    blocker = str(row.get("blockerCode") or "")
    if blocker not in P4_10D_RSI_FOCUS_BLOCKERS:
        return False
    breakdown = row.get("fitnessBreakdown") if isinstance(row.get("fitnessBreakdown"), dict) else {}
    backtest = breakdown.get("strategyBacktest") if isinstance(breakdown.get("strategyBacktest"), dict) else {}
    sample_count = int(_num(breakdown.get("sampleCount"), 0))
    trade_count = int(_num(backtest.get("tradeCount"), 0))
    return _num(row.get("fitness"), -99.0) > -8.0 or max(sample_count, trade_count) >= 12


def _rsi_focus_sort_key(row: Dict[str, Any]) -> tuple:
    breakdown = row.get("fitnessBreakdown") if isinstance(row.get("fitnessBreakdown"), dict) else {}
    backtest = breakdown.get("strategyBacktest") if isinstance(breakdown.get("strategyBacktest"), dict) else {}
    walk_forward = breakdown.get("walkForward") if isinstance(breakdown.get("walkForward"), dict) else {}
    summary = walk_forward.get("summary") if isinstance(walk_forward.get("summary"), dict) else {}
    sample_count = int(_num(breakdown.get("sampleCount"), 0))
    trade_count = int(_num(backtest.get("tradeCount"), 0))
    blocker = str(row.get("blockerCode") or "")
    return (
        1 if blocker in {"OVERFIT_RISK", "OVERFIT_RISK_HIGH"} else 0,
        min(40, max(sample_count, trade_count)),
        _num(summary.get("stabilityScore"), 0.0),
        _num(row.get("fitness"), -99.0),
        _num(row.get("generation"), 0.0),
        -_num(row.get("rank"), 9999.0),
    )


def _append_balanced_row(
    selected: List[Dict[str, Any]],
    seen: set[str],
    row: Dict[str, Any],
    limit: int,
) -> bool:
    if len(selected) >= limit:
        return False
    seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
    identity = str(seed.get("seedId") or row.get("seedId") or "")
    if not identity or identity in seen:
        return False
    seen.add(identity)
    selected.append(row)
    return True


def _build_quality_repair_seed(
    row: Dict[str, Any],
    generation_number: int,
    offset: int,
    profile: str,
) -> Dict[str, Any]:
    parent = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
    if not parent:
        return {}
    blocker = str(row.get("blockerCode") or "FITNESS_NOT_POSITIVE")
    family = str(parent.get("strategyFamily") or "RSI_Reversal")
    direction = str(parent.get("direction") or "LONG").upper()
    seed = clone_seed(parent, f"GA-USDJPY-G{generation_number:04d}-QR{offset:04d}", "QUALITY_REPAIR")
    seed["parentSeedId"] = parent.get("seedId") or row.get("seedId")
    seed["repairTargetBlocker"] = blocker
    seed["qualityProfile"] = profile
    seed["parentFitness"] = row.get("fitness")
    seed["explorationMode"] = "NO_ELITE_QUALITY_REPAIR"
    seed["explorationReasonZh"] = "上一代没有可晋级 elite，Agent 按 blocker 做质量修复搜索。"
    seed["repairReasonZh"] = _repair_reason_zh(blocker, profile)
    seed["strategyId"] = (
        f"USDJPY_{_strategy_id_token(family)}_{direction}_QUALITY_REPAIR_"
        f"{generation_number:03d}_{offset:03d}"
    )
    _apply_quality_profile(seed, blocker, profile, offset)
    _enforce_shadow_safety(seed)
    return seed


def _repair_profiles_for_row(row: Dict[str, Any]) -> List[str]:
    seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
    family = str(seed.get("strategyFamily") or "")
    direction = str(seed.get("direction") or "").upper()
    blocker = str(row.get("blockerCode") or "")
    base_profiles = _repair_profiles_for_blocker(blocker)
    family_profiles: List[str] = []
    if family == "BB_Triple" and direction == "SHORT":
        if blocker in {"INSUFFICIENT_SAMPLES", "STRATEGY_BACKTEST_NO_TRADES", "WALK_FORWARD_INSUFFICIENT", "OVERFIT_RISK"}:
            family_profiles = [
                "BB_SHORT_SAMPLE_EXPANDER",
                "BB_SHORT_SAMPLE_EXPANDER_M15",
                "BB_SHORT_RECLAIM_FAST_EXIT",
            ]
        elif blocker in {"WALK_FORWARD_UNSTABLE", "MAX_ADVERSE_TOO_HIGH"}:
            family_profiles = [
                "BB_SHORT_RECLAIM_STABILIZER",
                "BB_SHORT_RECLAIM_FAST_EXIT",
                "BB_SHORT_RECLAIM_WIDE_BAND",
            ]
    elif family == "RSI_Reversal" and blocker in QUALITY_REPAIR_BLOCKERS:
        if blocker in {"OVERFIT_RISK", "OVERFIT_RISK_HIGH"}:
            family_profiles = [
                "RSI_REVERSAL_OVERFIT_SAMPLE_EXPANDER",
                "RSI_REVERSAL_WALK_FORWARD_BALANCER",
                "RSI_REVERSAL_SEGMENT_SAMPLE_BALANCER",
                "RSI_REVERSAL_FAST_EXIT",
            ]
        elif blocker in {"INSUFFICIENT_SAMPLES", "WALK_FORWARD_INSUFFICIENT", "STRATEGY_BACKTEST_NO_TRADES"}:
            family_profiles = [
                "RSI_REVERSAL_SAMPLE_EXPANDER",
                "RSI_REVERSAL_SEGMENT_SAMPLE_BALANCER",
                "RSI_REVERSAL_FAST_EXIT",
            ]
        else:
            family_profiles = [
                "RSI_REVERSAL_WALK_FORWARD_BALANCER",
                "RSI_REVERSAL_STABILITY_REPAIR",
                "RSI_REVERSAL_SEGMENT_SAMPLE_BALANCER",
                "RSI_REVERSAL_FAST_EXIT",
            ]
    elif family == "MACD_Divergence" and blocker in QUALITY_REPAIR_BLOCKERS:
        family_profiles = [
            "MACD_HISTOGRAM_STABILIZER",
            "MACD_SAMPLE_EXPANDER",
            "MACD_FAST_EXIT",
        ]
    elif family == "USDJPY_H4_TREND_PULLBACK" and blocker in QUALITY_REPAIR_BLOCKERS:
        family_profiles = [
            "H4_PULLBACK_STABILIZER",
            "H4_PULLBACK_SAMPLE_EXPANDER",
            "H4_PULLBACK_FAST_EXIT",
        ]
    elif family == "USDJPY_TOKYO_RANGE_BREAKOUT" and blocker in {
        "WALK_FORWARD_UNSTABLE",
        "INSUFFICIENT_SAMPLES",
        "STRATEGY_BACKTEST_NO_TRADES",
    }:
        if blocker in {"INSUFFICIENT_SAMPLES", "STRATEGY_BACKTEST_NO_TRADES"}:
            family_profiles = [
                "TOKYO_RANGE_SAMPLE_EXPANDER",
                "TOKYO_RANGE_SESSION_STABILIZER",
                "TOKYO_RANGE_FAST_EXIT",
            ]
        else:
            family_profiles = [
                "TOKYO_RANGE_SESSION_STABILIZER",
                "TOKYO_RANGE_BUFFERED_BREAKOUT",
                "TOKYO_RANGE_FAST_EXIT",
            ]
    return family_profiles + [profile for profile in base_profiles if profile not in set(family_profiles)]


def _repair_profiles_for_blocker(blocker: str) -> List[str]:
    if blocker == "MAX_ADVERSE_TOO_HIGH":
        return [
            "MAX_ADVERSE_REPAIR",
            "MAX_ADVERSE_REPAIR_TIGHT_ENTRY",
            "MAX_ADVERSE_REPAIR_WIDER_STOP",
        ]
    if blocker in {"INSUFFICIENT_SAMPLES", "STRATEGY_BACKTEST_NO_TRADES", "WALK_FORWARD_INSUFFICIENT"}:
        return [
            "LOW_SAMPLE_EXPANDER",
            "LOW_SAMPLE_EXPANDER_M15",
            "LOW_SAMPLE_EXPANDER_FAST",
        ]
    if blocker in {"WALK_FORWARD_UNSTABLE", "OVERFIT_RISK", "OVERFIT_RISK_HIGH"}:
        return [
            "WALK_FORWARD_STABILIZER",
            "WALK_FORWARD_STABILIZER_FAST_EXIT",
            "WALK_FORWARD_STABILIZER_TIGHT_ENTRY",
        ]
    return ["QUALITY_STABILIZER", "QUALITY_TIGHT_ENTRY"]


def _apply_quality_profile(seed: Dict[str, Any], blocker: str, profile: str, offset: int) -> None:
    exit_cfg = seed.setdefault("exit", {})
    risk = seed.setdefault("risk", {})
    if _apply_family_quality_profile(seed, profile, offset):
        return
    if profile.startswith("LOW_SAMPLE"):
        _set_exit(seed, hold_h1=[4, 6, 8][offset % 3], hold_m15=[6, 8, 10][offset % 3])
        exit_cfg["breakevenDelayR"] = [0.8, 1.0, 1.2][offset % 3]
        exit_cfg["trailStartR"] = [1.1, 1.5, 2.0][offset % 3]
        exit_cfg["mfeGivebackPct"] = [0.5, 0.6, 0.7][offset % 3]
        risk["riskPips"] = max(12.5, min(22.5, _num(risk.get("riskPips"), 12.5) + (offset % 3) * 2.5))
        risk["opportunityLotMultiplier"] = max(0.2, min(0.5, _num(risk.get("opportunityLotMultiplier"), 0.35) + 0.05))
        _relax_family_entry(seed, offset)
        _set_family_timeframe(seed, "M15" if profile.endswith("M15") else "M5")
        return
    if profile.startswith("MAX_ADVERSE"):
        _set_exit(seed, hold_h1=[2, 3, 3][offset % 3], hold_m15=[3, 4, 5][offset % 3])
        exit_cfg["breakevenDelayR"] = [0.3, 0.5, 0.7][offset % 3]
        exit_cfg["trailStartR"] = [0.6, 0.8, 1.0][offset % 3]
        exit_cfg["mfeGivebackPct"] = [0.35, 0.42, 0.5][offset % 3]
        risk["riskPips"] = max(_num(risk.get("riskPips"), 10.0), [20.0, 25.0, 30.0][offset % 3])
        risk["opportunityLotMultiplier"] = min(0.25, _num(risk.get("opportunityLotMultiplier"), 0.35))
        _tighten_family_entry(seed, offset, strong=True)
        return
    _set_exit(seed, hold_h1=[2, 3, 4][offset % 3], hold_m15=[3, 4, 6][offset % 3])
    exit_cfg["breakevenDelayR"] = [0.4, 0.6, 0.8][offset % 3]
    exit_cfg["trailStartR"] = [0.8, 1.0, 1.2][offset % 3]
    exit_cfg["mfeGivebackPct"] = [0.42, 0.5, 0.58][offset % 3]
    risk["riskPips"] = max(_num(risk.get("riskPips"), 10.0), [15.0, 20.0, 25.0][offset % 3])
    risk["opportunityLotMultiplier"] = min(0.35, _num(risk.get("opportunityLotMultiplier"), 0.35))
    _tighten_family_entry(seed, offset, strong=profile.endswith("TIGHT_ENTRY") or blocker == "OVERFIT_RISK_HIGH")


def _apply_family_quality_profile(seed: Dict[str, Any], profile: str, offset: int) -> bool:
    if profile.startswith("BB_SHORT"):
        _apply_bb_short_reclaim_profile(seed, profile, offset)
        return True
    if profile.startswith("RSI_REVERSAL"):
        _apply_rsi_reversal_profile(seed, profile, offset)
        return True
    if profile.startswith("MACD_"):
        _apply_macd_profile(seed, profile, offset)
        return True
    if profile.startswith("H4_PULLBACK"):
        _apply_h4_pullback_profile(seed, profile, offset)
        return True
    if profile.startswith("TOKYO_RANGE"):
        _apply_tokyo_range_profile(seed, profile, offset)
        return True
    return False


def _apply_bb_short_reclaim_profile(seed: Dict[str, Any], profile: str, offset: int) -> None:
    indicators = seed.setdefault("indicators", {})
    bollinger = indicators.setdefault("bollinger", {})
    exit_cfg = seed.setdefault("exit", {})
    risk = seed.setdefault("risk", {})
    bollinger["timeframe"] = "H1" if profile.endswith("WIDE_BAND") else "M15"
    if profile.startswith("BB_SHORT_SAMPLE"):
        bollinger["timeframe"] = "M15"
        bollinger["period"] = max(14, min(28, int(_num(bollinger.get("period"), 20) - 2 + (offset % 2) * 2)))
        bollinger["deviations"] = round(max(1.7, min(2.35, _num(bollinger.get("deviations"), 2.0) - 0.15)), 2)
        bollinger["reclaimBufferPips"] = round(max(0.4, min(3.0, _num(bollinger.get("reclaimBufferPips"), 0.0) + 0.4)), 2)
        _set_exit(seed, hold_h1=3, hold_m15=5)
        exit_cfg["trailStartR"] = 1.0
        exit_cfg["mfeGivebackPct"] = 0.5
        exit_cfg["breakevenDelayR"] = 0.65
        risk["riskPips"] = max(16.0, _num(risk.get("riskPips"), 10.0))
        seed["direction"] = "SHORT"
        risk["opportunityLotMultiplier"] = min(0.32, _num(risk.get("opportunityLotMultiplier"), 0.35))
        return
    elif profile.endswith("FAST_EXIT"):
        bollinger["period"] = max(18, min(36, int(_num(bollinger.get("period"), 20) + 2)))
        bollinger["deviations"] = round(max(2.0, min(3.2, _num(bollinger.get("deviations"), 2.0) + 0.25)), 2)
        bollinger["reclaimBufferPips"] = round(max(1.5, min(8.0, _num(bollinger.get("reclaimBufferPips"), 0.0) + 1.5)), 2)
        _set_exit(seed, hold_h1=2, hold_m15=3)
        exit_cfg["trailStartR"] = 0.75
        exit_cfg["mfeGivebackPct"] = 0.42
        exit_cfg["breakevenDelayR"] = 0.4
        risk["riskPips"] = max(18.0, _num(risk.get("riskPips"), 10.0))
    elif profile.endswith("WIDE_BAND"):
        bollinger["period"] = max(24, min(44, int(_num(bollinger.get("period"), 20) + 6 + (offset % 2) * 4)))
        bollinger["deviations"] = round(max(2.35, min(3.6, _num(bollinger.get("deviations"), 2.0) + 0.45)), 2)
        bollinger["reclaimBufferPips"] = round(max(2.0, min(10.0, _num(bollinger.get("reclaimBufferPips"), 0.0) + 2.0)), 2)
        _set_exit(seed, hold_h1=3, hold_m15=4)
        exit_cfg["trailStartR"] = 0.95
        exit_cfg["mfeGivebackPct"] = 0.48
        exit_cfg["breakevenDelayR"] = 0.55
        risk["riskPips"] = max(22.5, _num(risk.get("riskPips"), 10.0))
    else:
        bollinger["period"] = max(20, min(40, int(_num(bollinger.get("period"), 20) + 4)))
        bollinger["deviations"] = round(max(2.15, min(3.4, _num(bollinger.get("deviations"), 2.0) + 0.3)), 2)
        bollinger["reclaimBufferPips"] = round(max(1.0, min(8.0, _num(bollinger.get("reclaimBufferPips"), 0.0) + 1.0)), 2)
        _set_exit(seed, hold_h1=3, hold_m15=4)
        exit_cfg["trailStartR"] = 0.9
        exit_cfg["mfeGivebackPct"] = 0.46
        exit_cfg["breakevenDelayR"] = 0.5
        risk["riskPips"] = max(20.0, _num(risk.get("riskPips"), 10.0))
    seed["direction"] = "SHORT"
    risk["opportunityLotMultiplier"] = min(0.28, _num(risk.get("opportunityLotMultiplier"), 0.35))
    _tighten_family_entry(seed, offset, strong=False)


def _apply_tokyo_range_profile(seed: Dict[str, Any], profile: str, offset: int) -> None:
    indicators = seed.setdefault("indicators", {})
    tokyo = indicators.setdefault("tokyoRange", {})
    exit_cfg = seed.setdefault("exit", {})
    risk = seed.setdefault("risk", {})
    tokyo["timeframe"] = "M15"
    if profile.endswith("SAMPLE_EXPANDER"):
        tokyo["rangeStartHourUtc"] = 0
        tokyo["rangeEndHourUtc"] = 2
        tokyo["tradeStartHourUtc"] = 3
        tokyo["tradeEndHourUtc"] = 7
        tokyo["lookbackBars"] = max(5, min(14, int(_num(tokyo.get("lookbackBars"), 8) - 2)))
        tokyo["bufferPips"] = round(max(0.4, min(4.0, _num(tokyo.get("bufferPips"), 0.0) + 0.4)), 2)
        _set_exit(seed, hold_h1=4, hold_m15=6)
        exit_cfg["trailStartR"] = 1.0
        exit_cfg["mfeGivebackPct"] = 0.5
        exit_cfg["breakevenDelayR"] = 0.7
        risk["riskPips"] = max(16.0, _num(risk.get("riskPips"), 10.0))
    elif profile.endswith("FAST_EXIT"):
        tokyo["rangeStartHourUtc"] = 0
        tokyo["rangeEndHourUtc"] = 2
        tokyo["tradeStartHourUtc"] = 3
        tokyo["tradeEndHourUtc"] = 4
        tokyo["lookbackBars"] = max(6, min(18, int(_num(tokyo.get("lookbackBars"), 8))))
        tokyo["bufferPips"] = round(max(1.5, min(7.0, _num(tokyo.get("bufferPips"), 0.0) + 1.5)), 2)
        _set_exit(seed, hold_h1=2, hold_m15=3)
        exit_cfg["trailStartR"] = 0.75
        exit_cfg["mfeGivebackPct"] = 0.42
        exit_cfg["breakevenDelayR"] = 0.4
        risk["riskPips"] = max(16.0, _num(risk.get("riskPips"), 10.0))
    elif profile.endswith("BUFFERED_BREAKOUT"):
        tokyo["rangeStartHourUtc"] = 0
        tokyo["rangeEndHourUtc"] = 2
        tokyo["tradeStartHourUtc"] = 3
        tokyo["tradeEndHourUtc"] = 5
        tokyo["lookbackBars"] = max(10, min(24, int(_num(tokyo.get("lookbackBars"), 8) + 4)))
        tokyo["bufferPips"] = round(max(2.0, min(9.0, _num(tokyo.get("bufferPips"), 0.0) + 2.0)), 2)
        _set_exit(seed, hold_h1=3, hold_m15=4)
        exit_cfg["trailStartR"] = 0.9
        exit_cfg["mfeGivebackPct"] = 0.46
        exit_cfg["breakevenDelayR"] = 0.5
        risk["riskPips"] = max(20.0, _num(risk.get("riskPips"), 10.0))
    else:
        start = 3 + (offset % 2)
        tokyo["rangeStartHourUtc"] = 0
        tokyo["rangeEndHourUtc"] = 2
        tokyo["tradeStartHourUtc"] = start
        tokyo["tradeEndHourUtc"] = start + 2
        tokyo["lookbackBars"] = max(8, min(20, int(_num(tokyo.get("lookbackBars"), 8) + 2)))
        tokyo["bufferPips"] = round(max(1.0, min(8.0, _num(tokyo.get("bufferPips"), 0.0) + 1.0)), 2)
        _set_exit(seed, hold_h1=3, hold_m15=4)
        exit_cfg["trailStartR"] = 0.85
        exit_cfg["mfeGivebackPct"] = 0.45
        exit_cfg["breakevenDelayR"] = 0.5
        risk["riskPips"] = max(18.0, _num(risk.get("riskPips"), 10.0))
    risk["opportunityLotMultiplier"] = min(0.3, _num(risk.get("opportunityLotMultiplier"), 0.35))


def _apply_rsi_reversal_profile(seed: Dict[str, Any], profile: str, offset: int) -> None:
    indicators = seed.setdefault("indicators", {})
    rsi = indicators.setdefault("rsi", {})
    exit_cfg = seed.setdefault("exit", {})
    risk = seed.setdefault("risk", {})
    direction = str(seed.get("direction") or "LONG").upper()
    if profile == "RSI_REVERSAL_OVERFIT_SAMPLE_EXPANDER":
        rsi["timeframe"] = "H1"
        rsi["period"] = [21, 23, 25][offset % 3]
        rsi["buyBand"] = [30, 31, 32][offset % 3]
        rsi["crossbackThreshold"] = [0.45, 0.55, 0.65][offset % 3]
        _set_exit(seed, hold_h1=[4, 5, 6][offset % 3], hold_m15=[6, 7, 8][offset % 3])
        exit_cfg["trailStartR"] = [0.9, 1.0, 1.1][offset % 3]
        exit_cfg["mfeGivebackPct"] = [0.46, 0.5, 0.54][offset % 3]
        exit_cfg["breakevenDelayR"] = [0.55, 0.65, 0.75][offset % 3]
        risk["riskPips"] = max([14.0, 16.0, 18.0][offset % 3], _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.34, _num(risk.get("opportunityLotMultiplier"), 0.35))
    elif profile == "RSI_REVERSAL_SEGMENT_SAMPLE_BALANCER":
        rsi["timeframe"] = "M15"
        rsi["period"] = [10, 12, 14][offset % 3]
        rsi["buyBand"] = [36, 38, 40][offset % 3]
        rsi["crossbackThreshold"] = [0.25, 0.4, 0.55][offset % 3]
        _set_exit(seed, hold_h1=[4, 5, 6][offset % 3], hold_m15=[6, 8, 10][offset % 3])
        exit_cfg["trailStartR"] = [0.95, 1.1, 1.25][offset % 3]
        exit_cfg["mfeGivebackPct"] = [0.5, 0.54, 0.58][offset % 3]
        exit_cfg["breakevenDelayR"] = [0.65, 0.8, 0.95][offset % 3]
        risk["riskPips"] = max([14.0, 16.0, 18.0][offset % 3], _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.38, _num(risk.get("opportunityLotMultiplier"), 0.35) + 0.02)
    elif profile == "RSI_REVERSAL_WALK_FORWARD_BALANCER":
        rsi["timeframe"] = "H1" if offset % 2 else "M15"
        rsi["period"] = [14, 18, 21][offset % 3]
        rsi["buyBand"] = [31, 33, 35][offset % 3]
        rsi["crossbackThreshold"] = [0.7, 0.95, 1.2][offset % 3]
        _set_exit(seed, hold_h1=[3, 4, 5][offset % 3], hold_m15=[5, 6, 8][offset % 3])
        exit_cfg["trailStartR"] = [0.9, 1.05, 1.2][offset % 3]
        exit_cfg["mfeGivebackPct"] = [0.46, 0.5, 0.54][offset % 3]
        exit_cfg["breakevenDelayR"] = [0.55, 0.7, 0.85][offset % 3]
        risk["riskPips"] = max([16.0, 18.0, 20.0][offset % 3], _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.32, _num(risk.get("opportunityLotMultiplier"), 0.35))
    elif profile.endswith("SAMPLE_EXPANDER"):
        rsi["timeframe"] = "M15"
        rsi["period"] = max(7, min(16, int(_num(rsi.get("period"), 14) - 3 + (offset % 3))))
        rsi["buyBand"] = max(26, min(42, _num(rsi.get("buyBand"), 34.0) + 2))
        rsi["crossbackThreshold"] = round(max(0.1, min(1.1, _num(rsi.get("crossbackThreshold"), 0.8) - 0.25)), 2)
        _set_exit(seed, hold_h1=4, hold_m15=7)
        exit_cfg["trailStartR"] = 1.1
        exit_cfg["mfeGivebackPct"] = 0.52
        exit_cfg["breakevenDelayR"] = 0.75
        risk["riskPips"] = max(14.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.4, _num(risk.get("opportunityLotMultiplier"), 0.35) + 0.05)
    elif profile.endswith("FAST_EXIT"):
        rsi["timeframe"] = "M15"
        rsi["period"] = max(9, min(21, int(_num(rsi.get("period"), 14))))
        rsi["buyBand"] = max(28, min(38, _num(rsi.get("buyBand"), 34.0)))
        rsi["crossbackThreshold"] = round(max(0.3, min(1.4, _num(rsi.get("crossbackThreshold"), 0.8) + 0.1)), 2)
        _set_exit(seed, hold_h1=2, hold_m15=3)
        exit_cfg["trailStartR"] = 0.75
        exit_cfg["mfeGivebackPct"] = 0.42
        exit_cfg["breakevenDelayR"] = 0.45
        risk["riskPips"] = max(16.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.3, _num(risk.get("opportunityLotMultiplier"), 0.35))
    else:
        rsi["timeframe"] = "H1" if offset % 2 else "M15"
        rsi["period"] = max(12, min(24, int(_num(rsi.get("period"), 14) + 2)))
        rsi["buyBand"] = max(28, min(36, _num(rsi.get("buyBand"), 34.0) - 1))
        rsi["crossbackThreshold"] = round(max(0.5, min(1.5, _num(rsi.get("crossbackThreshold"), 0.8) + 0.2)), 2)
        _set_exit(seed, hold_h1=3, hold_m15=4)
        exit_cfg["trailStartR"] = 0.9
        exit_cfg["mfeGivebackPct"] = 0.46
        exit_cfg["breakevenDelayR"] = 0.55
        risk["riskPips"] = max(18.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.32, _num(risk.get("opportunityLotMultiplier"), 0.35))
    if direction == "SHORT":
        rsi["sellBand"] = max(55, min(75, 100 - float(rsi.get("buyBand", 34))))


def _apply_macd_profile(seed: Dict[str, Any], profile: str, offset: int) -> None:
    indicators = seed.setdefault("indicators", {})
    macd = indicators.setdefault("macd", {})
    exit_cfg = seed.setdefault("exit", {})
    risk = seed.setdefault("risk", {})
    if profile.endswith("SAMPLE_EXPANDER"):
        macd["timeframe"] = "M15"
        _set_macd_periods(macd, fast=8 + (offset % 2) * 2, slow=21 + (offset % 3) * 3, signal=5 + (offset % 2) * 2)
        macd["minHistogramAbs"] = 0.0
        _set_exit(seed, hold_h1=4, hold_m15=7)
        exit_cfg["trailStartR"] = 1.1
        exit_cfg["mfeGivebackPct"] = 0.55
        exit_cfg["breakevenDelayR"] = 0.75
        risk["riskPips"] = max(14.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.38, _num(risk.get("opportunityLotMultiplier"), 0.35) + 0.03)
    elif profile.endswith("FAST_EXIT"):
        macd["timeframe"] = "M15"
        _set_macd_periods(macd, fast=10, slow=26, signal=7)
        macd["minHistogramAbs"] = round(max(0.0003, _num(macd.get("minHistogramAbs"), 0.0) + 0.0003), 4)
        _set_exit(seed, hold_h1=2, hold_m15=3)
        exit_cfg["trailStartR"] = 0.8
        exit_cfg["mfeGivebackPct"] = 0.44
        exit_cfg["breakevenDelayR"] = 0.45
        risk["riskPips"] = max(16.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.3, _num(risk.get("opportunityLotMultiplier"), 0.35))
    else:
        macd["timeframe"] = "H1" if offset % 2 else "M15"
        _set_macd_periods(macd, fast=12, slow=34, signal=9)
        macd["minHistogramAbs"] = round(max(0.0005, _num(macd.get("minHistogramAbs"), 0.0) + 0.0005), 4)
        _set_exit(seed, hold_h1=3, hold_m15=4)
        exit_cfg["trailStartR"] = 0.95
        exit_cfg["mfeGivebackPct"] = 0.48
        exit_cfg["breakevenDelayR"] = 0.6
        risk["riskPips"] = max(18.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.32, _num(risk.get("opportunityLotMultiplier"), 0.35))


def _apply_h4_pullback_profile(seed: Dict[str, Any], profile: str, offset: int) -> None:
    indicators = seed.setdefault("indicators", {})
    h4 = indicators.setdefault("h4Pullback", {})
    exit_cfg = seed.setdefault("exit", {})
    risk = seed.setdefault("risk", {})
    direction = str(seed.get("direction") or "LONG").upper()
    if profile.endswith("SAMPLE_EXPANDER"):
        h4["timeframe"] = "H1"
        _set_h4_periods(h4, fast=13, slow=50, pullback=13, rsi=12)
        h4["longRsiMin"] = 34
        h4["shortRsiMax"] = 66
        _set_exit(seed, hold_h1=5, hold_m15=8)
        exit_cfg["trailStartR"] = 1.15
        exit_cfg["mfeGivebackPct"] = 0.56
        exit_cfg["breakevenDelayR"] = 0.8
        risk["riskPips"] = max(20.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.35, _num(risk.get("opportunityLotMultiplier"), 0.35) + 0.03)
    elif profile.endswith("FAST_EXIT"):
        h4["timeframe"] = "H4"
        _set_h4_periods(h4, fast=20, slow=50, pullback=20, rsi=14)
        h4["longRsiMin"] = 40
        h4["shortRsiMax"] = 60
        _set_exit(seed, hold_h1=2, hold_m15=3)
        exit_cfg["trailStartR"] = 0.85
        exit_cfg["mfeGivebackPct"] = 0.45
        exit_cfg["breakevenDelayR"] = 0.55
        risk["riskPips"] = max(22.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.28, _num(risk.get("opportunityLotMultiplier"), 0.35))
    else:
        h4["timeframe"] = "H4"
        _set_h4_periods(h4, fast=20, slow=89, pullback=20, rsi=14)
        h4["longRsiMin"] = 42
        h4["shortRsiMax"] = 58
        _set_exit(seed, hold_h1=3, hold_m15=4)
        exit_cfg["trailStartR"] = 1.0
        exit_cfg["mfeGivebackPct"] = 0.5
        exit_cfg["breakevenDelayR"] = 0.65
        risk["riskPips"] = max(24.0, _num(risk.get("riskPips"), 10.0))
        risk["opportunityLotMultiplier"] = min(0.3, _num(risk.get("opportunityLotMultiplier"), 0.35))
    if direction == "SHORT":
        h4["shortRsiMax"] = min(95, max(35, h4.get("shortRsiMax", 62)))
    else:
        h4["longRsiMin"] = min(65, max(5, h4.get("longRsiMin", 38)))


def _set_exit(seed: Dict[str, Any], hold_h1: int, hold_m15: int) -> None:
    exit_cfg = seed.setdefault("exit", {})
    time_stop = exit_cfg.setdefault("timeStopBars", {})
    time_stop["H1"] = max(1, min(24, int(hold_h1)))
    time_stop["M15"] = max(1, min(48, int(hold_m15)))


def _tighten_family_entry(seed: Dict[str, Any], offset: int, strong: bool = False) -> None:
    indicators = seed.setdefault("indicators", {})
    step = 2 if strong else 1
    rsi = indicators.setdefault("rsi", {})
    rsi["buyBand"] = max(20, min(45, _num(rsi.get("buyBand"), 34.0) - step))
    rsi["crossbackThreshold"] = round(max(0.1, min(3.0, _num(rsi.get("crossbackThreshold"), 0.8) + 0.2 * step)), 2)
    bollinger = indicators.setdefault("bollinger", {})
    bollinger["deviations"] = round(max(0.5, min(4.0, _num(bollinger.get("deviations"), 2.0) + 0.15 * step)), 2)
    bollinger["reclaimBufferPips"] = round(max(0.0, min(30.0, _num(bollinger.get("reclaimBufferPips"), 0.0) + step)), 2)
    macd = indicators.setdefault("macd", {})
    macd["minHistogramAbs"] = round(max(0.0, min(1.0, _num(macd.get("minHistogramAbs"), 0.0) + 0.0005 * step)), 4)
    support = indicators.setdefault("supportResistance", {})
    support["lookbackBars"] = max(4, min(240, int(_num(support.get("lookbackBars"), 24) + 6 * step)))
    support["breakoutBufferPips"] = round(max(0.0, min(50.0, _num(support.get("breakoutBufferPips"), 0.0) + step)), 2)
    _tighten_time_window(indicators.setdefault("tokyoRange", {}), offset)
    _tighten_night_reversion(indicators.setdefault("nightReversion", {}), step)
    _tighten_h4_pullback(indicators.setdefault("h4Pullback", {}), seed.get("direction"), step)


def _relax_family_entry(seed: Dict[str, Any], offset: int) -> None:
    indicators = seed.setdefault("indicators", {})
    rsi = indicators.setdefault("rsi", {})
    rsi["buyBand"] = max(20, min(45, _num(rsi.get("buyBand"), 34.0) + 2))
    rsi["crossbackThreshold"] = round(max(0.0, min(3.0, _num(rsi.get("crossbackThreshold"), 0.8) - 0.25)), 2)
    ma = indicators.setdefault("ma", {})
    _set_ma_periods(ma, fast=max(3, int(_num(ma.get("fastPeriod"), 9) - 2)), slow=max(8, int(_num(ma.get("slowPeriod"), 21) - 6)))
    bollinger = indicators.setdefault("bollinger", {})
    bollinger["deviations"] = round(max(0.8, min(4.0, _num(bollinger.get("deviations"), 2.0) - 0.2)), 2)
    bollinger["reclaimBufferPips"] = round(max(0.0, _num(bollinger.get("reclaimBufferPips"), 0.0) - 1.0), 2)
    macd = indicators.setdefault("macd", {})
    macd["minHistogramAbs"] = round(max(0.0, _num(macd.get("minHistogramAbs"), 0.0) - 0.0005), 4)
    support = indicators.setdefault("supportResistance", {})
    support["lookbackBars"] = max(4, int(_num(support.get("lookbackBars"), 24) - 8))
    support["breakoutBufferPips"] = round(max(0.0, _num(support.get("breakoutBufferPips"), 0.0) - 1.0), 2)
    _widen_tokyo_window(indicators.setdefault("tokyoRange", {}), offset)
    _relax_night_reversion(indicators.setdefault("nightReversion", {}))
    _relax_h4_pullback(indicators.setdefault("h4Pullback", {}), seed.get("direction"))


def _set_family_timeframe(seed: Dict[str, Any], timeframe: str) -> None:
    family = str(seed.get("strategyFamily") or "RSI_Reversal")
    if family == "USDJPY_H4_TREND_PULLBACK":
        timeframe = "H4"
    indicators = seed.setdefault("indicators", {})
    cfg_key = FAMILY_CONFIG_KEYS.get(family, "rsi")
    indicators.setdefault(cfg_key, {})["timeframe"] = timeframe


def _set_ma_periods(ma: Dict[str, Any], fast: int, slow: int) -> None:
    ma["fastPeriod"] = max(2, min(80, int(fast)))
    ma["slowPeriod"] = max(ma["fastPeriod"] + 1, min(240, int(slow)))


def _set_macd_periods(macd: Dict[str, Any], fast: int, slow: int, signal: int) -> None:
    macd["fastPeriod"] = max(2, min(80, int(fast)))
    macd["slowPeriod"] = max(macd["fastPeriod"] + 1, min(160, int(slow)))
    macd["signalPeriod"] = max(2, min(80, int(signal)))


def _set_h4_periods(h4: Dict[str, Any], fast: int, slow: int, pullback: int, rsi: int) -> None:
    h4["fastEmaPeriod"] = max(2, min(120, int(fast)))
    h4["slowEmaPeriod"] = max(h4["fastEmaPeriod"] + 1, min(240, int(slow)))
    h4["pullbackEmaPeriod"] = max(2, min(120, int(pullback)))
    h4["rsiPeriod"] = max(2, min(50, int(rsi)))


def _tighten_time_window(tokyo: Dict[str, Any], offset: int) -> None:
    start = max(1, min(6, int(_num(tokyo.get("tradeStartHourUtc"), 3)) + (offset % 2)))
    tokyo["tradeStartHourUtc"] = start
    tokyo["tradeEndHourUtc"] = max(start, min(8, start + 2))
    tokyo["rangeStartHourUtc"] = max(0, start - 3)
    tokyo["rangeEndHourUtc"] = max(0, start - 1)
    tokyo["lookbackBars"] = max(4, min(96, int(_num(tokyo.get("lookbackBars"), 8) + 2)))
    tokyo["bufferPips"] = round(max(0.0, min(50.0, _num(tokyo.get("bufferPips"), 0.0) + 1.0)), 2)


def _widen_tokyo_window(tokyo: Dict[str, Any], offset: int) -> None:
    start = max(0, min(5, int(_num(tokyo.get("tradeStartHourUtc"), 3)) - 1))
    tokyo["tradeStartHourUtc"] = start
    tokyo["tradeEndHourUtc"] = min(23, start + 4 + (offset % 2))
    tokyo["rangeStartHourUtc"] = max(0, start - 4)
    tokyo["rangeEndHourUtc"] = max(0, start - 1)
    tokyo["lookbackBars"] = max(3, int(_num(tokyo.get("lookbackBars"), 8) - 2))
    tokyo["bufferPips"] = round(max(0.0, _num(tokyo.get("bufferPips"), 0.0) - 0.5), 2)


def _tighten_night_reversion(night: Dict[str, Any], step: int) -> None:
    night["deviations"] = round(max(0.5, min(4.0, _num(night.get("deviations"), 1.8) + 0.15 * step)), 2)
    night["entryBufferPips"] = round(max(0.0, min(30.0, _num(night.get("entryBufferPips"), 0.0) + 0.5 * step)), 2)
    night["bollingerPeriod"] = max(5, min(120, int(_num(night.get("bollingerPeriod"), 20) + 2 * step)))


def _relax_night_reversion(night: Dict[str, Any]) -> None:
    night["deviations"] = round(max(0.5, min(4.0, _num(night.get("deviations"), 1.8) - 0.2)), 2)
    night["entryBufferPips"] = round(max(0.0, _num(night.get("entryBufferPips"), 0.0) - 0.5), 2)
    night["bollingerPeriod"] = max(5, int(_num(night.get("bollingerPeriod"), 20) - 3))


def _tighten_h4_pullback(h4: Dict[str, Any], direction: Any, step: int) -> None:
    if str(direction or "LONG").upper() == "SHORT":
        h4["shortRsiMax"] = round(max(35.0, _num(h4.get("shortRsiMax"), 62.0) - 2 * step), 1)
    else:
        h4["longRsiMin"] = round(min(65.0, _num(h4.get("longRsiMin"), 38.0) + 2 * step), 1)


def _relax_h4_pullback(h4: Dict[str, Any], direction: Any) -> None:
    if str(direction or "LONG").upper() == "SHORT":
        h4["shortRsiMax"] = round(min(95.0, _num(h4.get("shortRsiMax"), 62.0) + 3), 1)
    else:
        h4["longRsiMin"] = round(max(5.0, _num(h4.get("longRsiMin"), 38.0) - 3), 1)


def _enforce_shadow_safety(seed: Dict[str, Any]) -> None:
    risk = seed.setdefault("risk", {})
    risk["stage"] = "SHADOW"
    risk["maxLot"] = min(2.0, _num(risk.get("maxLot"), 2.0))
    risk["riskPips"] = round(max(5.0, min(40.0, _num(risk.get("riskPips"), 10.0))), 2)
    risk["opportunityLotMultiplier"] = round(max(0.1, min(1.0, _num(risk.get("opportunityLotMultiplier"), 0.35))), 2)


def _repair_reason_zh(blocker: str, profile: str) -> str:
    if profile.startswith("RSI_REVERSAL_OVERFIT") or profile == "RSI_REVERSAL_SEGMENT_SAMPLE_BALANCER":
        return "P4-10D 针对 RSI 小样本过拟合，放宽触发并扩大跨分段有效交易样本。"
    if profile == "RSI_REVERSAL_WALK_FORWARD_BALANCER":
        return "P4-10D 针对 RSI walk-forward 稳定性，降低参数自由度并平衡持仓退出。"
    if profile.startswith("MAX_ADVERSE"):
        return "针对最大逆行过高，放宽 stop R 分母、缩短持仓并收紧入场。"
    if profile.startswith("LOW_SAMPLE"):
        return "针对样本不足，放宽触发条件并切到更高样本密度周期。"
    if blocker in {"WALK_FORWARD_UNSTABLE", "OVERFIT_RISK", "OVERFIT_RISK_HIGH"}:
        return "针对 walk-forward 不稳定，缩短持仓、提前保护盈利并降低参数自由度。"
    return "针对未晋级候选做保守质量修复，继续留在 shadow 评分。"


def _quality_repair_sort_key(row: Dict[str, Any]) -> tuple:
    fitness = _num(row.get("fitness"), -99.0)
    breakdown = row.get("fitnessBreakdown") if isinstance(row.get("fitnessBreakdown"), dict) else {}
    backtest = breakdown.get("strategyBacktest") if isinstance(breakdown.get("strategyBacktest"), dict) else {}
    walk_forward = breakdown.get("walkForward") if isinstance(breakdown.get("walkForward"), dict) else {}
    summary = walk_forward.get("summary") if isinstance(walk_forward.get("summary"), dict) else {}
    blocker = str(row.get("blockerCode") or "")
    blocker_score = {
        "MAX_ADVERSE_TOO_HIGH": 4,
        "WALK_FORWARD_UNSTABLE": 4,
        "OVERFIT_RISK": 4,
        "OVERFIT_RISK_HIGH": 3,
        "INSUFFICIENT_SAMPLES": 3,
        "STRATEGY_BACKTEST_NO_TRADES": 3,
        "WALK_FORWARD_INSUFFICIENT": 3,
        "FITNESS_NOT_POSITIVE": 2,
    }.get(blocker, 1)
    return (
        blocker_score,
        fitness,
        _num(backtest.get("netR"), 0.0),
        _num(summary.get("stabilityScore"), 0.0),
        _num(backtest.get("tradeCount"), 0.0),
        _num(row.get("generation"), 0.0),
        -_num(row.get("rank"), 9999.0),
    )


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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
