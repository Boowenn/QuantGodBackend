import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

test('USDJPY evidence OS API endpoints are exposed under USDJPY namespace', () => {
  const routes = read('Dashboard/usdjpy_strategy_lab_api_routes.js');
  for (const endpoint of [
    '/api/usdjpy-strategy-lab/strategy-backtest/sync-klines',
    '/api/usdjpy-strategy-lab/evidence-os/status',
    '/api/usdjpy-strategy-lab/evidence-os/run',
    '/api/usdjpy-strategy-lab/evidence-os/parity',
    '/api/usdjpy-strategy-lab/evidence-os/execution-feedback',
    '/api/usdjpy-strategy-lab/evidence-os/case-memory',
    '/api/usdjpy-strategy-lab/evidence-os/telegram-text',
    '/api/usdjpy-strategy-lab/telegram-gateway/status',
    '/api/usdjpy-strategy-lab/telegram-gateway/test-event',
    '/api/usdjpy-strategy-lab/telegram-gateway/dispatch',
    '/api/usdjpy-strategy-lab/agent-ops-health/status',
  ]) {
    assert.match(routes, new RegExp(endpoint.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('evidence OS remains read-only and feeds GA scoring', () => {
  const source = [
    read('tools/usdjpy_evidence_os/schema.py'),
    read('tools/usdjpy_evidence_os/parity.py'),
    read('tools/usdjpy_evidence_os/execution_feedback.py'),
    read('tools/usdjpy_evidence_os/case_memory.py'),
    read('tools/usdjpy_evidence_os/telegram_gateway.py'),
    read('tools/agent_ops_health.py'),
    read('tools/run_telegram_gateway.py'),
    read('tools/run_agent_ops_health.py'),
    read('tools/run_mac_agent_v25_loop.sh'),
    read('tools/ensure_mac_agent_v25_loop.sh'),
    read('tools/strategy_ga/fitness.py'),
  ].join('\n');

  assert.match(source, /STRATEGY_JSON_PYTHON_REPLAY_MQL5_EA_PARITY/);
  assert.match(source, /strategy_json_python_replay_mql5_gate_matrix/);
  assert.match(source, /strategy_json_multi_strategy_coverage_matrix/);
  assert.match(source, /quantgod\.strategy_backtest_coverage_matrix\.v1/);
  assert.match(source, /quantgod\.strategy_deep_parity_matrix\.v1/);
  assert.match(source, /posteriorMayAffectTrigger/);
  assert.match(source, /ordinaryNewsBlocksLive/);
  assert.match(source, /QuantGod_LiveExecutionFeedback\.jsonl/);
  assert.match(source, /QuantGod_CaseMemory\.jsonl/);
  assert.match(source, /promotionGate/);
  assert.match(source, /caseMemoryTriggers/);
  assert.match(source, /REQUIRED_LIVE_EXECUTION_FIELDS/);
  assert.match(source, /fieldCompleteness/);
  assert.match(source, /LIVE_EXECUTION_FEEDBACK_FIELD_GAP/);
  assert.match(source, /EXECUTION_FEEDBACK_SCHEMA_GAP/);
  assert.match(source, /gaSeedHints/);
  assert.match(source, /caseMemoryToGA/);
  assert.match(source, /strategyContractShadowEvaluation/);
  assert.match(source, /genericAdapterSummary/);
  assert.match(source, /genericAdapterStableFamilies/);
  assert.match(source, /QuantGod_TelegramGatewayLedger\.jsonl/);
  assert.match(source, /QuantGod_NotificationEventQueue\.jsonl/);
  assert.match(source, /collect_scheduled_events/);
  assert.match(source, /DAILY_AUTOPILOT_V2_REPORT/);
  assert.match(source, /GA_EVOLUTION_REPORT/);
  assert.match(source, /USDJPY_AUTONOMOUS_AGENT_REPORT/);
  assert.match(source, /POLYMARKET_RETUNE_REPORT/);
  assert.match(source, /dispatch_pending/);
  assert.match(source, /gateway_status/);
  assert.match(source, /quantgod\.agent_ops_health\.v1/);
  assert.match(source, /QuantGod_AgentOpsHealth\.json/);
  assert.match(source, /QuantGod_AgentV25LoopStatus\.json/);
  assert.match(source, /QuantGod_AgentV25SupervisorStatus\.json/);
  assert.match(source, /quantgod\.agent_v25_loop_status\.v1/);
  assert.match(source, /quantgod\.agent_v25_supervisor_status\.v1/);
  assert.match(source, /agentV25Loop/);
  assert.match(source, /QG_AGENT_V25_STALE_SECONDS/);
  assert.match(source, /QG_AGENT_V25_SUPERVISOR_INTERVAL_SECONDS/);
  assert.match(source, /polymarketRetune/);
  assert.match(source, /telegramGateway/);
  assert.match(source, /dailyAutopilot/);
  assert.match(source, /QG_AGENT_V25_INTERVAL_SECONDS/);
  assert.match(source, /QG_TELEGRAM_COMMANDS_ALLOWED/);
  assert.match(source, /rate_limited/);
  assert.match(source, /run-once/);
  assert.match(source, /PARITY_OR_EXECUTION_EVIDENCE_FAILED/);
  assert.doesNotMatch(source, /TRADE_ACTION_DEAL|OrderSendAsync|PositionClose|CTrade/);
  assert.doesNotMatch(source, /telegramCommandExecutionAllowed["']?\s*:\s*True/);
});

test('Mac Agent loop sends scheduled reports through the Telegram Gateway collector', () => {
  const source = [
    read('tools/run_mac_agent_v25_loop.sh'),
    read('tools/ensure_mac_agent_v25_loop.sh'),
    read('Start_QuantGod_mac.sh'),
  ].join('\n');
  assert.match(source, /run_telegram_gateway\.py/);
  assert.match(source, /run-once/);
  assert.match(source, /collect/);
  assert.match(source, /--refresh/);
  assert.match(source, /write_loop_status/);
  assert.match(source, /QuantGod_AgentV25LoopStatus\.json/);
  assert.match(source, /QuantGod_AgentV25SupervisorStatus\.json/);
  assert.match(source, /quantgod-agent-v25-supervisor/);
  assert.match(source, /ensure_mac_agent_v25_loop\.sh --loop/);
  assert.match(source, /matching_screen_sessions/);
  assert.match(source, /screen -S "\$session" -X quit/);
  assert.doesNotMatch(source, /run_daily_autopilot_v2\.py[\s\S]*telegram-text[\s\S]*--send/);
});

test('MT5 EA emits standardized live execution feedback for Evidence OS', () => {
  const eaSource = read('MQL5/Experts/QuantGod_MultiStrategy.mq5');
  for (const marker of [
    'QuantGod_LiveExecutionFeedback.jsonl',
    'QuantGod_LiveExecutionFeedbackHistory.jsonl',
    'quantgod.live_execution_feedback.v1',
    'OnTradeTransaction',
    'AppendPilotTradeResultFeedback',
    'AppendTradeTransactionFeedback',
    'BuildLiveExecutionFeedbackHistoryJsonl',
    'feedbackId',
    'eventType',
    'policyId',
    'strategyId',
    'intentId',
    'expectedPrice',
    'fillPrice',
    'slippagePips',
    'spreadAtEntry',
    'latencyMs',
    'profitR',
    'mfeR',
    'maeR',
    'parityContractVersion',
    'strategyJsonSchema',
    'PilotRsiCrossbackThreshold',
    'crossbackThreshold',
  ]) {
    assert.match(eaSource, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.match(eaSource, /ORDER_ACCEPTED/);
  assert.match(eaSource, /ORDER_REJECTED/);
  assert.match(eaSource, /ORDER_FILL/);
  assert.match(eaSource, /ORDER_CLOSE/);
  assert.match(eaSource, /frontendCanTrade\\":false/);
  assert.match(eaSource, /telegramCommandsAllowed\\":false/);
});

test('USDJPY operator reports use Telegram Gateway instead of direct senders', () => {
  const runners = [
    'tools/run_daily_autopilot_v2.py',
    'tools/run_usdjpy_autonomous_agent.py',
    'tools/run_usdjpy_bar_replay.py',
    'tools/run_usdjpy_live_loop.py',
    'tools/run_usdjpy_runtime_dataset.py',
    'tools/run_usdjpy_strategy_backtest.py',
    'tools/run_usdjpy_strategy_lab.py',
    'tools/run_usdjpy_walk_forward.py',
    'tools/run_strategy_ga.py',
  ];
  for (const file of runners) {
    const source = read(file);
    assert.match(source, /dispatch_text/, `${file} should dispatch through the Telegram Gateway`);
    assert.match(source, /telegramGateway/, `${file} should expose gateway delivery evidence`);
    assert.doesNotMatch(source, /urllib\.request|urllib\.parse|urlopen|sendMessage/, `${file} should not directly call Telegram`);
  }
});
