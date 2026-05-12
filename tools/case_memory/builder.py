from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.usdjpy_evidence_os.case_memory import build_case_memory
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.case_memory import build_case_memory

from .candidate_builder import build_strategy_candidates


def build_case_memory_candidates(
    runtime_dir: Path,
    *,
    write_case_memory: bool = True,
    limit: int = 8,
) -> Dict[str, Any]:
    case_summary = build_case_memory(Path(runtime_dir), write=write_case_memory)
    candidate_payload = build_strategy_candidates(Path(runtime_dir), limit=limit)
    return {
        "caseSummary": case_summary,
        **candidate_payload,
    }
