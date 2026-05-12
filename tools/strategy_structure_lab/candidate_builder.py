from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.case_memory.candidate_builder import build_strategy_candidates
except ModuleNotFoundError:  # pragma: no cover
    from case_memory.candidate_builder import build_strategy_candidates


def build_new_strategy_structure_candidates(runtime_dir: Path, *, limit: int = 8) -> Dict[str, Any]:
    return build_strategy_candidates(Path(runtime_dir), limit=limit)
