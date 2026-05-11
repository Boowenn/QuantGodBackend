from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from daily_autopilot_v2.orchestrator import read_latest_run
    from daily_autopilot_v2.report import build_daily_autopilot_v2
    from autonomous_lifecycle.polymarket_shadow_lane import build_polymarket_shadow_lane
    from usdjpy_evidence_os.io_utils import read_jsonl_tail, utc_now_iso, write_json
    from usdjpy_evidence_os.schema import SAFETY_BOUNDARY, gateway_ledger_path, gateway_queue_path
    from usdjpy_evidence_os.telegram_gateway import gateway_status
except ModuleNotFoundError:  # pragma: no cover - package import path when run from tests
    from tools.daily_autopilot_v2.orchestrator import read_latest_run
    from tools.daily_autopilot_v2.report import build_daily_autopilot_v2
    from tools.autonomous_lifecycle.polymarket_shadow_lane import build_polymarket_shadow_lane
    from tools.usdjpy_evidence_os.io_utils import read_jsonl_tail, utc_now_iso, write_json
    from tools.usdjpy_evidence_os.schema import SAFETY_BOUNDARY, gateway_ledger_path, gateway_queue_path
    from tools.usdjpy_evidence_os.telegram_gateway import gateway_status


SCHEMA = "quantgod.agent_ops_health.v1"
AGENT_VERSION = "v2.6-agent-ops-health"
OUTPUT_FILE = Path("agent") / "QuantGod_AgentOpsHealth.json"


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _age_seconds(value: Any) -> float | None:
    parsed = _parse_time(value)
    if not parsed:
        return None
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def _as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _status_rank(status: str) -> int:
    return {"PASS": 0, "WARN": 1, "BLOCKED": 2}.get(str(status).upper(), 1)


def _overall_status(checks: List[Dict[str, Any]]) -> str:
    if any(_status_rank(check.get("status", "WARN")) >= 2 for check in checks):
        return "BLOCKED"
    if any(_status_rank(check.get("status", "WARN")) >= 1 for check in checks):
        return "WARN"
    return "PASS"


def _status_zh(status: str) -> str:
    mapping = {
        "PASS": "自动化健康",
        "WARN": "需要观察",
        "BLOCKED": "自动化阻断",
    }
    return mapping.get(str(status).upper(), "需要观察")


def _check(key: str, label: str, status: str, detail: str, metric: Any = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "key": key,
        "label": label,
        "status": status,
        "statusZh": _status_zh(status),
        "detailZh": detail,
    }
    if metric is not None:
        payload["metric"] = metric
    return payload


def _latest_delivery(runtime_dir: Path) -> Dict[str, Any]:
    rows = read_jsonl_tail(gateway_ledger_path(runtime_dir), limit=50)
    if not rows:
        return {}
    row = rows[-1]
    delivery = row.get("delivery") if isinstance(row.get("delivery"), dict) else {}
    return {
        "eventId": row.get("eventId"),
        "topic": row.get("topic"),
        "source": row.get("source"),
        "createdAtIso": row.get("createdAtIso"),
        "deliveryOk": bool(delivery.get("ok")),
        "deliveryReason": delivery.get("reason") or delivery.get("error") or "",
        "sentAtIso": delivery.get("sentAtIso") or delivery.get("queuedAtIso") or row.get("createdAtIso"),
    }


def _daily_autopilot_health(runtime_dir: Path, repo_root: Path) -> Dict[str, Any]:
    report = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=False)
    latest_run = read_latest_run(runtime_dir)
    steps = latest_run.get("steps") if isinstance(latest_run.get("steps"), list) else []
    failed_steps = [
        str(step.get("name") or step.get("action") or step.get("step") or "unknown")
        for step in steps
        if str(step.get("status") or "").upper() not in {"OK", "PASS", "COMPLETED", "COMPLETED_BY_AGENT", "SKIPPED"}
    ]
    completed_steps = len(steps) - len(failed_steps)
    last_run_at = (
        latest_run.get("completedAtIso")
        or latest_run.get("generatedAtIso")
        or latest_run.get("startedAtIso")
        or report.get("generatedAtIso")
    )
    age_seconds = _age_seconds(last_run_at)
    interval = _as_int(os.environ.get("QG_AGENT_V25_INTERVAL_SECONDS"), 300)
    stale_after = max(1800, interval * 3)
    completed_by_agent = bool(report.get("completedByAgent", True))
    status = "PASS"
    detail = "Daily Autopilot 已由 Agent 生成今日待办和每日复盘。"
    if failed_steps:
        status = "BLOCKED"
        detail = f"Daily Autopilot 有失败步骤：{', '.join(failed_steps[:4])}"
    elif age_seconds is not None and age_seconds > stale_after:
        status = "WARN"
        detail = f"Daily Autopilot 最近一次运行已超过 {int(age_seconds)} 秒。"
    elif not completed_by_agent:
        status = "WARN"
        detail = "日报仍未标记为 Agent 自动完成。"
    return {
        "status": status,
        "statusZh": _status_zh(status),
        "completedByAgent": completed_by_agent,
        "autoAppliedByAgent": bool(report.get("autoAppliedByAgent", True)),
        "lastRunAtIso": last_run_at,
        "lastRunAgeSeconds": age_seconds,
        "stepCount": len(steps),
        "completedStepCount": completed_steps,
        "failedStepCount": len(failed_steps),
        "failedSteps": failed_steps,
        "detailZh": detail,
        "summary": report.get("summary", {}),
    }


