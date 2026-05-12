from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json, read_jsonl

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


def audit_execution_feedback(runtime_dir: Path) -> dict[str, Any]:
    report_path = runtime_dir / "execution" / "QuantGod_LiveExecutionQualityReport.json"
    ledger_path = runtime_dir / "execution" / "QuantGod_LiveExecutionFeedback.jsonl"
    report = read_json(report_path, {}) or {}
    rows = read_jsonl(ledger_path, 1000)
    total = len(rows)
    complete = 0
    missing_counter: dict[str, int] = {}
    for row in rows:
        missing = [field for field in REQUIRED_FIELDS if row.get(field) in (None, "")]
        if not missing:
            complete += 1
        for field in missing:
            missing_counter[field] = missing_counter.get(field, 0) + 1
    coverage = (complete / total) if total else 0.0
    status = "PASS" if total >= 5 and coverage >= 0.8 else ("WARN" if total else "WARN")
    return {
        "status": status,
        "reportPath": str(report_path) if report_path.exists() else "",
        "ledgerPath": str(ledger_path) if ledger_path.exists() else "",
        "sampleCount": total,
        "completeSamples": complete,
        "fieldCoverage": round(coverage, 4),
        "missingFieldCounts": missing_counter,
        "qualityReportStatus": report.get("status") or report.get("summary", {}).get("status"),
        "recommendation": "Collect more live/shadow execution feedback samples." if total < 5 else "Improve missing feedback fields." if coverage < 0.8 else "Execution feedback coverage is usable.",
    }
