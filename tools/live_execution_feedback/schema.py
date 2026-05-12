from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.usdjpy_evidence_os.schema import (
        FOCUS_SYMBOL,
        SAFETY_BOUNDARY,
        execution_feedback_public_ledger_path,
        execution_feedback_public_path,
    )
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.schema import (
        FOCUS_SYMBOL,
        SAFETY_BOUNDARY,
        execution_feedback_public_ledger_path,
        execution_feedback_public_path,
    )


FEEDBACK_SCHEMA = "quantgod.live_execution_feedback.v1"
QUALITY_REPORT_SCHEMA = "quantgod.live_execution_quality_report.v1"

REQUIRED_FEEDBACK_FIELDS: List[str] = [
    "strategyId",
    "policyId",
    "intentId",
    "entrySignalTime",
    "orderSendTime",
    "fillTime",
    "expectedPrice",
    "fillPrice",
    "slippagePips",
    "spreadAtEntry",
    "latencyMs",
    "exitReason",
    "profitR",
    "mfeR",
    "maeR",
]

SAFETY: Dict[str, Any] = dict(SAFETY_BOUNDARY)


def report_path(runtime_dir: Path) -> Path:
    return execution_feedback_public_path(runtime_dir)


def ledger_path(runtime_dir: Path) -> Path:
    return execution_feedback_public_ledger_path(runtime_dir)
