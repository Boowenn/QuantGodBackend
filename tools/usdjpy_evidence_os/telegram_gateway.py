from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from .io_utils import append_jsonl, append_jsonl_unique, read_jsonl_tail, utc_now_iso, write_json
from .schema import AGENT_VERSION, SAFETY_BOUNDARY, gateway_ledger_path, gateway_queue_path, gateway_status_path

MAX_EVENTS_PER_RUN = 8
SCHEDULED_REPORT_TOPICS = (
    "DAILY_AUTOPILOT_V2_REPORT",
    "GA_EVOLUTION_REPORT",
    "USDJPY_AUTONOMOUS_AGENT_REPORT",
    "POLYMARKET_RETUNE_REPORT",
)


def build_notification_event(
    source: str,
    topic: str,
    severity: str,
    text: str,
    payload: Dict[str, Any] | None = None,
    dedupe_key: str | None = None,
) -> Dict[str, Any]:
    digest_material = dedupe_key or f"{source}|{topic}|{severity}|{text[:1000]}"
    digest = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()
    return {
        "schema": "quantgod.notification.v1",
        "agentVersion": AGENT_VERSION,
        "eventId": digest[:24],
        "dedupeKey": dedupe_key,
        "createdAt": utc_now_iso(),
        "source": source,
        "topic": topic,
        "severity": severity,
        "lang": "zh-CN",
        "text": text,
        "payload": payload or {},
        "safety": dict(SAFETY_BOUNDARY),
    }


def dispatch_text(
    runtime_dir: Path,
    source: str,
    topic: str,
    severity: str,
    text: str,
    payload: Dict[str, Any] | None = None,
    send: bool = False,
    dedupe_key: str | None = None,
) -> Dict[str, Any]:
    event = build_notification_event(source, topic, severity, text, payload=payload, dedupe_key=dedupe_key)
    return dispatch_event(runtime_dir, event, send=send)


