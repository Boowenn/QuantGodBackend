from __future__ import annotations

from typing import Any, Dict


def _fmt(value: Any, default: str = "—") -> str:
    if value in (None, ""):
        return default
    return str(value)


def _num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


def daily_autopilot_v2_to_chinese_text(payload: Dict[str, Any]) -> str:
    morning = payload.get("morningPlan") if isinstance(payload.get("morningPlan"), dict) else {}
    evening = payload.get("eveningReview") if isinstance(payload.get("eveningReview"), dict) else {}
    daily_todo = payload.get("dailyTodo") if isinstance(payload.get("dailyTodo"), dict) else {}
    daily_review = payload.get("dailyReview") if isinstance(payload.get("dailyReview"), dict) else {}
    next_phase = payload.get("nextPhaseTodos") if isinstance(payload.get("nextPhaseTodos"), dict) else {}
    next_phase_items = next_phase.get("items") if isinstance(next_phase.get("items"), list) else []
    ga_review = payload.get("gaReview") if isinstance(payload.get("gaReview"), dict) else {}
    history_production = payload.get("historyProductionStatus") if isinstance(payload.get("historyProductionStatus"), dict) else {}
    if not history_production:
        history_production = ga_review.get("historyProductionStatus") if isinstance(ga_review.get("historyProductionStatus"), dict) else {}
    review_metrics = daily_review.get("metrics") if isinstance(daily_review.get("metrics"), dict) else {}
    live = morning.get("liveLane") if isinstance(morning.get("liveLane"), dict) else {}
    mt5 = morning.get("mt5ShadowLane") if isinstance(morning.get("mt5ShadowLane"), dict) else {}
    mt5_summary = mt5.get("summary") if isinstance(mt5.get("summary"), dict) else {}
    polymarket = morning.get("polymarketShadowLane") if isinstance(morning.get("polymarketShadowLane"), dict) else {}
    poly_summary = polymarket.get("summary") if isinstance(polymarket.get("summary"), dict) else {}
    news_gate = morning.get("newsGate") if isinstance(morning.get("newsGate"), dict) else {}
    news_review = evening.get("newsGateReview") if isinstance(evening.get("newsGateReview"), dict) else {}
    evening_live = evening.get("liveLane") if isinstance(evening.get("liveLane"), dict) else {}
    evening_mt5 = evening.get("mt5ShadowLane") if isinstance(evening.get("mt5ShadowLane"), dict) else {}
    fast_shadow = _fmt(mt5_summary.get("fastShadow"), "0")
    tester_only = _fmt(mt5_summary.get("testerOnly"), "0")
    paused = _fmt(mt5_summary.get("paused"), "0")
    net_r = _fmt(review_metrics.get("netR"), "0")
    max_adverse = _fmt(review_metrics.get("maxAdverseR"))
    capture = _fmt(review_metrics.get("profitCaptureRatio"))
    promoted = evening_mt5.get("promotedCount", 0)
    evening_paused = evening_mt5.get("pausedCount", 0)
    rejected = evening_mt5.get("rejectedCount", 0)
    news_mode = _fmt(news_review.get("mode"), "SOFT")
    news_risk = _fmt(news_review.get("riskLevel"), "UNKNOWN")
    history_status = _fmt(history_production.get("statusZh"), "等待生产状态")
    history_gate = _fmt(history_production.get("promotionGateStatus"), "BLOCKED")
    history_reason = _fmt(
        history_production.get("reasonZh"),
        "等待 USDJPY SQLite 历史生产状态；未 PASS 时只允许 shadow/tester 观察。",
    )
    consistency = payload.get("executionConsistencyReview") if isinstance(payload.get("executionConsistencyReview"), dict) else {}

    lines = [
        "【QuantGod 今日自动作战计划】",
        "",
        f"账户模式：{_fmt(morning.get('accountMode'), 'cent')} / {_fmt(morning.get('accountCurrencyUnit'), 'USC')}",
        f"实盘车道：{_fmt(live.get('symbol'), 'USDJPYc')} {_fmt(live.get('strategy'), 'RSI_Reversal')} {_fmt(live.get('direction'), 'LONG')}",
        f"当前阶段：{_fmt(live.get('stageZh') or live.get('stage'))}",
        f"建议阶段仓位：{_num(live.get('stageMaxLot'))} / 最大上限 {_num(live.get('maxLot') or 2.0)}",
        "",
        "MT5 模拟车道：",
        f"- 路线：{_fmt(mt5_summary.get('routeCount'), '0')} 条",
        f"- 快速模拟：{fast_shadow}，测试器：{tester_only}，暂停：{paused}",
        "",
        "Polymarket 模拟车道：",
        f"- 状态：{_fmt(polymarket.get('stageZh') or polymarket.get('stage'))}",
        f"- 模拟 PF：{_fmt(poly_summary.get('shadowProfitFactor'), '0')}，模拟净值：{_fmt(poly_summary.get('shadowNetUSDC'), '0')} USDC",
        "- 只做模拟账本和事件风险，不连接真实钱包。",
        "",
        "新闻门禁：",
        f"- 模式：{_fmt(news_gate.get('mode'), 'SOFT')}；风险：{_fmt(news_gate.get('riskLevel'), 'UNKNOWN')}",
        f"- 普通新闻：不阻断，只降仓/降级；仓位倍率 {_fmt(news_gate.get('lotMultiplier'), '1.0')}",
        f"- 高冲击新闻：{'硬阻断' if news_gate.get('hardBlock') else '当前无高冲击硬阻断'}",
        f"- 说明：{_fmt(news_gate.get('reasonZh'), '普通新闻不挡 RSI 买入，高冲击新闻才硬挡。')}",
        "",
        "今日禁止：",
    ]
    for item in morning.get("todayForbiddenZh") or []:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Agent 今日待办：",
        f"- 状态：{_fmt(daily_todo.get('status'), 'COMPLETED_BY_AGENT')}；无需人工回灌。",
        f"- 自动推动：{'是' if daily_todo.get('autoAppliedByAgent') else '否'}；回滚：{'是' if daily_todo.get('rollbackTriggered') else '否'}。",
        "",
        "【QuantGod 今日自动复盘】",
        f"Agent 版本：{_fmt(payload.get('agentVersion'), 'v2.5')}",
        f"Live 阶段：{_fmt(evening_live.get('stageZh') or evening_live.get('stage'))}",
        f"是否触发回滚：{'是' if evening_live.get('rollbackTriggered') else '否'}",
        f"净 R：{net_r}；最大不利 R：{max_adverse}；利润捕获：{capture}",
        f"错失机会：{_fmt(review_metrics.get('missedOpportunity'), '0')}；早出场改善：{_fmt(review_metrics.get('earlyExit'), '0')}",
        f"MT5 模拟：晋级/强化 {promoted}，暂停 {evening_paused}，淘汰 {rejected}",
        f"新闻风险复盘：{news_mode} / {news_risk}；普通新闻不硬阻断，高冲击新闻硬阻断。",
        "",
        "执行一致性复盘：",
        f"- Strategy JSON 与 EA 一致性：{_fmt(consistency.get('parityStatus'), 'MISSING')}；晋级门：{_fmt(consistency.get('parityGateStatus'), 'MISSING')}",
        (
            f"- 实盘执行质量：平均滑点 {_fmt(consistency.get('avgSlippagePips'), '0')} pips；"
            f"平均延迟 {_fmt(consistency.get('avgLatencyMs'), '0')}ms；"
            f"拒单 {_fmt(consistency.get('rejectCount'), '0')} 次"
        ),
        f"- Agent 结论：{_fmt(consistency.get('agentConclusionZh'), '继续收集 parity 和执行反馈。')}",
        "",
        "GA 全过程：",
        f"- 当前代数：第 {_fmt(ga_review.get('currentGeneration'), '0')} 代；最佳分数：{_fmt(ga_review.get('bestFitness'), '0')}",
        f"- Elite：{_fmt(ga_review.get('eliteCount'), '0')}；阻断：{_fmt(ga_review.get('blockedCandidates'), '0')}",
        f"- GA 历史样本：{history_status}；晋级门：{history_gate}",
        f"- 样本说明：{history_reason}",
        f"- 下一步：{_fmt(ga_review.get('nextAction'), '运行下一代 Strategy JSON 评分')}",
        f"明日阶段：{_fmt(evening.get('tomorrowStageZh'))}",
        "",
        "下一阶段任务：",
    ])
    if next_phase_items:
        for item in next_phase_items[:3]:
            if isinstance(item, dict):
                title = _fmt(item.get("titleZh") or item.get("id"))
                status = _fmt(item.get("status"), "WAITING_NEXT_PHASE")
                summary = _fmt(item.get("summaryZh"))
                lines.append(f"- {title}：{status}，{summary}")
    else:
        lines.append("- Strategy JSON / GA Evolution / Telegram Gateway：已接入 Agent 证据链；下一阶段聚焦高保真样本和 parity 深化。")
    lines.extend([
        "",
        "安全边界：不会下单、不会平仓、不会撤单、不会修改订单或 live preset；",
        "DeepSeek 只解释，不批准越权；机器硬风控和自动回滚不可被取消。",
    ])
    return "\n".join(lines)
