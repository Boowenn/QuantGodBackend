from __future__ import annotations

BLOCKER_ZH = {
    "SCHEMA_INVALID": "Strategy JSON schema 不合法",
    "SAFETY_REJECTED": "安全边界拒绝：含代码、密钥或交易执行原语",
    "STRATEGY_BACKTEST_MISSING": "缺少 USDJPY SQLite Strategy JSON 回测证据",
    "STRATEGY_BACKTEST_FAILED": "USDJPY SQLite Strategy JSON 回测失败",
    "STRATEGY_BACKTEST_NO_TRADES": "USDJPY SQLite Strategy JSON 回测没有成交，不能证明策略有效",
    "HISTORY_PRODUCTION_NOT_READY": "USDJPY 历史样本未达到生产级 PASS，不能晋级",
    "INSUFFICIENT_SAMPLES": "样本不足，不能证明策略稳定",
    "REPLAY_FAILED": "回放评分失败",
    "WALK_FORWARD_INSUFFICIENT": "每个 seed 的 train / validation / forward 分段样本不足",
    "WALK_FORWARD_FAILED": "Walk-forward forward/validation 段不稳定",
    "WALK_FORWARD_UNSTABLE": "每个 seed 的 validation 或 forward 段不稳定，疑似过拟合",
    "OVERFIT_RISK": "过拟合风险偏高",
    "RSI_MIN_TRADE_GATE": "RSI LONG 少于 20 笔有效交易，正收益不能晋级",
    "MAX_ADVERSE_TOO_HIGH": "最大不利波动扩大",
    "FITNESS_TOO_LOW": "综合 fitness 太低",
    "DUPLICATE_STRATEGY": "重复策略，已归档",
    "HARD_RISK_GATE_VIOLATION": "尝试绕过 runtime / fastlane / news / spread 硬门禁",
    "PARITY_PROMOTION_GATE_BLOCKED": "P4-2 parity 失败或缺失，禁止进入 SHADOW、GA elite 或 MICRO_LIVE",
    "PARITY_OR_EXECUTION_EVIDENCE_FAILED": "Strategy JSON / Python Replay / MQL5 EA 或执行反馈证据失败",
}


def explain_blocker(code: str | None) -> str:
    if not code:
        return "通过 GA 评分"
    return BLOCKER_ZH.get(str(code), str(code))
