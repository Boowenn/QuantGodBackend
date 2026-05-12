#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict

from daily_autopilot_v2.orchestrator import run_daily_autopilot_cycle
from daily_autopilot_v2.report import build_daily_autopilot_v2
from daily_autopilot_v2.telegram_text import daily_autopilot_v2_to_chinese_text
from usdjpy_evidence_os.telegram_gateway import dispatch_text


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


def emit(payload) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def todo_text(payload: Dict[str, object]) -> str:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    history = payload.get("historyProductionStatus") if isinstance(payload.get("historyProductionStatus"), dict) else {}
    lines = [
        "【QuantGod Agent 今日待办】",
        "",
        f"状态：{payload.get('status', 'COMPLETED_BY_AGENT')}",
        f"Agent 版本：{payload.get('agentVersion', 'v2.5')}",
        "无需人工回灌；每项由 Agent 自动检查、完成、晋级或回滚。",
        f"GA 历史样本：{history.get('statusZh', '等待生产状态')}；晋级门：{history.get('promotionGateStatus', 'BLOCKED')}",
        "",
    ]
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- {item.get('laneZh') or item.get('lane')}｜{item.get('status')}｜"
            f"{item.get('summaryZh', '')}"
        )
    return "\n".join(lines)


def review_text(payload: Dict[str, object]) -> str:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    live = payload.get("liveLane") if isinstance(payload.get("liveLane"), dict) else {}
    mt5 = payload.get("mt5ShadowLane") if isinstance(payload.get("mt5ShadowLane"), dict) else {}
    poly = payload.get("polymarketShadowLane") if isinstance(payload.get("polymarketShadowLane"), dict) else {}
    history = payload.get("historyProductionStatus") if isinstance(payload.get("historyProductionStatus"), dict) else {}
    consistency = payload.get("executionConsistencyReview") if isinstance(payload.get("executionConsistencyReview"), dict) else {}
    lines = [
        "【QuantGod Agent 每日复盘】",
        "",
        f"阶段：{live.get('stageZh') or live.get('stage') or payload.get('promotionDecision', 'SHADOW')}",
        f"回滚：{'是' if payload.get('rollbackTriggered') else '否'}",
        f"净 R：{metrics.get('netR', 0)}｜最大不利 R：{metrics.get('maxAdverseR', '—')}｜利润捕获：{metrics.get('profitCaptureRatio', '—')}",
        f"错失机会：{metrics.get('missedOpportunity', 0)}｜早出场改善：{metrics.get('earlyExit', 0)}",
        f"MT5 模拟路线：{(mt5.get('summary') or {}).get('routeCount', 0)}｜Polymarket：{poly.get('stageZh') or poly.get('stage', '模拟观察')}",
        f"GA 历史样本：{history.get('statusZh', '等待生产状态')}｜{history.get('reasonZh', '未 PASS 时只允许 shadow/tester 观察')}",
        "",
        "【QuantGod 执行一致性复盘】",
        f"Strategy JSON 与 EA 一致性：{consistency.get('parityStatus', 'MISSING')}｜晋级门：{consistency.get('parityGateStatus', 'MISSING')}",
        f"实盘执行质量：滑点 {consistency.get('avgSlippagePips', 0)} pips｜延迟 {consistency.get('avgLatencyMs', 0)}ms｜拒单 {consistency.get('rejectCount', 0)}",
        f"Agent 结论：{consistency.get('agentConclusionZh', '继续收集 parity 和执行反馈。')}",
        "",
        "复盘已由 Agent 自动完成；不等待人工确认，不修改 live preset，不连接 Polymarket 钱包。",
    ]
    return "\n".join(lines)


