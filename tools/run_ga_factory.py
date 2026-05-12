#!/usr/bin/env python3
"""Compatibility CLI alias for Strategy JSON GA Factory."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from tools.run_strategy_ga_factory import main
except ModuleNotFoundError:  # pragma: no cover
    from run_strategy_ga_factory import main


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
