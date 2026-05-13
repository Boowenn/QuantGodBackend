from __future__ import annotations

from typing import Final

SCHEMA: Final[str] = "quantgod.execution_feedback_producer.v1"
FOCUS_SYMBOL: Final[str] = "USDJPYc"
OUTPUT_DIR: Final[str] = "execution"
FEEDBACK_LEDGER: Final[str] = "QuantGod_LiveExecutionFeedback.jsonl"
PRODUCER_REPORT: Final[str] = "QuantGod_LiveExecutionFeedbackProducerReport.json"

CORE_FIELDS: Final[tuple[str, ...]] = (
    "strategyId",
    "eventType",
    "expectedPrice",
    "fillPrice",
    "slippagePips",
    "latencyMs",
    "spreadAtEntry",
    "profitR",
    "mfeR",
    "maeR",
)

SAFETY: Final[dict[str, object]] = {
    "localOnly": True,
    "readOnlyDataPlane": True,
    "advisoryOnly": True,
    "executionFeedbackOnly": True,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "livePresetMutationAllowed": False,
    "telegramCommandExecutionAllowed": False,
    "polymarketRealMoneyAllowed": False,
}
