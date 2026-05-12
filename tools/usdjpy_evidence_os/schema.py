from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

AGENT_VERSION = "perfect-v1.1"
FOCUS_SYMBOL = "USDJPYc"

SAFETY_BOUNDARY: Dict[str, Any] = {
    "usdJpyOnly": True,
    "strategyJsonContract": True,
    "readOnlyAuditPlane": True,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "livePresetMutationAllowed": False,
    "polymarketRealMoneyAllowed": False,
    "telegramCommandExecutionAllowed": False,
    "gatewayReceivesCommands": False,
}


def evidence_dir(runtime_dir: Path) -> Path:
    return runtime_dir / "evidence_os"


def parity_path(runtime_dir: Path) -> Path:
    return evidence_dir(runtime_dir) / "QuantGod_StrategyParityReport.json"


def parity_public_dir(runtime_dir: Path) -> Path:
    return runtime_dir / "parity"


def parity_public_path(runtime_dir: Path) -> Path:
    return parity_public_dir(runtime_dir) / "QuantGod_StrategyParityReport.json"


def parity_ledger_path(runtime_dir: Path) -> Path:
    return parity_public_dir(runtime_dir) / "QuantGod_StrategyParityLedger.csv"


def execution_feedback_path(runtime_dir: Path) -> Path:
    return evidence_dir(runtime_dir) / "QuantGod_LiveExecutionQualityReport.json"


def execution_feedback_ledger_path(runtime_dir: Path) -> Path:
    return evidence_dir(runtime_dir) / "QuantGod_LiveExecutionFeedback.jsonl"


def execution_public_dir(runtime_dir: Path) -> Path:
    return runtime_dir / "execution"


def execution_feedback_public_path(runtime_dir: Path) -> Path:
    return execution_public_dir(runtime_dir) / "QuantGod_LiveExecutionQualityReport.json"


def execution_feedback_public_ledger_path(runtime_dir: Path) -> Path:
    return execution_public_dir(runtime_dir) / "QuantGod_LiveExecutionFeedback.jsonl"


def case_memory_path(runtime_dir: Path) -> Path:
    return evidence_dir(runtime_dir) / "QuantGod_CaseMemory.jsonl"


def case_summary_path(runtime_dir: Path) -> Path:
    return evidence_dir(runtime_dir) / "QuantGod_CaseMemorySummary.json"


def os_status_path(runtime_dir: Path) -> Path:
    return evidence_dir(runtime_dir) / "QuantGod_USDJPYEvidenceOSStatus.json"


def notification_dir(runtime_dir: Path) -> Path:
    return runtime_dir / "notifications"


def gateway_status_path(runtime_dir: Path) -> Path:
    return notification_dir(runtime_dir) / "QuantGod_TelegramGatewayStatus.json"


def gateway_ledger_path(runtime_dir: Path) -> Path:
    return notification_dir(runtime_dir) / "QuantGod_TelegramGatewayLedger.jsonl"


def gateway_queue_path(runtime_dir: Path) -> Path:
    return notification_dir(runtime_dir) / "QuantGod_NotificationEventQueue.jsonl"
