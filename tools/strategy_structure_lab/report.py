from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.case_memory.report import build_case_memory_report, status as case_memory_status
except ModuleNotFoundError:  # pragma: no cover
    from case_memory.report import build_case_memory_report, status as case_memory_status

from .schema import AGENT_VERSION, SCHEMA_STRATEGY_STRUCTURE_REPORT, safety_boundary


def _mark_strategy_structure(report: Dict[str, Any]) -> Dict[str, Any]:
    marked = dict(report)
    marked["strategyStructureProduction"] = True
    marked["strategyStructureSchema"] = SCHEMA_STRATEGY_STRUCTURE_REPORT
    marked["strategyStructureAgentVersion"] = AGENT_VERSION
    marked["p4Stage"] = "P4-7"
    marked["reasonZh"] = marked.get("reasonZh") or marked.get("nextActionZh") or "等待 Case Memory 生成新策略结构候选。"
    marked["safety"] = {
        **safety_boundary(),
        **(marked.get("safety") if isinstance(marked.get("safety"), dict) else {}),
        "strategyStructureProductionOnly": True,
        "shadowStrategyJsonCandidateOnly": True,
        "gaSeedHintOnly": True,
    }
    return marked


def build_report(runtime_dir: Path, *, write: bool = True, limit: int = 8) -> Dict[str, Any]:
    return _mark_strategy_structure(build_case_memory_report(Path(runtime_dir), write=write, limit=limit))


def status(runtime_dir: Path) -> Dict[str, Any]:
    return _mark_strategy_structure(case_memory_status(Path(runtime_dir)))
