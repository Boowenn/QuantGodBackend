from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .parity_engine import run_parity_engine


def build_strategy_parity_report(runtime_dir: Path, *, write: bool = True) -> Dict[str, Any]:
    return run_parity_engine(runtime_dir, write=write)
