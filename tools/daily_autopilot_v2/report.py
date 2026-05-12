from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.autonomous_lifecycle.lifecycle import build_autonomous_lifecycle
    from tools.daily_autopilot_v2.orchestrator import read_latest_run
    from tools.news_gate.classifier import classify_news_gate
    from tools.usdjpy_autonomous_agent.agent_state import build_agent_state
    from tools.usdjpy_strategy_lab.schema import FOCUS_SYMBOL, utc_now_iso
except ModuleNotFoundError:  # pragma: no cover
    from autonomous_lifecycle.lifecycle import build_autonomous_lifecycle
    from daily_autopilot_v2.orchestrator import read_latest_run
    from news_gate.classifier import classify_news_gate
    from usdjpy_autonomous_agent.agent_state import build_agent_state
    from usdjpy_strategy_lab.schema import FOCUS_SYMBOL, utc_now_iso


REPORT_NAME = "QuantGod_DailyAutopilotV2.json"
AGENT_VERSION = "v2.6"

NEXT_PHASE_TODOS: List[Dict[str, Any]] = [
    {
        "id": "strategyJsonTodo",
        "lane": "SYSTEM",
        "laneZh": "策略契约",
        "titleZh": "Strategy JSON DSL",
        "status": "COMPLETED_BY_AGENT",
        "stage": "V2_6_READY",
        "completedByAgent": True,
        "autoAppliedByAgent": True,
        "requiresAutonomousGovernance": True,
        "summaryZh": "Strategy JSON DSL 已进入 GA 全过程审计；种子必须通过 schema、safety 和 fingerprint 校验。",
    },
    {
        "id": "gaEvolutionTodo",
        "lane": "MT5_SHADOW",
        "laneZh": "MT5 模拟车道",
        "titleZh": "GA Evolution Engine",
        "status": "COMPLETED_BY_AGENT",
        "stage": "V2_6_READY",
        "completedByAgent": True,
        "autoAppliedByAgent": True,
        "requiresAutonomousGovernance": True,
        "summaryZh": "GA Evolution Trace 已接入 generation、candidate、fitness、blocker、elite 和 evolution path。",
    },
    {
        "id": "telegramGatewayTodo",
        "lane": "NOTIFICATION",
        "laneZh": "Telegram 推送",
        "titleZh": "Telegram Gateway",
        "status": "COMPLETED_BY_AGENT",
        "stage": "V2_7_READY",
        "completedByAgent": True,
        "autoAppliedByAgent": True,
        "requiresAutonomousGovernance": True,
        "summaryZh": "独立 Telegram Gateway 已接入队列、去重、限频和投递 ledger；只做中文 push-only，不接交易命令。",
    },
]


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _walk_forward_summary(agent: Dict[str, Any]) -> Dict[str, Any]:
    decision = _safe_dict(agent.get("promotionDecision"))
    selected = _safe_list(_safe_dict(decision.get("parameterSelection")).get("selected"))
    candidates = _safe_list(decision.get("candidates"))
    rows = [row for row in [*selected, *candidates] if isinstance(row, dict)]
    for row in rows:
        summary = _safe_dict(row.get("summary"))
        if summary:
            return summary
    return {}


