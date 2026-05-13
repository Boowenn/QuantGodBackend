from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import ensure_dir, read_csv_rows, read_json, read_jsonl, write_json, write_jsonl
from .schema import CORE_FIELDS, FEEDBACK_LEDGER, FOCUS_SYMBOL, OUTPUT_DIR, PRODUCER_REPORT, SAFETY, SCHEMA


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _float(row: dict[str, Any], *keys: str, default: float | None = None) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except Exception:
            continue
    return default


def _text(row: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _is_usdjpy(row: dict[str, Any]) -> bool:
    symbol = _text(row, "symbol", "Symbol", "instrument", "pair").upper()
    return symbol in {"USDJPY", "USDJPYC", "USDJPY.C", FOCUS_SYMBOL.upper()}


def _fingerprint(row: dict[str, Any]) -> str:
    key = "|".join(
        str(row.get(name, ""))
        for name in (
            "feedbackId",
            "timestamp",
            "createdAt",
            "strategyId",
            "eventType",
            "executionMode",
            "expectedPrice",
            "fillPrice",
            "profitR",
        )
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _complete(row: dict[str, Any]) -> bool:
    return all(row.get(field) not in (None, "") for field in CORE_FIELDS)


def _event_from_shadow(row: dict[str, Any], source: str) -> dict[str, Any] | None:
    if not _is_usdjpy(row):
        return None
    strategy = _text(row, "strategyId", "strategy", "strategyName", "route", default="USDJPY_SHADOW_STRATEGY")
    expected = _float(row, "expectedPrice", "entryPrice", "priceAtSignal", "signalPrice", "open", "currentPrice")
    fill = _float(row, "fillPrice", "exitPrice", "closePrice", "currentPrice", "priceAfter60m", "price")
    profit_r = _float(row, "profitR", "scoreR", "r", "posteriorR", "netR", default=0.0)
    mfe_r = _float(row, "mfeR", "maxFavorableR", "mfe", default=max(float(profit_r or 0.0), 0.0))
    mae_r = _float(row, "maeR", "maxAdverseR", "mae", default=min(float(profit_r or 0.0), 0.0))
    if expected is None and fill is None:
        expected = 0.0
        fill = 0.0
    elif expected is None:
        expected = fill
    elif fill is None:
        fill = expected
    event = {
        "schema": "quantgod.execution_feedback.v1",
        "timestamp": _text(row, "timestamp", "time", "generatedAt", default=_now_iso()),
        "symbol": FOCUS_SYMBOL,
        "strategyId": strategy,
        "eventType": "SHADOW_EXIT",
        "executionMode": "SHADOW",
        "expectedPrice": expected,
        "fillPrice": fill,
        "slippagePips": _float(row, "slippagePips", "slippage", default=0.0),
        "latencyMs": _float(row, "latencyMs", "latency", default=0.0),
        "spreadAtEntry": _float(row, "spreadAtEntry", "spread", "spreadPips", default=0.0),
        "profitR": profit_r,
        "mfeR": mfe_r,
        "maeR": mae_r,
        "source": source,
        "sourceKind": "shadow_outcome",
    }
    event["feedbackId"] = _fingerprint(event)
    return event if _complete(event) else None


def _event_from_close_history(row: dict[str, Any], source: str) -> dict[str, Any] | None:
    if not _is_usdjpy(row):
        return None
    strategy = _text(row, "strategyId", "strategy", "comment", "magic", default="USDJPY_LIVE_UNKNOWN")
    expected = _float(row, "expectedPrice", "entryPrice", "openPrice", "priceOpen")
    fill = _float(row, "fillPrice", "closePrice", "priceClose", "exitPrice")
    profit_r = _float(row, "profitR", "r", "scoreR")
    if profit_r is None:
        profit = _float(row, "profit", "profitUSC", "pnl", default=0.0)
        profit_r = float(profit or 0.0) / 10.0
    if expected is None and fill is None:
        return None
    if expected is None:
        expected = fill
    if fill is None:
        fill = expected
    event = {
        "schema": "quantgod.execution_feedback.v1",
        "timestamp": _text(row, "timestamp", "closeTime", "time", default=_now_iso()),
        "symbol": FOCUS_SYMBOL,
        "strategyId": strategy,
        "eventType": "LIVE_EXIT",
        "executionMode": "LIVE",
        "expectedPrice": expected,
        "fillPrice": fill,
        "slippagePips": _float(row, "slippagePips", "slippage", default=0.0),
        "latencyMs": _float(row, "latencyMs", default=0.0),
        "spreadAtEntry": _float(row, "spreadAtEntry", "spread", default=0.0),
        "profitR": profit_r,
        "mfeR": _float(row, "mfeR", "maxFavorableR", default=max(float(profit_r or 0.0), 0.0)),
        "maeR": _float(row, "maeR", "maxAdverseR", default=min(float(profit_r or 0.0), 0.0)),
        "exitReason": _text(row, "exitReason", "reason", default="UNKNOWN"),
        "source": source,
        "sourceKind": "close_history",
    }
    event["feedbackId"] = _fingerprint(event)
    return event if _complete(event) else None


def _default_mt5_files_dir() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "net.metaquotes.wine.metatrader5"
        / "drive_c"
        / "Program Files"
        / "MetaTrader 5"
        / "MQL5"
        / "Files"
    )


def _source_dirs(runtime_dir: Path) -> list[Path]:
    raw_dirs = [
        runtime_dir,
        Path(os.environ.get("QG_MT5_FILES_DIR", "")).expanduser() if os.environ.get("QG_MT5_FILES_DIR") else None,
        Path(os.environ.get("QG_HFM_FILES_DIR", "")).expanduser() if os.environ.get("QG_HFM_FILES_DIR") else None,
        _default_mt5_files_dir(),
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in raw_dirs:
        if not path:
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _candidate_csvs(runtime_dir: Path) -> list[Path]:
    names = [
        "ShadowCandidateOutcomeLedger.csv",
        "QuantGod_ShadowCandidateOutcomeLedger.csv",
        "QuantGod_ShadowOutcomeLedger.csv",
        "QuantGod_CloseHistory.csv",
    ]
    paths: list[Path] = []
    for directory in _source_dirs(runtime_dir):
        paths.extend(directory / name for name in names)
        paths.extend(directory.glob("QuantGod_CloseHistory*.csv"))
        paths.extend((directory / "adaptive").glob("*Outcome*.csv") if (directory / "adaptive").exists() else [])
        paths.extend((directory / "journal").glob("*Outcome*.csv") if (directory / "journal").exists() else [])
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _candidate_feedback_jsonl(runtime_dir: Path) -> list[Path]:
    names = [
        "QuantGod_LiveExecutionFeedback.jsonl",
        "QuantGod_LiveExecutionFeedbackHistory.jsonl",
        "execution/QuantGod_LiveExecutionFeedback.jsonl",
        "evidence_os/QuantGod_LiveExecutionFeedback.jsonl",
    ]
    paths = [directory / name for directory in _source_dirs(runtime_dir) for name in names]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _event_from_feedback(row: dict[str, Any], source: str) -> dict[str, Any] | None:
    if not _is_usdjpy(row):
        return None
    profit_r = _float(row, "profitR", "r", "scoreR", default=0.0)
    event = {
        "schema": "quantgod.execution_feedback.v1",
        "timestamp": _text(row, "timestamp", "createdAt", "generatedAt", "generatedAtServer", "eventTimeServer", default=_now_iso()),
        "symbol": FOCUS_SYMBOL,
        "strategyId": _text(row, "strategyId", "strategy", default="USDJPY_FEEDBACK_UNKNOWN"),
        "eventType": _text(row, "eventType", "event", "type", default="FEEDBACK_EVENT").upper(),
        "executionMode": _text(row, "executionMode", "lane", "mode", default="LIVE" if _text(row, "orderTicket", "dealTicket") else "SHADOW").upper(),
        "policyId": _text(row, "policyId", default=""),
        "intentId": _text(row, "intentId", default=""),
        "expectedPrice": _float(row, "expectedPrice", default=0.0),
        "fillPrice": _float(row, "fillPrice", default=0.0),
        "slippagePips": _float(row, "slippagePips", "slippage", default=0.0),
        "latencyMs": _float(row, "latencyMs", "latency", default=0.0),
        "spreadAtEntry": _float(row, "spreadAtEntry", "spread", "spreadPips", default=0.0),
        "profitR": profit_r,
        "mfeR": _float(row, "mfeR", "maxFavorableR", default=max(float(profit_r or 0.0), 0.0)),
        "maeR": _float(row, "maeR", "maxAdverseR", default=min(float(profit_r or 0.0), 0.0)),
        "rejectReason": _text(row, "rejectReason", default=""),
        "exitReason": _text(row, "exitReason", default=""),
        "source": source,
        "sourceKind": "existing_feedback",
    }
    event["feedbackId"] = _text(row, "feedbackId", default="") or _fingerprint(event)
    return event if _complete(event) else None


def build_feedback(runtime_dir: Path, write: bool = False) -> dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    out_dir = ensure_dir(runtime_dir / OUTPUT_DIR)
    ledger_path = out_dir / FEEDBACK_LEDGER
    existing = read_jsonl(ledger_path, 10000)
    by_id = {str(row.get("feedbackId") or _fingerprint(row)): row for row in existing if isinstance(row, dict)}
    source_counts: dict[str, int] = {}
    skipped = 0
    generated = 0
    for jsonl_path in _candidate_feedback_jsonl(runtime_dir):
        if jsonl_path == ledger_path:
            continue
        for row in read_jsonl(jsonl_path, 10000):
            source_name = str(jsonl_path.relative_to(jsonl_path.parent.parent)) if jsonl_path.parent.name in {"execution", "evidence_os"} else jsonl_path.name
            event = _event_from_feedback(row, source_name)
            if event is None:
                skipped += 1
                continue
            feedback_id = str(event["feedbackId"])
            if feedback_id not in by_id:
                by_id[feedback_id] = event
                generated += 1
                source_counts[source_name] = source_counts.get(source_name, 0) + 1
    for csv_path in _candidate_csvs(runtime_dir):
        for row in read_csv_rows(csv_path):
            source_name = csv_path.name
            event = None
            if "CloseHistory" in source_name:
                event = _event_from_close_history(row, source_name)
            if event is None:
                event = _event_from_shadow(row, source_name)
            if event is None:
                skipped += 1
                continue
            feedback_id = str(event["feedbackId"])
            if feedback_id not in by_id:
                by_id[feedback_id] = event
                generated += 1
                source_counts[source_name] = source_counts.get(source_name, 0) + 1
    rows = list(by_id.values())
    complete_rows = [row for row in rows if _complete(row)]
    report = {
        "schema": SCHEMA,
        "generatedAt": _now_iso(),
        "status": "PASS" if len(complete_rows) >= 5 else "WARN",
        "summaryZh": "执行反馈样本已自动补齐" if len(complete_rows) >= 5 else "执行反馈样本仍需积累",
        "ledgerPath": str(ledger_path),
        "existingCount": len(existing),
        "generatedCount": generated,
        "sampleCount": len(rows),
        "completeSampleCount": len(complete_rows),
        "skippedRows": skipped,
        "sourceCounts": source_counts,
        "safety": SAFETY,
        "nextActionsZh": [
            "继续让 EA / shadow 链路写入 execution feedback",
            "P4-6 会读取该 ledger 并更新覆盖率",
        ],
    }
    if write:
        write_jsonl(ledger_path, rows)
        write_json(out_dir / PRODUCER_REPORT, report)
    return report


def load_latest(runtime_dir: Path) -> dict[str, Any] | None:
    return read_json(Path(runtime_dir) / OUTPUT_DIR / PRODUCER_REPORT, None)


def write_sample(runtime_dir: Path, overwrite: bool = False) -> dict[str, str]:
    runtime_dir = Path(runtime_dir)
    csv_path = runtime_dir / "ShadowCandidateOutcomeLedger.csv"
    if csv_path.exists() and not overwrite:
        return {"sample": str(csv_path)}
    ensure_dir(runtime_dir)
    csv_path.write_text(
        "timestamp,symbol,strategy,entryPrice,exitPrice,profitR,mfeR,maeR,spreadAtEntry\n"
        "2026-05-13T00:00:00Z,USDJPYc,USDJPY_RSI_REVERSAL_LONG_V1,155.10,155.18,0.32,0.58,-0.12,0.8\n"
        "2026-05-13T01:00:00Z,USDJPYc,USDJPY_RSI_REVERSAL_LONG_V1,155.20,155.14,-0.24,0.10,-0.35,0.9\n",
        encoding="utf-8",
    )
    return {"sample": str(csv_path)}
