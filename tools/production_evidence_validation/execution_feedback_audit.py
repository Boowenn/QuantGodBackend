from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from .io_utils import read_json, read_jsonl
from .source_attribution import build_source_attribution, classify_source_tier

REQUIRED_FIELDS = [
    "strategyId",
    "eventType",
    "expectedPrice",
    "fillPrice",
    "slippagePips",
    "latencyMs",
    "spreadAtEntry",
    "profitR",
    "mfeR",
    "maeR",
]

CORE_FIELDS = [
    "strategyId",
    "eventType",
    "profitR",
    "mfeR",
    "maeR",
]

NUMERIC_FIELDS = [
    "slippagePips",
    "latencyMs",
    "spreadAtEntry",
    "profitR",
    "mfeR",
    "maeR",
]

MIN_USABLE_SAMPLES = 5
MIN_PRODUCTION_SAMPLES = 20
MIN_FIELD_COVERAGE = 0.80
MIN_CORE_COVERAGE = 0.95

FILL_OR_CLOSE_EVENTS = {"ORDER_FILL", "ORDER_CLOSE", "LIVE_ENTRY", "LIVE_EXIT", "FILL", "CLOSE", "LIVE_FILL"}


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_name(row: dict[str, Any]) -> str:
    return str(row.get("source") or row.get("feedbackSource") or row.get("executionSource") or "")


def _infer_source_kind(row: dict[str, Any]) -> str:
    explicit = str(row.get("sourceKind") or "").strip()
    if explicit:
        return explicit
    source = _source_name(row).lower()
    if "liveexecutionfeedbackhistory" in source:
        return "live_feedback_history"
    if "liveexecutionfeedback" in source:
        return "live_execution_feedback"
    if "closehistory" in source:
        return "close_history"
    if "eadryrun" in source or "dryrun" in source:
        return "ea_dry_run"
    if "liveloopledger" in source or "live_loop" in source:
        return "live_loop_advisory"
    if "tradejournal" in source:
        return "trade_journal"
    if "tradeeventlinks" in source:
        return "trade_event_links"
    if "tradeoutcomelabels" in source:
        return "trade_outcome_labels"
    if "shadow" in source:
        return "shadow_outcome"
    return "unknown"


def _infer_event_type(row: dict[str, Any], source_kind: str) -> str:
    explicit = str(row.get("eventType") or row.get("event") or row.get("type") or "").strip().upper()
    if explicit:
        return explicit
    mapping = {
        "close_history": "LIVE_EXIT",
        "ea_dry_run": "EA_DRY_RUN_DECISION",
        "live_loop_advisory": "LIVE_LOOP_DECISION",
        "trade_event_links": "TRADE_EVENT_LINK",
        "trade_outcome_labels": "TRADE_OUTCOME",
        "trade_journal": "TRADE_JOURNAL",
        "shadow_outcome": "SHADOW_EXIT",
    }
    return mapping.get(source_kind, "")


def _infer_source_tier(row: dict[str, Any], source_kind: str, event_type: str) -> str:
    explicit = str(row.get("sourceTier") or row.get("sourceAttribution") or "").strip().lower()
    if explicit:
        return explicit
    if source_kind == "live_execution_feedback" and event_type in FILL_OR_CLOSE_EVENTS:
        if row.get("fillPrice") not in (None, "", 0, "0"):
            return "live_real_fill"
    if source_kind in {"close_history", "trade_journal"}:
        return "mt5_close_history"
    if source_kind in {"ea_dry_run", "live_loop_advisory"}:
        return "ea_shadow"
    if source_kind == "shadow_outcome":
        return "strategy_shadow"
    if source_kind in {"live_feedback_history", "trade_event_links", "trade_outcome_labels"}:
        return "backfilled_history"
    return "unknown"


def _infer_execution_mode(row: dict[str, Any], source_kind: str, source_tier: str) -> str:
    explicit = str(row.get("executionMode") or row.get("lane") or row.get("mode") or "").strip().upper()
    if explicit:
        return explicit
    if source_tier in {"live_real_fill", "mt5_close_history"}:
        return "LIVE"
    if source_tier in {"ea_shadow", "strategy_shadow"}:
        return "SHADOW"
    if source_kind in {"live_execution_feedback", "close_history", "trade_journal"}:
        return "LIVE"
    return ""


