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
export QG_TELEGRAM_COMMANDS_ALLOWED="${QG_TELEGRAM_COMMANDS_ALLOWED:-0}"
export QG_AGENT_V25_SEND_TELEGRAM="${QG_AGENT_V25_SEND_TELEGRAM:-${QG_TELEGRAM_PUSH_ALLOWED:-0}}"
export QG_AGENT_OPS_HEALTH_ENABLED="${QG_AGENT_OPS_HEALTH_ENABLED:-1}"
export QG_PRODUCTION_BURN_IN_ENABLED="${QG_PRODUCTION_BURN_IN_ENABLED:-1}"
export QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS="${QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS:-300}"
export QG_PRODUCTION_BURN_IN_SAMPLE_INTERVAL_MINUTES="${QG_PRODUCTION_BURN_IN_SAMPLE_INTERVAL_MINUTES:-5}"
export QG_PRODUCTION_BURN_IN_WINDOW_HOURS="${QG_PRODUCTION_BURN_IN_WINDOW_HOURS:-72}"
export QG_PRODUCTION_BURN_IN_MAX_STALE_MINUTES="${QG_PRODUCTION_BURN_IN_MAX_STALE_MINUTES:-15}"

PYTHON_BIN="${QG_PYTHON_BIN:-python3}"
SCREEN_NAME="${QG_AGENT_V25_SCREEN:-quantgod-agent-v25}"
INTERVAL_SECONDS="${QG_AGENT_V25_INTERVAL_SECONDS:-60}"
STALE_SECONDS="${QG_AGENT_V25_STALE_SECONDS:-$((INTERVAL_SECONDS * 4))}"
if [[ "$STALE_SECONDS" -lt 900 ]]; then
  STALE_SECONDS=900
fi
SUPERVISOR_INTERVAL_SECONDS="${QG_AGENT_V25_SUPERVISOR_INTERVAL_SECONDS:-60}"
MODE="${1:---once}"
if [[ "$MODE" == "--loop" || "$MODE" == "--once" ]]; then
  shift || true
else
  MODE="--once"
fi

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

STATUS_FILE="$RUNTIME_DIR/agent/QuantGod_AgentV25LoopStatus.json"
SUPERVISOR_FILE="$RUNTIME_DIR/agent/QuantGod_AgentV25SupervisorStatus.json"
LOCK_DIR="${QG_AGENT_V25_LOCK_DIR:-$RUNTIME_DIR/agent/QuantGod_AgentV25Loop.lock}"
MAINTENANCE_LOCK_DIR="${QG_AGENT_V25_MAINTENANCE_LOCK_DIR:-$RUNTIME_DIR/agent/QuantGod_AgentV25Maintenance.lock}"
LOG_FILE="$REPO_ROOT/runtime/agent_v25_screen.log"
RUNTIME_LOG_ROOT="${QG_RUNTIME_LOG_ROOT:-$REPO_ROOT/runtime}"

maintain_runtime_logs() {
  "$PYTHON_BIN" "$REPO_ROOT/tools/maintain_runtime_logs.py" \
    --runtime-root "$RUNTIME_LOG_ROOT" >/dev/null 2>&1 || true
}

refresh_agent_health_and_burn_in() {
  "$PYTHON_BIN" "$REPO_ROOT/tools/run_mac_agent_v25_maintenance.py" \
    --runtime-dir "$RUNTIME_DIR" \
    --repo-root "$REPO_ROOT" \
    --burn-in-window-hours "$QG_PRODUCTION_BURN_IN_WINDOW_HOURS" \
    --burn-in-sample-interval-minutes "$QG_PRODUCTION_BURN_IN_SAMPLE_INTERVAL_MINUTES" \
    --burn-in-max-stale-minutes "$QG_PRODUCTION_BURN_IN_MAX_STALE_MINUTES" \
    --burn-in-min-interval-seconds "$QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS" >/dev/null 2>&1 || true
}

refresh_agent_health_and_burn_in_async() {
  local holder=""
  mkdir -p "$(dirname "$MAINTENANCE_LOCK_DIR")"
  if ! mkdir "$MAINTENANCE_LOCK_DIR" 2>/dev/null; then
    holder="$(cat "$MAINTENANCE_LOCK_DIR/pid" 2>/dev/null || true)"
    if [[ "$holder" =~ ^[0-9]+$ ]] && kill -0 "$holder" >/dev/null 2>&1; then
      return 0
    fi
    rm -rf "$MAINTENANCE_LOCK_DIR"
    mkdir "$MAINTENANCE_LOCK_DIR" 2>/dev/null || return 0
  fi
  (
    printf '%s\n' "${BASHPID:-$$}" > "$MAINTENANCE_LOCK_DIR/pid"
    date -u '+%Y-%m-%dT%H:%M:%SZ' > "$MAINTENANCE_LOCK_DIR/acquired_at"
    refresh_agent_health_and_burn_in
    rm -rf "$MAINTENANCE_LOCK_DIR"
  ) &
}

