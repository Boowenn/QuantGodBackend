from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from tools.usdjpy_evidence_os.execution_feedback import _collect_rows
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.execution_feedback import _collect_rows


def read_mt5_trade_feedback(runtime_dir: Path) -> List[Tuple[Dict[str, Any], str]]:
    return _collect_rows(runtime_dir)