def collect_scheduled_events(
    runtime_dir: Path,
    repo_root: Path | None = None,
    refresh: bool = True,
) -> Dict[str, Any]:
    """Collect operator reports into the Gateway queue.

    The scheduled agent loop should not call individual Telegram senders. It
    should build auditable reports, enqueue them with stable dedupe keys, and
    let the Gateway handle rate limiting and delivery.
    """
    runtime_dir = Path(runtime_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    _ensure_import_paths(repo_root)
    collected: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for builder in (
        _build_daily_autopilot_event,
        _build_ga_event,
        _build_autonomous_agent_event,
        _build_polymarket_retune_event,
    ):
        try:
            event = builder(runtime_dir, repo_root, refresh)
            if not event:
                continue
            enqueue_result = enqueue_event(runtime_dir, event)
            collected.append(
                {
                    "topic": event.get("topic"),
                    "source": event.get("source"),
                    "eventId": event.get("eventId"),
                    "dedupeKey": event.get("dedupeKey"),
                    "queued": enqueue_result.get("queued", 0),
                }
            )
        except Exception as exc:
            errors.append({"builder": getattr(builder, "__name__", "unknown"), "error": f"{type(exc).__name__}: {exc}"})
    status = gateway_status(runtime_dir)
    status.update(
        {
            "scheduledCollector": True,
            "scheduledTopics": list(SCHEDULED_REPORT_TOPICS),
            "collectedCount": len(collected),
            "collectedEvents": collected,
            "collectErrors": errors,
            "reasonZh": "Telegram Gateway 已收集日报、GA、Agent 回滚/patch、Polymarket retune 报告；统一排队、去重、限频和投递。",
        }
    )
    write_json(gateway_status_path(runtime_dir), status)
    return status


def dispatch_event(runtime_dir: Path, event: Dict[str, Any], send: bool = False) -> Dict[str, Any]:
    ledger = gateway_ledger_path(runtime_dir)
    recent_ids = {
        row.get("eventId")
        for row in read_jsonl_tail(ledger, 200)
        if _delivery_counts_as_processed(row)
    }
    duplicate = event.get("eventId") in recent_ids
    rate_limited = _rate_limited(ledger)
    delivery = {"ok": False, "skipped": True, "reason": "send_not_requested"}
    if send and not duplicate and not rate_limited:
        delivery = _send_telegram(event.get("text", ""))
    elif duplicate:
        delivery = {"ok": False, "skipped": True, "reason": "duplicate_suppressed"}
    elif rate_limited:
        delivery = {"ok": False, "skipped": True, "reason": "rate_limited"}
    row = {
        **event,
        "duplicateSuppressed": duplicate,
        "rateLimited": rate_limited,
        "sendRequested": bool(send),
        "delivery": delivery,
    }
    append_jsonl(ledger, [row])
    status = {
        "ok": True,
        "schema": "quantgod.telegram_gateway_status.v1",
        "agentVersion": AGENT_VERSION,
        "lastEventId": event.get("eventId"),
        "duplicateSuppressed": duplicate,
        "rateLimited": rate_limited,
        "sendRequested": bool(send),
        "delivery": delivery,
        "reasonZh": "独立 Telegram Gateway 统一做中文模板、去重、限频、投递账本；不接收 Telegram 交易命令。",
        "safety": dict(SAFETY_BOUNDARY),
    }
    write_json(gateway_status_path(runtime_dir), status)
    return status


def enqueue_event(runtime_dir: Path, event: Dict[str, Any]) -> Dict[str, Any]:
    queued = append_jsonl_unique(gateway_queue_path(runtime_dir), [event], "eventId")
    status = gateway_status(runtime_dir)
    status.update(
        {
            "queued": queued,
            "lastQueuedEventId": event.get("eventId"),
            "reasonZh": "NotificationEvent 已进入独立 Telegram Gateway 队列，等待统一投递。",
        }
    )
    write_json(gateway_status_path(runtime_dir), status)
    return status


def dispatch_pending(
    runtime_dir: Path,
    send: bool = False,
    limit: int = MAX_EVENTS_PER_RUN,
    allowed_topics: List[str] | None = None,
) -> Dict[str, Any]:
    queue = read_jsonl_tail(gateway_queue_path(runtime_dir), 1000)
    ledger_ids = {
        row.get("eventId")
        for row in read_jsonl_tail(gateway_ledger_path(runtime_dir), 2000)
        if _delivery_counts_as_processed(row)
    }
    pending = [row for row in queue if row.get("eventId") not in ledger_ids]
    if allowed_topics is not None:
        allowed = set(allowed_topics)
        pending = [row for row in pending if row.get("topic") in allowed]
    dispatched = []
    for event in pending[: max(1, min(int(limit), MAX_EVENTS_PER_RUN))]:
        dispatched.append(dispatch_event(runtime_dir, event, send=send))
    status = gateway_status(runtime_dir)
    post_dispatch_pending = status.get("pendingCount", max(0, len(pending)))
    status.update(
        {
            "pendingCount": post_dispatch_pending,
            "dispatchedCount": len(dispatched),
            "sendRequested": bool(send),
            "dispatchResults": dispatched[-5:],
            "reasonZh": "独立 Telegram Gateway 已处理队列；只 push 中文通知，不接收交易命令。",
        }
    )
    write_json(gateway_status_path(runtime_dir), status)
    return status


def gateway_status(runtime_dir: Path) -> Dict[str, Any]:
    queue = read_jsonl_tail(gateway_queue_path(runtime_dir), 1000)
    ledger = read_jsonl_tail(gateway_ledger_path(runtime_dir), 1000)
    delivered_rows = [row for row in ledger if _delivery_counts_as_processed(row)]
    delivered_ids = {row.get("eventId") for row in delivered_rows}
    pending = [row for row in queue if row.get("eventId") not in delivered_ids]
    last = ledger[-1] if ledger else {}
    return {
        "ok": True,
        "schema": "quantgod.telegram_gateway_status.v1",
        "agentVersion": AGENT_VERSION,
        "queuedCount": len(queue),
        "ledgerCount": len(ledger),
        "deliveredCount": len(delivered_rows),
        "pendingCount": len(pending),
        "lastEventId": last.get("eventId"),
        "lastTopic": last.get("topic"),
        "lastDelivery": last.get("delivery"),
        "pushAllowed": os.environ.get("QG_TELEGRAM_PUSH_ALLOWED", "0").strip() == "1",
        "commandsAllowed": os.environ.get("QG_TELEGRAM_COMMANDS_ALLOWED", "0").strip() == "1",
        "reasonZh": "独立 Telegram Gateway 当前可审计；负责去重、限频、投递 ledger，不接收命令。",
        "safety": dict(SAFETY_BOUNDARY),
    }


def polymarket_retune_to_chinese_text(plan: Dict[str, Any]) -> str:
    counts = plan.get("recommendationCounts") if isinstance(plan.get("recommendationCounts"), dict) else {}
    review = plan.get("copyTradingReview") if isinstance(plan.get("copyTradingReview"), dict) else {}
    metrics = review.get("bestMetrics") if isinstance(review.get("bestMetrics"), dict) else {}
    capital = review.get("capitalSimulation") if isinstance(review.get("capitalSimulation"), dict) else {}
    next_actions = review.get("nextActions") if isinstance(review.get("nextActions"), list) else plan.get("nextActions")
    if not isinstance(next_actions, list):
        next_actions = []
    lines = [
        "【QuantGod Polymarket 跟单复盘】",
        "",
        f"状态：{_fmt(review.get('operatorStatusLabel') or review.get('status') or plan.get('decision'))}",
        f"Agent：{_fmt(review.get('agentRetuneStatus'))}",
        f"红/黄/绿/灰：{_fmt(counts.get('red'), '0')} / {_fmt(counts.get('yellow'), '0')} / {_fmt(counts.get('green'), '0')} / {_fmt(counts.get('gray'), '0')}",
        (
            "最佳样本："
            f"{_fmt(metrics.get('source'))}｜样本 {_fmt(metrics.get('closed'), '0')}｜"
            f"PF {_fmt(metrics.get('profitFactor'), '0')}｜胜率 {_fmt(metrics.get('winRatePct'), '0')}%"
        ),
        (
            "模拟账本："
            f"现金折算 {_fmt(capital.get('cashScaledUSDC'), '$0')}｜"
            f"账本净值 {_fmt(capital.get('ledgerNetUSDC'), '$0')}；不连接真实钱包。"
        ),
        "",
        f"结论：{_fmt(review.get('summary') or plan.get('summary'))}",
        "下一步：",
    ]
    if next_actions:
        for item in next_actions[:5]:
            lines.append(f"- {_fmt(item)}")
    else:
        lines.append("- 保持 shadow-only，等待下一轮 Agent retune。")
    lines.extend(
        [
            "",
            "安全边界：Polymarket 只做模拟账本和事件风险；不连接钱包、不签名、不下单、不撤单。",
        ]
    )
    return "\n".join(lines)


def _build_daily_autopilot_event(runtime_dir: Path, repo_root: Path, refresh: bool) -> Dict[str, Any]:
    from daily_autopilot_v2.report import build_daily_autopilot_v2
    from daily_autopilot_v2.telegram_text import daily_autopilot_v2_to_chinese_text

    payload = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=refresh)
    text = daily_autopilot_v2_to_chinese_text(payload)
    return build_notification_event(
        "daily_autopilot_v2",
        "DAILY_AUTOPILOT_V2_REPORT",
        "INFO",
        text,
        payload={"dailyAutopilotV2": payload},
        dedupe_key=f"{_local_day()}|DAILY_AUTOPILOT_V2_REPORT",
    )


