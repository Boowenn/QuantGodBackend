from __future__ import annotations

from typing import Any


def _section_status(name: str, section: dict[str, Any]) -> str:
    return f"- {name}：{section.get('status', 'UNKNOWN')}｜{section.get('recommendation', '')}"


def build_telegram_text(report: dict[str, Any]) -> str:
    lines = [
        "【QuantGod 生产证据验证】",
        "",
        f"总状态：{report.get('status', 'UNKNOWN')}",
        f"结论：{report.get('summaryZh', '')}",
        "",
        "证据分项：",
        _section_status("历史数据", report.get("historyProduction") or {}),
        _section_status("策略一致性", report.get("strategyFamilyParity") or {}),
        _section_status("执行反馈", report.get("liveExecutionFeedbackCoverage") or {}),
        _section_status("GA 多代稳定性", report.get("gaMultiGenerationStability") or {}),
    ]
    blockers = report.get("blockersZh") or []
    if blockers:
        lines.extend(["", "主要阻断："])
        lines.extend([f"- {item}" for item in blockers])
    lines.extend([
        "",
        "安全边界：",
        "- 本报告只做生产证据验证，不会下单、不会平仓、不会撤单。",
        "- 不会修改 MT5 live preset，不接收 Telegram 交易命令。",
        "- Polymarket 仍然只做模拟和事件风险，不接真钱钱包。",
    ])
    return "\n".join(lines)