def send_telegram(runtime_dir: Path, topic: str, text: str) -> Dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.telegram.local")
    return dispatch_text(runtime_dir, "daily_autopilot_v2", topic, "INFO", text, send=True)


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.usdjpy.local")
    parser = argparse.ArgumentParser(description="QuantGod Daily Autopilot 2.0 for USDJPY cent-account autonomous agent")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    parser.add_argument("--repo-root", default=str(root))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    build = sub.add_parser("build")
    build.add_argument("--write", action="store_true")
    run_cycle = sub.add_parser("run-cycle")
    run_cycle.add_argument("--write", action="store_true")
    run_cycle.add_argument("--bootstrap-samples", action="store_true")
    run_cycle.add_argument("--view", choices=["full", "daily-todo", "daily-review"], default="full")
    todo = sub.add_parser("daily-todo")
    todo.add_argument("--write", action="store_true")
    review = sub.add_parser("daily-review")
    review.add_argument("--write", action="store_true")
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    text.add_argument("--write", action="store_true")
    text.add_argument("--send", action="store_true")
    todo_text_parser = sub.add_parser("daily-todo-telegram-text")
    todo_text_parser.add_argument("--refresh", action="store_true")
    todo_text_parser.add_argument("--write", action="store_true")
    todo_text_parser.add_argument("--send", action="store_true")
    review_text_parser = sub.add_parser("daily-review-telegram-text")
    review_text_parser.add_argument("--refresh", action="store_true")
    review_text_parser.add_argument("--write", action="store_true")
    review_text_parser.add_argument("--send", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)
    repo_root = Path(args.repo_root)
    if args.command == "status":
        return emit(build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=False))
    if args.command == "build":
        return emit(build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=args.write))
    if args.command == "run-cycle":
        run_payload = run_daily_autopilot_cycle(
            runtime_dir,
            repo_root=repo_root,
            write=args.write or True,
            bootstrap_samples=args.bootstrap_samples,
        )
        payload = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=args.write or True)
        payload["orchestrationRun"] = run_payload
        if args.view == "daily-todo":
            daily_todo = payload.get("dailyTodo") if isinstance(payload.get("dailyTodo"), dict) else {}
            daily_todo["orchestrationRun"] = run_payload
            return emit(daily_todo)
        if args.view == "daily-review":
            daily_review = payload.get("dailyReview") if isinstance(payload.get("dailyReview"), dict) else {}
            daily_review["orchestrationRun"] = run_payload
            return emit(daily_review)
        return emit(payload)
    if args.command == "daily-todo":
        payload = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=args.write)
        return emit(payload.get("dailyTodo") or {"ok": False, "error": "daily_todo_missing"})
    if args.command == "daily-review":
        payload = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=args.write)
        return emit(payload.get("dailyReview") or {"ok": False, "error": "daily_review_missing"})
    if args.command == "telegram-text":
        payload = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=args.write or args.refresh)
        content = daily_autopilot_v2_to_chinese_text(payload)
        result = {"ok": True, "text": content, "dailyAutopilotV2": payload}
        if args.send:
            result["telegramGateway"] = send_telegram(runtime_dir, "DAILY_AUTOPILOT_V2_REPORT", content)
        return emit(result)
    if args.command == "daily-todo-telegram-text":
        payload = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=args.write or args.refresh)
        daily_todo = payload.get("dailyTodo") if isinstance(payload.get("dailyTodo"), dict) else {}
        content = todo_text(daily_todo)
        result = {"ok": True, "text": content, "dailyTodo": daily_todo}
        if args.send:
            result["telegramGateway"] = send_telegram(runtime_dir, "DAILY_TODO_AGENT_REPORT", content)
        return emit(result)
    if args.command == "daily-review-telegram-text":
        payload = build_daily_autopilot_v2(runtime_dir, repo_root=repo_root, write=args.write or args.refresh)
        daily_review = payload.get("dailyReview") if isinstance(payload.get("dailyReview"), dict) else {}
        content = review_text(daily_review)
        result = {"ok": True, "text": content, "dailyReview": daily_review}
        if args.send:
            result["telegramGateway"] = send_telegram(runtime_dir, "DAILY_REVIEW_AGENT_REPORT", content)
        return emit(result)
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
