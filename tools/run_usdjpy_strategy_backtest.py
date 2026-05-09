#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from usdjpy_evidence_os.telegram_gateway import dispatch_text
from usdjpy_strategy_backtest.history_sync import build_history_production_status, sync_historical_klines
from usdjpy_strategy_backtest.quality import build_quality_report, write_quality_report
from usdjpy_strategy_backtest.report import build_sample, run_backtest, status
from usdjpy_strategy_backtest.telegram_text import backtest_to_chinese_text


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


def load_strategy(path: str | None) -> Dict[str, Any] | None:
    if not path:
        return None
    target = Path(path)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as exc:
        return {"schema": "invalid", "seedId": "LOAD_FAILED", "loadError": str(exc)}


def send_telegram(runtime_dir: Path, text: str) -> Dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.telegram.local")
    return dispatch_text(runtime_dir, "usdjpy_strategy_backtest", "USDJPY_STRATEGY_BACKTEST_REPORT", "INFO", text, send=True)


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.usdjpy.local")
    parser = argparse.ArgumentParser(description="QuantGod USDJPY Strategy JSON SQLite backtest")
    parser.add_argument("--runtime-dir", default=os.environ.get("QG_RUNTIME_DIR", str(root / "runtime")))
    parser.add_argument("--strategy-json", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("sample")
    sample.add_argument("--overwrite", action="store_true")
    sync = sub.add_parser("sync-klines")
    sync.add_argument("--months", type=int, default=int(os.environ.get("QG_USDJPY_HISTORY_MONTHS", "12")))
    sync.add_argument("--lookback-days", type=int, default=int(os.environ["QG_USDJPY_HISTORY_LOOKBACK_DAYS"]) if os.environ.get("QG_USDJPY_HISTORY_LOOKBACK_DAYS") else None)
    sync.add_argument("--timeframes", default=os.environ.get("QG_USDJPY_HISTORY_TIMEFRAMES", "M1,M5,M15,H1"))
    sync.add_argument("--symbol", default=os.environ.get("QG_USDJPY_MT5_SYMBOL", "USDJPYc"))
    sync.add_argument("--terminal-path", default=os.environ.get("QG_MT5_TERMINAL_PATH", ""))
    sync.add_argument("--full-refresh", action="store_true")
    sync.add_argument("--max-bars-per-timeframe", type=int, default=int(os.environ.get("QG_USDJPY_HISTORY_MAX_BARS", "700000")))
    sync.add_argument("--max-latest-lag-hours", type=float, default=float(os.environ.get("QG_USDJPY_HISTORY_MAX_LAG_HOURS", "96")))
    run = sub.add_parser("run")
    run.add_argument("--write", action="store_true")
    sub.add_parser("status")
    sub.add_parser("quality")
    prod = sub.add_parser("production-status")
    prod.add_argument("--lookback-days", type=int, default=int(os.environ["QG_USDJPY_HISTORY_LOOKBACK_DAYS"]) if os.environ.get("QG_USDJPY_HISTORY_LOOKBACK_DAYS") else None)
    prod.add_argument("--months", type=int, default=int(os.environ.get("QG_USDJPY_HISTORY_MONTHS", "12")))
    prod.add_argument("--max-latest-lag-hours", type=float, default=float(os.environ.get("QG_USDJPY_HISTORY_MAX_LAG_HOURS", "96")))
    text = sub.add_parser("telegram-text")
    text.add_argument("--refresh", action="store_true")
    text.add_argument("--send", action="store_true")
    args = parser.parse_args(argv)
    runtime_dir = Path(args.runtime_dir)

    if args.command == "sample":
        return emit(build_sample(runtime_dir, overwrite=args.overwrite))
    if args.command == "sync-klines":
        return emit(
            sync_historical_klines(
                runtime_dir,
                months=args.months,
                lookback_days=args.lookback_days,
                timeframes=args.timeframes.split(","),
                symbol=args.symbol,
                terminal_path=args.terminal_path,
                full_refresh=args.full_refresh,
                max_bars_per_timeframe=args.max_bars_per_timeframe,
                max_latest_lag_hours=args.max_latest_lag_hours,
            )
        )
    if args.command == "run":
        return emit(run_backtest(runtime_dir, load_strategy(args.strategy_json), write=True if args.write else True))
    if args.command == "status":
        return emit(status(runtime_dir))
    if args.command == "quality":
        current = status(runtime_dir)
        payload = build_quality_report(current, current.get("latestReport", {}))
        write_quality_report(runtime_dir, payload)
        return emit(payload)
    if args.command == "production-status":
        target_days = int(args.lookback_days or max(180, int(args.months) * 31))
        payload = build_history_production_status(
            runtime_dir,
            sync_report=status(runtime_dir).get("historySyncReport", {}),
            target_days=target_days,
            max_latest_lag_hours=args.max_latest_lag_hours,
        )
        return emit(payload)
    if args.command == "telegram-text":
        report = run_backtest(runtime_dir, load_strategy(args.strategy_json), write=True) if args.refresh else status(runtime_dir).get("latestReport", {})
        content = backtest_to_chinese_text(report)
        payload: Dict[str, Any] = {"ok": True, "text": content, "report": report}
        if args.send:
            payload["telegramGateway"] = send_telegram(runtime_dir, content)
        return emit(payload)
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
