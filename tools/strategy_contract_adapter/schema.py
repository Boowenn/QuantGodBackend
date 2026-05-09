from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

AGENT_VERSION = "v2.8"
CONTRACT_SCHEMA = "quantgod.strategy_json_ea_contract.v1"
CONTRACT_DIR = "strategy_contract"
CONTRACT_JSON_FILE = "QuantGod_StrategyJsonEAContract.json"
CONTRACT_EA_FILE = "QuantGod_StrategyJsonEAContract_EA.txt"
CONTRACT_STATUS_FILE = "QuantGod_StrategyJsonEAContractStatus.json"
EA_STATUS_FILE = "QuantGod_StrategyJsonEAContractEAStatus.json"

CONTRACT_MODE = "SHADOW_EVALUATION_ONLY"
ALLOWED_CONTRACT_MODES = {
    "SHADOW_EVALUATION_ONLY",
    "TESTER_EVALUATION_ONLY",
    "PAPER_LIVE_SIM_EVALUATION_ONLY",
}

SAFETY_BOUNDARY: Dict[str, Any] = {
    "usdJpyOnly": True,
    "strategyJsonOnly": True,
    "readOnlyAdapter": True,
    "shadowFirst": True,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "livePresetMutationAllowed": False,
    "writesMt5OrderRequest": False,
    "gaDirectLiveAllowed": False,
    "polymarketRealMoneyAllowed": False,
    "telegramCommandExecutionAllowed": False,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def contract_dir(runtime_dir: Path) -> Path:
    return runtime_dir / CONTRACT_DIR

