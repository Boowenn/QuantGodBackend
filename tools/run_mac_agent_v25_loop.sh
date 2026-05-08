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
SEND_TELEGRAM="${QG_AGENT_V25_SEND_TELEGRAM:-0}"

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

MODE="--loop"
if [[ "${1:-}" == "--once" ]]; then
  MODE="--once"
  shift
elif [[ "${1:-}" == "--loop" ]]; then
  MODE="--loop"
  shift
fi

run_once() {
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

  "$PYTHON_BIN" tools/run_daily_autopilot_v2.py \
    --runtime-dir "$RUNTIME_DIR" \
    --repo-root "$REPO_ROOT" \
    build \
    --write || echo "Daily Autopilot v2.5 build failed"

  if [[ "$SEND_TELEGRAM" == "1" ]]; then
    "$PYTHON_BIN" tools/run_daily_autopilot_v2.py \
      --runtime-dir "$RUNTIME_DIR" \
      --repo-root "$REPO_ROOT" \
      telegram-text \
      --refresh \
      --write \
      --send || echo "Daily Autopilot v2.5 Telegram push failed"
  fi

  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] QuantGod Agent v2.5 cycle complete"
}

if [[ "$MODE" == "--once" ]]; then
  run_once
  exit 0
fi

while true; do
  run_once
  sleep "$INTERVAL_SECONDS"
done
