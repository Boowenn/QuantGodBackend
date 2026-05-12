#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

try:
    from tools.case_memory.report import build_case_memory_report, status
    from tools.case_memory.telegram_text import case_memory_to_chinese_text
except ModuleNotFoundError:  # pragma: no cover
    from case_memory.report import build_case_memory_report, status
    from case_memory.telegram_text import case_memory_to_chinese_text


def emit(payload) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="QuantGod P4-3 Case Memory strategy candidate runner")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    build = sub.add_parser("build")
    build.add_argument("--write", action="store_true")
    build.add_argument("--limit", type=int, default=8)
    sample = sub.add_parser("sample")
    sample.add_argument("--overwrite", action="store_true")
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)

    if args.command == "status":
        return emit(status(runtime_dir))
    if args.command == "sample":
        return emit(write_sample_runtime(runtime_dir, overwrite=args.overwrite))
    if args.command == "build":
        return emit(build_case_memory_report(runtime_dir, write=True, limit=args.limit))
    if args.command == "telegram-text":
        report = build_case_memory_report(runtime_dir, write=True) if args.refresh else status(runtime_dir)
        return emit({"ok": True, "text": case_memory_to_chinese_text(report), "report": report})
    return 1


def write_sample_runtime(runtime_dir: Path, *, overwrite: bool = False) -> dict:
    if overwrite and runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    replay_dir = runtime_dir / "replay" / "usdjpy"
    evidence_dir = runtime_dir / "evidence_os"
    parity_dir = runtime_dir / "parity"
    replay_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    parity_dir.mkdir(parents=True, exist_ok=True)
    (replay_dir / "QuantGod_USDJPYBarReplayReport.json").write_text(
        json.dumps(
            {
                "entryComparison": {
                    "variants": [
                        {"metrics": {"entryCountDelta": 2, "maxAdverseR": -0.4}},
                        {"metrics": {"entryCountDelta": 4, "maxAdverseR": -0.2}},
                    ]
                },
                "exitComparison": {
                    "variants": [
                        {"metrics": {"profitCaptureRatio": 0.2}},
                        {"metrics": {"profitCaptureRatio": 0.52}},
                    ]
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    feedback = {
        "metrics": {
            "rejectCount": 0,
            "avgAbsSlippagePips": 1.1,
            "avgLatencyMs": 420,
            "acceptedWithoutFillCount": 0,
            "policyMismatchCount": 0,
        },
        "caseMemoryTriggers": [],
        "recentFeedback": [],
    }
    (evidence_dir / "QuantGod_LiveExecutionQualityReport.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    parity = {
        "status": "PARITY_PASS",
        "promotionGate": {"status": "PASS", "promotionAllowed": True},
        "reasonZh": "sample parity pass",
    }
    (parity_dir / "QuantGod_StrategyParityReport.json").write_text(
        json.dumps(parity, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, "runtimeDir": str(runtime_dir), "sample": "P4_3_CASE_MEMORY"}


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