def _normalize_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    source_kind = _infer_source_kind(normalized)
    event_type = _infer_event_type(normalized, source_kind)
    source_tier = _infer_source_tier(normalized, source_kind, event_type)
    execution_mode = _infer_execution_mode(normalized, source_kind, source_tier)
    if _is_missing(normalized.get("sourceKind")):
        normalized["sourceKind"] = source_kind
    if _is_missing(normalized.get("eventType")) and event_type:
        normalized["eventType"] = event_type
    if _is_missing(normalized.get("sourceTier")):
        normalized["sourceTier"] = source_tier
    if _is_missing(normalized.get("executionMode")) and execution_mode:
        normalized["executionMode"] = execution_mode
    return normalized


def _row_mode(row: dict[str, Any]) -> str:
    raw = row.get("lane") or row.get("executionMode") or row.get("mode") or row.get("source") or "UNKNOWN"
    value = str(raw).upper()
    if "LIVE" in value:
        return "LIVE"
    if "SHADOW" in value or "DRY" in value or "SIM" in value:
        return "SHADOW"
    return "UNKNOWN"


def _strategy_id(row: dict[str, Any]) -> str:
    return str(row.get("strategyId") or row.get("strategy") or "UNKNOWN")


def _event_type(row: dict[str, Any]) -> str:
    return str(row.get("eventType") or row.get("event") or row.get("type") or "UNKNOWN").upper()


def _field_coverage(rows: list[dict[str, Any]], fields: list[str]) -> tuple[float, dict[str, int]]:
    if not rows:
        return 0.0, {field: 0 for field in fields}
    present: dict[str, int] = {field: 0 for field in fields}
    for row in rows:
        for field in fields:
            if not _is_missing(row.get(field)):
                present[field] += 1
    total_cells = len(rows) * len(fields)
    present_cells = sum(present.values())
    return round(present_cells / total_cells, 4), present


def _numeric_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    summary: dict[str, dict[str, float | int | None]] = {}
    for field in NUMERIC_FIELDS:
        values = [_safe_float(row.get(field)) for row in rows]
        clean = [value for value in values if value is not None]
        if not clean:
            summary[field] = {"count": 0, "avg": None, "median": None, "min": None, "max": None}
            continue
        summary[field] = {
            "count": len(clean),
            "avg": round(mean(clean), 6),
            "median": round(median(clean), 6),
            "min": round(min(clean), 6),
            "max": round(max(clean), 6),
        }
    return summary


def _coverage_status(sample_count: int, field_coverage: float, core_coverage: float) -> tuple[str, str, str]:
    if sample_count <= 0:
        return "WARN", "NO_SAMPLES", "NOT_USABLE"
    if core_coverage < MIN_CORE_COVERAGE:
        return "WARN", "CORE_FIELD_GAPS", "SHADOW_ONLY"
    if field_coverage < MIN_FIELD_COVERAGE:
        return "WARN", "FIELD_GAPS", "SHADOW_ONLY"
    if sample_count < MIN_USABLE_SAMPLES:
        return "WARN", "LOW_SAMPLE_COUNT", "SHADOW_ONLY"
    if sample_count < MIN_PRODUCTION_SAMPLES:
        return "WARN", "USABLE_BUT_THIN", "PRODUCTION_WATCH"
    return "PASS", "PRODUCTION_READY", "PRODUCTION_USABLE"


