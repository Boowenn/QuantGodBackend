from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

try:
    from tools.usdjpy_evidence_os.parity import _load_rsi_diagnostics
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.parity import _load_rsi_diagnostics


def load_mql5_rsi_diagnostics(runtime_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return _load_rsi_diagnostics(runtime_dir)
