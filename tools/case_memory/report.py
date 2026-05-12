from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .builder import build_case_memory_candidates
from .io_utils import append_jsonl_unique, load_json, utc_now_iso, write_json
from .schema import (
    AGENT_VERSION,
    CASE_MEMORY_SOURCES,
    FOCUS_SYMBOL,
    SAFETY,
    SCHEMA_REPORT,
    candidate_ledger_path,
    report_path,
)


def build_case_memory_report(
    runtime_dir: Path,
    *,
    write: bool = True,
    limit: int = 8,
) -> Dict[str, Any]:
    payload = build_case_memory_candidates(runtime_dir, write_case_memory=write, limit=limit)
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    ga_seeds = payload.get("gaSeeds") if isinstance(payload.get("gaSeeds"), list) else []
    report: Dict[str, Any] = {
        "ok": payload.get("status") != "BLOCKED_BY_PARITY",
        "schema": SCHEMA_REPORT,
        "agentVersion": AGENT_VERSION,
        "createdAt": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "status": payload.get("status"),
        "caseSummary": payload.get("caseSummary") or {},
        "candidateCount": len(candidates),
        "gaSeedCount": len(ga_seeds),
        "candidates": candidates,
        "gaSeeds": ga_seeds,
        "parityGate": payload.get("parityGate") or {},
        "sources": CASE_MEMORY_SOURCES,
        "nextActionZh": _next_action(payload),
        "reasonZh": payload.get("reasonZh") or "",
        "safety": dict(SAFETY),
    }
    if write:
        write_json(report_path(runtime_dir), report)
        if candidates:
            append_jsonl_unique(candidate_ledger_path(runtime_dir), candidates, "candidateId")
    return report


def status(runtime_dir: Path) -> Dict[str, Any]:
    payload = load_json(report_path(runtime_dir))
    if payload:
        return {"ok": True, **payload}
    return {
        "ok": True,
        "schema": SCHEMA_REPORT,
        "agentVersion": AGENT_VERSION,
        "symbol": FOCUS_SYMBOL,
        "status": "WAITING_FIRST_RUN",
        "candidateCount": 0,
        "gaSeedCount": 0,
        "reasonZh": "等待 Case Memory 生成 Strategy JSON candidate。",
        "safety": dict(SAFETY),
    }


def _next_action(payload: Dict[str, Any]) -> str:
    if payload.get("status") == "BLOCKED_BY_PARITY":
        return "先修复 Strategy / Replay / EA parity，再生成 Strategy JSON candidate。"
    if payload.get("gaSeeds"):
        return "下一轮 GA population 应纳入这些 CASE_MEMORY shadow seeds。"
    return "等待 replay、执行反馈或 GA blocker 产生可转写的 Case Memory。"
