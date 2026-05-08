from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .io_utils import append_jsonl_unique, load_json, read_jsonl_tail, utc_now_iso, write_json
from .schema import (
    AGENT_VERSION,
    FOCUS_SYMBOL,
    SAFETY_BOUNDARY,
    execution_feedback_ledger_path,
    execution_feedback_path,
)

AUDITED_FEEDBACK_SOURCES = {
    "QuantGod_LiveExecutionFeedback.jsonl",
    "QuantGod_LiveExecutionFeedbackHistory.jsonl",
}

REQUIRED_LIVE_EXECUTION_FIELDS = {
    "core": ("policyId", "intentId", "eventType", "symbol", "strategyId"),
    "send": ("expectedPrice", "latencyMs"),
    "fill": ("fillPrice", "slippagePips", "latencyMs"),
    "reject": ("rejectReason", "latencyMs"),
    "outcome": ("profitR", "mfeR", "maeR", "exitReason"),
}

SEND_EVENT_TYPES = {"ORDER_ACCEPTED", "ORDER_SEND", "ORDER_REQUESTED"}
FILL_EVENT_TYPES = {"ORDER_FILL"}
CLOSE_EVENT_TYPES = {"ORDER_CLOSE", "POSITION_CLOSE", "HISTORY_CLOSE"}
REJECT_EVENT_TYPES = {"ORDER_REJECT", "ORDER_REJECTED"}
OUTCOME_EVENT_TYPES = CLOSE_EVENT_TYPES | {"TRADE_OUTCOME", "HISTORY_OUTCOME"}


def build_execution_feedback(runtime_dir: Path, write: bool = True) -> Dict[str, Any]:
    rows = _collect_rows(runtime_dir)
    normalized = _dedupe_feedback(
        [_normalize_row(index, row, source) for index, (row, source) in enumerate(rows, start=1)]
    )
    metrics = _metrics(normalized)
    field_completeness = _field_completeness(normalized)
    metrics = {
        **metrics,
        "fieldCoveragePct": field_completeness.get("fieldCoveragePct", 0.0),
        "coreMissingFieldCount": field_completeness.get("coreMissingFieldCount", 0),
        "conditionalMissingFieldCount": field_completeness.get("conditionalMissingFieldCount", 0),
        "fieldCompletenessStatus": field_completeness.get("status"),
    }
    quality_gates = _quality_gates_from_metrics(metrics, field_completeness)
    promotion_gate = _promotion_gate(metrics, quality_gates, field_completeness)
    case_memory_triggers = _case_memory_triggers(metrics, promotion_gate)
    report = {
        "ok": True,
        "schema": "quantgod.live_execution_quality_report.v1",
        "agentVersion": AGENT_VERSION,
        "createdAt": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "sampleCount": len(normalized),
        "metrics": metrics,
        "fieldCompleteness": field_completeness,
        "qualityGates": quality_gates,
        "promotionGate": promotion_gate,
        "caseMemoryTriggers": case_memory_triggers,
        "agentAction": _agent_action(promotion_gate),
        "nextActionZh": _next_action_zh(promotion_gate),
        "recentFeedback": normalized[-20:],
        "reasonZh": "执行反馈统一审计 EA trade event、成交、拒单、滑点、延迟和 policy 偏离；不会下单。",
        "safety": dict(SAFETY_BOUNDARY),
    }
    if write:
        if normalized:
            append_jsonl_unique(execution_feedback_ledger_path(runtime_dir), normalized, "feedbackId")
        write_json(execution_feedback_path(runtime_dir), report)
    return report


