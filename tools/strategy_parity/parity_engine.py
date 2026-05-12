from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.usdjpy_evidence_os.parity import build_parity_report
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.parity import build_parity_report


def run_parity_engine(runtime_dir: Path, *, write: bool = True) -> Dict[str, Any]:
    return build_parity_report(runtime_dir, write=write)
