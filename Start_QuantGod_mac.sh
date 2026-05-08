#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

load_env_file() {
  local env_file="$1"
  local line
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#$'\xef\xbb\xbf'}"
    line="${line#export }"
    [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue
    export "$line"
  done < "$env_file"
}

is_import_snapshot_dir() {
  local candidate="$1"
  [[ "$candidate" == *"runtime/mac_import/mt5_files_snapshot"* ]]
}

patch_ini_key() {
  local file="$1"
  local key="$2"
  local value="$3"
  if grep -q "^${key}=" "$file"; then
    perl -0pi -e "s/^\\Q${key}\\E=.*/${key}=${value}/mg" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

start_screen() {
  local name="$1"
  local log_file="$2"
  local command="$3"
  mkdir -p "$(dirname "$log_file")"
  : > "$log_file"
  if command -v screen >/dev/null 2>&1; then
    screen -S "$name" -X quit >/dev/null 2>&1 || true
    screen -dmS "$name" /bin/zsh -lc "$command >> '$log_file' 2>&1"
    echo "Started screen: $name"
  else
    /bin/zsh -lc "$command >> '$log_file' 2>&1" &
    echo "Started background process for $name. Log: $log_file"
  fi
}

quit_screen() {
  local name="$1"
  command -v screen >/dev/null 2>&1 || return 0
  screen -S "$name" -X quit >/dev/null 2>&1 || true
}

load_env_file "$SCRIPT_DIR/.env.local"
load_env_file "$SCRIPT_DIR/.env.usdjpy.local"
load_env_file "$SCRIPT_DIR/.env.auto.local"
load_env_file "$SCRIPT_DIR/.env.telegram.local"
load_env_file "$SCRIPT_DIR/.env.deepseek.local"

RUNTIME_CONFIGURED=0
if [[ -n "${QG_RUNTIME_DIR:-}" || -n "${QG_MT5_FILES_DIR:-}" ]]; then
  RUNTIME_CONFIGURED=1
fi

export QG_DASHBOARD_HOST="${QG_DASHBOARD_HOST:-127.0.0.1}"
export QG_DASHBOARD_PORT="${QG_DASHBOARD_PORT:-8080}"
export QG_FRONTEND_HOST="${QG_FRONTEND_HOST:-127.0.0.1}"
export QG_FRONTEND_PORT="${QG_FRONTEND_PORT:-5173}"
export QG_PYTHON_BIN="${QG_PYTHON_BIN:-python3}"
export QG_RUNTIME_DIR="${QG_RUNTIME_DIR:-./Dashboard}"
export QG_MT5_FILES_DIR="${QG_MT5_FILES_DIR:-./Dashboard}"
export QG_FOCUS_SYMBOL="${QG_FOCUS_SYMBOL:-USDJPYc}"
export QG_ALLOWED_SYMBOLS="${QG_ALLOWED_SYMBOLS:-USDJPYc}"
export QG_DISABLE_NON_FOCUS_SYMBOLS="${QG_DISABLE_NON_FOCUS_SYMBOLS:-1}"
export QG_AUTOMATION_SYMBOLS="${QG_AUTOMATION_SYMBOLS:-USDJPYc}"
export QG_MT5_AI_MONITOR_SYMBOLS="${QG_MT5_AI_MONITOR_SYMBOLS:-USDJPYc}"
export QG_ACCOUNT_MODE="${QG_ACCOUNT_MODE:-cent}"
export QG_ACCOUNT_CURRENCY_UNIT="${QG_ACCOUNT_CURRENCY_UNIT:-USC}"
export QG_CENT_ACCOUNT_ACCELERATION="${QG_CENT_ACCOUNT_ACCELERATION:-1}"
export QG_TELEGRAM_COMMANDS_ALLOWED="${QG_TELEGRAM_COMMANDS_ALLOWED:-0}"

FRONTEND_DIR="${QG_FRONTEND_ROOT:-$WORKSPACE_ROOT/QuantGodFrontend}"
MT5_APP_PATH="${QG_MT5_APP_PATH:-$HOME/Applications/MetaTrader 5.app}"
MT5_PREFIX="${QG_MT5_WINE_PREFIX:-$HOME/Library/Application Support/net.metaquotes.wine.metatrader5}"
MT5_ROOT="${QG_MT5_ROOT:-$MT5_PREFIX/drive_c/Program Files/MetaTrader 5}"
MT5_MQL5="$MT5_ROOT/MQL5"
MT5_FILES="$MT5_MQL5/Files"
MT5_EXPERTS="$MT5_MQL5/Experts"
MT5_PRESETS="$MT5_MQL5/Presets"
WINE64="$MT5_APP_PATH/Contents/SharedSupport/wine/bin/wine64"
MT5_SHADOW_CONFIG="$MT5_PREFIX/drive_c/qg/QuantGod_MT5_HFM_Shadow_mac.ini"
MT5_LIVE_CONFIG="$MT5_PREFIX/drive_c/qg/QuantGod_MT5_HFM_LivePilot_mac.ini"

export QG_MT5_TERMINAL_PATH="${QG_MT5_TERMINAL_PATH:-$MT5_ROOT/terminal64.exe}"
export QG_MT5_PYTHON_BIN="${QG_MT5_PYTHON_BIN:-$QG_PYTHON_BIN}"
export QG_USDJPY_HISTORY_SYNC_ENABLED="${QG_USDJPY_HISTORY_SYNC_ENABLED:-1}"
export QG_USDJPY_HISTORY_INTERVAL_SECONDS="${QG_USDJPY_HISTORY_INTERVAL_SECONDS:-3600}"
export QG_USDJPY_HISTORY_MONTHS="${QG_USDJPY_HISTORY_MONTHS:-12}"
export QG_USDJPY_HISTORY_TIMEFRAMES="${QG_USDJPY_HISTORY_TIMEFRAMES:-M1,M5,M15,H1}"
export QG_USDJPY_HISTORY_MAX_BARS="${QG_USDJPY_HISTORY_MAX_BARS:-700000}"
export QG_USDJPY_MT5_SYMBOL="${QG_USDJPY_MT5_SYMBOL:-USDJPYc}"
export QG_PARAMLAB_HFM_ROOT="${QG_PARAMLAB_HFM_ROOT:-$SCRIPT_DIR/runtime/ParamLab_Tester_Sandbox/live_hfm_placeholder}"
export QG_PARAMLAB_TESTER_ROOT="${QG_PARAMLAB_TESTER_ROOT:-$SCRIPT_DIR/runtime/HFM_MT5_Tester_Isolated}"
export QG_MT5_TESTER_ROOT="${QG_MT5_TESTER_ROOT:-$QG_PARAMLAB_TESTER_ROOT}"

MT5_SHADOW_SCREEN="${QG_MT5_SHADOW_SCREEN:-quantgod-mt5-shadow}"
MT5_LIVE_SCREEN="${QG_MT5_LIVE_SCREEN:-quantgod-mt5-live}"
BACKEND_API_SCREEN="${QG_BACKEND_API_SCREEN:-quantgod-backend-api}"
FRONTEND_SCREEN="${QG_FRONTEND_SCREEN:-quantgod-frontend-dev}"
AGENT_V25_SCREEN="${QG_AGENT_V25_SCREEN:-quantgod-agent-v25}"
HISTORY_SYNC_SCREEN="${QG_USDJPY_HISTORY_SYNC_SCREEN:-quantgod-usdjpy-history-sync}"
LEGACY_DAILY_AUTOPILOT_SCREEN="${QG_DAILY_AUTOPILOT_SCREEN:-quantgod-daily-autopilot}"

RUNTIME_SOURCE="${QG_MAC_RUNTIME_SOURCE:-auto}"
MT5_START_MODE="${QG_MT5_START_MODE:-live}"
MT5_LIVE_LAUNCH_ALLOWED="${QG_MT5_LIVE_LAUNCH_ALLOWED:-1}"
MT5_START_SYMBOL="${QG_MT5_START_SYMBOL:-USDJPYc}"
BACKEND_API_ENABLED="${QG_BACKEND_API_ENABLED:-1}"
FRONTEND_ENABLED="${QG_FRONTEND_ENABLED:-1}"
AGENT_V25_ENABLED="${QG_AGENT_V25_ENABLED:-1}"
LEGACY_DAILY_AUTOPILOT_ENABLED="${QG_LEGACY_DAILY_AUTOPILOT_ENABLED:-0}"

RUNTIME_IS_IMPORT_SNAPSHOT=0
if is_import_snapshot_dir "$QG_RUNTIME_DIR"; then
  RUNTIME_IS_IMPORT_SNAPSHOT=1
fi

if [[ -d "$MT5_ROOT" && ( "$RUNTIME_SOURCE" == "mt5" || ( "$RUNTIME_SOURCE" == "auto" && ( "$RUNTIME_CONFIGURED" == "0" || "$RUNTIME_IS_IMPORT_SNAPSHOT" == "1" ) ) ) ]]; then
  export QG_RUNTIME_DIR="$MT5_FILES"
  export QG_MT5_FILES_DIR="$MT5_FILES"
fi

echo "QuantGod v2.5 Mac one-click launcher"
echo "Backend: $SCRIPT_DIR"
echo "Frontend: $FRONTEND_DIR"
echo "Runtime: $QG_RUNTIME_DIR"
echo "Focus symbol: $QG_FOCUS_SYMBOL"
echo "MT5 start mode: $MT5_START_MODE"
echo "MT5 start symbol: $MT5_START_SYMBOL"
echo "MT5 live launch allowed: $MT5_LIVE_LAUNCH_ALLOWED"
echo "MT5 terminal path: $QG_MT5_TERMINAL_PATH"
echo "MT5 Python bin: $QG_MT5_PYTHON_BIN"
echo "USDJPY history sync: $QG_USDJPY_HISTORY_SYNC_ENABLED every ${QG_USDJPY_HISTORY_INTERVAL_SECONDS}s for ${QG_USDJPY_HISTORY_MONTHS} months"
echo "Frontend: http://$QG_FRONTEND_HOST:$QG_FRONTEND_PORT/vue/?workspace=mt5"
echo "Backend API: http://$QG_DASHBOARD_HOST:$QG_DASHBOARD_PORT/vue/"

if [[ -d "$MT5_ROOT" ]]; then
  echo "Syncing QuantGod files into MT5..."
  mkdir -p "$MT5_FILES" "$MT5_EXPERTS" "$MT5_PRESETS" "$MT5_PREFIX/drive_c/qg"
  rsync -a Dashboard/vue-dist/ "$MT5_FILES/vue-dist/" || true
  cp Dashboard/dashboard_server.js "$MT5_FILES/dashboard_server.js"
  rsync -a --include='QuantGod_*' --include='*/' --exclude='*' Dashboard/ "$MT5_FILES/"
  if [[ -d "$QG_MT5_FILES_DIR" ]]; then
    SRC_MT5_FILES="$(cd "$QG_MT5_FILES_DIR" && pwd -P)"
    DST_MT5_FILES="$(cd "$MT5_FILES" && pwd -P)"
    if [[ "$SRC_MT5_FILES" != "$DST_MT5_FILES" ]]; then
      rsync -a --include='QuantGod_*' --include='*/' --exclude='*' "$QG_MT5_FILES_DIR/" "$MT5_FILES/"
    fi
  fi
  cp MQL5/Experts/QuantGod_MultiStrategy.mq5 "$MT5_EXPERTS/QuantGod_MultiStrategy.mq5"
  rsync -a MQL5/Presets/ "$MT5_PRESETS/"
  cp MQL5/Config/QuantGod_MT5_HFM_Shadow.ini "$MT5_SHADOW_CONFIG"
  patch_ini_key "$MT5_SHADOW_CONFIG" "Symbol" "$MT5_START_SYMBOL"
  perl -0pi -e 's/AllowLiveTrading=1/AllowLiveTrading=0/g' "$MT5_SHADOW_CONFIG"

  if [[ -x "$WINE64" ]]; then
    echo "Compiling QuantGod_MultiStrategy.mq5 with MetaEditor..."
    cp MQL5/Experts/QuantGod_MultiStrategy.mq5 "$MT5_PREFIX/drive_c/qg/QuantGod_MultiStrategy.mq5"
    set +e
    WINEPREFIX="$MT5_PREFIX" "$WINE64" \
      'C:\Program Files\MetaTrader 5\metaeditor64.exe' \
      '/compile:C:\qg\QuantGod_MultiStrategy.mq5' \
      '/log:C:\qg\compile.log'
    COMPILE_CODE=$?
    set -e
    if [[ -f "$MT5_PREFIX/drive_c/qg/QuantGod_MultiStrategy.ex5" ]]; then
      cp "$MT5_PREFIX/drive_c/qg/QuantGod_MultiStrategy.ex5" "$MT5_EXPERTS/QuantGod_MultiStrategy.ex5"
      cp "$MT5_PREFIX/drive_c/qg/QuantGod_MultiStrategy.ex5" MQL5/Experts/QuantGod_MultiStrategy.ex5
      echo "EA compiled and synced to MT5 Experts."
    else
      echo "MetaEditor did not produce QuantGod_MultiStrategy.ex5. Exit code: $COMPILE_CODE"
      echo "Check: $MT5_PREFIX/drive_c/qg/compile.log"
    fi

    if [[ "${QG_PREPARE_ISOLATED_TESTER:-1}" != "0" ]]; then
      echo "Preparing isolated Strategy Tester root..."
      "$QG_PYTHON_BIN" tools/prepare_isolated_mt5_tester.py \
        --source-root "$MT5_ROOT" \
        --tester-root "$QG_PARAMLAB_TESTER_ROOT" \
        --status "$SCRIPT_DIR/runtime/QuantGod_IsolatedTesterStatus.json" \
        --refresh || echo "Isolated tester preparation failed; AUTO_TESTER_WINDOW will stay locked."
    fi

    if [[ "$MT5_START_MODE" == "off" ]]; then
      echo "MT5 launch skipped because QG_MT5_START_MODE=off."
    elif [[ "$MT5_START_MODE" == "live" ]]; then
      cp MQL5/Config/QuantGod_MT5_HFM_LivePilot.ini "$MT5_LIVE_CONFIG"
      patch_ini_key "$MT5_LIVE_CONFIG" "Symbol" "$MT5_START_SYMBOL"
      echo "Live MT5 config prepared at $MT5_LIVE_CONFIG."
      if [[ "$MT5_LIVE_LAUNCH_ALLOWED" != "1" ]]; then
        echo "Live launch is locked. Set QG_MT5_LIVE_LAUNCH_ALLOWED=1 after checking live risk controls."
      else
        echo "Starting MT5 with the HFM LivePilot config..."
        quit_screen "$MT5_SHADOW_SCREEN"
        start_screen "$MT5_LIVE_SCREEN" "$SCRIPT_DIR/runtime/mt5_hfm_livepilot_screen.log" \
          "cd '$MT5_ROOT' && exec env WINEPREFIX='$MT5_PREFIX' '$WINE64' terminal64.exe /portable '/config:C:\\qg\\QuantGod_MT5_HFM_LivePilot_mac.ini'"
      fi
    else
      echo "Starting MT5 with the read-only HFM shadow config..."
      start_screen "$MT5_SHADOW_SCREEN" "$SCRIPT_DIR/runtime/mt5_hfm_shadow_screen.log" \
        "cd '$MT5_ROOT' && exec env WINEPREFIX='$MT5_PREFIX' '$WINE64' terminal64.exe /portable '/config:C:\\qg\\QuantGod_MT5_HFM_Shadow_mac.ini'"
    fi
  fi
else
  echo "MT5 data folder not found yet: $MT5_ROOT"
  echo "Install/open MetaTrader 5 once, then run this script again."
fi

if [[ -d "$MT5_APP_PATH" && ! -x "$WINE64" ]]; then
  open "$MT5_APP_PATH" || true
fi

if [[ "$BACKEND_API_ENABLED" == "1" ]]; then
  start_screen "$BACKEND_API_SCREEN" "$SCRIPT_DIR/runtime/backend_api_screen.log" \
    "cd '$SCRIPT_DIR' && exec node Dashboard/dashboard_server.js"
fi

if [[ "$FRONTEND_ENABLED" == "1" && -d "$FRONTEND_DIR" ]]; then
  start_screen "$FRONTEND_SCREEN" "$SCRIPT_DIR/runtime/frontend_dev_screen.log" \
    "cd '$FRONTEND_DIR' && exec npm run dev -- --host '$QG_FRONTEND_HOST' --port '$QG_FRONTEND_PORT'"
fi

if [[ "$AGENT_V25_ENABLED" == "1" ]]; then
  quit_screen "$LEGACY_DAILY_AUTOPILOT_SCREEN"
  start_screen "$AGENT_V25_SCREEN" "$SCRIPT_DIR/runtime/agent_v25_screen.log" \
    "cd '$SCRIPT_DIR' && exec bash tools/run_mac_agent_v25_loop.sh --loop"
fi

if [[ "$QG_USDJPY_HISTORY_SYNC_ENABLED" == "1" ]]; then
  start_screen "$HISTORY_SYNC_SCREEN" "$SCRIPT_DIR/runtime/usdjpy_history_sync_screen.log" \
    "cd '$SCRIPT_DIR' && exec bash tools/run_mac_usdjpy_history_sync_loop.sh --loop"
fi

if [[ "$LEGACY_DAILY_AUTOPILOT_ENABLED" == "1" ]]; then
  start_screen "$LEGACY_DAILY_AUTOPILOT_SCREEN" "$SCRIPT_DIR/runtime/daily_autopilot_legacy_screen.log" \
    "cd '$SCRIPT_DIR' && exec bash tools/run_mac_daily_autopilot.sh --loop"
fi

open "http://$QG_FRONTEND_HOST:$QG_FRONTEND_PORT/vue/?workspace=mt5" || \
  open "http://$QG_DASHBOARD_HOST:$QG_DASHBOARD_PORT/vue/?workspace=mt5" || true

echo "QuantGod v2.5 launcher complete."
echo "Screens: $BACKEND_API_SCREEN, $FRONTEND_SCREEN, $AGENT_V25_SCREEN, $HISTORY_SYNC_SCREEN, $MT5_LIVE_SCREEN"
