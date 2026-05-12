from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .feedback_writer import write_feedback


def build_live_execution_feedback_report(runtime_dir: Path, *, write: bool = True) -> Dict[str, Any]:
    if write:
        return write_feedback(runtime_dir)
    try:
        from tools.usdjpy_evidence_os.execution_feedback import build_execution_feedback
    except ModuleNotFoundError:  # pragma: no cover
        from usdjpy_evidence_os.execution_feedback import build_execution_feedback
    return build_execution_feedback(runtime_dir, write=False)
