from __future__ import annotations

from typing import Any


def slippage_pips(expected_price: Any, fill_price: Any, pip_size: float = 0.01) -> float:
    try:
        expected = float(expected_price)
        fill = float(fill_price)
        return round((fill - expected) / pip_size, 4)
    except Exception:
        return 0.0
