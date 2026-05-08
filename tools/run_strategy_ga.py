#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from strategy_ga.generation_runner import build_ga_status, read_candidate, read_candidates, read_generations, run_generation
from strategy_ga.schema import BLOCKER_FILE, EVOLUTION_PATH_FILE, ga_dir
from strategy_ga.telegram_text import ga_to_chinese_text
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


def _load_json(path: Path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def send_telegram(runtime_dir: Path, text: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.telegram.local")
    return dispatch_text(runtime_dir, "strategy_ga", "GA_EVOLUTION_REPORT", "INFO", text, send=True)


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.usdjpy.local")
    parser = argparse.ArgumentParser(description="QuantGod Strategy JSON GA Evolution Trace")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--write", action="store_true")
    run = sub.add_parser("run-generation")
    run.add_argument("--write", action="store_true")
    run.add_argument("--force", action="store_true")
    sub.add_parser("generations")
    sub.add_parser("candidates")
    candidate = sub.add_parser("candidate")
    candidate.add_argument("--seed-id", required=True)
    sub.add_parser("evolution-path")
    sub.add_parser("blockers")
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    text.add_argument("--send", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)

    if args.command == "status":
        if args.write and not (ga_dir(runtime_dir) / "QuantGod_GAStatus.json").exists():
            return emit(run_generation(runtime_dir, write=True))
        return emit(build_ga_status(runtime_dir))
    if args.command == "run-generation":
        return emit(run_generation(runtime_dir, write=True if args.write else True, force=args.force))
    if args.command == "generations":
        return emit(read_generations(runtime_dir))
    if args.command == "candidates":
        return emit(read_candidates(runtime_dir))
    if args.command == "candidate":
        return emit(read_candidate(runtime_dir, args.seed_id))
    if args.command == "evolution-path":
        return emit(_load_json(ga_dir(runtime_dir) / EVOLUTION_PATH_FILE))
    if args.command == "blockers":
        return emit(_load_json(ga_dir(runtime_dir) / BLOCKER_FILE))
    if args.command == "telegram-text":
        payload = run_generation(runtime_dir, write=True) if args.refresh else build_ga_status(runtime_dir)
        content = ga_to_chinese_text(payload)
        result = {"ok": True, "text": content, "ga": payload}
        if args.send:
            result["telegramGateway"] = send_telegram(runtime_dir, content)
        return emit(result)
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
