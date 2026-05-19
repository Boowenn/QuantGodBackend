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
export QG_AGENT_OPS_HEALTH_ENABLED="${QG_AGENT_OPS_HEALTH_ENABLED:-1}"
export QG_PRODUCTION_BURN_IN_ENABLED="${QG_PRODUCTION_BURN_IN_ENABLED:-1}"
export QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS="${QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS:-300}"
export QG_PRODUCTION_BURN_IN_SAMPLE_INTERVAL_MINUTES="${QG_PRODUCTION_BURN_IN_SAMPLE_INTERVAL_MINUTES:-5}"
export QG_PRODUCTION_BURN_IN_WINDOW_HOURS="${QG_PRODUCTION_BURN_IN_WINDOW_HOURS:-72}"
export QG_PRODUCTION_BURN_IN_MAX_STALE_MINUTES="${QG_PRODUCTION_BURN_IN_MAX_STALE_MINUTES:-15}"

PYTHON_BIN="${QG_PYTHON_BIN:-python3}"
INTERVAL_SECONDS="${QG_AGENT_V25_INTERVAL_SECONDS:-60}"
HEAVY_INTERVAL_SECONDS="${QG_AGENT_V25_HEAVY_INTERVAL_SECONDS:-1800}"
TELEGRAM_TIMEOUT_SECONDS="${QG_AGENT_V25_TELEGRAM_TIMEOUT_SECONDS:-20}"
SEND_TELEGRAM="${QG_AGENT_V25_SEND_TELEGRAM:-${QG_TELEGRAM_PUSH_ALLOWED:-0}}"
SCREEN_NAME="${QG_AGENT_V25_SCREEN:-quantgod-agent-v25}"
AUTOPILOT_COMMAND="${QG_AGENT_V25_AUTOPILOT_COMMAND:-build}"
case "$AUTOPILOT_COMMAND" in
  build|run-cycle) ;;
  *)
    echo "Unsupported QG_AGENT_V25_AUTOPILOT_COMMAND=$AUTOPILOT_COMMAND; falling back to build"
    AUTOPILOT_COMMAND="build"
    ;;
esac

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
HEAVY_LOCK_DIR="${QG_AGENT_V25_HEAVY_LOCK_DIR:-$RUNTIME_DIR/agent/QuantGod_AgentV25HeavyTasks.lock}"
HEAVY_STAMP_FILE="${QG_AGENT_V25_HEAVY_STAMP_FILE:-$RUNTIME_DIR/agent/QuantGod_AgentV25HeavyTasksLastRun.txt}"
HEAVY_STATUS_FILE="${QG_AGENT_V25_HEAVY_STATUS_FILE:-$RUNTIME_DIR/agent/QuantGod_AgentV25HeavyTasksStatus.json}"
HEAVY_LOG_FILE="${QG_AGENT_V25_HEAVY_LOG_FILE:-$REPO_ROOT/runtime/agent_v25_heavy_tasks.log}"

