from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

try:
    from tools.execution_feedback_producer.producer import build_feedback, load_latest, write_sample
    from tools.execution_feedback_producer.telegram_text import build_telegram_text
except ModuleNotFoundError:  # pragma: no cover
    from execution_feedback_producer.producer import build_feedback, load_latest, write_sample
    from execution_feedback_producer.telegram_text import build_telegram_text


def _runtime_dir(value: str | None) -> Path:
    return Path(value or os.environ.get("QG_RUNTIME_DIR") or "runtime")


def main() -> int:
    parser = argparse.ArgumentParser(description="QuantGod execution feedback producer")
    parser.add_argument("--runtime-dir", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sample = sub.add_parser("sample")
    sample.add_argument("--overwrite", action="store_true")
    build = sub.add_parser("build")
    build.add_argument("--write", action="store_true")
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    runtime = _runtime_dir(args.runtime_dir)
    if args.command == "sample":
        print(json.dumps(write_sample(runtime, overwrite=args.overwrite), ensure_ascii=False, indent=2))
        return 0
    if args.command == "build":
        report = build_feedback(runtime, write=args.write)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "telegram-text":
        report = build_feedback(runtime, write=True) if args.refresh else load_latest(runtime)
        if not report:
            report = build_feedback(runtime, write=False)
        print(build_telegram_text(report))
        return 0
    if args.command == "status":
        report = load_latest(runtime) or build_feedback(runtime, write=False)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
