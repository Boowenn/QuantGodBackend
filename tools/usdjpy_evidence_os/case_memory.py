from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List

from .io_utils import append_jsonl_unique, load_json, utc_now_iso, write_json
from .schema import AGENT_VERSION, FOCUS_SYMBOL, SAFETY_BOUNDARY, case_memory_path, case_summary_path


def build_case_memory(runtime_dir: Path, write: bool = True) -> Dict[str, Any]:
    cases = (
        _cases_from_replay(runtime_dir)
        + _cases_from_execution(runtime_dir)
        + _cases_from_strategy_contract_shadow(runtime_dir)
        + _cases_from_ga(runtime_dir)
    )
    ga_seed_hints = _ga_seed_hints(cases)
    summary = {
        "ok": True,
        "schema": "quantgod.case_memory_summary.v1",
        "agentVersion": AGENT_VERSION,
        "createdAt": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "caseCount": len(cases),
        "caseTypeCounts": _type_counts(cases),
        "mutationHints": _mutation_hints(cases),
        "gaSeedHints": ga_seed_hints,
        "caseMemoryToGA": {
            "schema": "quantgod.case_memory_to_ga.v1",
            "queuedHintCount": len(ga_seed_hints),
            "source": "CASE_MEMORY",
            "nextActionZh": "GA 会优先把高优先级 Case Memory 转成 Strategy JSON shadow 候选。",
        },
        "cases": cases[-50:],
        "queuedForGA": sum(1 for item in cases if item.get("status") == "QUEUED_FOR_GA"),
        "reasonZh": "Case Memory 把错失机会、早出场、执行偏差和过拟合风险转成下一轮 Strategy JSON/GA 种子线索。",
        "safety": dict(SAFETY_BOUNDARY),
    }
    if write:
        if cases:
            append_jsonl_unique(case_memory_path(runtime_dir), cases, "caseId")
        write_json(case_summary_path(runtime_dir), summary)
    return summary


def _cases_from_replay(runtime_dir: Path) -> List[Dict[str, Any]]:
    replay = load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYBarReplayReport.json")
    cases: List[Dict[str, Any]] = []
    entry_variants = ((replay.get("entryComparison") or {}).get("variants") or []) if isinstance(replay.get("entryComparison"), dict) else []
    for variant in entry_variants:
        metrics = variant.get("metrics") if isinstance(variant, dict) and isinstance(variant.get("metrics"), dict) else variant
        if not isinstance(metrics, dict):
            continue
        if float(metrics.get("entryCountDelta") or 0) > 0:
            cases.append(_case("MISSED_BIG_MOVE", "RSI crossback 或战术确认过严，产生错失机会", metrics, "relax_rsi_crossback"))
        if float(metrics.get("maxAdverseR") or metrics.get("maxAdverseRDelta") or 0) < -1.0:
            cases.append(_case("BAD_ENTRY", "入场候选最大不利波动偏大，需要收紧触发条件", metrics, "tighten_entry_filter"))
    exit_variants = ((replay.get("exitComparison") or {}).get("variants") or []) if isinstance(replay.get("exitComparison"), dict) else []
    for variant in exit_variants:
        metrics = variant.get("metrics") if isinstance(variant, dict) and isinstance(variant.get("metrics"), dict) else variant
        if isinstance(metrics, dict) and float(metrics.get("profitCaptureRatio") or 0) > 0.35:
            cases.append(_case("EARLY_EXIT", "出场可能过早，盈利捕获率有改善空间", metrics, "let_profit_run"))
    news = load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYNewsGateReplayReport.json")
    for variant in news.get("variants", []) if isinstance(news.get("variants"), list) else []:
        if isinstance(variant, dict) and float(variant.get("softNewsOpportunityR") or variant.get("netRDelta") or 0) > 0:
            cases.append(_case("NEWS_DAMAGE", "普通新闻硬阻断可能造成错失机会，继续使用软新闻门禁观察", variant, "keep_soft_news_gate"))
    return cases


