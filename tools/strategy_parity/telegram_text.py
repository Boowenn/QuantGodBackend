from __future__ import annotations

from typing import Any, Dict


def strategy_parity_to_chinese_text(report: Dict[str, Any]) -> str:
    gate = report.get("promotionGate") if isinstance(report.get("promotionGate"), dict) else {}
    deep = report.get("deepParity") if isinstance(report.get("deepParity"), dict) else {}
    mismatches = deep.get("hardMismatches") if isinstance(deep.get("hardMismatches"), list) else []
    return "\n".join(
        [
            "【QuantGod 策略一致性复盘】",
            f"Strategy JSON 与 EA 一致性：{report.get('status', 'MISSING')}",
            f"晋级门：{gate.get('status', 'MISSING')}",
            f"硬差异：{len(mismatches)}",
            report.get("reasonZh") or "等待 Strategy JSON / Replay / EA 三方证据。",
        ]
    )