def _collect_rows(runtime_dir: Path) -> List[Tuple[Dict[str, Any], str]]:
    rows: List[Tuple[Dict[str, Any], str]] = []
    for name in ("QuantGod_LiveExecutionFeedback.jsonl", "QuantGod_LiveExecutionFeedbackHistory.jsonl"):
        path = runtime_dir / name
        rows.extend((row, path.name) for row in read_jsonl_tail(path, 1000))
    trade_events = runtime_dir / "QuantGod_RuntimeTradeEvents.jsonl"
    rows.extend((row, trade_events.name) for row in read_jsonl_tail(trade_events, 500))
    live_loop_ledger = runtime_dir / "live" / "QuantGod_USDJPYLiveLoopLedger.csv"
    if live_loop_ledger.exists():
        rows.extend((row, live_loop_ledger.name) for row in _read_csv(live_loop_ledger))
    for name in (
        "QuantGod_TradeJournal.csv",
        "QuantGod_TradeEventLinks.csv",
        "QuantGod_TradeOutcomeLabels.csv",
        "QuantGod_USDJPYEADryRunDecisionLedger.csv",
    ):
        path = runtime_dir / name
        if path.exists():
            rows.extend((row, path.name) for row in _read_csv(path))
    adaptive_dry_run = runtime_dir / "adaptive" / "QuantGod_USDJPYEADryRunDecisionLedger.csv"
    if adaptive_dry_run.exists():
        rows.extend((row, adaptive_dry_run.name) for row in _read_csv(adaptive_dry_run))
    for path in runtime_dir.glob("QuantGod_CloseHistory*.csv"):
        rows.extend((row, path.name) for row in _read_csv(path))
    if not rows:
        status = load_json(runtime_dir / "live" / "QuantGod_USDJPYLiveLoopStatus.json")
        if status:
            rows.append((status, "QuantGod_USDJPYLiveLoopStatus.json"))
    return rows


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except Exception:
        return []


def _normalize_row(index: int, row: Dict[str, Any], source: str) -> Dict[str, Any]:
    symbol = _first(row, "symbol", "Symbol") or FOCUS_SYMBOL
    event_type = _first(row, "eventType", "EventType")
    expected_price = _num(_first(row, "expectedPrice", "entryPrice", "EntryPrice", "openPrice"))
    fill_price = _num(_first(row, "fillPrice", "price", "Price", "exitPrice", "ClosePrice"))
    slippage_pips = _num(_first(row, "slippagePips", "SlippagePips"))
    if slippage_pips == 0.0 and expected_price and fill_price:
        slippage_pips = round((fill_price - expected_price) / 0.01, 4)
    retcode = _first(row, "retcode", "Retcode", "retCode")
    reject_reason = _reject_reason(row, retcode)
    feedback_id = _feedback_id(index, row, source)
    raw_policy_id = _first(row, "policyId", "PolicyId")
    raw_intent_id = _first(row, "intentId", "IntentId")
    raw_strategy_id = _first(row, "strategyId", "strategy", "Strategy")
    raw_field_presence = _field_presence(row, source, event_type, retcode)
    return {
        "schema": "quantgod.live_execution_feedback.v1",
        "feedbackId": feedback_id,
        "createdAt": utc_now_iso(),
        "symbol": symbol,
        "eventType": event_type,
        "side": _first(row, "side", "Side"),
        "policyId": raw_policy_id or "USDJPY_LIVE_LOOP",
        "intentId": raw_intent_id or feedback_id,
        "strategyId": raw_strategy_id or "RSI_Reversal",
        "entrySignalTime": _first(row, "entrySignalTime", "createdAt", "generatedAtServer", "timestamp", "time", "Time"),
        "orderSendTime": _first(row, "orderSendTime", "generatedAt", "generatedAtServer", "sendTime"),
        "fillTime": _first(row, "fillTime", "eventTimeServer", "CloseTime", "exitTime"),
        "expectedPrice": expected_price,
        "fillPrice": fill_price,
        "slippagePips": slippage_pips,
        "spreadAtEntry": _num(_first(row, "spreadAtEntry", "spreadPoints", "Spread", "spread")),
        "latencyMs": _num(_first(row, "latencyMs", "LatencyMs")),
        "retcode": retcode,
        "rejectReason": reject_reason,
        "exitReason": _first(row, "exitReason", "ExitReason"),
        "profitR": _num(_first(row, "profitR", "ProfitR")),
        "mfeR": _num(_first(row, "mfeR", "MfeR")),
        "maeR": _num(_first(row, "maeR", "MaeR")),
        "source": source,
        "fieldPresence": raw_field_presence,
        "sourceKeys": sorted(row.keys())[:20],
        "safety": dict(SAFETY_BOUNDARY),
    }


