from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from tools.news_gate.classifier import classify_news_gate
    from tools.news_gate.policy import apply_news_gate_to_live_policy
except ModuleNotFoundError:  # CLI execution from tools/
    from news_gate.classifier import classify_news_gate
    from news_gate.policy import apply_news_gate_to_live_policy

from .data_loader import (
    adaptive_policy,
    dynamic_sltp,
    entry_trigger_plan,
    fastlane_quality,
    focus_runtime_snapshot,
    runtime_fresh_limit_seconds,
)
from .schema import (
    ENTRY_BLOCKED,
    ENTRY_OPPORTUNITY,
    ENTRY_STANDARD,
    FOCUS_SYMBOL,
    PolicyItem,
    READ_ONLY_SAFETY,
    STATUS_PAUSED,
    STATUS_RUNNABLE,
    STATUS_WATCH_ONLY,
    STRATEGY_CATALOG_VERSION,
    assert_no_secret_or_execution_flags,
    utc_now_iso,
)
from .strategy_signals import build_candidate_signals
from .strategy_scoreboard import build_strategy_scoreboard

FASTLANE_PASS_STATES = {"OK", "PASS", "PASSED", "GOOD", "HEALTHY", "FAST", "EA_DASHBOARD_OK"}
LIVE_ELIGIBLE_STRATEGY = "RSI_Reversal"
LIVE_ELIGIBLE_DIRECTION = "LONG"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except Exception:
        return default


def _round_lot(value: float, step: float = 0.01, min_lot: float = 0.01, max_lot: float = 2.0) -> float:
    if value <= 0:
        return 0.0
    value = max(min_lot, min(value, max_lot))
    steps = round(value / step)
    return round(max(min_lot, min(max_lot, steps * step)), 2)


def _runtime_ok(snapshot: Dict[str, Any]) -> tuple[bool, List[str]]:
    reasons = []
    if not snapshot:
        return False, ["缺少 USDJPY 运行快照"]
    if bool(snapshot.get("fallback")):
        reasons.append("运行快照处于回退模式")
    age = snapshot.get("runtimeAgeSeconds")
    fresh = snapshot.get("runtimeFresh")
    fresh_limit = runtime_fresh_limit_seconds()
    try:
        if age is not None and float(age) > fresh_limit:
            reasons.append(f"运行快照过旧：{age}s")
    except Exception:
        pass
    if fresh is False:
        reasons.append("运行快照标记为不新鲜")
    return not reasons, reasons or ["运行快照通过"]


def _fastlane_ok(quality: Dict[str, Any]) -> tuple[bool, List[str]]:
    if not quality.get("found"):
        return False, ["缺少 USDJPY 快通道质量证据"]
    state = str(quality.get("quality") or "MISSING").upper()
    if state not in FASTLANE_PASS_STATES:
        return False, [f"快通道质量未通过：{state}"]
    if quality.get("focusSymbolFound") is False:
        return False, ["快通道质量文件未包含 USDJPY"]
    if state == "EA_DASHBOARD_OK":
        return True, ["快通道质量降级可用：使用 HFM EA Dashboard 新鲜快照"]
    return True, ["快通道质量通过"]


def _is_live_route(item: PolicyItem) -> bool:
    return item.strategy == LIVE_ELIGIBLE_STRATEGY and str(item.direction).upper() == LIVE_ELIGIBLE_DIRECTION


def _is_live_eligible(item: PolicyItem) -> bool:
    return _is_live_route(item) and item.entryMode in {ENTRY_STANDARD, ENTRY_OPPORTUNITY} and bool(item.allowed)


def _trigger_state(plan: Dict[str, Any], direction: str) -> tuple[str, List[str], float]:
    items = plan.get("plans") or plan.get("triggers") or plan.get("items") or plan.get("decisions") or []
    if isinstance(items, dict):
        items = list(items.values())
    best = None
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        if str(item.get("symbol") or "").upper().startswith("USDJPY") and str(item.get("direction") or "").upper() == direction:
            best = item
            break
    if not best:
        return "MISSING", ["缺少 USDJPY 入场触发计划"], 0.0
    status = str(best.get("status") or best.get("state") or best.get("entryMode") or "UNKNOWN").upper()
    score = best.get("triggerScore") or best.get("score") or 0.0
    try:
        score = float(score)
        if score <= 1.0:
            score *= 100
    except Exception:
        score = 0.0
    missing = best.get("missingConfirmations") or best.get("missing") or []
    if isinstance(missing, str):
        missing = [missing]
    if status in {"READY_FOR_CONFIRMATION", "WAIT_TRIGGER_CONFIRMATION", "STANDARD_ENTRY", "PASS", "READY", "OPPORTUNITY_ENTRY"}:
        if len(missing) <= 1:
            return "TACTICAL_OK", ["入场触发允许：核心项通过，战术确认最多缺一项"], score
    reasons = best.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    blocked_detail = missing or reasons
    return "BLOCKED", ["入场触发阻断" if not blocked_detail else "入场触发阻断：" + "、".join([str(item) for item in blocked_detail[:3]])], score