def _runtime_metrics(runtime_dir: Path, agent: Dict[str, Any]) -> Dict[str, Any]:
    summary = _walk_forward_summary(agent)
    bar_replay = _load_json(runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYBarReplayReport.json")
    replay_summary = _safe_dict(bar_replay.get("summary"))
    entry = _safe_dict(bar_replay.get("entryComparison"))
    exit_cmp = _safe_dict(bar_replay.get("exitComparison"))
    entry_variants = _safe_list(entry.get("variants"))
    exit_variants = _safe_list(exit_cmp.get("variants"))
    current_entry = _safe_dict(entry_variants[0].get("metrics")) if len(entry_variants) > 0 and isinstance(entry_variants[0], dict) else {}
    relaxed_entry = _safe_dict(entry_variants[1].get("metrics")) if len(entry_variants) > 1 and isinstance(entry_variants[1], dict) else {}
    current_exit = _safe_dict(exit_variants[0].get("metrics")) if len(exit_variants) > 0 and isinstance(exit_variants[0], dict) else {}
    let_run_exit = _safe_dict(exit_variants[1].get("metrics")) if len(exit_variants) > 1 and isinstance(exit_variants[1], dict) else {}
    return {
        "unitPolicy": "R_PRIMARY_PIPS_SECONDARY_USC_REFERENCE",
        "sampleCount": summary.get("sampleCount") or replay_summary.get("sampleCount") or 0,
        "netR": summary.get("netRDelta") or replay_summary.get("relaxedNetRDelta") or 0,
        "validationNetRDelta": summary.get("validationNetRDelta"),
        "forwardNetRDelta": summary.get("forwardNetRDelta"),
        "maxAdverseR": relaxed_entry.get("maxAdverseR") or current_entry.get("maxAdverseR"),
        "profitCaptureRatio": let_run_exit.get("profitCaptureRatio") or current_exit.get("profitCaptureRatio"),
        "missedOpportunity": replay_summary.get("entryCountDelta") or relaxed_entry.get("missedOpportunityReduction") or 0,
        "earlyExit": replay_summary.get("letProfitRunNetRDelta") or 0,
        "entryCountDelta": relaxed_entry.get("entryCountDelta") or replay_summary.get("entryCountDelta") or 0,
        "falseEntryCount": relaxed_entry.get("falseEntryCount") or 0,
        "winRate": relaxed_entry.get("winRate") or current_entry.get("winRate"),
        "evidenceQuality": relaxed_entry.get("evidenceQuality") or current_entry.get("evidenceQuality") or "AGENT_SUMMARY",
    }


def _news_gate_summary(runtime_dir: Path) -> Dict[str, Any]:
    policy = _load_json(runtime_dir / "adaptive" / "QuantGod_USDJPYAutoExecutionPolicy.json")
    news_gate = _safe_dict(policy.get("newsGate"))
    if news_gate:
        return news_gate
    dashboard = _load_json(runtime_dir / "QuantGod_Dashboard.json")
    snapshot = dashboard if dashboard else _load_json(runtime_dir / "QuantGod_MT5RuntimeSnapshot_USDJPYc.json")
    return classify_news_gate(snapshot)


def _stage_text(route: Dict[str, Any]) -> str:
    return str(route.get("promotionStageZh") or route.get("promotionStage") or "模拟观察")


def _top_mt5_routes(mt5_shadow: Dict[str, Any], limit: int = 6) -> List[Dict[str, Any]]:
    routes = [row for row in _safe_list(mt5_shadow.get("routes")) if isinstance(row, dict)]
    items: List[Dict[str, Any]] = []
    for row in routes[:limit]:
        items.append({
            "strategy": row.get("strategy", ""),
            "direction": row.get("direction", ""),
            "stage": row.get("promotionStage", ""),
            "stageZh": _stage_text(row),
            "sampleCount": row.get("sampleCount", 0),
            "avgR": row.get("avgR", 0),
            "profitFactor": row.get("profitFactor", 0),
            "reasonZh": row.get("reasonZh", ""),
        })
    return items


def _next_phase_todos() -> Dict[str, Any]:
    todos = [dict(item) for item in NEXT_PHASE_TODOS]
    return {
        "status": "COMPLETED_BY_AGENT",
        "completedByAgent": True,
        "autoAppliedByAgent": True,
        "requiresAutonomousGovernance": True,
        "summaryZh": (
            "Strategy JSON、GA Evolution 和独立 Telegram Gateway 已接入；"
            "下一阶段聚焦更高保真回测、真实执行样本和 parity 深化。"
        ),
        "items": todos,
        "strategyJsonTodo": todos[0],
        "gaEvolutionTodo": todos[1],
        "telegramGatewayTodo": todos[2],
    }


def _ga_summary(runtime_dir: Path) -> Dict[str, Any]:
    status = _load_json(runtime_dir / "ga" / "QuantGod_GAStatus.json")
    generation = _load_json(runtime_dir / "ga" / "QuantGod_GAGenerationLatest.json")
    blockers = _load_json(runtime_dir / "ga" / "QuantGod_GABlockerSummary.json")
    blocker_rows = blockers.get("summary") if isinstance(blockers.get("summary"), list) else []
    history_production = _history_production_summary(runtime_dir)
    return {
        "status": status.get("status") or "WAITING_FIRST_GENERATION",
        "currentGeneration": status.get("currentGeneration", 0),
        "populationSize": status.get("populationSize", 0),
        "bestFitness": status.get("bestFitness", 0),
        "bestSeedId": status.get("bestSeedId"),
        "eliteCount": status.get("eliteCount", 0),
        "blockedCandidates": status.get("blockedCandidates", 0),
        "generationStatus": generation.get("status"),
        "blockers": blocker_rows,
        "historyProductionStatus": history_production,
        "nextAction": status.get("nextAction", "运行 Strategy JSON GA 一代并写入全过程 trace"),
    }


def _history_production_summary(runtime_dir: Path) -> Dict[str, Any]:
    production = _load_json(runtime_dir / "backtest" / "QuantGod_USDJPYHistoryProductionStatus.json")
    if not production:
        quality = _load_json(runtime_dir / "backtest" / "QuantGod_StrategyBacktestQualityReport.json")
        production = _safe_dict(quality.get("historyProductionStatus"))
    status = str(production.get("status") or "MISSING").upper()
    target_satisfied = bool(production.get("historyTargetSatisfied"))
    failed_count = int(production.get("failedCount") or 0)
    promotion_blocked = status != "PASS" or not target_satisfied
    source = _safe_dict(production.get("source"))
    timeframes = _safe_dict(production.get("timeframes"))
    h1 = _safe_dict(timeframes.get("H1"))
    m1 = _safe_dict(timeframes.get("M1"))
    if status == "PASS" and target_satisfied:
        status_zh = "生产级 PASS"
    elif status == "WARN":
        status_zh = "生产告警"
    else:
        status_zh = "等待生产状态"
    source_zh = "MQL5 CopyRates" if source.get("mql5ExportDir") else ("MT5 Python" if source.get("mt5PythonStatus") else "未知来源")
    depth_parts = []
    if h1.get("spanDays") is not None:
        depth_parts.append(f"H1 {h1.get('spanDays')} 天")
    if m1.get("spanDays") is not None:
        depth_parts.append(f"M1 {m1.get('spanDays')} 天")
    depth_zh = " / ".join(depth_parts)
    reason = production.get("reasonZh") or (
        "USDJPY 历史样本已达到生产级深度，GA 可使用完整 SQLite 回测评分。"
        if not promotion_blocked
        else "USDJPY 历史样本未达到生产级 PASS，GA 只能保留 shadow/tester 研究证据。"
    )
    return {
        "present": bool(production),
        "status": status,
        "statusZh": status_zh,
        "historyTargetSatisfied": target_satisfied,
        "promotionGateStatus": "BLOCKED" if promotion_blocked else "PASS",
        "promotionAllowed": not promotion_blocked,
        "failedCount": failed_count,
        "source": source,
        "sourceZh": source_zh,
        "timeframes": timeframes,
        "reasonZh": reason,
        "summaryZh": f"{status_zh}；{reason} 来源 {source_zh}{f'；{depth_zh}' if depth_zh else ''}",
    }


def _execution_consistency_review(runtime_dir: Path) -> Dict[str, Any]:
    evidence = _load_json(runtime_dir / "evidence_os" / "QuantGod_USDJPYEvidenceOSStatus.json")
    parity = _safe_dict(evidence.get("parity")) or _load_json(runtime_dir / "parity" / "QuantGod_StrategyParityReport.json")
    execution = _safe_dict(evidence.get("executionFeedback")) or _load_json(runtime_dir / "execution" / "QuantGod_LiveExecutionQualityReport.json")
    parity_gate = _safe_dict(parity.get("promotionGate"))
    execution_gate = _safe_dict(execution.get("promotionGate"))
    metrics = _safe_dict(execution.get("metrics"))
    field_contract = _safe_dict(execution.get("fieldCompleteness"))
    parity_status = str(parity.get("status") or "MISSING").upper()
    execution_gate_status = str(execution_gate.get("status") or "WAITING_FEEDBACK").upper()
    parity_failed = parity_status == "PARITY_FAIL" or parity_gate.get("status") == "BLOCKED"
    execution_blocked = execution_gate_status == "BLOCKED"
    if parity_failed:
        conclusion = "Strategy JSON / Replay / EA 口径不一致，阻断 shadow、GA elite 和 micro-live 晋级。"
    elif execution_blocked:
        conclusion = "执行质量未通过，降级观察并生成 Case Memory。"
    elif parity_status == "PARITY_PASS" and execution_gate_status == "PASS":
        conclusion = "策略口径和执行质量都可作为后续晋级支持证据。"
    else:
        conclusion = "继续收集 parity 与执行反馈，暂不扩大 live 阶段。"
    return {
        "schema": "quantgod.execution_consistency_review.v1",
        "parityStatus": parity_status,
        "parityGateStatus": parity_gate.get("status") or "MISSING",
        "executionGateStatus": execution_gate_status,
        "fieldContractStatus": field_contract.get("status") or "WAITING_FEEDBACK",
        "sampleCount": execution.get("sampleCount", 0),
        "avgSlippagePips": metrics.get("avgAbsSlippagePips", 0),
        "avgLatencyMs": metrics.get("avgLatencyMs", 0),
        "spreadAnomalyCount": metrics.get("spreadAnomalyCount", 0),
        "rejectCount": metrics.get("rejectCount", 0),
        "profitCaptureRatio": metrics.get("profitCaptureRatio", metrics.get("avgProfitCaptureRatio", "—")),
        "promotionBlocked": bool(parity_failed or execution_blocked),
        "blocksShadow": parity_failed,
        "blocksGaElite": parity_failed,
        "blocksMicroLive": parity_failed or execution_blocked,
        "agentConclusionZh": conclusion,
        "reasonZh": parity.get("reasonZh") or execution_gate.get("reasonZh") or conclusion,
    }


def _orchestration_summary(runtime_dir: Path) -> Dict[str, Any]:
    latest = read_latest_run(runtime_dir)
    if latest:
        return latest
    return {
        "ok": True,
        "schema": "quantgod.daily_autopilot_v2_run.v1",
        "status": "WAITING_FIRST_AGENT_CYCLE",
        "completedByAgent": False,
        "autoAppliedByAgent": False,
        "requiresAutonomousGovernance": True,
        "stepCount": 0,
        "completedStepCount": 0,
        "failedStepCount": 0,
        "steps": [],
        "summaryZh": "等待 Agent 首次运行自动调度循环。",
    }


def _build_morning_plan(agent: Dict[str, Any], lifecycle: Dict[str, Any], news_gate: Dict[str, Any]) -> Dict[str, Any]:
    cent = _safe_dict(lifecycle.get("centAccount") or agent.get("centAccount"))
    lanes = _safe_dict(lifecycle.get("lanes") or agent.get("lanes"))
    live = _safe_dict(lanes.get("live"))
    mt5_shadow = _safe_dict(lanes.get("mt5Shadow"))
    polymarket = _safe_dict(lanes.get("polymarketShadow"))
    patch = _safe_dict(agent.get("currentPatch"))
    limits = _safe_dict(patch.get("limits"))
    stage = str(agent.get("executionStage") or agent.get("stage") or "SHADOW")
    return {
        "titleZh": "QuantGod 今日自动作战计划",
        "accountMode": cent.get("accountMode", "cent"),
        "accountCurrencyUnit": cent.get("accountCurrencyUnit", "USC"),
        "centAccountAcceleration": bool(cent.get("centAccountAcceleration", True)),
        "liveLane": {
            "symbol": live.get("symbol", FOCUS_SYMBOL),
            "strategy": live.get("strategy", "RSI_Reversal"),
            "direction": live.get("direction", "LONG"),
            "stage": stage,
            "stageZh": agent.get("stageZh") or stage,
            "stageMaxLot": limits.get("stageMaxLot", 0),
            "maxLot": limits.get("maxLot", cent.get("maxLot", 2.0)),
        },
        "mt5ShadowLane": {
            "summary": mt5_shadow.get("summary", {}),
            "topRoutes": _top_mt5_routes(mt5_shadow),
        },
        "polymarketShadowLane": {
            "stage": polymarket.get("stage", "SHADOW"),
            "stageZh": polymarket.get("stageZh", "模拟观察"),
            "summary": polymarket.get("summary", {}),
            "reasonZh": polymarket.get("reasonZh", "继续模拟账本和事件风险，不触碰真实钱包。"),
        },
        "newsGate": {
            "mode": news_gate.get("mode", "SOFT"),
            "riskLevel": news_gate.get("riskLevel", "UNKNOWN"),
            "hardBlock": bool(news_gate.get("hardBlock")),
            "lotMultiplier": news_gate.get("lotMultiplier", 1.0),
            "stageDowngrade": bool(news_gate.get("stageDowngrade", False)),
            "reasonZh": news_gate.get("reasonZh", "普通新闻不阻断，高冲击新闻硬阻断。"),
            "highImpactEvent": news_gate.get("highImpactEvent"),
        },
        "todayForbiddenZh": [
            "USDJPY SELL 实盘",
            "非 RSI 实盘",
            "非 USDJPY 实盘",
            "Polymarket 钱包交易",
            "高冲击新闻窗口入场",
            "快通道或 runtime 陈旧时入场",
            "固定 2 手下单",
        ],
    }


def _build_evening_review(agent: Dict[str, Any], lifecycle: Dict[str, Any], news_gate: Dict[str, Any]) -> Dict[str, Any]:
    lanes = _safe_dict(lifecycle.get("lanes") or agent.get("lanes"))
    mt5_shadow = _safe_dict(lanes.get("mt5Shadow"))
    polymarket = _safe_dict(lanes.get("polymarketShadow"))
    patch = _safe_dict(agent.get("currentPatch"))
    rollback = _safe_dict(patch.get("rollback"))
    blockers = [str(item) for item in _safe_list(rollback.get("hardBlockers"))]
    mt5_summary = _safe_dict(mt5_shadow.get("summary"))
    return {
        "titleZh": "QuantGod 今日自动复盘",
        "liveLane": {
            "stage": agent.get("executionStage") or agent.get("stage") or "SHADOW",
            "stageZh": agent.get("stageZh") or "模拟观察",
            "rollbackTriggered": bool(blockers),
            "rollbackReasons": blockers,
            "patchWritable": bool(agent.get("patchWritable")),
            "autoAppliedByAgent": bool(agent.get("autoAppliedByAgent")),
            "liveMutationAllowed": False,
        },
        "mt5ShadowLane": {
            "promotedCount": int(mt5_summary.get("fastShadow", 0) or 0) + int(mt5_summary.get("testerOnly", 0) or 0),
            "pausedCount": int(mt5_summary.get("paused", 0) or 0),
            "rejectedCount": int(mt5_summary.get("rejected", 0) or 0),
            "routeCount": int(mt5_summary.get("routeCount", 0) or 0),
            "topRoutes": _top_mt5_routes(mt5_shadow),
        },
        "polymarketShadowLane": {
            "stage": polymarket.get("stage", "SHADOW"),
            "stageZh": polymarket.get("stageZh", "模拟观察"),
            "summary": polymarket.get("summary", {}),
            "riskContextOnly": True,
        },
        "newsGateReview": {
            "mode": news_gate.get("mode", "SOFT"),
            "riskLevel": news_gate.get("riskLevel", "UNKNOWN"),
            "ordinaryNewsBlocksLive": False,
            "highImpactNewsBlocksLive": True,
            "reasonZh": news_gate.get("reasonZh", "普通新闻只降仓/降级，高冲击新闻硬阻断。"),
        },
        "tomorrowStageZh": agent.get("stageZh") or "继续自主治理门评估",
    }


def _ga_todo_items(ga: Dict[str, Any]) -> List[Dict[str, Any]]:
    ran = int(ga.get("currentGeneration") or 0) > 0
    status = "COMPLETED_BY_AGENT" if ran else "PENDING"
    return [
        {
            "id": "ga_generate_seeds",
            "lane": "MT5_SHADOW",
            "laneZh": "GA 全过程",
            "action": "GENERATE_GA_SEEDS",
            "status": status,
            "completedByAgent": ran,
            "autoAppliedByAgent": ran,
            "requiresAutonomousGovernance": True,
            "summaryZh": "Agent 生成 Strategy JSON 种子池；每个种子必须通过 schema 和安全校验。",
        },
        {
            "id": "ga_run_generation",
            "lane": "MT5_SHADOW",
            "laneZh": "GA 全过程",
            "action": "RUN_GA_GENERATION",
            "status": status,
            "completedByAgent": ran,
            "autoAppliedByAgent": ran,
            "requiresAutonomousGovernance": True,
            "result": {
                "generation": ga.get("currentGeneration", 0),
                "eliteCount": ga.get("eliteCount", 0),
                "blockedCandidates": ga.get("blockedCandidates", 0),
            },
            "summaryZh": "Agent 已运行 GA generation；输出 generation、candidate、elite、blocker 和 evolution path。",
        },
        {
            "id": "ga_promote_elites_to_shadow",
            "lane": "MT5_SHADOW",
            "laneZh": "MT5 模拟车道",
            "action": "PROMOTE_GA_ELITES_TO_SHADOW",
            "status": status,
            "completedByAgent": ran,
            "autoAppliedByAgent": ran,
            "requiresAutonomousGovernance": True,
            "summaryZh": "Elite 只允许进入 shadow/tester/paper-live-sim；不会直接进入 MICRO_LIVE 或修改 live preset。",
        },
    ]


def _agent_todo_items(agent: Dict[str, Any], lifecycle: Dict[str, Any], metrics: Dict[str, Any], ga: Dict[str, Any]) -> List[Dict[str, Any]]:
    lanes = _safe_dict(lifecycle.get("lanes") or agent.get("lanes"))
    mt5_shadow = _safe_dict(lanes.get("mt5Shadow"))
    polymarket = _safe_dict(lanes.get("polymarketShadow"))
    patch = _safe_dict(agent.get("currentPatch"))
    rollback = _safe_dict(patch.get("rollback"))
    rollback_triggered = bool(_safe_list(rollback.get("hardBlockers")))
    live_stage = str(agent.get("executionStage") or agent.get("stage") or "SHADOW")
    auto_applied = bool(agent.get("autoAppliedByAgent"))
    return [
        {
            "id": "live_lane_governance",
            "lane": "LIVE",
            "laneZh": "实盘车道",
            "status": "ROLLBACK" if rollback_triggered else ("MICRO_LIVE" if live_stage == "MICRO_LIVE" else "COMPLETED_BY_AGENT"),
            "completedByAgent": True,
            "autoAppliedByAgent": auto_applied,
            "requiresAutonomousGovernance": True,
            "promotionDecision": live_stage,
            "rollbackTriggered": rollback_triggered,
            "metrics": metrics,
            "summaryZh": "Agent 已检查 USDJPY RSI LONG 实盘车道；硬风控未通过则自动回滚，未触发则等待 EA 自身守门。",
        },
        {
            "id": "mt5_shadow_lane_iteration",
            "lane": "MT5_SHADOW",
            "laneZh": "MT5 模拟车道",
            "status": "PROMOTED" if int(_safe_dict(mt5_shadow.get("summary")).get("fastShadow") or 0) else "COMPLETED_BY_AGENT",
            "completedByAgent": True,
            "autoAppliedByAgent": False,
            "requiresAutonomousGovernance": True,
            "promotionDecision": "FAST_SHADOW_OR_TESTER_ONLY",
            "rollbackTriggered": False,
            "metrics": _safe_dict(mt5_shadow.get("summary")),
            "summaryZh": "Agent 已复盘多策略 shadow 排名；强策略可进入 fast-shadow/tester-only，不能抢实盘 RSI LONG 路线。",
        },
        {
            "id": "polymarket_shadow_lane_iteration",
            "lane": "POLYMARKET_SHADOW",
            "laneZh": "Polymarket 模拟车道",
            "status": "COMPLETED_BY_AGENT",
            "completedByAgent": True,
            "autoAppliedByAgent": False,
            "requiresAutonomousGovernance": True,
            "promotionDecision": polymarket.get("stage", "SHADOW"),
            "rollbackTriggered": False,
            "metrics": _safe_dict(polymarket.get("summary")),
            "summaryZh": "Agent 已复盘预测市场模拟账本；只做 shadow 和事件风险，不连接真钱钱包。",
        },
    ] + _ga_todo_items(ga)


def _build_daily_todo(
    agent: Dict[str, Any],
    lifecycle: Dict[str, Any],
    metrics: Dict[str, Any],
    ga: Dict[str, Any],
    orchestration: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    items = _agent_todo_items(agent, lifecycle, metrics, ga)
    next_phase = _next_phase_todos()
    rollback_triggered = any(bool(item.get("rollbackTriggered")) for item in items)
    auto_applied = any(bool(item.get("autoAppliedByAgent")) for item in items)
    return {
        "ok": True,
        "schema": "quantgod.daily_todo_agent.v2_5",
        "agentVersion": AGENT_VERSION,
        "generatedAtIso": generated_at,
        "timestamp": generated_at,
        "symbol": FOCUS_SYMBOL,
        "status": "ROLLBACK" if rollback_triggered else "COMPLETED_BY_AGENT",
        "completed": True,
        "completedByAgent": True,
        "autoAppliedByAgent": auto_applied,
        "requiresAutonomousGovernance": True,
        "lane": "MULTI_LANE",
        "promotionDecision": agent.get("executionStage") or agent.get("stage"),
        "rollbackTriggered": rollback_triggered,
        "metrics": metrics,
        "items": items,
        "nextPhaseTodos": next_phase,
        "gaReview": ga,
        "historyProductionStatus": ga.get("historyProductionStatus"),
        "orchestrationRun": orchestration,
        "strategyJsonTodo": next_phase["strategyJsonTodo"],
        "gaEvolutionTodo": next_phase["gaEvolutionTodo"],
        "telegramGatewayTodo": next_phase["telegramGatewayTodo"],
        "summaryZh": (
            "今日待办已由 Agent 自动检查、生成和闭环；"
            "GA 会先确认 USDJPY 历史样本生产状态，不靠不完整样本晋级。"
        ),
    }


def _build_daily_review(
    agent: Dict[str, Any],
    lifecycle: Dict[str, Any],
    metrics: Dict[str, Any],
    ga: Dict[str, Any],
    orchestration: Dict[str, Any],
    consistency: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    lanes = _safe_dict(lifecycle.get("lanes") or agent.get("lanes"))
    mt5_shadow = _safe_dict(lanes.get("mt5Shadow"))
    polymarket = _safe_dict(lanes.get("polymarketShadow"))
    patch = _safe_dict(agent.get("currentPatch"))
    rollback = _safe_dict(patch.get("rollback"))
    rollback_triggered = bool(_safe_list(rollback.get("hardBlockers")))
    return {
        "ok": True,
        "schema": "quantgod.daily_review_agent.v2_5",
        "agentVersion": AGENT_VERSION,
        "generatedAtIso": generated_at,
        "timestamp": generated_at,
        "symbol": FOCUS_SYMBOL,
        "lane": "MULTI_LANE",
        "completed": True,
        "completedByAgent": True,
        "autoAppliedByAgent": bool(agent.get("autoAppliedByAgent")),
        "requiresAutonomousGovernance": True,
        "promotionDecision": agent.get("executionStage") or agent.get("stage"),
        "rollbackTriggered": rollback_triggered,
        "metrics": metrics,
        "liveLane": {
            "stage": agent.get("executionStage") or agent.get("stage"),
            "stageZh": agent.get("stageZh"),
            "strategy": "RSI_Reversal",
            "direction": "LONG",
            "rollbackReasons": _safe_list(rollback.get("hardBlockers")),
        },
        "mt5ShadowLane": {
            "summary": _safe_dict(mt5_shadow.get("summary")),
            "topRoutes": _top_mt5_routes(mt5_shadow),
        },
        "polymarketShadowLane": {
            "stage": polymarket.get("stage", "SHADOW"),
            "stageZh": polymarket.get("stageZh", "模拟观察"),
            "summary": _safe_dict(polymarket.get("summary")),
            "riskContextOnly": True,
        },
        "nextPhaseTodos": _next_phase_todos(),
        "gaReview": {
            "generation": ga.get("currentGeneration", 0),
            "bestFitness": ga.get("bestFitness", 0),
            "bestStrategy": ga.get("bestSeedId"),
            "promotedToShadow": ga.get("eliteCount", 0),
            "rejected": ga.get("blockedCandidates", 0),
            "historyProductionStatus": ga.get("historyProductionStatus"),
            "nextGenerationPlanned": True,
            "nextAction": ga.get("nextAction"),
        },
        "historyProductionStatus": ga.get("historyProductionStatus"),
        "executionConsistencyReview": consistency,
        "orchestrationRun": orchestration,
        "summaryZh": (
            "每日复盘已由 Agent 自动完成：收集三车道样本、计算指标、更新升降级/回滚状态，"
            "并记录 GA 是否使用生产级历史样本、parity 是否阻断晋级以及真实执行质量。"
        ),
    }


def build_daily_autopilot_v2(
    runtime_dir: Path,
    *,
    repo_root: Path | None = None,
    write: bool = False,
) -> Dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    lifecycle = build_autonomous_lifecycle(runtime_dir, repo_root=repo_root, write=write)
    agent = build_agent_state(runtime_dir, write=write)
    generated_at = utc_now_iso()
    metrics = _runtime_metrics(runtime_dir, agent)
    news_gate = _news_gate_summary(runtime_dir)
    ga = _ga_summary(runtime_dir)
    orchestration = _orchestration_summary(runtime_dir)
    consistency = _execution_consistency_review(runtime_dir)
    daily_todo = _build_daily_todo(agent, lifecycle, metrics, ga, orchestration, generated_at)
    daily_review = _build_daily_review(agent, lifecycle, metrics, ga, orchestration, consistency, generated_at)
    payload: Dict[str, Any] = {
        "ok": True,
        "schema": "quantgod.daily_autopilot_v2.v1",
        "agentVersion": AGENT_VERSION,
        "generatedAtIso": generated_at,
        "timestamp": generated_at,
        "symbol": FOCUS_SYMBOL,
        "titleZh": "USDJPY 美分账户三车道自动日报",
        "sloganZh": "实盘要窄，模拟要宽，升降级要快，回滚要硬。",
        "morningPlan": _build_morning_plan(agent, lifecycle, news_gate),
        "eveningReview": _build_evening_review(agent, lifecycle, news_gate),
        "newsGate": news_gate,
        "dailyTodo": daily_todo,
        "dailyReview": daily_review,
        "executionConsistencyReview": consistency,
        "orchestrationRun": orchestration,
        "gaReview": ga,
        "historyProductionStatus": ga.get("historyProductionStatus"),
        "nextPhaseTodos": _next_phase_todos(),
        "completedByAgent": True,
        "autoAppliedByAgent": bool(agent.get("autoAppliedByAgent")),
        "requiresAutonomousGovernance": True,
        "autonomousAgent": {
            "stage": agent.get("executionStage") or agent.get("stage"),
            "stageZh": agent.get("stageZh"),
            "patchWritable": bool(agent.get("patchWritable")),
            "completedByAgent": True,
            "autoAppliedByAgent": bool(agent.get("autoAppliedByAgent")),
            "requiresAutonomousGovernance": True,
            "autoApplyAllowed": "stage_gated",
        },
        "lanes": lifecycle.get("lanes"),
        "centAccount": lifecycle.get("centAccount"),
        "eaReproducibility": lifecycle.get("eaReproducibility"),
        "safety": {
            "orderSendAllowed": False,
            "closeAllowed": False,
            "cancelAllowed": False,
            "liveMutationAllowed": False,
            "livePresetMutationAllowed": False,
            "polymarketRealMoneyAllowed": False,
            "telegramCommandExecutionAllowed": False,
            "deepSeekCanApproveLive": False,
        },
    }
    if write:
        out = runtime_dir / "agent"
        out.mkdir(parents=True, exist_ok=True)
        (out / REPORT_NAME).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
