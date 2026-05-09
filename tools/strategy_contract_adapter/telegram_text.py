from __future__ import annotations

from typing import Any, Dict


def _fmt(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def contract_to_chinese_text(payload: Dict[str, Any]) -> str:
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
    ea_status = payload.get("eaStatus") if isinstance(payload.get("eaStatus"), dict) else {}
    lines = [
        "【QuantGod Strategy JSON → EA 只读契约】",
        "",
        f"状态：{_fmt(payload.get('status'))}",
        f"策略：{_fmt(strategy.get('strategyFamily'))} / {_fmt(strategy.get('direction'))}",
        f"Seed：{_fmt(contract.get('selectedSeedId'))}",
        f"Contract：{_fmt(contract.get('contractMode'))}",
        f"EA 回执：{_fmt(ea_status.get('status'), '等待 EA 同步')}",
        "",
        "安全边界：",
        "- 只读、影子/测试/纸面评估先行。",
        "- 不下单、不平仓、不撤单、不写 MT5 OrderRequest。",
        "- 不修改源码、不修改 live preset，不让 GA 直接进实盘。",
    ]
    return "\n".join(lines)

