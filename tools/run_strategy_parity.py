#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from strategy_parity.data_loader import load_existing_parity
from strategy_parity.report import build_strategy_parity_report
from strategy_parity.telegram_text import strategy_parity_to_chinese_text


def emit(payload) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="QuantGod Strategy / Replay / EA parity harness")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    parser.add_argument("command", nargs="?", choices=["status", "build", "telegram-text"], default="build")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)
    if args.command == "status":
        return emit(load_existing_parity(runtime_dir) or {"ok": True, "status": "WAITING_PARITY_RUN"})
    report = build_strategy_parity_report(runtime_dir, write=args.write or args.command == "build")
    if args.command == "telegram-text":
        return emit({"ok": True, "text": strategy_parity_to_chinese_text(report), "report": report})
    return emit(report)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
