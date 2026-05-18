from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_VERSION = "p4-8c"
SCHEMA_STABILITY_REPORT = "quantgod.ga_multi_generation_stability.report.v1"
REPORT_FILE = "QuantGod_GAMultiGenerationStabilityReport.json"
LEDGER_FILE = "QuantGod_GAMultiGenerationStabilityLedger.csv"

MIN_GENERATIONS_WATCH = 2
MIN_GENERATIONS_STABLE = 3
MIN_GENERATIONS_PRODUCTION_READY = 5
MIN_CANDIDATES_WATCH = 8
MIN_CANDIDATES_STABLE = 16
MIN_ELITE_STABLE = 1
MIN_ELITE_REPEAT_STABLE = 1
MIN_GRAVEYARD_CLOSED = 48
MIN_LINEAGE_NODES_STABLE = 4
MIN_LINEAGE_EDGES_STABLE = 1

SAFETY: dict[str, Any] = {
    "usdJpyOnly": True,
    "strategyJsonOnly": True,
    "gaStabilityAuditOnly": True,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "livePresetMutationAllowed": False,
    "writesMt5OrderRequest": False,
    "telegramCommandExecutionAllowed": False,
    "polymarketRealMoneyAllowed": False,
    "gaDirectLiveAllowed": False,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def output_dir(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / "production_validation"


def report_path(runtime_dir: Path) -> Path:
    return output_dir(runtime_dir) / REPORT_FILE


def ledger_path(runtime_dir: Path) -> Path:
    return output_dir(runtime_dir) / LEDGER_FILE