def _build_ga_event(runtime_dir: Path, repo_root: Path, refresh: bool) -> Dict[str, Any]:
    del repo_root, refresh
    from strategy_ga.generation_runner import build_ga_status
    from strategy_ga.telegram_text import ga_to_chinese_text

    ga_status = build_ga_status(runtime_dir)
    payload = {
        "status": ga_status.get("status") if isinstance(ga_status.get("status"), dict) else {},
        "generation": ga_status.get("generation") if isinstance(ga_status.get("generation"), dict) else {},
        "blockers": ga_status.get("blockers") if isinstance(ga_status.get("blockers"), dict) else {},
        "evolutionPath": ga_status.get("evolutionPath") if isinstance(ga_status.get("evolutionPath"), dict) else {},
    }
    text = ga_to_chinese_text(payload)
    status = payload["status"]
    dedupe_key = "|".join(
        [
            "GA_EVOLUTION_REPORT",
            str(status.get("currentGeneration") or 0),
            str(status.get("bestSeedId") or "none"),
            str(status.get("bestFitness") or 0),
            str(status.get("blockedCandidates") or 0),
        ]
    )
    severity = "WARN" if int(status.get("blockedCandidates") or 0) else "INFO"
    return build_notification_event(
        "strategy_ga",
        "GA_EVOLUTION_REPORT",
        severity,
        text,
        payload={"strategyGa": ga_status},
        dedupe_key=dedupe_key,
    )


def _build_autonomous_agent_event(runtime_dir: Path, repo_root: Path, refresh: bool) -> Dict[str, Any]:
    del repo_root
    from usdjpy_autonomous_agent.agent_state import build_agent_state
    from usdjpy_autonomous_agent.telegram_text import autonomous_agent_to_chinese_text

    payload = build_agent_state(runtime_dir, write=refresh)
    text = autonomous_agent_to_chinese_text(payload)
    patch = payload.get("currentPatch") if isinstance(payload.get("currentPatch"), dict) else {}
    rollback = patch.get("rollback") if isinstance(patch.get("rollback"), dict) else {}
    hard_blockers = rollback.get("hardBlockers") if isinstance(rollback.get("hardBlockers"), list) else []
    severity = "WARN" if hard_blockers or "ROLLBACK" in str(payload.get("stage") or "") else "INFO"
    blocker_signature = _blocker_signature(hard_blockers)
    dedupe_key = "|".join(
        [
            _local_day(),
            "USDJPY_AUTONOMOUS_AGENT_REPORT",
            str(payload.get("stage") or "UNKNOWN"),
            str(patch.get("patchId") or "no_patch"),
            blocker_signature,
        ]
    )
    return build_notification_event(
        "usdjpy_autonomous_agent",
        "USDJPY_AUTONOMOUS_AGENT_REPORT",
        severity,
        text,
        payload={"autonomousAgent": payload},
        dedupe_key=dedupe_key,
    )


