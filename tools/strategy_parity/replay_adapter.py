from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.usdjpy_bar_replay.replay_engine import build_bar_replay_report
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_bar_replay.replay_engine import build_bar_replay_report


def build_python_bar_replay(runtime_dir: Path) -> Dict[str, Any]:
    return build_bar_replay_report(runtime_dir, write=True)
