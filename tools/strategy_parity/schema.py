from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.usdjpy_evidence_os.schema import (
        FOCUS_SYMBOL,
        SAFETY_BOUNDARY,
        parity_ledger_path,
        parity_public_path,
    )
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.schema import FOCUS_SYMBOL, SAFETY_BOUNDARY, parity_ledger_path, parity_public_path


PARITY_REPORT_SCHEMA = "quantgod.strategy_parity_report.v1"
PARITY_LEDGER_SCHEMA = "quantgod.strategy_parity_ledger.v1"

PARITY_COMPARE_FIELDS: List[str] = [
    "symbol",
    "strategyId",
    "timeframe",
    "barTime",
    "rsiValue",
    "rsiCrossback",
    "sessionAllowed",
    "spreadAllowed",
    "newsRisk",
    "runtimeFresh",
    "fastlaneState",
    "entryAllowed",
    "entryMode",
    "exitMode",
    "lotSuggestion",
]

PROMOTION_BLOCK_RULES: Dict[str, Any] = {
    "PARITY_FAIL": ["SHADOW", "GA_ELITE", "MICRO_LIVE"],
    "reasonZh": "Strategy / Replay / EA parity 失败时禁止进入 shadow、GA elite 和 micro-live。",
}


def report_path(runtime_dir: Path) -> Path:
    return parity_public_path(runtime_dir)


def ledger_path(runtime_dir: Path) -> Path:
    return parity_ledger_path(runtime_dir)