screen_running() {
  command -v screen >/dev/null 2>&1 || return 1
  screen -ls 2>/dev/null | grep -Eq "[[:space:]][0-9]+\\.${SCREEN_NAME}[[:space:]]"
}

matching_screen_sessions() {
  command -v screen >/dev/null 2>&1 || return 0
  { screen -ls 2>/dev/null || true; } | awk -v name="$SCREEN_NAME" '
    $1 ~ "^[0-9]+\\." name "$" { print $1 }
  '
}

stop_orphan_lock_holder() {
  local holder=""
  local command=""
  holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  [[ "$holder" =~ ^[0-9]+$ ]] || return 0
  command="$(ps -p "$holder" -o command= 2>/dev/null || true)"
  [[ "$command" == *"run_mac_agent_v25_loop.sh"* ]] || return 0
  kill "$holder" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "$holder" >/dev/null 2>&1; then
    kill -9 "$holder" >/dev/null 2>&1 || true
  fi
  rm -rf "$LOCK_DIR"
}

status_age_seconds() {
  "$PYTHON_BIN" - "$STATUS_FILE" <<'PY' || printf '999999\n'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print(999999)
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = str(payload.get("lastHeartbeatAtIso") or payload.get("generatedAtIso") or "")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    print(int(max(0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())))
except Exception:
    print(999999)
PY
}

write_supervisor_status() {
  local action="$1"
  local reason="$2"
  local age="$3"
  "$PYTHON_BIN" - "$SUPERVISOR_FILE" "$RUNTIME_DIR" "$action" "$reason" "$age" "$SCREEN_NAME" "$STALE_SECONDS" <<'PY' || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

target = Path(sys.argv[1])
runtime_dir = sys.argv[2]
action = sys.argv[3]
reason = sys.argv[4]
age = int(sys.argv[5])
screen_name = sys.argv[6]
stale_seconds = int(sys.argv[7])
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(
    json.dumps(
        {
            "schema": "quantgod.agent_v25_supervisor_status.v1",
            "generatedAtIso": now,
            "action": action,
            "reasonZh": reason,
            "runtimeDir": runtime_dir,
            "screenName": screen_name,
            "heartbeatAgeSeconds": age,
            "staleSeconds": stale_seconds,
            "commandsAllowed": False,
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

restart_loop() {
  mkdir -p "$(dirname "$LOG_FILE")"
  if command -v screen >/dev/null 2>&1; then
    local session
    while IFS= read -r session; do
      [[ -n "$session" ]] || continue
      screen -S "$session" -X quit >/dev/null 2>&1 || true
    done < <(matching_screen_sessions)
    stop_orphan_lock_holder
    screen -dmS "$SCREEN_NAME" /bin/zsh -lc "cd '$REPO_ROOT' && exec bash tools/run_mac_agent_v25_loop.sh --loop >> '$LOG_FILE' 2>&1"
  else
    stop_orphan_lock_holder
    /bin/zsh -lc "cd '$REPO_ROOT' && exec bash tools/run_mac_agent_v25_loop.sh --loop >> '$LOG_FILE' 2>&1" &
  fi
}

ensure_once() {
  local age reason session_count
  maintain_runtime_logs
  age="$(status_age_seconds)"
  session_count="$(matching_screen_sessions | wc -l | tr -d ' ')"
  if [[ "$session_count" == "1" && "$age" -le "$STALE_SECONDS" ]]; then
    write_supervisor_status "NOOP" "Agent v2.5 后台循环在线，心跳新鲜。" "$age"
    echo "Agent v2.5 loop is healthy: screen=$SCREEN_NAME heartbeatAge=${age}s runtime=$RUNTIME_DIR"
    refresh_agent_health_and_burn_in_async
    return 0
  fi

  if [[ "$session_count" -gt 1 ]]; then
    reason="Agent v2.5 后台循环出现重复 screen，已自动清理并只保留一个。"
  elif [[ "$session_count" == "1" ]]; then
    reason="Agent v2.5 后台循环心跳过旧，已自动重启。"
  else
    reason="Agent v2.5 后台循环 screen 不存在，已自动拉起。"
  fi
  restart_loop
  write_supervisor_status "RESTARTED" "$reason" "$age"
  echo "$reason screen=$SCREEN_NAME previousHeartbeatAge=${age}s runtime=$RUNTIME_DIR"
  refresh_agent_health_and_burn_in_async
}

if [[ "$MODE" == "--loop" ]]; then
  while true; do
    ensure_once || true
    sleep "$SUPERVISOR_INTERVAL_SECONDS"
  done
fi

ensure_once