def _cases_from_execution(runtime_dir: Path) -> List[Dict[str, Any]]:
    feedback = load_json(runtime_dir / "evidence_os" / "QuantGod_LiveExecutionQualityReport.json")
    metrics = feedback.get("metrics") if isinstance(feedback.get("metrics"), dict) else {}
    cases: List[Dict[str, Any]] = []
    triggers = feedback.get("caseMemoryTriggers") if isinstance(feedback.get("caseMemoryTriggers"), list) else []
    if triggers:
        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue
            evidence = trigger.get("metrics") if isinstance(trigger.get("metrics"), dict) else metrics
            cases.append(
                _case(
                    str(trigger.get("caseType") or "EXECUTION_QUALITY"),
                    str(trigger.get("reasonZh") or "执行反馈触发 Case Memory"),
                    evidence,
                    str(trigger.get("mutationHint") or "inspect_execution_quality"),
                    priority=str(trigger.get("priority") or "HIGH"),
                    recommended_lane=str(trigger.get("recommendedLane") or "MT5_SHADOW"),
                )
            )
    if int(metrics.get("rejectCount") or 0) > 0:
        reason = metrics.get("dominantRejectReason") or "UNKNOWN_REJECT"
        cases.append(_case("EXECUTION_REJECT", f"EA 或券商拒单偏多，主因：{reason}", metrics, "inspect_execution_quality", priority="HIGH"))
    if float(metrics.get("avgAbsSlippagePips") or 0) > 0.8:
        cases.append(_case("EXECUTION_SLIPPAGE", "平均滑点偏高，需要限制触发窗口或降仓", metrics, "tighten_execution_filter", priority="HIGH"))
    if float(metrics.get("avgLatencyMs") or 0) > 1500.0:
        cases.append(_case("EXECUTION_LATENCY", "平均执行延迟偏高，需要检查 VPS、终端或券商链路", metrics, "reduce_execution_latency", priority="HIGH"))
    if int(metrics.get("acceptedWithoutFillCount") or 0) > 2:
        cases.append(_case("POLICY_MISMATCH", "EA 已接受指令但未看到成交回执偏多，需要核对历史同步和回执链路", metrics, "verify_execution_ack_fill_sync", priority="HIGH"))
    if int(metrics.get("policyMismatchCount") or 0) > 0:
        cases.append(_case("POLICY_MISMATCH", "发现 policy 阻断态仍有执行痕迹，需要检查 EA 同步", metrics, "verify_ea_policy_sync", priority="HIGH"))
    for row in feedback.get("recentFeedback", []) if isinstance(feedback.get("recentFeedback"), list) else []:
        if not isinstance(row, dict):
            continue
        if str(row.get("strategyId") or "RSI_Reversal") != "RSI_Reversal":
            cases.append(_case("POLICY_MISMATCH", "执行反馈出现非 RSI_Reversal 策略，需要确认实盘路线仍被锁定", row, "verify_live_lane_strategy_lock", priority="HIGH"))
            break
    return cases


def _cases_from_strategy_contract_shadow(runtime_dir: Path) -> List[Dict[str, Any]]:
    from .io_utils import candidate_mt5_files_dirs, read_jsonl_tail

    rows: List[Dict[str, Any]] = []
    for directory in candidate_mt5_files_dirs(runtime_dir):
        rows.extend(read_jsonl_tail(directory / "QuantGod_StrategyJsonEAShadowEvaluationLedger.jsonl", 200))
    status = load_json(runtime_dir / "QuantGod_StrategyJsonEAShadowEvaluationStatus.json")
    if status:
        rows.append(status)
    cases: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows[-100:]:
        if not isinstance(row, dict):
            continue
        status_value = str(row.get("status") or "")
        blocker = str(row.get("blocker") or "")
        selected_seed_id = str(row.get("selectedSeedId") or "")
        dedupe_key = "|".join(
            [
                selected_seed_id,
                str(row.get("fingerprint") or ""),
                str(row.get("strategyFamily") or ""),
                str(row.get("direction") or ""),
                status_value,
                blocker,
            ]
        )
        if dedupe_key and dedupe_key in seen:
            continue
        if dedupe_key:
            seen.add(dedupe_key)
        evidence = {
            "selectedSeedId": selected_seed_id,
            "fingerprint": row.get("fingerprint"),
            "strategyId": row.get("strategyId"),
            "strategyFamily": row.get("strategyFamily"),
            "direction": row.get("direction"),
            "lane": row.get("lane"),
            "status": status_value,
            "blocker": blocker,
            "wouldEnter": bool(row.get("wouldEnter")),
            "hardGuardsPass": bool(row.get("hardGuardsPass")),
            "rsiClosed1": row.get("rsiClosed1"),
            "rsiClosed2": row.get("rsiClosed2"),
            "spreadPips": row.get("spreadPips"),
            "source": "STRATEGY_JSON_EA_SHADOW_EVALUATION",
        }
        if status_value == "SHADOW_WOULD_ENTER":
            cases.append(
                _case(
                    "STRATEGY_CONTRACT_SHADOW_SIGNAL",
                    "EA 已按 Strategy JSON contract 看到 shadow 入场机会；下一代 GA 应优先复核该 seed 的回测、parity 与 tester 结果。",
                    evidence,
                    "promote_contract_candidate_to_tester",
                    priority="MEDIUM",
                    recommended_lane="MT5_SHADOW",
                )
            )
        elif blocker in {"EA_CONTRACT_FAMILY_NOT_IMPLEMENTED", "EA_CONTRACT_DIRECTION_NOT_LIVE_ROUTE"}:
            cases.append(
                _case(
                    "STRATEGY_CONTRACT_EA_ADAPTER_GAP",
                    row.get("reasonZh") or "EA 已读取 Strategy JSON contract，但当前策略族/方向尚未具备 EA shadow evaluation 适配。",
                    evidence,
                    "add_ea_contract_adapter_family",
                    priority="MEDIUM",
                    recommended_lane="MT5_SHADOW",
                )
            )
        elif blocker in {"CONTRACT_SAFETY_REJECTED", "NON_USDJPY_CONTRACT", "CONTRACT_MODE_REJECTED"}:
            cases.append(
                _case(
                    "STRATEGY_CONTRACT_SAFETY_REJECTED",
                    row.get("reasonZh") or "EA 拒绝了不安全或不在范围内的 Strategy JSON contract。",
                    evidence,
                    "repair_strategy_json_contract_safety",
                    priority="HIGH",
                    recommended_lane="MT5_SHADOW",
                )
            )
    return cases


