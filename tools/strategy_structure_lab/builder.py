from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.case_memory.builder import build_case_memory_candidates
except ModuleNotFoundError:  # pragma: no cover
    from case_memory.builder import build_case_memory_candidates


def build_strategy_structure_cases(
    runtime_dir: Path,
    *,
    write_case_memory: bool = True,
    limit: int = 8,
) -> Dict[str, Any]:
    return build_case_memory_candidates(
        Path(runtime_dir),
        write_case_memory=write_case_memory,
        limit=limit,
    )
