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

default_mt5_root() {
  printf '%s\n' "$HOME/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5"
}

default_mt5_files_dir() {
  printf '%s\n' "$(default_mt5_root)/MQL5/Files"
}

default_mt5_terminal_path() {
  printf '%s\n' "$(default_mt5_root)/terminal64.exe"
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

RUNTIME_DIR="$(resolve_runtime_dir)"
export QG_RUNTIME_DIR="${QG_RUNTIME_DIR:-$RUNTIME_DIR}"
export QG_MT5_FILES_DIR="${QG_MT5_FILES_DIR:-$RUNTIME_DIR}"
export QG_MT5_TERMINAL_PATH="${QG_MT5_TERMINAL_PATH:-$(default_mt5_terminal_path)}"
export QG_MT5_PYTHON_BIN="${QG_MT5_PYTHON_BIN:-${QG_PYTHON_BIN:-python3}}"
export QG_USDJPY_MT5_SYMBOL="${QG_USDJPY_MT5_SYMBOL:-USDJPYc}"
export QG_USDJPY_HISTORY_MONTHS="${QG_USDJPY_HISTORY_MONTHS:-12}"
export QG_USDJPY_HISTORY_TIMEFRAMES="${QG_USDJPY_HISTORY_TIMEFRAMES:-M1,M5,M15,H1}"
export QG_USDJPY_HISTORY_INTERVAL_SECONDS="${QG_USDJPY_HISTORY_INTERVAL_SECONDS:-3600}"
export QG_USDJPY_HISTORY_MAX_BARS="${QG_USDJPY_HISTORY_MAX_BARS:-700000}"
export QG_USDJPY_HISTORY_MAX_LAG_HOURS="${QG_USDJPY_HISTORY_MAX_LAG_HOURS:-96}"

MODE="--loop"
if [[ "${1:-}" == "--once" ]]; then
  MODE="--once"
  shift
elif [[ "${1:-}" == "--loop" ]]; then
  MODE="--loop"
  shift
fi

history_sync_command() {
  local command=(
    "$QG_MT5_PYTHON_BIN"
    tools/run_usdjpy_strategy_backtest.py
    --runtime-dir "$RUNTIME_DIR"
    sync-klines
    --months "$QG_USDJPY_HISTORY_MONTHS"
    --timeframes "$QG_USDJPY_HISTORY_TIMEFRAMES"
    --symbol "$QG_USDJPY_MT5_SYMBOL"
    --terminal-path "$QG_MT5_TERMINAL_PATH"
    --max-bars-per-timeframe "$QG_USDJPY_HISTORY_MAX_BARS"
    --max-latest-lag-hours "$QG_USDJPY_HISTORY_MAX_LAG_HOURS"
  )
  if [[ -n "${QG_USDJPY_HISTORY_LOOKBACK_DAYS:-}" ]]; then
    command+=(--lookback-days "$QG_USDJPY_HISTORY_LOOKBACK_DAYS")
  fi
  "${command[@]}"
}

run_once() {
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] USDJPY historical kline sync start"
  echo "runtimeDir=$RUNTIME_DIR"
  echo "mt5FilesDir=$QG_MT5_FILES_DIR"
  echo "mt5TerminalPath=$QG_MT5_TERMINAL_PATH"
  echo "mt5PythonBin=$QG_MT5_PYTHON_BIN"
  echo "months=$QG_USDJPY_HISTORY_MONTHS timeframes=$QG_USDJPY_HISTORY_TIMEFRAMES symbol=$QG_USDJPY_MT5_SYMBOL maxLatestLagHours=$QG_USDJPY_HISTORY_MAX_LAG_HOURS"
  history_sync_command || echo "USDJPY historical kline sync failed"
  "$QG_MT5_PYTHON_BIN" tools/run_usdjpy_strategy_backtest.py --runtime-dir "$RUNTIME_DIR" quality || echo "USDJPY strategy backtest quality refresh failed"
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] USDJPY historical kline sync complete"
}

if [[ "$MODE" == "--once" ]]; then
  run_once
  exit 0
fi

while true; do
  run_once
  sleep "$QG_USDJPY_HISTORY_INTERVAL_SECONDS"
done