def _cases_from_ga(runtime_dir: Path) -> List[Dict[str, Any]]:
    blockers = load_json(runtime_dir / "ga" / "QuantGod_GABlockerSummary.json")
    rows = blockers.get("summary") if isinstance(blockers.get("summary"), list) else []
    cases: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        blocker = str(row.get("blockerCode") or "")
        if blocker == "OVERFIT_RISK":
            cases.append(_case("GA_OVERFIT", "GA 候选存在过拟合风险，需要降低 mutation 幅度或扩大样本", row, "reduce_mutation_rate"))
        elif blocker in {"MAX_ADVERSE_TOO_HIGH", "WALK_FORWARD_FAILED"}:
            cases.append(_case("BAD_ENTRY", "候选在 forward 或最大不利波动上不稳定", row, "reject_unstable_seed"))
    return cases


def _case(
    case_type: str,
    root_cause: str,
    evidence: Dict[str, Any],
    mutation_hint: str,
    priority: str | None = None,
    recommended_lane: str = "MT5_SHADOW",
) -> Dict[str, Any]:
    digest = hashlib.sha256(
        f"{case_type}|{root_cause}|{mutation_hint}|{sorted((evidence or {}).items())[:8]}".encode("utf-8", errors="ignore")
    ).hexdigest()[:16]
    priority_value = priority or _default_priority(case_type)
    return {
        "schema": "quantgod.case_memory.v1",
        "caseId": f"USDJPY-{case_type}-{digest}",
        "createdAt": utc_now_iso(),
        "type": case_type,
        "symbol": FOCUS_SYMBOL,
        "strategy": "RSI_Reversal",
        "priority": priority_value,
        "recommendedLane": recommended_lane,
        "rootCause": root_cause,
        "evidence": evidence,
        "proposedAction": {
            "generateStrategyJsonCandidate": True,
            "mutationHint": mutation_hint,
            "recommendedLane": recommended_lane,
            "priority": priority_value,
        },
        "status": "QUEUED_FOR_GA",
        "safety": dict(SAFETY_BOUNDARY),
    }


def _type_counts(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in cases:
        key = str(item.get("type") or "UNKNOWN")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _mutation_hints(cases: List[Dict[str, Any]]) -> List[str]:
    hints: List[str] = []
    for item in cases:
        hint = ((item.get("proposedAction") or {}).get("mutationHint") or "")
        if hint and hint not in hints:
            hints.append(str(hint))
    return hints[:12]


def _ga_seed_hints(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    queued = [item for item in cases if item.get("status") == "QUEUED_FOR_GA"]
    queued.sort(key=lambda item: (_priority_rank(str(item.get("priority") or "")), str(item.get("caseId") or "")))
    hints: List[Dict[str, Any]] = []
    for item in queued[:24]:
        action = item.get("proposedAction") if isinstance(item.get("proposedAction"), dict) else {}
        hints.append(
            {
                "caseId": item.get("caseId"),
                "caseType": item.get("type"),
                "priority": item.get("priority") or "MEDIUM",
                "recommendedLane": item.get("recommendedLane") or action.get("recommendedLane") or "MT5_SHADOW",
                "mutationHint": action.get("mutationHint") or "case_memory_observe",
                "reasonZh": item.get("rootCause") or "Case Memory 进入下一代 GA 候选。",
                "status": "QUEUED_FOR_GA",
            }
        )
    return hints


def _default_priority(case_type: str) -> str:
    if case_type in {
        "POLICY_MISMATCH",
        "EXECUTION_REJECT",
        "EXECUTION_SLIPPAGE",
        "EXECUTION_LATENCY",
        "EXECUTION_FEEDBACK_SCHEMA_GAP",
        "STRATEGY_CONTRACT_SAFETY_REJECTED",
    }:
        return "HIGH"
    if case_type in {
        "MISSED_BIG_MOVE",
        "EARLY_EXIT",
        "BAD_ENTRY",
        "GA_OVERFIT",
        "STRATEGY_CONTRACT_SHADOW_SIGNAL",
        "STRATEGY_CONTRACT_EA_ADAPTER_GAP",
    }:
        return "MEDIUM"
    return "LOW"


def _priority_rank(priority: str) -> int:
    return {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(priority.upper(), 3)
