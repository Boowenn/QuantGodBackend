from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.strategy_json.schema import base_strategy_seed
    from tools.usdjpy_strategy_backtest.report import run_backtest
except ModuleNotFoundError:  # pragma: no cover
    from strategy_json.schema import base_strategy_seed
    from usdjpy_strategy_backtest.report import run_backtest


def build_strategy_json_backtest(runtime_dir: Path, seed: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return run_backtest(runtime_dir, seed or base_strategy_seed("PARITY-HARNESS"), write=True)
