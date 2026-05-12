from __future__ import annotations

from typing import Any, Dict


def exit_quality(row: Dict[str, Any]) -> Dict[str, Any]:
    mfe = _num(row.get("mfeR"))
    profit = _num(row.get("profitR"))
    capture = round(profit / mfe, 4) if mfe > 0 else 0.0
    return {
        "exitReason": row.get("exitReason") or "",
        "profitCaptureRate": capture,
        "status": "PASS" if capture >= 0.35 or mfe <= 0 else "WATCH",
    }


def _num(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0