if ! [[ "$HEAVY_INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
  HEAVY_INTERVAL_SECONDS=1800
fi
if ! [[ "$TELEGRAM_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$TELEGRAM_TIMEOUT_SECONDS" -lt 1 ]]; then
  TELEGRAM_TIMEOUT_SECONDS=20
fi

MODE="--loop"
if [[ "${1:-}" == "--once" ]]; then
  MODE="--once"
  shift
elif [[ "${1:-}" == "--loop" ]]; then
  MODE="--loop"
  shift
fi

LOCK_DIR="${QG_AGENT_V25_LOCK_DIR:-$RUNTIME_DIR/agent/QuantGod_AgentV25Loop.lock}"
LOCK_OWNER=0

process_is_agent_loop() {
  local pid="$1"
  local command
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1 || return 1
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command" == *"run_mac_agent_v25_loop.sh"* ]]
}

release_loop_lock() {
  local holder=""
  [[ "$LOCK_OWNER" == "1" ]] || return 0
  holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [[ "$holder" == "$$" ]]; then
    rm -rf "$LOCK_DIR"
  fi
}

acquire_loop_lock() {
  local holder=""
  local holder_mode=""
  mkdir -p "$(dirname "$LOCK_DIR")"
  while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
    holder_mode="$(cat "$LOCK_DIR/mode" 2>/dev/null || true)"
    if process_is_agent_loop "$holder"; then
      echo "Agent v2.5 loop already running: pid=$holder mode=${holder_mode:-unknown} runtime=$RUNTIME_DIR"
      exit 0
    fi
    rm -rf "$LOCK_DIR"
  done
  LOCK_OWNER=1
  printf '%s\n' "$$" > "$LOCK_DIR/pid"
  printf '%s\n' "$MODE" > "$LOCK_DIR/mode"
  date -u '+%Y-%m-%dT%H:%M:%SZ' > "$LOCK_DIR/acquired_at"
  trap release_loop_lock EXIT INT TERM
}

write_loop_status() {
  local status="$1"
  local detail="$2"
  "$PYTHON_BIN" - "$RUNTIME_DIR" "$REPO_ROOT" "$status" "$detail" "$MODE" "$INTERVAL_SECONDS" "$SEND_TELEGRAM" "$SCREEN_NAME" "$$" "$TELEGRAM_TIMEOUT_SECONDS" <<'PY' || true
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
telegram_timeout_seconds = int(sys.argv[10])
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
    "telegramTimeoutSeconds": telegram_timeout_seconds,
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

run_with_timeout() {
  local timeout_seconds="$1"
  shift
  "$PYTHON_BIN" - "$timeout_seconds" "$@" <<'PY'
import subprocess
import sys

timeout_seconds = int(sys.argv[1])
command = sys.argv[2:]
try:
    completed = subprocess.run(command, timeout=timeout_seconds)
except subprocess.TimeoutExpired:
    print(
        f"Command timed out after {timeout_seconds}s: {' '.join(command)}",
        file=sys.stderr,
    )
    raise SystemExit(124)
raise SystemExit(completed.returncode)
PY
}

run_maintenance() {
  "$PYTHON_BIN" tools/run_mac_agent_v25_maintenance.py \
    --runtime-dir "$RUNTIME_DIR" \
    --repo-root "$REPO_ROOT" \
    --burn-in-window-hours "$QG_PRODUCTION_BURN_IN_WINDOW_HOURS" \
    --burn-in-sample-interval-minutes "$QG_PRODUCTION_BURN_IN_SAMPLE_INTERVAL_MINUTES" \
    --burn-in-max-stale-minutes "$QG_PRODUCTION_BURN_IN_MAX_STALE_MINUTES" \
    --burn-in-min-interval-seconds "$QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS" \
    --force-burn-in || echo "Agent v2.5 maintenance failed"
}

write_heavy_status() {
  local status="$1"
  local detail="$2"
  "$PYTHON_BIN" - "$HEAVY_STATUS_FILE" "$RUNTIME_DIR" "$status" "$detail" "$HEAVY_INTERVAL_SECONDS" <<'PY' || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

target = Path(sys.argv[1])
runtime_dir = sys.argv[2]
status = sys.argv[3]
detail = sys.argv[4]
interval_seconds = int(sys.argv[5])
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(
    json.dumps(
        {
            "schema": "quantgod.agent_v25_heavy_tasks_status.v1",
            "generatedAtIso": now,
            "status": status,
            "statusZh": "重任务运行中" if status == "RUNNING" else ("重任务待调度" if status == "WAITING" else "重任务已完成"),
            "detailZh": detail,
            "runtimeDir": runtime_dir,
            "intervalSeconds": interval_seconds,
            "safety": {
                "orderSendAllowed": False,
                "closeAllowed": False,
                "cancelAllowed": False,
                "livePresetMutationAllowed": False,
                "telegramCommandsAllowed": False,
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
}

heavy_task_age_seconds() {
  "$PYTHON_BIN" - "$HEAVY_STAMP_FILE" <<'PY' || printf '999999\n'
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print(999999)
else:
    print(int(max(0, time.time() - path.stat().st_mtime)))
PY
}

heavy_task_running() {
  local holder=""
  holder="$(cat "$HEAVY_LOCK_DIR/pid" 2>/dev/null || true)"
  [[ "$holder" =~ ^[0-9]+$ ]] && kill -0 "$holder" >/dev/null 2>&1
}

acquire_heavy_lock() {
  local holder=""
  mkdir -p "$(dirname "$HEAVY_LOCK_DIR")"
  if ! mkdir "$HEAVY_LOCK_DIR" 2>/dev/null; then
    if heavy_task_running; then
      holder="$(cat "$HEAVY_LOCK_DIR/pid" 2>/dev/null || true)"
      write_heavy_status "RUNNING" "Daily Autopilot/GA/evidence_os 重任务仍在后台运行，pid=${holder:-unknown}。"
      return 1
    fi
    rm -rf "$HEAVY_LOCK_DIR"
    mkdir "$HEAVY_LOCK_DIR" 2>/dev/null || return 1
  fi
  printf '%s\n' "${BASHPID:-$$}" > "$HEAVY_LOCK_DIR/pid"
  date -u '+%Y-%m-%dT%H:%M:%SZ' > "$HEAVY_LOCK_DIR/acquired_at"
  return 0
}

release_heavy_lock() {
  rm -rf "$HEAVY_LOCK_DIR"
}

run_heavy_tasks() {
  acquire_heavy_lock || return 0
  mkdir -p "$(dirname "$HEAVY_STAMP_FILE")"
  date -u '+%Y-%m-%dT%H:%M:%SZ' > "$HEAVY_STAMP_FILE"
  write_heavy_status "RUNNING" "Strategy Lab/Polymarket readonly cycle/Daily Autopilot/GA/evidence_os 重任务独立后台运行；快控制环不会等待它完成。"
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] QuantGod Agent v2.5 heavy tasks start"

  "$PYTHON_BIN" tools/run_usdjpy_strategy_lab.py \
    --runtime-dir "$RUNTIME_DIR" \
    build \
    --write || echo "USDJPY strategy lab build failed"

  "$PYTHON_BIN" tools/run_usdjpy_strategy_lab.py \
    --runtime-dir "$RUNTIME_DIR" \
    dry-run \
    --write || echo "USDJPY strategy lab dry-run failed"

  QG_DASHBOARD_FILES_DIR="${QG_POLYMARKET_HEAVY_DASHBOARD_DIR:-$RUNTIME_DIR}" \
    bash tools/run_mac_polymarket_readonly_cycle.sh || echo "Polymarket readonly cycle failed"

  "$PYTHON_BIN" tools/run_daily_autopilot_v2.py \
    --runtime-dir "$RUNTIME_DIR" \
    --repo-root "$REPO_ROOT" \
    "$AUTOPILOT_COMMAND" \
    --write || echo "Daily Autopilot v2.5 $AUTOPILOT_COMMAND failed"

  run_maintenance
  date -u '+%Y-%m-%dT%H:%M:%SZ' > "$HEAVY_STAMP_FILE"
  write_heavy_status "COMPLETED" "Strategy Lab/Polymarket readonly cycle/Daily Autopilot/GA/evidence_os 重任务已完成或记录为可重试；快控制环继续独立刷新。"
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] QuantGod Agent v2.5 heavy tasks complete"
  release_heavy_lock
}

maybe_start_heavy_tasks() {
  local age
  if heavy_task_running; then
    write_heavy_status "RUNNING" "Strategy Lab/Polymarket readonly cycle/Daily Autopilot/GA/evidence_os 重任务仍在后台运行；本轮快控制环跳过等待。"
    return 0
  fi
  age="$(heavy_task_age_seconds)"
  if ! [[ "$age" =~ ^[0-9]+$ ]]; then
    age=999999
  fi
  if [[ "$age" -lt "$HEAVY_INTERVAL_SECONDS" ]]; then
    write_heavy_status "WAITING" "距离上次 Strategy Lab/Polymarket readonly cycle/Daily Autopilot/GA/evidence_os 重任务 ${age}s，未达到 ${HEAVY_INTERVAL_SECONDS}s；本轮只跑快控制环。"
    return 0
  fi
  mkdir -p "$(dirname "$HEAVY_LOG_FILE")"
  if [[ "$MODE" == "--loop" ]]; then
    ( run_heavy_tasks ) >> "$HEAVY_LOG_FILE" 2>&1 &
    echo "Heavy Agent tasks launched in background: log=$HEAVY_LOG_FILE"
  else
    run_heavy_tasks
  fi
}

acquire_loop_lock

run_once() {
  write_loop_status "RUNNING" "Agent v2.5 快控制环开始执行。"
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] QuantGod Agent v2.5 fast cycle start"

  "$PYTHON_BIN" tools/run_automation_chain.py \
    --runtime-dir "$RUNTIME_DIR" \
    --symbols USDJPYc \
    once || echo "automation-chain cycle failed"

  "$PYTHON_BIN" tools/run_usdjpy_live_loop.py \
    --runtime-dir "$RUNTIME_DIR" \
    --repo-root "$REPO_ROOT" \
    once \
    --write || echo "USDJPY live loop failed"

  if [[ "$SEND_TELEGRAM" == "1" ]]; then
    run_with_timeout "$TELEGRAM_TIMEOUT_SECONDS" "$PYTHON_BIN" tools/run_telegram_gateway.py \
      --runtime-dir "$RUNTIME_DIR" \
      --repo-root "$REPO_ROOT" \
      run-once \
      --refresh \
      --send \
      --limit 8 || echo "Telegram Gateway queued dispatch failed or timed out"
  else
    run_with_timeout "$TELEGRAM_TIMEOUT_SECONDS" "$PYTHON_BIN" tools/run_telegram_gateway.py \
      --runtime-dir "$RUNTIME_DIR" \
      --repo-root "$REPO_ROOT" \
      collect \
      --refresh || echo "Telegram Gateway scheduled collect failed or timed out"
  fi

  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] QuantGod Agent v2.5 fast cycle complete"
  write_loop_status "COMPLETED" "Agent v2.5 快控制环已完成；Strategy Lab/Polymarket readonly cycle/Daily Autopilot/GA/evidence_os 重任务低频独立调度。"
  maybe_start_heavy_tasks
}

if [[ "$MODE" == "--once" ]]; then
  run_once
  exit 0
fi

while true; do
  run_once
  sleep "$INTERVAL_SECONDS"
done
