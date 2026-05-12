from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.usdjpy_evidence_os.schema import FOCUS_SYMBOL, SAFETY_BOUNDARY
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.schema import FOCUS_SYMBOL, SAFETY_BOUNDARY


SCHEMA_REPORT = "quantgod.case_memory_strategy_candidate_report.v1"
SCHEMA_CANDIDATE = "quantgod.case_memory_strategy_candidate.v1"
AGENT_VERSION = "p4-3"

CASE_MEMORY_SOURCES: List[str] = [
    "USDJPY_BAR_REPLAY",
    "LIVE_EXECUTION_FEEDBACK",
    "STRATEGY_CONTRACT_SHADOW",
    "GA_BLOCKERS",
]

SAFETY: Dict[str, Any] = {
    **SAFETY_BOUNDARY,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "livePresetMutationAllowed": False,
    "telegramCommandExecutionAllowed": False,
    "polymarketRealMoneyAllowed": False,
    "shadowStrategyJsonCandidateOnly": True,
    "writesMt5OrderRequest": False,
    "writesMt5LivePreset": False,
}


def case_memory_dir(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / "case_memory"


def report_path(runtime_dir: Path) -> Path:
    return case_memory_dir(runtime_dir) / "QuantGod_CaseMemoryStrategyCandidates.json"


def candidate_ledger_path(runtime_dir: Path) -> Path:
    return case_memory_dir(runtime_dir) / "QuantGod_CaseMemoryStrategyCandidateLedger.jsonl"
