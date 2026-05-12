from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json, read_csv_rows
from .schema import REQUIRED_STRATEGY_FAMILIES


def _status_from_text(value: str) -> str:
    text = (value or "").upper()
    if "FAIL" in text or "BLOCK" in text or "REJECT" in text:
        return "FAIL"
    if "WARN" in text or "MISS" in text or "NEED" in text:
        return "WARN"
    if "PASS" in text or "OK" in text or "READY" in text:
        return "PASS"
    return "UNKNOWN"


def audit_parity(runtime_dir: Path) -> dict[str, Any]:
    report_path = runtime_dir / "parity" / "QuantGod_StrategyParityReport.json"
    ledger_path = runtime_dir / "parity" / "QuantGod_StrategyParityLedger.csv"
    report = read_json(report_path, {}) or {}
    ledger = read_csv_rows(ledger_path, 1000)
    rows: list[dict[str, Any]] = []
    observed: dict[str, str] = {}

    for item in report.get("families") or report.get("matrix") or []:
        if not isinstance(item, dict):
            continue
        family = item.get("strategyFamily") or item.get("strategy") or item.get("family")
        status = _status_from_text(str(item.get("status") or item.get("parityStatus") or ""))
        if family:
            observed[str(family)] = status

    for row in ledger:
        family = row.get("strategyFamily") or row.get("strategy") or row.get("family")
        status = _status_from_text(row.get("status") or row.get("parityStatus") or "")
        if family and str(family) not in observed:
            observed[str(family)] = status

    for family in REQUIRED_STRATEGY_FAMILIES:
        rows.append({"strategyFamily": family, "parityStatus": observed.get(family, "MISSING")})

    fail_count = sum(1 for row in rows if row["parityStatus"] == "FAIL")
    missing_count = sum(1 for row in rows if row["parityStatus"] == "MISSING")
    pass_count = sum(1 for row in rows if row["parityStatus"] == "PASS")
    status = "FAIL" if fail_count else ("WARN" if missing_count else "PASS")
    return {
        "status": status,
        "reportPath": str(report_path) if report_path.exists() else "",
        "ledgerPath": str(ledger_path) if ledger_path.exists() else "",
        "passCount": pass_count,
        "missingCount": missing_count,
        "failCount": fail_count,
        "matrix": rows,
        "recommendation": "Fix PARITY_FAIL before promotion." if fail_count else "Run full family parity batch until missing families are covered.",
    }
