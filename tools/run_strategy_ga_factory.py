#!/usr/bin/env python3
"""CLI entrypoint for Strategy JSON GA Factory archive builds."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

try:
    from tools.strategy_ga.generation_runner import run_generation
    from tools.strategy_ga_factory.factory_runner import (
        build_factory_state,
        read_factory_state,
    )
    from tools.strategy_ga_factory.telegram_text import ga_factory_to_chinese_text
except ModuleNotFoundError:  # pragma: no cover
    from strategy_ga.generation_runner import run_generation
    from strategy_ga_factory.factory_runner import (
        build_factory_state,
        read_factory_state,
    )
    from strategy_ga_factory.telegram_text import ga_factory_to_chinese_text


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="QuantGod P4-4 Strategy JSON GA Factory")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    build = sub.add_parser("build")
    build.add_argument("--write", action="store_true")
    sample = sub.add_parser("sample")
    sample.add_argument("--overwrite", action="store_true")
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)

    if args.command == "status":
        return emit(read_factory_state(runtime_dir))
    if args.command == "sample":
        return emit(write_sample_runtime(runtime_dir, overwrite=args.overwrite))
    if args.command == "build":
        return emit(build_factory_state(runtime_dir, write=True))
    if args.command == "telegram-text":
        state = build_factory_state(runtime_dir, write=True) if args.refresh else read_factory_state(runtime_dir)
        return emit({"ok": True, "text": ga_factory_to_chinese_text(state), "state": state})
    return 1


def write_sample_runtime(runtime_dir: Path, *, overwrite: bool = False) -> dict:
    if overwrite and runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    generation = run_generation(runtime_dir, write=True, force=True)
    state = build_factory_state(runtime_dir, write=True)
    return {
        "ok": True,
        "sample": "P4_4_GA_FACTORY",
        "generationId": generation.get("generation", {}).get("generationId"),
        "candidateCount": state.get("candidateCount", 0),
        "eliteCount": state.get("eliteCount", 0),
        "runtimeDir": str(runtime_dir),
    }


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
