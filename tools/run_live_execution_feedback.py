#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from tools.usdjpy_evidence_os.io_utils import load_json
    from tools.usdjpy_evidence_os.schema import execution_feedback_path, execution_feedback_public_path
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.io_utils import load_json
    from usdjpy_evidence_os.schema import execution_feedback_path, execution_feedback_public_path

from live_execution_feedback.report import build_live_execution_feedback_report
from live_execution_feedback.telegram_text import live_execution_feedback_to_chinese_text


def emit(payload) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="QuantGod live execution feedback hardening")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    parser.add_argument("command", nargs="?", choices=["status", "build", "telegram-text"], default="build")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)
    if args.command == "status":
        return emit(
            load_json(execution_feedback_public_path(runtime_dir))
            or load_json(execution_feedback_path(runtime_dir))
            or {"ok": True, "status": "WAITING_EXECUTION_FEEDBACK"}
        )
    report = build_live_execution_feedback_report(runtime_dir, write=args.write or args.command == "build")
    if args.command == "telegram-text":
        return emit({"ok": True, "text": live_execution_feedback_to_chinese_text(report), "report": report})
    return emit(report)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