def _metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    slippage = [abs(float(row["slippagePips"])) for row in rows if row.get("slippagePips")]
    rejects = [row for row in rows if row.get("rejectReason")]
    fill_event_types = {"ORDER_FILL", "ORDER_CLOSE"}
    accepted_event_types = {"ORDER_ACCEPTED"}
    fills = [
        row
        for row in rows
        if str(row.get("eventType") or "").upper() in fill_event_types
        and row.get("fillPrice")
        and not row.get("rejectReason")
    ]
    accepted = [row for row in rows if str(row.get("eventType") or "").upper() in accepted_event_types]
    filled_feedback_ids = {
        str(row.get("feedbackId") or "")
        for row in fills
        if row.get("feedbackId")
    }
    accepted_without_fill = [
        row
        for row in accepted
        if str(row.get("feedbackId") or "") not in filled_feedback_ids
        and not row.get("fillPrice")
    ]
    latency = [float(row["latencyMs"]) for row in rows if row.get("latencyMs")]
    profits = [float(row.get("profitR") or 0.0) for row in rows]
    wins = [value for value in profits if value > 0]
    losses = [value for value in profits if value < 0]
    policy_mismatch = [
        row
        for row in rows
        if str(row.get("policyId") or "").upper() in {"EVIDENCE_MISSING", "BLOCKED"}
        and (row.get("fillPrice") or row.get("retcode"))
    ]
    return {
        "feedbackRows": len(rows),
        "acceptedCount": len(accepted),
        "fillCount": len(fills),
        "rejectCount": len(rejects),
        "acceptedWithoutFillCount": len(accepted_without_fill),
        "rejectRatePct": round((len(rejects) / len(rows) * 100.0), 2) if rows else 0.0,
        "dominantRejectReason": _dominant_reject_reason(rejects),
        "avgAbsSlippagePips": round(sum(slippage) / len(slippage), 4) if slippage else 0.0,
        "maxAbsSlippagePips": round(max(slippage), 4) if slippage else 0.0,
        "avgLatencyMs": round(sum(latency) / len(latency), 2) if latency else 0.0,
        "maxLatencyMs": round(max(latency), 2) if latency else 0.0,
        "netR": round(sum(profits), 4),
        "winRatePct": round(len(wins) / (len(wins) + len(losses)) * 100.0, 2) if wins or losses else 0.0,
        "policyMismatchCount": len(policy_mismatch),
        "feedbackQuality": _feedback_quality(len(rows), len(fills), len(rejects)),
    }


def _quality_gates(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    field_completeness = _field_completeness(rows)
    return _quality_gates_from_metrics(_metrics(rows), field_completeness)


def _quality_gates_from_metrics(metrics: Dict[str, Any], field_completeness: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "name": "slippage",
            "status": "PASS" if float(metrics["avgAbsSlippagePips"]) <= 0.8 else "WARN",
            "reasonZh": "平均滑点处于可接受范围" if float(metrics["avgAbsSlippagePips"]) <= 0.8 else "平均滑点偏高，需要降仓或限制触发窗口",
        },
        {
            "name": "reject_rate",
            "status": "PASS" if float(metrics["rejectRatePct"]) <= 15.0 else "WARN",
            "reasonZh": "拒单率正常" if float(metrics["rejectRatePct"]) <= 15.0 else "拒单率偏高，需要检查 EA 与券商执行",
        },
        {
            "name": "latency",
            "status": "PASS" if float(metrics["avgLatencyMs"]) <= 1500.0 else "WARN",
            "reasonZh": "平均执行延迟可接受" if float(metrics["avgLatencyMs"]) <= 1500.0 else "平均执行延迟偏高，需要检查 VPS/终端/券商链路",
        },
        {
            "name": "accepted_without_fill",
            "status": "PASS" if int(metrics["acceptedWithoutFillCount"]) <= 2 else "WARN",
            "reasonZh": "未成交挂起数量可接受" if int(metrics["acceptedWithoutFillCount"]) <= 2 else "已接受但未看到成交回执偏多，需要确认 EA/历史同步",
        },
        {
            "name": "policy_mismatch",
            "status": "PASS" if int(metrics["policyMismatchCount"]) == 0 else "WARN",
            "reasonZh": "未发现 policy 与执行明显偏离" if int(metrics["policyMismatchCount"]) == 0 else "发现 policy 阻断态仍有执行痕迹，需要复盘",
        },
        {
            "name": "field_contract",
            "status": "PASS" if field_completeness.get("status") == "PASS" else "WARN",
            "reasonZh": field_completeness.get("reasonZh") or "LiveExecutionFeedback 字段契约仍需继续观察。",
        },
    ]


