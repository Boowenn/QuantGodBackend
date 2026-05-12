from __future__ import annotations

from typing import Any, Dict


def live_execution_feedback_to_chinese_text(report: Dict[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    gate = report.get("promotionGate") if isinstance(report.get("promotionGate"), dict) else {}
    return "\n".join(
        [
            "【QuantGod 执行质量复盘】",
            f"执行反馈晋级门：{gate.get('status', 'WAITING_FEEDBACK')}",
            f"平均滑点：{metrics.get('avgAbsSlippagePips', 0)} pips",
            f"平均延迟：{metrics.get('avgLatencyMs', 0)} ms",
            f"拒单：{metrics.get('rejectCount', 0)} 次",
            report.get("nextActionZh") or "等待更多 shadow/live 执行反馈。",
        ]
    )
