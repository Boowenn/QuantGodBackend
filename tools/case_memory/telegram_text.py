from __future__ import annotations

from typing import Any, Dict


def case_memory_to_chinese_text(report: Dict[str, Any]) -> str:
    gate = report.get("parityGate") if isinstance(report.get("parityGate"), dict) else {}
    return "\n".join(
        [
            "【QuantGod Case Memory → Strategy JSON Candidate】",
            f"状态：{report.get('status', 'WAITING_FIRST_RUN')}",
            f"Case 数：{(report.get('caseSummary') or {}).get('caseCount', 0)}",
            f"候选：{report.get('candidateCount', 0)}；GA seed：{report.get('gaSeedCount', 0)}",
            f"Parity：{gate.get('status', 'MISSING')} / {gate.get('promotionGateStatus', 'MISSING')}",
            report.get("nextActionZh") or "等待 Case Memory 生成新策略候选。",
        ]
    )