def _promotion_gate(
    metrics: Dict[str, Any],
    quality_gates: List[Dict[str, Any]],
    field_completeness: Dict[str, Any],
) -> Dict[str, Any]:
    rows = int(metrics.get("feedbackRows") or 0)
    if rows <= 0:
        return {
            "schema": "quantgod.live_execution_promotion_gate.v1",
            "status": "WAITING_FEEDBACK",
            "promotionAllowed": False,
            "liveStageAllowed": False,
            "blockerCount": 0,
            "blockers": [],
            "warnings": [],
            "reasonZh": "尚无真实执行反馈；可以继续 shadow/tester，但不能把执行质量视为已通过。",
        }

    blockers: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    def add_blocker(code: str, reason: str, value: Any, limit: Any, case_type: str, mutation_hint: str) -> None:
        blockers.append(
            {
                "code": code,
                "reasonZh": reason,
                "value": value,
                "limit": limit,
                "caseType": case_type,
                "mutationHint": mutation_hint,
            }
        )

    if int(metrics.get("policyMismatchCount") or 0) > 0:
        add_blocker(
            "POLICY_MISMATCH",
            "发现 policy 阻断态仍有执行痕迹，必须先核对 EA 与后端策略同步。",
            metrics.get("policyMismatchCount"),
            0,
            "POLICY_MISMATCH",
            "verify_ea_policy_sync",
        )
    if int(metrics.get("acceptedWithoutFillCount") or 0) > 5:
        add_blocker(
            "ACCEPTED_WITHOUT_FILL_HIGH",
            "EA 接受请求后缺少成交回执过多，需要核对成交历史同步。",
            metrics.get("acceptedWithoutFillCount"),
            5,
            "POLICY_MISMATCH",
            "verify_execution_ack_fill_sync",
        )
    if float(metrics.get("rejectRatePct") or 0.0) > 30.0 and int(metrics.get("rejectCount") or 0) >= 2:
        add_blocker(
            "REJECT_RATE_HIGH",
            "拒单率过高，不能把当前执行链路视为可晋级。",
            metrics.get("rejectRatePct"),
            "30%",
            "EXECUTION_REJECT",
            "inspect_execution_quality",
        )
    if float(metrics.get("avgAbsSlippagePips") or 0.0) > 2.0:
        add_blocker(
            "SLIPPAGE_HIGH",
            "平均滑点超过 2 pips，需要限制触发窗口或降仓。",
            metrics.get("avgAbsSlippagePips"),
            2.0,
            "EXECUTION_SLIPPAGE",
            "tighten_execution_filter",
        )
    if float(metrics.get("avgLatencyMs") or 0.0) > 3000.0:
        add_blocker(
            "LATENCY_HIGH",
            "平均执行延迟超过 3000ms，需要检查 VPS、终端或券商链路。",
            metrics.get("avgLatencyMs"),
            3000,
            "EXECUTION_LATENCY",
            "reduce_execution_latency",
        )

    field_status = str(field_completeness.get("status") or "WAITING_FEEDBACK")
    if field_status == "BLOCKED":
        add_blocker(
            "LIVE_EXECUTION_FEEDBACK_FIELD_GAP",
            field_completeness.get("reasonZh") or "EA LiveExecutionFeedback 缺少稳定必填字段，不能用于晋级。",
            field_completeness.get("fieldCoveragePct"),
            "100%",
            "EXECUTION_FEEDBACK_SCHEMA_GAP",
            "stabilize_live_execution_feedback_fields",
        )
    elif field_status in {"WATCH", "WAITING_FEEDBACK"}:
        warnings.append(
            {
                "code": "LIVE_EXECUTION_FEEDBACK_FIELD_STABILITY_WATCH",
                "reasonZh": field_completeness.get("reasonZh") or "EA LiveExecutionFeedback 字段仍需继续收集样本。",
            }
        )

    for gate in quality_gates:
        if gate.get("status") == "WARN" and not any(item.get("code") == gate.get("name") for item in blockers):
            warnings.append(
                {
                    "code": str(gate.get("name") or "EXECUTION_WARN").upper(),
                    "reasonZh": gate.get("reasonZh") or "执行质量有轻微风险，需要继续观察。",
                }
            )

    if blockers:
        status = "BLOCKED"
        reason = "真实执行反馈未通过晋级门；需要进入 Case Memory 并阻止实盘阶段扩大。"
    elif warnings:
        status = "WATCH"
        reason = "真实执行反馈有轻微风险；允许继续观察，但不建议扩大 live 阶段。"
    else:
        status = "PASS"
        reason = "真实执行反馈未发现拒单、滑点、延迟或 policy 偏离硬风险。"

    return {
        "schema": "quantgod.live_execution_promotion_gate.v1",
        "status": status,
        "promotionAllowed": status == "PASS",
        "liveStageAllowed": status == "PASS",
        "blockerCount": len(blockers),
        "blockers": blockers,
        "warnings": warnings,
        "reasonZh": reason,
    }