def _polymarket_health(runtime_dir: Path) -> Dict[str, Any]:
    lane = build_polymarket_shadow_lane(runtime_dir, write=False)
    summary = lane.get("summary") if isinstance(lane.get("summary"), dict) else {}
    retune_plan_ready = bool(summary.get("retunePlanReady"))
    todo_count = _as_int(summary.get("todoCount"), 0)
    retune_red = _as_int(summary.get("retuneRed"), 0)
    retune_yellow = _as_int(summary.get("retuneYellow"), 0)
    agent_status = str(summary.get("retuneAgentStatus") or "").upper()
    status = "PASS"
    detail = "Polymarket 跟单复盘已由 Agent 自动处理，真钱仍隔离。"
    if todo_count > 0 and not retune_plan_ready:
        status = "WARN"
        detail = "Polymarket 仍有待自动重调的黄字事项，等待 Agent 生成 retune plan。"
    elif retune_red > 0 or retune_yellow > 0:
        status = "WARN"
        detail = f"Polymarket 有 {retune_red} 个红项 / {retune_yellow} 个黄项，仅进入 shadow retune。"
    elif agent_status and agent_status not in {"COMPLETE", "COMPLETED", "REVIEW_COMPLETE_NO_CODE_CHANGE"}:
        status = "WARN"
        detail = f"Polymarket Agent 状态：{agent_status}"
    return {
        "status": status,
        "statusZh": _status_zh(status),
        "stage": lane.get("stage"),
        "stageZh": lane.get("stageZh"),
        "retunePlanReady": retune_plan_ready,
        "retuneAgentStatus": summary.get("retuneAgentStatus"),
        "todoCount": todo_count,
        "retuneRed": retune_red,
        "retuneYellow": retune_yellow,
        "detailZh": detail,
        "walletIntegrationAllowed": False,
        "polymarketRealMoneyAllowed": False,
    }


def _telegram_health(runtime_dir: Path) -> Dict[str, Any]:
    status_payload = gateway_status(runtime_dir)
    latest = _latest_delivery(runtime_dir)
    queue_rows = read_jsonl_tail(gateway_queue_path(runtime_dir), limit=500)
    pending_count = _as_int(status_payload.get("pendingCount"), len(queue_rows))
    delivered_count = _as_int(status_payload.get("deliveredCount"), 0)
    push_allowed = bool(status_payload.get("pushAllowed"))
    commands_allowed = bool(status_payload.get("commandsAllowed"))
    status = "PASS"
    detail = "Telegram Gateway 已启用 push-only 投递。"
    if commands_allowed:
        status = "BLOCKED"
        detail = "Telegram 命令接收被打开，违反 push-only 边界。"
    elif not push_allowed:
        status = "WARN"
        detail = "Telegram 推送未启用，Agent 会生成消息但不会发送。"
    elif pending_count > 0 and delivered_count == 0:
        status = "WARN"
        detail = "Telegram 队列有待投递消息，尚未看到成功投递。"
    elif latest and not latest.get("deliveryOk"):
        status = "WARN"
        detail = f"最近 Telegram 投递未成功：{latest.get('deliveryReason') or '等待下一轮'}"
    return {
        "status": status,
        "statusZh": _status_zh(status),
        "queuedCount": _as_int(status_payload.get("queuedCount"), len(queue_rows)),
        "pendingCount": pending_count,
        "deliveredCount": delivered_count,
        "ledgerCount": _as_int(status_payload.get("ledgerCount"), 0),
        "pushAllowed": push_allowed,
        "commandsAllowed": commands_allowed,
        "lastTopic": latest.get("topic") or status_payload.get("lastTopic"),
        "lastEventId": latest.get("eventId") or status_payload.get("lastEventId"),
        "lastDeliveryOk": latest.get("deliveryOk"),
        "lastDeliveryReason": latest.get("deliveryReason"),
        "lastDeliveryAtIso": latest.get("sentAtIso"),
        "detailZh": detail,
    }


def build_agent_ops_health(runtime_dir: Path, repo_root: Path | None = None, write: bool = False) -> Dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    daily = _daily_autopilot_health(runtime_dir, repo_root)
    polymarket = _polymarket_health(runtime_dir)
    telegram = _telegram_health(runtime_dir)
    checks = [
        _check("dailyAutopilot", "Daily Autopilot", daily["status"], daily["detailZh"], daily.get("lastRunAgeSeconds")),
        _check("polymarketRetune", "Polymarket 跟单重调", polymarket["status"], polymarket["detailZh"], polymarket.get("todoCount")),
        _check("telegramGateway", "Telegram Gateway", telegram["status"], telegram["detailZh"], telegram.get("pendingCount")),
    ]
    overall = _overall_status(checks)
    blockers = [check["detailZh"] for check in checks if check.get("status") == "BLOCKED"]
    warnings = [check["detailZh"] for check in checks if check.get("status") == "WARN"]
    payload: Dict[str, Any] = {
        "schema": SCHEMA,
        "agentVersion": AGENT_VERSION,
        "generatedAtIso": utc_now_iso(),
        "overallStatus": overall,
        "overallStatusZh": _status_zh(overall),
        "ok": overall != "BLOCKED",
        "dailyAutopilot": daily,
        "polymarketRetune": polymarket,
        "telegramGateway": telegram,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "safety": {
            **SAFETY_BOUNDARY,
            "agentOpsHealthOnly": True,
            "orderSendAllowed": False,
            "livePresetMutationAllowed": False,
            "telegramCommandsAllowed": False,
        },
    }
    if write:
        write_json(runtime_dir / OUTPUT_FILE, payload)
    return payload
