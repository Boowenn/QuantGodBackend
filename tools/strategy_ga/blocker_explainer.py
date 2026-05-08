from __future__ import annotations

BLOCKER_ZH = {
    "SCHEMA_INVALID": "Strategy JSON schema 不合法",
    "SAFETY_REJECTED": "安全边界拒绝：含代码、密钥或交易执行原语",
    "STRATEGY_BACKTEST_MISSING": "缺少 USDJPY SQLite Strategy JSON 回测证据",
    "STRATEGY_BACKTEST_FAILED": "USDJPY SQLite Strategy JSON 回测失败",
    "INSUFFICIENT_SAMPLES": "样本不足，不能证明策略稳定",
    "REPLAY_FAILED": "回放评分失败",
    "WALK_FORWARD_FAILED": "Walk-forward forward/validation 段不稳定",
    "OVERFIT_RISK": "过拟合风险偏高",
    "MAX_ADVERSE_TOO_HIGH": "最大不利波动扩大",
    "FITNESS_TOO_LOW": "综合 fitness 太低",
    "DUPLICATE_STRATEGY": "重复策略，已归档",
    "HARD_RISK_GATE_VIOLATION": "尝试绕过 runtime / fastlane / news / spread 硬门禁",
    "PARITY_OR_EXECUTION_EVIDENCE_FAILED": "Strategy JSON / Python Replay / MQL5 EA 或执行反馈证据失败",
}


def explain_blocker(code: str | None) -> str:
    if not code:
        return "通过 GA 评分"
    return BLOCKER_ZH.get(str(code), str(code))
