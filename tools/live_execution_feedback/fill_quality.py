from __future__ import annotations

from typing import Any, Dict


def fill_quality(row: Dict[str, Any]) -> str:
    if row.get("rejectReason"):
        return "REJECTED"
    if row.get("fillPrice"):
        return "FILLED"
    if row.get("eventType") in {"ORDER_ACCEPTED", "ORDER_SEND", "ORDER_REQUESTED"}:
        return "ACCEPTED_WAITING_FILL"
    return "OBSERVED"
