"""Chinese operator text for GA Factory summaries."""

from __future__ import annotations

from typing import (
    Any,
    Dict,
)


def ga_factory_to_chinese_text(state: Dict[str, Any]) -> str:
    next_generation = state.get("nextGeneration") if isinstance(state.get("nextGeneration"), dict) else {}
    safety = state.get("safety") if isinstance(state.get("safety"), dict) else {}
    return "\n".join(
        [
            "【QuantGod GA Factory 生产化复盘】",
            f"状态：{state.get('statusZh') or state.get('status', 'WAITING_GA_TRACE')}",
            f"当前代数：{state.get('currentGeneration', 0)}",
            f"候选：{state.get('candidateCount', 0)}",
            f"Elite：{state.get('eliteCount', 0)}",
            f"策略墓园：{state.get('graveyardCount', 0)}",
            f"Lineage 节点：{state.get('lineageNodeCount', 0)}",
            f"下一代：{next_generation.get('status', 'WAITING_GA_TRACE')}",
            next_generation.get("reasonZh") or "等待 GA trace 生成。",
            "安全边界：只允许 SHADOW / FAST_SHADOW / TESTER_ONLY / PAPER_LIVE_SIM。",
            f"直接实盘：{bool(safety.get('gaFactoryDirectLiveAllowed'))}",
        ]
    )
