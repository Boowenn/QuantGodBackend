# QuantGodBackend

QuantGodBackend is the local-first execution evidence, API, MT5, research, and autonomous governance repository for QuantGod.

The current production direction is narrow by design:

```text
Live lane: USDJPYc / RSI_Reversal / LONG / cent account
Shadow lanes: MT5 multi-strategy simulation and Polymarket event research
Agent: autonomous daily todo, daily review, promotion, demotion, and rollback
Safety: machine hard guards remain mandatory
```

This repository owns the backend data plane and MT5 integration. It does not own Vue source, Cloudflare deployment code, or the documentation hub.

## Repository Role

| Area | Path | Responsibility |
|---|---|---|
| MT5 assets | `MQL5/` | EA source, presets, HFM live/shadow configuration, Strategy Tester assets |
| Local API | `Dashboard/` | Node API server and static `/vue/` runtime host |
| Research and governance | `tools/` | USDJPY replay, walk-forward, lifecycle Agent, Telegram push, AI explanation, ParamLab, guards |
| Tests | `tests/` | Python unit tests, Node contract tests, safety guards |
| Runtime output | `runtime/`, `Dashboard/QuantGod_*` | Local generated evidence; ignored unless explicitly documented |

Related repositories:

- Backend: this repository
- Frontend: `../QuantGodFrontend`
- Infra: `../QuantGodInfra`
- Docs: `../QuantGodDocs`

## Current System Model

QuantGod v2.5 is organized as three lanes:

| Lane | Scope | What it can do | What it cannot do |
|---|---|---|---|
| Live Lane | `USDJPYc / RSI_Reversal / LONG` | Cent-account micro live, limited live, autonomous rollback | USDJPY short, non-RSI live, non-USDJPY live |
| MT5 Shadow Lane | USDJPY strategy pool | Multi-strategy shadow ranking, replay, tester-only validation | Steal the live route or mutate live preset directly |
| Polymarket Shadow Lane | Prediction-market research | Shadow ledger and macro/event context | Real wallet, USDC orders, signing, redeeming |

DeepSeek may explain evidence and produce Chinese summaries. It cannot approve live execution, override hard gates, raise lot limits, or cancel rollback.

## macOS One-Click Startup

Main entry point:

```bash
cd /Users/bowen/Desktop/Quard/QuantGodBackend
./Start_QuantGod_mac.sh
```

The launcher starts the current v2.5 stack:

- MT5 HFM LivePilot preset focused on `USDJPYc`.
- Backend API at `http://127.0.0.1:8080`.
- Frontend Vite workbench at `http://127.0.0.1:5173/vue/?workspace=mt5`.
- Agent v2.5 loop for USDJPY live-loop, policy generation, EA dry-run, daily todo, daily review, and rollback evidence.
- USDJPY history sync remains enabled, with lower default MT5 chart/history bar caps for 16 GB Macs.

The launcher keeps the original full stack but applies local memory controls by default:

- Node heap cap: `NODE_OPTIONS=--max-old-space-size=768`.
- MT5 chart max bars: `QG_MT5_MAX_BARS=300000`.
- USDJPY history max bars: `QG_USDJPY_HISTORY_MAX_BARS=300000`.
- USDJPY history sync interval: `QG_USDJPY_HISTORY_INTERVAL_SECONDS=7200`.
- Old `com.quantgod.*` LaunchAgents are stopped before startup to avoid duplicate backend/frontend/history/Agent loops.

The legacy daily autopilot loop is disabled by default. To deliberately use it for historical debugging only:

```bash
export QG_LEGACY_DAILY_AUTOPILOT_ENABLED=1
```

## Agent v2.5 Loop

Run one cycle without launching the whole desktop stack:

```bash
cd /Users/bowen/Desktop/Quard/QuantGodBackend
QG_AGENT_V25_SEND_TELEGRAM=0 bash tools/run_mac_agent_v25_loop.sh --once
```

Run continuously:

```bash
QG_AGENT_V25_INTERVAL_SECONDS=300 \
QG_AGENT_V25_SEND_TELEGRAM=0 \
bash tools/run_mac_agent_v25_loop.sh --loop
```

Each cycle refreshes:

1. USDJPY automation chain.
2. USDJPY strategy policy and EA dry-run.
3. USDJPY live-loop recovery status.
4. Agent v2.5 daily todo and daily review.
5. Optional Telegram push-only summary.

## Local API

Start only the backend API:

```bash
cd /Users/bowen/Desktop/Quard/QuantGodBackend
node Dashboard/dashboard_server.js
```

The front-end calls backend data through `/api/*` only. Runtime files such as `QuantGod_*.json` and CSV ledgers are backend-owned evidence and should not be read directly by the Vue app.

## Frontend Dist Sync

Vue source lives in `QuantGodFrontend`. Build and sync it through Infra:

```bash
cd /Users/bowen/Desktop/Quard/QuantGodFrontend
npm install
npm run build

cd /Users/bowen/Desktop/Quard/QuantGodInfra
python3 scripts/qg-workspace.py --workspace workspace/quantgod.workspace.json sync-frontend-dist
```

`Dashboard/vue-dist/` is an ignored runtime artifact. Do not commit it.

## Validation

Common backend checks:

```bash
cd /Users/bowen/Desktop/Quard/QuantGodBackend
python3 -m unittest discover tests -v
node --test tests/node/*.mjs
bash -n Start_QuantGod_mac.sh tools/run_mac_agent_v25_loop.sh tools/run_mac_daily_autopilot.sh
```

Focused Agent checks:

```bash
python3 -m unittest tests.test_run_daily_autopilot -v
python3 -m unittest tests.test_mt5_rsi_exit_protection -v
python3 -m py_compile tools/run_daily_autopilot_v2.py tools/run_usdjpy_live_loop.py
```

## Safety Boundaries

The following boundaries are deliberate and should be treated as architectural constraints:

- Live lane is limited to `USDJPYc / RSI_Reversal / LONG`.
- `QG_AUTO_MAX_LOT=2.0` is a ceiling, not a fixed position size.
- MT5 Shadow strategies may rank, replay, and graduate through non-live stages, but cannot become live unless explicitly allowed by the Live Lane contract.
- Polymarket remains shadow-only and event-context-only.
- Telegram is push-only; no Telegram command execution.
- DeepSeek explains and summarizes; it does not approve execution.
- Runtime stale, fastlane degraded, high-impact news windows, abnormal spread, daily loss, and loss streak gates cannot be bypassed by Agent or AI. Ordinary news is a soft risk modifier by default.
- Agent may write controlled patch evidence; it must not mutate source code, live preset, private keys, or broker credentials.

## Documentation

Primary documentation lives in `../QuantGodDocs`. Start with:

- `docs/ops/usdjpy-cent-autonomous-multilane-agent.md`
- `docs/ops/usdjpy-autonomous-agent.md`
- `docs/ops/usdjpy-bar-replay-simulator.md`
- `docs/backend/usdjpy-strategy-lab-api.md`
- `docs/backend/safety-boundaries.md`
