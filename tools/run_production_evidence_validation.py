#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from production_evidence_validation.burn_in import build_burn_in_report, load_latest_burn_in
from production_evidence_validation.report import build_report, load_latest, write_reports
from production_evidence_validation.rsi_lineage_closure import (
    build_rsi_lineage_closure,
    load_latest_rsi_lineage_closure,
)
from production_evidence_validation.telegram_text import build_telegram_text


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def runtime_dir_from_args(args: argparse.Namespace) -> Path:
    return Path(args.runtime_dir or Path.cwd() / "runtime").resolve()


def command_status(args: argparse.Namespace) -> int:
    runtime_dir = runtime_dir_from_args(args)
    report = load_latest(runtime_dir) if not args.refresh else None
    if report is None:
        report = build_report(runtime_dir)
        if args.write:
            write_reports(runtime_dir, report)
    emit({"ok": True, "runtimeDir": str(runtime_dir), "report": report})
    return 0


def command_build(args: argparse.Namespace) -> int:
    runtime_dir = runtime_dir_from_args(args)
    report = build_report(runtime_dir)
    paths = write_reports(runtime_dir, report) if args.write else {}
    emit({"ok": True, "runtimeDir": str(runtime_dir), "written": paths, "report": report})
    return 0


def command_telegram_text(args: argparse.Namespace) -> int:
    runtime_dir = runtime_dir_from_args(args)
    report = load_latest(runtime_dir) if not args.refresh else None
    if report is None:
        report = build_report(runtime_dir)
        if args.write or args.refresh:
            write_reports(runtime_dir, report)
    text = build_telegram_text(report)
    emit({"ok": True, "runtimeDir": str(runtime_dir), "text": text, "report": report})
    return 0


def command_burn_in(args: argparse.Namespace) -> int:
    runtime_dir = runtime_dir_from_args(args)
    report = load_latest_burn_in(runtime_dir) if not args.refresh and not args.write else None
    if report is None:
        report = build_burn_in_report(
            runtime_dir,
            write=args.write,
            window_hours=args.window_hours,
            sample_interval_minutes=args.sample_interval_minutes,
            max_stale_minutes=args.max_stale_minutes,
        )
    emit({"ok": True, "runtimeDir": str(runtime_dir), "report": report})
    return 0


def command_rsi_lineage_closure(args: argparse.Namespace) -> int:
    runtime_dir = runtime_dir_from_args(args)
    report = load_latest_rsi_lineage_closure(runtime_dir) if not args.refresh and not args.write else None
    if report is None:
        report = build_rsi_lineage_closure(runtime_dir, write=args.write)
    emit({"ok": True, "runtimeDir": str(runtime_dir), "report": report})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="P4-6 Production Evidence Validation")
    parser.add_argument("--runtime-dir", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--refresh", action="store_true")
    status.add_argument("--write", action="store_true")
    status.set_defaults(func=command_status)
    build = sub.add_parser("build")
    build.add_argument("--write", action="store_true")
    build.set_defaults(func=command_build)
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    text.add_argument("--write", action="store_true")
    text.set_defaults(func=command_telegram_text)
    burn_in = sub.add_parser("burn-in")
    burn_in.add_argument("--refresh", action="store_true")
    burn_in.add_argument("--write", action="store_true")
    burn_in.add_argument("--window-hours", type=int, default=72)
    burn_in.add_argument("--sample-interval-minutes", type=int, default=5)
    burn_in.add_argument("--max-stale-minutes", type=int, default=15)
    burn_in.set_defaults(func=command_burn_in)
    rsi = sub.add_parser("rsi-lineage-closure")
    rsi.add_argument("--refresh", action="store_true")
    rsi.add_argument("--write", action="store_true")
    rsi.set_defaults(func=command_rsi_lineage_closure)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