def _case_memory_triggers(metrics: Dict[str, Any], promotion_gate: Dict[str, Any]) -> List[Dict[str, Any]]:
    triggers: List[Dict[str, Any]] = []
    for blocker in promotion_gate.get("blockers", []) if isinstance(promotion_gate.get("blockers"), list) else []:
        if not isinstance(blocker, dict):
            continue
        triggers.append(
            {
                "caseType": blocker.get("caseType") or "EXECUTION_QUALITY",
                "mutationHint": blocker.get("mutationHint") or "inspect_execution_quality",
                "priority": "HIGH",
                "recommendedLane": "MT5_SHADOW",
                "reasonZh": blocker.get("reasonZh") or "执行反馈触发 Case Memory。",
                "metrics": {
                    "rejectRatePct": metrics.get("rejectRatePct"),
                    "avgAbsSlippagePips": metrics.get("avgAbsSlippagePips"),
                    "avgLatencyMs": metrics.get("avgLatencyMs"),
                    "acceptedWithoutFillCount": metrics.get("acceptedWithoutFillCount"),
                    "policyMismatchCount": metrics.get("policyMismatchCount"),
                },
            }
        )
    return triggers


def _agent_action(promotion_gate: Dict[str, Any]) -> Dict[str, Any]:
    status = str(promotion_gate.get("status") or "WAITING_FEEDBACK")
    if status == "BLOCKED":
        action = "BLOCK_PROMOTION_AND_QUEUE_CASE_MEMORY"
    elif status == "WATCH":
        action = "KEEP_SHADOW_AND_MONITOR_EXECUTION"
    elif status == "PASS":
        action = "ALLOW_EXECUTION_FEEDBACK_TO_SUPPORT_PROMOTION"
    else:
        action = "WAIT_FOR_LIVE_EXECUTION_FEEDBACK"
    return {
        "action": action,
        "completedByAgent": True,
        "autoAppliedByAgent": status == "BLOCKED",
        "requiresAutonomousGovernance": True,
        "requiresManualReview": False,
    }


def _next_action_zh(promotion_gate: Dict[str, Any]) -> str:
    status = str(promotion_gate.get("status") or "WAITING_FEEDBACK")
    if status == "BLOCKED":
        return "执行反馈触发晋级阻断：写入 Case Memory，下一代 GA 需优先生成执行质量修复候选。"
    if status == "WATCH":
        return "执行反馈有轻微风险：继续 shadow/tester 收集，不扩大 live 阶段。"
    if status == "PASS":
        return "执行反馈通过：可作为后续自主晋级的支持证据。"
    return "等待 EA 输出标准化 LiveExecutionFeedback 后再评估执行质量。"