def _build_polymarket_retune_event(runtime_dir: Path, repo_root: Path, refresh: bool) -> Optional[Dict[str, Any]]:
    del repo_root, refresh
    plan_path = runtime_dir / "QuantGod_PolymarketRetunePlanner.json"
    plan = _load_json(plan_path)
    if not plan:
        return None
    text = polymarket_retune_to_chinese_text(plan)
    review = plan.get("copyTradingReview") if isinstance(plan.get("copyTradingReview"), dict) else {}
    counts = plan.get("recommendationCounts") if isinstance(plan.get("recommendationCounts"), dict) else {}
    severity = "WARN" if int(counts.get("red") or 0) or int(counts.get("yellow") or 0) else "INFO"
    dedupe_key = "|".join(
        [
            _local_day(),
            "POLYMARKET_RETUNE_REPORT",
            str(review.get("agentRetuneStatus") or plan.get("decision") or "UNKNOWN"),
            str(counts.get("red") or 0),
            str(counts.get("yellow") or 0),
        ]
    )
    return build_notification_event(
        "polymarket_retune",
        "POLYMARKET_RETUNE_REPORT",
        severity,
        text,
        payload={"polymarketRetune": plan},
        dedupe_key=dedupe_key,
    )


def _send_telegram(text: str) -> Dict[str, Any]:
    if os.environ.get("QG_TELEGRAM_PUSH_ALLOWED", "0").strip() != "1":
        return {"ok": False, "skipped": True, "reason": "QG_TELEGRAM_PUSH_ALLOWED is not 1"}
    if os.environ.get("QG_TELEGRAM_COMMANDS_ALLOWED", "0").strip() == "1":
        return {"ok": False, "skipped": True, "reason": "Telegram command execution must stay disabled"}
    token = os.environ.get("QG_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("QG_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"ok": False, "skipped": True, "reason": "Telegram token/chat_id missing"}
    url = f"https://api.telegram.org/bot{urllib.parse.quote(token, safe=':')}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:3900]}).encode("utf-8")
    try:
        with urllib.request.urlopen(url, data=body, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return {"ok": bool(payload.get("ok")), "telegram": payload}
    except Exception as exc:
        curl_result = _send_telegram_with_curl(token, chat_id, text[:3900])
        if curl_result.get("ok"):
            curl_result["urllibFallbackReason"] = str(exc)
            return curl_result
        return {"ok": False, "error": str(exc), "curlFallback": curl_result}


def _send_telegram_with_curl(token: str, chat_id: str, text: str) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--max-time",
                "20",
                "--request",
                "POST",
                url,
                "--data-urlencode",
                f"chat_id={chat_id}",
                "--data-urlencode",
                f"text={text}",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=25,
        )
    except Exception as exc:
        return {"ok": False, "error": f"curl_failed: {type(exc).__name__}: {exc}"}
    if result.returncode != 0:
        return {"ok": False, "error": f"curl_exit_{result.returncode}: {result.stderr.strip()[:300]}"}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": "curl_returned_non_json", "body": result.stdout[:300]}
    return {"ok": bool(payload.get("ok")), "telegram": payload, "transport": "curl"}


def _fmt(value: Any, default: str = "—") -> str:
    if value in (None, ""):
        return default
    return str(value)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _blocker_signature(blockers: List[Any]) -> str:
    if not blockers:
        return "no_blockers"
    normalized: List[str] = []
    for item in blockers[:8]:
        text = str(item)
        for sep in ("：", ":"):
            if sep in text:
                text = text.split(sep, 1)[0]
                break
        normalized.append(text.strip() or "UNKNOWN")
    return _short_hash("|".join(normalized))


def _local_day() -> str:
    return date.today().isoformat()


def _ensure_import_paths(repo_root: Path) -> None:
    for candidate in (repo_root, repo_root / "tools"):
        value = str(candidate)
        if value not in sys.path:
            sys.path.insert(0, value)


def _rate_limited(ledger: Path) -> bool:
    current_hour = utc_now_iso()[:13]
    recent = read_jsonl_tail(ledger, 200)
    sent = [
        row
        for row in recent
        if (row.get("delivery") or {}).get("ok") and str(row.get("createdAt") or "").startswith(current_hour)
    ]
    return len(sent) >= MAX_EVENTS_PER_RUN


def _delivery_counts_as_processed(row: Dict[str, Any]) -> bool:
    delivery = row.get("delivery") or {}
    return bool(delivery.get("ok"))