def _sltp_available(plan: Dict[str, Any], strategy: str, direction: str) -> tuple[bool, List[str], Dict[str, Any]]:
    plans = plan.get("plans") or plan.get("items") or plan.get("calibrations") or []
    if isinstance(plans, dict):
        plans = list(plans.values())
    for item in plans if isinstance(plans, list) else []:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("symbol") or "").upper()
        item_strategy = str(item.get("strategy") or "").strip()
        item_direction = str(item.get("direction") or "").upper()
        status = str(item.get("status") or "").upper()
        if sym.startswith("USDJPY") and item_strategy == strategy and item_direction == direction and status not in {"PAUSED", "BLOCKED", "INSUFFICIENT_DATA"}:
            return True, ["动态止盈止损可用"], item
    direction_plans = plan.get("dynamicSltpPlans") or []
    if isinstance(direction_plans, dict):
        direction_plans = list(direction_plans.values())
    for item in direction_plans if isinstance(direction_plans, list) else []:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("symbol") or "").upper()
        item_direction = str(item.get("direction") or "").upper()
        risk_mode = str(item.get("riskMode") or "").upper()
        if sym.startswith("USDJPY") and item_direction == direction and risk_mode != "暂停":
            return True, ["动态止盈止损方向级计划可用"], item
    if plan:
        return False, ["动态止盈止损未匹配当前策略方向"], {}
    return False, ["缺少动态止盈止损计划"], {}


def _soften_live_route_trigger(status: str, strategy: str, direction: str, trigger_status: str, trigger_reasons: List[str]) -> tuple[str, List[str]]:
    if status != STATUS_RUNNABLE:
        return trigger_status, trigger_reasons
    if strategy != LIVE_ELIGIBLE_STRATEGY or str(direction).upper() != LIVE_ELIGIBLE_DIRECTION:
        return trigger_status, trigger_reasons
    if trigger_status != "BLOCKED":
        return trigger_status, trigger_reasons
    text = "；".join(str(item) for item in trigger_reasons)
    if "影子样本" not in text:
        return trigger_status, trigger_reasons
    return "TACTICAL_OK", [
        "RSI 实盘买入 forward 为正；影子方向池偏弱不阻断现有 EA 路线，仍由 EA 的 RSI、新闻、session、spread 风控二次确认。"
    ]


def _recommended_lot(score: float, entry_mode: str, *, max_lot: float, min_lot: float, step: float) -> float:
    risk_pct = _env_float("QG_AUTO_RISK_PER_TRADE_PCT", 0.5)
    opportunity_mult = _env_float("QG_AUTO_OPPORTUNITY_LOT_MULTIPLIER", 0.35)
    standard_mult = _env_float("QG_AUTO_STANDARD_LOT_MULTIPLIER", 1.0)
    equity = _env_float("QG_AUTO_ACCOUNT_EQUITY", 1000.0)
    base = max_lot * max(0.10, min(1.0, score / 100.0)) * max(0.05, min(2.0, risk_pct / 0.5))
    if entry_mode == ENTRY_OPPORTUNITY:
        base *= opportunity_mult
    elif entry_mode == ENTRY_STANDARD:
        base *= standard_mult
    else:
        base = 0.0
    return _round_lot(base, step=step, min_lot=min_lot, max_lot=max_lot)


