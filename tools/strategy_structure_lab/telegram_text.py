from __future__ import annotations

from typing import Any, Dict

try:
    from tools.case_memory.telegram_text import case_memory_to_chinese_text
except ModuleNotFoundError:  # pragma: no cover
    from case_memory.telegram_text import case_memory_to_chinese_text


def build_telegram_text(report: Dict[str, Any]) -> str:
    base = case_memory_to_chinese_text(report)
    return "\n".join(
        [
            base,
            "",
            "P4-7：Case Memory 已作为新策略结构生产化入口。",
            "候选只进入 shadow Strategy JSON / GA seed，不会下单、不改 live preset。",
        ]
    )
