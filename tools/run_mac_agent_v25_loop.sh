#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

load_env_file() {
  local env_file="$1"
  local line key
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#$'\xef\xbb\xbf'}"
    line="${line#export }"
    [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue
    key="${line%%=*}"
    [[ -n "${!key+x}" ]] && continue
    export "$line"
  done < "$env_file"
}

load_env_file "$REPO_ROOT/.env.local"
load_env_file "$REPO_ROOT/.env.usdjpy.local"
load_env_file "$REPO_ROOT/.env.auto.local"
load_env_file "$REPO_ROOT/.env.telegram.local"
load_env_file "$REPO_ROOT/.env.deepseek.local"

export QG_FOCUS_SYMBOL="${QG_FOCUS_SYMBOL:-USDJPYc}"
export QG_ALLOWED_SYMBOLS="${QG_ALLOWED_SYMBOLS:-USDJPYc}"
export QG_DISABLE_NON_FOCUS_SYMBOLS="${QG_DISABLE_NON_FOCUS_SYMBOLS:-1}"
export QG_AUTOMATION_SYMBOLS="${QG_AUTOMATION_SYMBOLS:-USDJPYc}"
export QG_MT5_AI_MONITOR_SYMBOLS="${QG_MT5_AI_MONITOR_SYMBOLS:-USDJPYc}"
export QG_ACCOUNT_MODE="${QG_ACCOUNT_MODE:-cent}"
export QG_ACCOUNT_CURRENCY_UNIT="${QG_ACCOUNT_CURRENCY_UNIT:-USC}"
export QG_CENT_ACCOUNT_ACCELERATION="${QG_CENT_ACCOUNT_ACCELERATION:-1}"
export QG_TELEGRAM_COMMANDS_ALLOWED="${QG_TELEGRAM_COMMANDS_ALLOWED:-0}"

PYTHON_BIN="${QG_PYTHON_BIN:-python3}"
INTERVAL_SECONDS="${QG_AGENT_V25_INTERVAL_SECONDS:-300}"
SEND_TELEGRAM="${QG_AGENT_V25_SEND_TELEGRAM:-${QG_TELEGRAM_PUSH_ALLOWED:-0}}"
SCREEN_NAME="${QG_AGENT_V25_SCREEN:-quantgod-agent-v25}"

default_mt5_files_dir() {
  printf '%s\n' "$HOME/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/MQL5/Files"
}

resolve_runtime_dir() {
  local mt5_files
  mt5_files="$(default_mt5_files_dir)"
  if [[ -n "${QG_RUNTIME_DIR:-}" ]]; then
    printf '%s\n' "$QG_RUNTIME_DIR"
  elif [[ -n "${QG_MT5_FILES_DIR:-}" ]]; then
    printf '%s\n' "$QG_MT5_FILES_DIR"
  elif [[ -d "$mt5_files" ]]; then
    printf '%s\n' "$mt5_files"
  else
    printf '%s\n' "$REPO_ROOT/runtime"
  fi
}

RUNTIME_DIR="$(resolve_runtime_dir)"
export QG_RUNTIME_DIR="${QG_RUNTIME_DIR:-$RUNTIME_DIR}"
export QG_MT5_FILES_DIR="${QG_MT5_FILES_DIR:-$RUNTIME_DIR}"

write_loop_status() {
  local status="$1"
  local detail="$2"
  "$PYTHON_BIN" - "$RUNTIME_DIR" "$REPO_ROOT" "$status" "$detail" "$MODE" "$INTERVAL_SECONDS" "$SEND_TELEGRAM" "$SCREEN_NAME" "$$" <<'PY' || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

runtime_dir = Path(sys.argv[1])
repo_root = sys.argv[2]
status = sys.argv[3]
detail = sys.argv[4]
mode = sys.argv[5]
interval_seconds = int(sys.argv[6])
send_telegram = sys.argv[7] == "1"
screen_name = sys.argv[8]
pid = int(sys.argv[9])
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
payload = {
    "schema": "quantgod.agent_v25_loop_status.v1",
    "generatedAtIso": now,
    "lastHeartbeatAtIso": now,
    "status": status,
    "statusZh": "后台循环运行中" if status in {"RUNNING", "COMPLETED"} else "后台循环需要观察",
    "detailZh": detail,
    "mode": mode.lstrip("-"),
    "pid": pid,
    "screenName": screen_name,
    "runtimeDir": str(runtime_dir),
    "repoRoot": repo_root,
    "intervalSeconds": interval_seconds,
    "sendTelegram": send_telegram,
    "pushOnly": True,
    "commandsAllowed": False,
    "safety": {
        "orderSendAllowed": False,
        "closeAllowed": False,
        "cancelAllowed": False,
        "livePresetMutationAllowed": False,
        "telegramCommandsAllowed": False,
    },
}
target = runtime_dir / "agent" / "QuantGod_AgentV25LoopStatus.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

MODE="--loop"
if [[ "${1:-}" == "--once" ]]; then
  MODE="--once"
  shift
elif [[ "${1:-}" == "--loop" ]]; then
  MODE="--loop"
  shift
fi

run_once() {
  write_loop_status "RUNNING" "Agent v2.5 后台循环开始执行。"
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] QuantGod Agent v2.5 cycle start"

  "$PYTHON_BIN" tools/run_automation_chain.py \
    --runtime-dir "$RUNTIME_DIR" \
    --symbols USDJPYc \
    once || echo "automation-chain cycle failed"

  "$PYTHON_BIN" tools/run_usdjpy_strategy_lab.py \
    --runtime-dir "$RUNTIME_DIR" \
    build \
    --write || echo "USDJPY strategy lab build failed"

  "$PYTHON_BIN" tools/run_usdjpy_strategy_lab.py \
    --runtime-dir "$RUNTIME_DIR" \
    dry-run \
    --write || echo "USDJPY strategy lab dry-run failed"

  "$PYTHON_BIN" tools/run_usdjpy_live_loop.py \
    --runtime-dir "$RUNTIME_DIR" \
    --repo-root "$REPO_ROOT" \
    once \
    --write || echo "USDJPY live loop failed"

  "$PYTHON_BIN" tools/build_polymarket_retune_planner.py \
    --runtime-dir "$RUNTIME_DIR" \
    --dashboard-dir "$REPO_ROOT/Dashboard" || echo "Polymarket shadow retune planner failed"

  "$PYTHON_BIN" tools/run_daily_autopilot_v2.py \
    --runtime-dir "$RUNTIME_DIR" \
    --repo-root "$REPO_ROOT" \
    build \
    --write || echo "Daily Autopilot v2.5 build failed"

  if [[ "$SEND_TELEGRAM" == "1" ]]; then
    "$PYTHON_BIN" tools/run_telegram_gateway.py \
      --runtime-dir "$RUNTIME_DIR" \
      --repo-root "$REPO_ROOT" \
      run-once \
      --refresh \
      --send \
      --limit 8 || echo "Telegram Gateway queued dispatch failed"
  else
    "$PYTHON_BIN" tools/run_telegram_gateway.py \
      --runtime-dir "$RUNTIME_DIR" \
      --repo-root "$REPO_ROOT" \
      collect \
      --refresh || echo "Telegram Gateway scheduled collect failed"
  fi

  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] QuantGod Agent v2.5 cycle complete"
  write_loop_status "COMPLETED" "Agent v2.5 后台循环已完成一轮，等待下一次调度。"
}

if [[ "$MODE" == "--once" ]]; then
  run_once
  exit 0
fi

while true; do
  run_once
  sleep "$INTERVAL_SECONDS"
done