def build_usdjpy_policy(runtime_dir: Path, *, write: bool = False, min_samples: int = 5) -> Dict[str, Any]:
    max_lot = _env_float("QG_AUTO_MAX_LOT", 2.0)
    min_lot = _env_float("QG_AUTO_MIN_LOT", 0.01)
    step = _env_float("QG_AUTO_LOT_STEP", 0.01)
    scoreboard = build_strategy_scoreboard(runtime_dir, min_samples=min_samples)
    candidate_signals = build_candidate_signals(runtime_dir, limit=20)
    snapshot = focus_runtime_snapshot(runtime_dir)
    quality = fastlane_quality(runtime_dir)
    trigger = entry_trigger_plan(runtime_dir)
    sltp = dynamic_sltp(runtime_dir)
    adaptive = adaptive_policy(runtime_dir)
    news_gate = classify_news_gate(snapshot or {})
    runtime_ok, runtime_reasons = _runtime_ok(snapshot or {})
    fast_ok, fast_reasons = _fastlane_ok(quality)
    core_ok = runtime_ok and fast_ok
    policies: List[PolicyItem] = []
    for route in scoreboard.get("routes", []):
        status = route.get("status")
        strategy = route.get("strategy") or "UNKNOWN_STRATEGY"
        direction = route.get("direction") or "UNKNOWN"
        regime = route.get("regime") or "UNKNOWN"
        score = float(route.get("score") or 0.0)
        reasons = list(route.get("reasons") or [])
        reasons.extend(runtime_reasons)
        reasons.extend(fast_reasons)
        trigger_status, trigger_reasons, trigger_score = _trigger_state(trigger, direction)
        trigger_status, trigger_reasons = _soften_live_route_trigger(status, strategy, direction, trigger_status, trigger_reasons)
        sltp_ok, sltp_reasons, sltp_item = _sltp_available(sltp, strategy, direction)
        reasons.extend(trigger_reasons)
        reasons.extend(sltp_reasons)
        entry_mode = ENTRY_BLOCKED
        allowed = False
        strictness = "BLOCKED_CORE_EVIDENCE"
        if status == STATUS_PAUSED:
            reasons.append("策略方向近期表现为负，暂停")
        elif not core_ok:
            reasons.append("核心证据未通过，禁止机会入场")
        elif not sltp_ok:
            reasons.append("缺少动态止盈止损，禁止自动政策放行")
        elif status == STATUS_RUNNABLE and trigger_status == "TACTICAL_OK" and score >= 70:
            entry_mode = ENTRY_STANDARD
            allowed = True
            strictness = "STANDARD_ALL_CORE_AND_TACTICAL_PASS"
        elif status in {STATUS_RUNNABLE, STATUS_WATCH_ONLY} and trigger_status in {"TACTICAL_OK", "MISSING"} and score >= 45:
            entry_mode = ENTRY_OPPORTUNITY
            allowed = True
            strictness = "RELAXED_ONE_MISSING_CONFIRMATION"
            reasons.append("核心安全通过，允许小仓机会观察")
        else:
            reasons.append("分数或触发状态不足，保持阻断")
        lot = _recommended_lot(score, entry_mode, max_lot=max_lot, min_lot=min_lot, step=step)
        if strategy == LIVE_ELIGIBLE_STRATEGY and str(direction).upper() == LIVE_ELIGIBLE_DIRECTION:
            entry_mode, allowed, lot, strictness, reasons = apply_news_gate_to_live_policy(
                entry_mode=entry_mode,
                allowed=allowed,
                recommended_lot=lot,
                strictness=strictness,
                reasons=reasons,
                news_gate=news_gate,
                min_lot=min_lot,
                max_lot=max_lot,
                step=step,
            )
        else:
            reasons.append("新闻风险只记录到 shadow / replay，不阻断 MT5 模拟策略。")
        policies.append(PolicyItem(
            symbol=FOCUS_SYMBOL,
            strategy=strategy,
            direction=direction,
            regime=regime,
            entryMode=entry_mode,
            allowed=allowed,
            recommendedLot=lot,
            maxLot=max_lot,
            score=round(score, 2),
            entryStrictness=strictness,
            exitMode="LET_PROFIT_RUN" if allowed else "NO_POSITION",
            breakevenDelayR=float(sltp_item.get("breakevenDelayR", 0.9)) if sltp_item else 0.9,
            trailStartR=float(sltp_item.get("trailStartR", 1.4)) if sltp_item else 1.4,
            timeStopBars=int(float(sltp_item.get("timeStopBars", 6))) if sltp_item else 6,
            reasons=list(dict.fromkeys([str(r) for r in reasons if r])),
            newsGate=dict(news_gate),
        ))

    policies.sort(key=lambda item: (item.entryMode == ENTRY_BLOCKED, -item.score, -item.recommendedLot, item.strategy))
    top_shadow_policy = policies[0].to_dict() if policies else None
    live_route_candidates = [item for item in policies if _is_live_route(item)]
    live_eligible_candidates = [item for item in policies if _is_live_eligible(item)]
    top_live_policy = live_eligible_candidates[0].to_dict() if live_eligible_candidates else None
    live_recovery_candidate = live_route_candidates[0].to_dict() if live_route_candidates else None
    top_policy = top_live_policy or live_recovery_candidate or top_shadow_policy
    payload = {
        "schema": "quantgod.usdjpy_auto_execution_policy.v1",
        "generatedAt": utc_now_iso(),
        "strategyCatalogVersion": STRATEGY_CATALOG_VERSION,
        "focusOnly": True,
        "symbol": FOCUS_SYMBOL,
        "allowedSymbols": [FOCUS_SYMBOL],
        "ignoredNonFocusSymbols": True,
        "marketRegime": (snapshot or {}).get("regime") or (snapshot or {}).get("marketRegime") or "UNKNOWN",
        "policyConstraints": {
            "focusOnly": True,
            "newStrategiesShadowOnlyUntilEvidencePass": True,
            "requiresBacktestBeforeLive": True,
            "requiresGovernanceBeforeLive": True,
            "requiresAutonomousGovernance": True,
            "operatorApprovalRequired": False,
            "unattendedLiveExpansionAllowed": True,
            "liveScopeExpansionMode": "autonomous_governance_stage_gated",
            "autoApplyAllowed": "stage_gated",
            "patchWritable": True,
            "liveMutationAllowed": False,
            "rsiLiveRoutePreserved": True,
            "newsGateDefaultMode": news_gate.get("mode"),
            "ordinaryNewsHardBlocksLive": False,
            "highImpactNewsHardBlocksLive": True,
        },
        "newsGate": news_gate,
        "maxLot": max_lot,
        "standardEntryCount": sum(1 for item in policies if item.entryMode == ENTRY_STANDARD),
        "opportunityEntryCount": sum(1 for item in policies if item.entryMode == ENTRY_OPPORTUNITY),
        "blockedCount": sum(1 for item in policies if item.entryMode == ENTRY_BLOCKED),
        "topPolicy": top_policy,
        "topShadowPolicy": top_shadow_policy,
        "topLiveEligiblePolicy": top_live_policy,
        "liveRecoveryCandidate": live_recovery_candidate,
        "strategies": [item.to_dict() for item in policies],
        "evidence": {
            "runtimeOk": runtime_ok,
            "fastlaneOk": fast_ok,
            "triggerPlanFound": bool(trigger),
            "dynamicSltpFound": bool(sltp),
            "adaptivePolicyFound": bool(adaptive),
            "scoreboardRoutes": len(scoreboard.get("routes", [])),
            "candidateSignalCount": candidate_signals.get("count", 0),
            "topLiveEligiblePolicyFound": bool(top_live_policy),
            "topShadowPolicyStrategy": (top_shadow_policy or {}).get("strategy"),
            "newsGateMode": news_gate.get("mode"),
            "newsRiskLevel": news_gate.get("riskLevel"),
            "newsHardBlock": bool(news_gate.get("hardBlock")),
        },
        "candidateSignals": candidate_signals.get("signals", []),
        "scoreboard": scoreboard,
        "safety": dict(READ_ONLY_SAFETY),
    }
    assert_no_secret_or_execution_flags(payload)
    if write:
        adaptive_dir = runtime_dir / "adaptive"
        adaptive_dir.mkdir(parents=True, exist_ok=True)
        policy_path = adaptive_dir / "QuantGod_USDJPYAutoExecutionPolicy.json"
        policy_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        ledger_path = adaptive_dir / "QuantGod_USDJPYAutoExecutionPolicyLedger.csv"
        is_new = not ledger_path.exists()
        with ledger_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["generatedAt", "symbol", "standard", "opportunity", "blocked", "topStrategy", "topMode", "topLot"])
            if is_new:
                writer.writeheader()
            top = payload.get("topPolicy") or {}
            writer.writerow({
                "generatedAt": payload["generatedAt"],
                "symbol": FOCUS_SYMBOL,
                "standard": payload["standardEntryCount"],
                "opportunity": payload["opportunityEntryCount"],
                "blocked": payload["blockedCount"],
                "topStrategy": top.get("strategy", ""),
                "topMode": top.get("entryMode", ""),
                "topLot": top.get("recommendedLot", 0),
            })
    return payload