def _field_presence(row: Dict[str, Any], source: str, event_type: Any, retcode: Any) -> Dict[str, Any]:
    reject_reason = _reject_reason(row, retcode)
    return {
        "audited": source in AUDITED_FEEDBACK_SOURCES,
        "eventTypeNormalized": str(event_type or "").upper(),
        "policyId": _has_field(row, "policyId", "PolicyId"),
        "intentId": _has_field(row, "intentId", "IntentId"),
        "eventType": _has_field(row, "eventType", "EventType"),
        "symbol": _has_field(row, "symbol", "Symbol"),
        "strategyId": _has_field(row, "strategyId", "strategy", "Strategy"),
        "expectedPrice": _has_field(row, "expectedPrice", "entryPrice", "EntryPrice", "openPrice"),
        "fillPrice": _has_field(row, "fillPrice", "price", "Price", "exitPrice", "ClosePrice"),
        "slippagePips": _has_field(row, "slippagePips", "SlippagePips"),
        "latencyMs": _has_field(row, "latencyMs", "LatencyMs"),
        "rejectReason": bool(reject_reason),
        "exitReason": _has_field(row, "exitReason", "ExitReason"),
        "profitR": _has_field(row, "profitR", "ProfitR"),
        "mfeR": _has_field(row, "mfeR", "MfeR"),
        "maeR": _has_field(row, "maeR", "MaeR"),
    }


