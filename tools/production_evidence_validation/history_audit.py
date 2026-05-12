from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json, sqlite_table_summary

BAR_TABLES = ["bars_m1", "bars_m5", "bars_m15", "bars_h1", "usd_jpy_bars_m1", "usd_jpy_bars_m5"]


def audit_history(runtime_dir: Path) -> dict[str, Any]:
    candidates = [
        runtime_dir / "backtest" / "usdjpy.sqlite",
        runtime_dir / "history" / "usdjpy.sqlite",
        runtime_dir / "usdjpy.sqlite",
    ]
    existing = next((path for path in candidates if path.exists()), None)
    backtest_report = read_json(runtime_dir / "backtest" / "QuantGod_StrategyBacktestReport.json", {}) or {}
    if not existing:
        return {
            "status": "WARN",
            "reason": "USDJPY SQLite history database not found in expected runtime paths",
            "databaseFound": False,
            "backtestReportFound": bool(backtest_report),
            "recommendation": "Run USDJPY history sync and strategy backtest before trusting GA fitness.",
        }
    summaries = sqlite_table_summary(existing, BAR_TABLES)
    non_empty = [row for row in summaries if int(row.get("rows") or 0) > 0]
    status = "PASS" if len(non_empty) >= 2 else "WARN"
    return {
        "status": status,
        "databaseFound": True,
        "databasePath": str(existing),
        "tables": summaries,
        "nonEmptyTables": len(non_empty),
        "backtestReportFound": bool(backtest_report),
        "recommendation": "History looks usable." if status == "PASS" else "History exists but needs more populated bar tables.",
    }
