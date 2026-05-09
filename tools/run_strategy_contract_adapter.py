#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from strategy_contract_adapter.builder import build_strategy_contract, read_strategy_contract_status
from strategy_contract_adapter.telegram_text import contract_to_chinese_text
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


def emit(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def send_telegram(runtime_dir: Path, text: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.telegram.local")
    return dispatch_text(runtime_dir, "strategy_contract_adapter", "STRATEGY_JSON_EA_CONTRACT", "INFO", text, send=True)


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.usdjpy.local")
    parser = argparse.ArgumentParser(description="QuantGod Strategy JSON to MQL5 EA read-only contract adapter")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--write", action="store_true")
    sub.add_parser("build")
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    text.add_argument("--send", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)

    if args.command == "status":
        if args.write:
            return emit(build_strategy_contract(runtime_dir, write=True))
        return emit(read_strategy_contract_status(runtime_dir))
    if args.command == "build":
        return emit(build_strategy_contract(runtime_dir, write=True))
    if args.command == "telegram-text":
        payload = build_strategy_contract(runtime_dir, write=True) if args.refresh else read_strategy_contract_status(runtime_dir)
        content = contract_to_chinese_text(payload)
        result = {"ok": True, "text": content, "contractStatus": payload}
        if args.send:
            result["telegramGateway"] = send_telegram(runtime_dir, content)
        return emit(result)
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())