def _field_completeness(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    audited_rows = [row for row in rows if ((row.get("fieldPresence") or {}).get("audited"))]
    missing_counts: Dict[str, int] = {}
    row_issues: List[Dict[str, Any]] = []
    required_checks = 0
    present_checks = 0
    fill_rows = 0
    reject_rows = 0
    outcome_rows = 0

    def require(row: Dict[str, Any], fields: Iterable[str], group: str) -> None:
        nonlocal required_checks, present_checks
        presence = row.get("fieldPresence") if isinstance(row.get("fieldPresence"), dict) else {}
        missing = []
        for field in fields:
            required_checks += 1
            if presence.get(field):
                present_checks += 1
            else:
                missing.append(field)
                missing_counts[field] = missing_counts.get(field, 0) + 1
        if missing:
            row_issues.append(
                {
                    "feedbackId": row.get("feedbackId"),
                    "source": row.get("source"),
                    "eventType": row.get("eventType"),
                    "group": group,
                    "missingFields": missing,
                }
            )

    for row in audited_rows:
        presence = row.get("fieldPresence") if isinstance(row.get("fieldPresence"), dict) else {}
        event_type = str(presence.get("eventTypeNormalized") or row.get("eventType") or "").upper()
        require(row, REQUIRED_LIVE_EXECUTION_FIELDS["core"], "core")
        if event_type in SEND_EVENT_TYPES:
            require(row, REQUIRED_LIVE_EXECUTION_FIELDS["send"], "send")
        if event_type in FILL_EVENT_TYPES:
            fill_rows += 1
            require(row, REQUIRED_LIVE_EXECUTION_FIELDS["fill"], "fill")
        if event_type in CLOSE_EVENT_TYPES:
            fill_rows += 1
            outcome_rows += 1
            require(row, REQUIRED_LIVE_EXECUTION_FIELDS["fill"], "fill")
            require(row, REQUIRED_LIVE_EXECUTION_FIELDS["outcome"], "outcome")
        if event_type in REJECT_EVENT_TYPES:
            reject_rows += 1
            require(row, REQUIRED_LIVE_EXECUTION_FIELDS["reject"], "reject")
        if event_type in OUTCOME_EVENT_TYPES and event_type not in CLOSE_EVENT_TYPES:
            outcome_rows += 1
            require(row, REQUIRED_LIVE_EXECUTION_FIELDS["outcome"], "outcome")

    field_coverage = round((present_checks / required_checks * 100.0), 2) if required_checks else 0.0
    core_missing_count = sum(int(missing_counts.get(field, 0)) for field in REQUIRED_LIVE_EXECUTION_FIELDS["core"])
    conditional_missing_count = sum(
        int(value)
        for key, value in missing_counts.items()
        if key not in REQUIRED_LIVE_EXECUTION_FIELDS["core"]
    )
    warnings: List[Dict[str, Any]] = []
    if not audited_rows:
        status = "WAITING_FEEDBACK"
        reason = "尚未看到 EA 标准化 LiveExecutionFeedback 文件；无法证明 policyId、intentId、成交、滑点、延迟和 R 倍数字段长期稳定。"
    elif core_missing_count or conditional_missing_count:
        status = "BLOCKED"
        reason = "EA LiveExecutionFeedback 缺少必填字段；必须先稳定 policyId、intentId、fill/slippage/latency、profitR/mfeR/maeR 或 rejectReason。"
    else:
        status = "PASS"
        reason = "EA LiveExecutionFeedback 必填字段契约通过；policyId、intentId、成交、滑点、延迟、拒单和出场 R 字段按事件类型稳定输出。"
    if audited_rows and fill_rows == 0:
        status = "WATCH" if status == "PASS" else status
        warnings.append(
            {
                "code": "NO_FILL_SAMPLE_YET",
                "reasonZh": "尚未看到成交样本；fillPrice/slippagePips/latencyMs 需要继续用真实成交验证。",
            }
        )
        if status == "WATCH":
            reason = "字段身份契约已通过，但还缺真实成交样本来验证 fill/slippage/latency 长期稳定。"
    if audited_rows and outcome_rows == 0:
        status = "WATCH" if status == "PASS" else status
        warnings.append(
            {
                "code": "NO_OUTCOME_SAMPLE_YET",
                "reasonZh": "尚未看到平仓/结果样本；profitR/mfeR/maeR 需要继续用真实结果验证。",
            }
        )
        if status == "WATCH":
            reason = "字段身份契约已通过，但还缺平仓结果样本来验证 profitR/mfeR/maeR 长期稳定。"
    return {
        "schema": "quantgod.live_execution_field_completeness.v1",
        "status": status,
        "auditedSources": sorted(AUDITED_FEEDBACK_SOURCES),
        "auditedRows": len(audited_rows),
        "requiredChecks": required_checks,
        "presentChecks": present_checks,
        "fieldCoveragePct": field_coverage,
        "requiredFields": REQUIRED_LIVE_EXECUTION_FIELDS,
        "missingCounts": missing_counts,
        "coreMissingFieldCount": core_missing_count,
        "conditionalMissingFieldCount": conditional_missing_count,
        "fillSampleCount": fill_rows,
        "rejectSampleCount": reject_rows,
        "outcomeSampleCount": outcome_rows,
        "warnings": warnings,
        "rowIssues": row_issues[:50],
        "reasonZh": reason,
    }


def _dedupe_feedback(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for row in rows:
        key = row.get("feedbackId")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _first(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in {None, ""}:
            return row[key]
    return None


def _has_field(row: Dict[str, Any], *keys: str) -> bool:
    return _first(row, *keys) is not None


def _num(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _feedback_quality(rows: int, fills: int, rejects: int) -> str:
    if rows >= 30 and fills:
        return "HIGH"
    if rows >= 10 or fills or rejects:
        return "MEDIUM"
    if rows:
        return "LOW"
    return "MISSING"


def _reject_reason(row: Dict[str, Any], retcode: Any) -> str:
    event_type = str(_first(row, "eventType", "EventType") or "").upper()
    explicit = _first(row, "rejectReason", "mainBlocker", "reason", "Reason")
    if event_type in {"ORDER_REJECT", "ORDER_REJECTED"}:
        return str(explicit) if explicit else "ORDER_REJECTED"
    code = str(retcode or "").strip()
    if not code or code in {"0", "10009", "10008"}:
        return ""
    return str(explicit) if explicit else f"MT5_RETCODE_{code}"


def _dominant_reject_reason(rejects: List[Dict[str, Any]]) -> str:
    counts: Dict[str, int] = {}
    for row in rejects:
        reason = str(row.get("rejectReason") or "UNKNOWN_REJECT")
        counts[reason] = counts.get(reason, 0) + 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _feedback_id(index: int, row: Dict[str, Any], source: str) -> str:
    explicit = _first(row, "feedbackId", "FeedbackId")
    if explicit:
        return str(explicit)
    raw = "|".join(
        str(_first(row, key) or "")
        for key in (
            "ticket",
            "Ticket",
            "order",
            "deal",
            "intentId",
            "policyId",
            "generatedAt",
            "time",
            "Time",
            "CloseTime",
        )
    )
    seed = f"{source}|{raw}|{index if not raw.strip('|') else ''}"
    return "USDJPY-FEEDBACK-" + hashlib.sha256(seed.encode("utf-8", errors="ignore")).hexdigest()[:16]
