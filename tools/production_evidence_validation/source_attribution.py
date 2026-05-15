from __future__ import annotations

from collections import Counter
from typing import Any


SOURCE_TIER_WEIGHTS = {
    "live_real_fill": 1.0,
    "mt5_close_history": 0.7,
    "ea_shadow": 0.45,
    "strategy_shadow": 0.25,
    "backfilled_history": 0.15,
    "unknown": 0.0,
}


def _text(row: dict[str, Any], *keys: str) -> str:
    parts = []
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts)


def _has_real_ticket(row: dict[str, Any]) -> bool:
    for key in ("dealTicket", "orderTicket", "positionTicket", "ticket", "fillTicket"):
        value = row.get(key)
        if value not in (None, "", 0, "0"):
            return True
    return False


def _looks_like_real_fill(row: dict[str, Any], source_text: str) -> bool:
    mode = str(row.get("executionMode") or row.get("lane") or row.get("mode") or "").upper()
    event_type = str(row.get("eventType") or row.get("event") or "").upper()
    if "DRY" in source_text or "SHADOW" in source_text or "SIM" in source_text:
        return False
    if _has_real_ticket(row):
        return True
    live_feedback_source = (
        "QUANTGOD_LIVEEXECUTIONFEEDBACK.JSONL" in source_text
        or "QUANTGOD_MULTISTRATEGY.MQ5" in source_text
    )
    real_fill_event = event_type in {"ORDER_FILL", "ORDER_CLOSE", "LIVE_ENTRY", "LIVE_EXIT", "FILL", "CLOSE", "LIVE_FILL"}
    if live_feedback_source and real_fill_event:
        return row.get("fillPrice") not in (None, "", 0, "0")
    if "LIVE" in mode and event_type in {"LIVE_ENTRY", "LIVE_EXIT", "FILL", "CLOSE", "LIVE_FILL"}:
        return row.get("fillPrice") not in (None, "", 0, "0")
    return False


def classify_source_tier(row: dict[str, Any]) -> str:
    explicit = str(row.get("sourceTier") or row.get("sourceAttribution") or "").strip().lower()
    if explicit in SOURCE_TIER_WEIGHTS:
        return explicit

    source_kind = str(row.get("sourceKind") or "").strip().lower()
    source = str(row.get("source") or row.get("feedbackSource") or row.get("executionSource") or "")
    source_text = _text(
        row,
        "source",
        "sourceKind",
        "executionMode",
        "lane",
        "mode",
        "eventType",
        "policyId",
        "strategyId",
    ).upper()
    source_lower = source.lower()

    if _looks_like_real_fill(row, source_text):
        return "live_real_fill"
    if source_kind == "close_history" or "closehistory" in source_lower or "close_history" in source_lower:
        return "mt5_close_history"
    if "eadryrun" in source_lower or "ea_dry" in source_lower or "dryrun" in source_lower:
        return "ea_shadow"
    if "live_loop" in source_lower or "livedecision" in source_lower:
        return "ea_shadow"
    if source_kind == "shadow_outcome" or "shadow" in source_lower:
        return "strategy_shadow"
    if "history" in source_lower or "backfill" in source_lower or "evidence_os" in source_lower:
        return "backfilled_history"
    if source_kind == "existing_feedback":
        return "backfilled_history"
    return "unknown"


def source_weight(tier: str) -> float:
    return float(SOURCE_TIER_WEIGHTS.get(tier, 0.0))


def build_source_attribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tier_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    source_kind_counts: Counter[str] = Counter()
    weighted_samples = 0.0
    for row in rows:
        tier = classify_source_tier(row)
        tier_counts[tier] += 1
        source = str(row.get("source") or "unknown")
        source_kind = str(row.get("sourceKind") or "unknown")
        source_counts[source] += 1
        source_kind_counts[source_kind] += 1
        weighted_samples += source_weight(tier)

    sample_count = len(rows)
    live_real = tier_counts.get("live_real_fill", 0)
    live_like = live_real + tier_counts.get("mt5_close_history", 0)
    shadow = tier_counts.get("ea_shadow", 0) + tier_counts.get("strategy_shadow", 0)
    dominant = tier_counts.most_common(1)[0][0] if tier_counts else "unknown"
    if live_real >= 20:
        grade = "REAL_LIVE_READY"
    elif live_like >= 20:
        grade = "LIVE_HISTORY_WATCH"
    elif shadow >= 20:
        grade = "SHADOW_HEAVY"
    elif sample_count:
        grade = "THIN_ATTRIBUTION"
    else:
        grade = "NO_SAMPLES"

    recommendations: list[str] = []
    if live_real == 0:
        recommendations.append("继续分离真实成交 sourceTier=live_real_fill，避免 shadow 样本误作实盘成交。")
    if tier_counts.get("unknown", 0):
        recommendations.append("补齐未知来源样本的 sourceKind/sourceTier。")
    if shadow > live_like:
        recommendations.append("GA / Case Memory 对 shadow 样本应低权重处理。")
    if not recommendations:
        recommendations.append("执行反馈来源分层可用于生产观察。")

    return {
        "schema": "quantgod.execution_feedback_source_attribution.v1",
        "sampleCount": sample_count,
        "tierCounts": dict(tier_counts),
        "sourceCounts": dict(source_counts),
        "sourceKindCounts": dict(source_kind_counts),
        "liveRealFillCount": live_real,
        "liveLikeSampleCount": live_like,
        "shadowSampleCount": shadow,
        "weightedSampleCount": round(weighted_samples, 4),
        "dominantTier": dominant,
        "grade": grade,
        "weights": SOURCE_TIER_WEIGHTS,
        "recommendationsZh": recommendations,
    }
