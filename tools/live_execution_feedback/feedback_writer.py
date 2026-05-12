from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.usdjpy_evidence_os.execution_feedback import build_execution_feedback
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.execution_feedback import build_execution_feedback


def write_feedback(runtime_dir: Path) -> Dict[str, Any]:
    return build_execution_feedback(runtime_dir, write=True)
