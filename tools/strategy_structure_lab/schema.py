from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.case_memory.schema import (
        AGENT_VERSION as CASE_MEMORY_AGENT_VERSION,
        CASE_MEMORY_SOURCES,
        FOCUS_SYMBOL,
        SAFETY,
        SCHEMA_CANDIDATE,
        SCHEMA_REPORT,
        candidate_ledger_path,
        report_path,
    )
except ModuleNotFoundError:  # pragma: no cover
    from case_memory.schema import (
        AGENT_VERSION as CASE_MEMORY_AGENT_VERSION,
        CASE_MEMORY_SOURCES,
        FOCUS_SYMBOL,
        SAFETY,
        SCHEMA_CANDIDATE,
        SCHEMA_REPORT,
        candidate_ledger_path,
        report_path,
    )


AGENT_VERSION = "p4-7"
SCHEMA_STRATEGY_STRUCTURE_REPORT = "quantgod.strategy_structure_production_report.v1"


def strategy_structure_dir(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / "case_memory"


def strategy_structure_report_path(runtime_dir: Path) -> Path:
    return report_path(runtime_dir)


def strategy_structure_candidate_ledger_path(runtime_dir: Path) -> Path:
    return candidate_ledger_path(runtime_dir)


def safety_boundary() -> Dict[str, Any]:
    return {
        **SAFETY,
        "strategyStructureProductionOnly": True,
        "shadowStrategyJsonCandidateOnly": True,
        "gaSeedHintOnly": True,
    }
