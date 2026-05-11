#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from usdjpy_evidence_os.telegram_gateway import (
    SCHEDULED_REPORT_TOPICS,
    build_notification_event,
    collect_scheduled_events,
    dispatch_pending,
    enqueue_event,
    gateway_status,
)


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


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.local")
    load_env(root / ".env.usdjpy.local")
    load_env(root / ".env.auto.local")
    load_env(root / ".env.telegram.local")
    load_env(root / ".env.deepseek.local")
    parser = argparse.ArgumentParser(description="QuantGod independent Telegram Gateway")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    parser.add_argument("--repo-root", default=str(root))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("--source", default="manual_gateway_test")
    enqueue.add_argument("--topic", default="GATEWAY_TEST")
    enqueue.add_argument("--severity", default="INFO")
    enqueue.add_argument("--text", required=True)
    enqueue.add_argument("--dedupe-key")
    collect = sub.add_parser("collect")
    collect.add_argument("--refresh", action="store_true")
    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--send", action="store_true")
    dispatch.add_argument("--limit", type=int, default=8)
    run_once = sub.add_parser("run-once")
    run_once.add_argument("--refresh", action="store_true")
    run_once.add_argument("--send", action="store_true")
    run_once.add_argument("--limit", type=int, default=8)
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)
    repo_root = Path(args.repo_root)
    if args.command == "status":
        return emit(gateway_status(runtime_dir))
    if args.command == "enqueue":
        event = build_notification_event(args.source, args.topic, args.severity, args.text, dedupe_key=args.dedupe_key)
        return emit(enqueue_event(runtime_dir, event))
    if args.command == "collect":
        return emit(collect_scheduled_events(runtime_dir, repo_root=repo_root, refresh=args.refresh))
    if args.command == "dispatch":
        return emit(dispatch_pending(runtime_dir, send=args.send, limit=args.limit))
    if args.command == "run-once":
        collect_status = collect_scheduled_events(runtime_dir, repo_root=repo_root, refresh=args.refresh)
        if not args.send:
            collect_status["sendRequested"] = False
            collect_status["reasonZh"] = "Telegram Gateway 已完成报告收集；未请求真实发送，队列等待下一次 dispatch --send。"
            return emit(collect_status)
        dispatch_status = dispatch_pending(
            runtime_dir,
            send=True,
            limit=args.limit,
            allowed_topics=list(SCHEDULED_REPORT_TOPICS),
        )
        return emit({"ok": True, "collect": collect_status, "dispatch": dispatch_status})
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
