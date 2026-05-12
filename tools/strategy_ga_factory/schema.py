"""Shared schema constants for the Strategy JSON GA Factory."""

from __future__ import annotations

from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

try:
    from tools.strategy_ga.schema import SAFETY_BOUNDARY, utc_now_iso
except ModuleNotFoundError:  # pragma: no cover
    from strategy_ga.schema import SAFETY_BOUNDARY, utc_now_iso


AGENT_VERSION = "p4-4"
SCHEMA_FACTORY_STATE = "quantgod.strategy_ga_factory.state.v1"
SCHEMA_ELITE_ARCHIVE = "quantgod.strategy_ga_factory.elite_archive.v1"
SCHEMA_GRAVEYARD = "quantgod.strategy_ga_factory.strategy_graveyard.v1"
SCHEMA_LINEAGE_TREE = "quantgod.strategy_ga_factory.lineage_tree.v1"

STATE_FILE = "QuantGod_GAFactoryState.json"
ELITE_ARCHIVE_FILE = "QuantGod_GAEliteArchive.json"
GRAVEYARD_FILE = "QuantGod_GAStrategyGraveyard.json"
LINEAGE_TREE_FILE = "QuantGod_GALineageTree.json"
LEDGER_FILE = "QuantGod_GAFactoryLedger.csv"

ALLOWED_PROMOTION_STAGES: List[str] = [
    "SHADOW",
    "FAST_SHADOW",
    "TESTER_ONLY",
    "PAPER_LIVE_SIM",
]

SAFETY: Dict[str, Any] = {
    **SAFETY_BOUNDARY,
    "gaFactoryAuditOnly": True,
    "strategyJsonOnly": True,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "livePresetMutationAllowed": False,
    "writesMt5OrderRequest": False,
    "telegramCommandExecutionAllowed": False,
    "polymarketRealMoneyAllowed": False,
    "gaFactoryDirectLiveAllowed": False,
    "allowedPromotionStages": ALLOWED_PROMOTION_STAGES,
}


def ga_factory_dir(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / "ga_factory"


def state_path(runtime_dir: Path) -> Path:
    return ga_factory_dir(runtime_dir) / STATE_FILE


def elite_archive_path(runtime_dir: Path) -> Path:
    return ga_factory_dir(runtime_dir) / ELITE_ARCHIVE_FILE


def graveyard_path(runtime_dir: Path) -> Path:
    return ga_factory_dir(runtime_dir) / GRAVEYARD_FILE


def lineage_tree_path(runtime_dir: Path) -> Path:
    return ga_factory_dir(runtime_dir) / LINEAGE_TREE_FILE


def ledger_path(runtime_dir: Path) -> Path:
    return ga_factory_dir(runtime_dir) / LEDGER_FILE