def audit_execution_feedback(runtime_dir: Path) -> dict[str, Any]:
    report_path = runtime_dir / "execution" / "QuantGod_LiveExecutionQualityReport.json"
    ledger_path = runtime_dir / "execution" / "QuantGod_LiveExecutionFeedback.jsonl"
    report = read_json(report_path, {}) or {}
    rows = [_normalize_audit_row(row) for row in read_jsonl(ledger_path, 5000)]
    sample_count = len(rows)

    full_field_coverage, present_by_field = _field_coverage(rows, REQUIRED_FIELDS)
    core_coverage, present_core = _field_coverage(rows, CORE_FIELDS)

    missing_field_counts = {
        field: max(sample_count - present_by_field.get(field, 0), 0) for field in REQUIRED_FIELDS
    }
    complete_samples = sum(1 for row in rows if all(not _is_missing(row.get(field)) for field in REQUIRED_FIELDS))
    core_complete_samples = sum(1 for row in rows if all(not _is_missing(row.get(field)) for field in CORE_FIELDS))

    modes = Counter(_row_mode(row) for row in rows)
    events = Counter(_event_type(row) for row in rows)
    strategies = Counter(_strategy_id(row) for row in rows)
    source_attribution = build_source_attribution(rows)

    by_strategy: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_strategy_id(row)].append(row)
    for strategy, strategy_rows in sorted(grouped.items()):
        strategy_field_coverage, _ = _field_coverage(strategy_rows, REQUIRED_FIELDS)
        strategy_core_coverage, _ = _field_coverage(strategy_rows, CORE_FIELDS)
        by_strategy[strategy] = {
            "sampleCount": len(strategy_rows),
            "fieldCoverage": strategy_field_coverage,
            "coreCoverage": strategy_core_coverage,
            "eventTypeCounts": dict(Counter(_event_type(row) for row in strategy_rows)),
            "modeCounts": dict(Counter(_row_mode(row) for row in strategy_rows)),
            "sourceTierCounts": dict(Counter(classify_source_tier(row) for row in strategy_rows)),
        }

    status, coverage_grade, evidence_usability = _coverage_status(
        sample_count,
        full_field_coverage,
        core_coverage,
    )

    blockers: list[str] = []
    if sample_count <= 0:
        blockers.append("没有 live/shadow execution feedback 样本")
    if core_coverage < MIN_CORE_COVERAGE:
        blockers.append("核心执行反馈字段覆盖率不足")
    if full_field_coverage < MIN_FIELD_COVERAGE:
        blockers.append("执行反馈字段覆盖率不足")
    if sample_count and sample_count < MIN_USABLE_SAMPLES:
        blockers.append("执行反馈样本过少，暂不能用于生产级裁决")
    elif sample_count and sample_count < MIN_PRODUCTION_SAMPLES:
        blockers.append("执行反馈样本仍偏薄，建议继续观察")

    recommendations: list[str] = []
    if sample_count < MIN_PRODUCTION_SAMPLES:
        recommendations.append("继续收集 live/shadow execution feedback 样本")
    top_missing = [field for field, count in missing_field_counts.items() if count > 0]
    if top_missing:
        recommendations.append("补齐缺失字段：" + ", ".join(top_missing[:5]))
    if source_attribution.get("liveRealFillCount", 0) <= 0:
        recommendations.append("执行反馈需要继续区分 live_real_fill 与 shadow/backfilled 样本")
    if not recommendations:
        recommendations.append("执行反馈覆盖率可用于生产观察")

    return {
        "status": status,
        "coverageGrade": coverage_grade,
        "evidenceUsability": evidence_usability,
        "reportPath": str(report_path) if report_path.exists() else "",
        "ledgerPath": str(ledger_path) if ledger_path.exists() else "",
        "sampleCount": sample_count,
        "completeSamples": complete_samples,
        "coreCompleteSamples": core_complete_samples,
        "fieldCoverage": full_field_coverage,
        "coreCoverage": core_coverage,
        "requiredFields": REQUIRED_FIELDS,
        "coreFields": CORE_FIELDS,
        "presentFieldCounts": present_by_field,
        "presentCoreFieldCounts": present_core,
        "missingFieldCounts": missing_field_counts,
        "modeCounts": dict(modes),
        "eventTypeCounts": dict(events),
        "strategyCounts": dict(strategies),
        "sourceAttribution": source_attribution,
        "strategyCoverage": by_strategy,
        "numericSummary": _numeric_summary(rows),
        "qualityReportStatus": report.get("status") or report.get("summary", {}).get("status"),
        "blockersZh": blockers,
        "recommendationsZh": recommendations,
        "thresholds": {
            "minUsableSamples": MIN_USABLE_SAMPLES,
            "minProductionSamples": MIN_PRODUCTION_SAMPLES,
            "minFieldCoverage": MIN_FIELD_COVERAGE,
            "minCoreCoverage": MIN_CORE_COVERAGE,
        },
    }
