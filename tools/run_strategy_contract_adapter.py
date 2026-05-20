#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from strategy_contract_adapter.builder import (
    build_rsi_opportunity_layer_audit,
    build_rsi_shadow_contract_observation,
    build_strategy_contract,
    read_strategy_contract_status,
)
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
    status.add_argument("--seed-id")
    status.add_argument("--family")
    status.add_argument("--frozen-rsi", action="store_true")
    build = sub.add_parser("build")
    build.add_argument("--seed-id")
    build.add_argument("--family")
    build.add_argument("--frozen-rsi", action="store_true")
    frozen = sub.add_parser("build-frozen-rsi")
    frozen.add_argument("--observe", action="store_true")
    observe = sub.add_parser("rsi-shadow-observation")
    observe.add_argument("--write", action="store_true")
    opportunity_audit = sub.add_parser("rsi-opportunity-layer-audit")
    opportunity_audit.add_argument("--write", action="store_true")
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    text.add_argument("--send", action="store_true")
    text.add_argument("--seed-id")
    text.add_argument("--family")
    text.add_argument("--frozen-rsi", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)

    if args.command == "status":
        if args.write:
            return emit(
                build_strategy_contract(
                    runtime_dir,
                    write=True,
                    forced_seed_id=args.seed_id,
                    forced_family=args.family,
                    force_frozen_rsi=args.frozen_rsi,
                )
            )
        return emit(read_strategy_contract_status(runtime_dir))
    if args.command == "build":
        return emit(
            build_strategy_contract(
                runtime_dir,
                write=True,
                forced_seed_id=args.seed_id,
                forced_family=args.family,
                force_frozen_rsi=args.frozen_rsi,
            )
        )
    if args.command == "build-frozen-rsi":
        payload = build_strategy_contract(runtime_dir, write=True, force_frozen_rsi=True)
        if args.observe:
            payload["rsiShadowContractObservation"] = build_rsi_shadow_contract_observation(runtime_dir, write=True)
        return emit(payload)
    if args.command == "rsi-shadow-observation":
        return emit(build_rsi_shadow_contract_observation(runtime_dir, write=args.write))
    if args.command == "rsi-opportunity-layer-audit":
        return emit(build_rsi_opportunity_layer_audit(runtime_dir, write=args.write))
    if args.command == "telegram-text":
        payload = (
            build_strategy_contract(
                runtime_dir,
                write=True,
                forced_seed_id=args.seed_id,
                forced_family=args.family,
                force_frozen_rsi=args.frozen_rsi,
            )
            if args.refresh
            else read_strategy_contract_status(runtime_dir)
        )
        content = contract_to_chinese_text(payload)
        result = {"ok": True, "text": content, "contractStatus": payload}
        if args.send:
            result["telegramGateway"] = send_telegram(runtime_dir, content)
        return emit(result)
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
