import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';

const files = [
  'tools/run_mac_agent_v25_maintenance.py',
  'tools/run_production_evidence_validation.py',
  'tools/production_evidence_validation/schema.py',
  'tools/production_evidence_validation/io_utils.py',
  'tools/production_evidence_validation/history_audit.py',
  'tools/production_evidence_validation/parity_audit.py',
  'tools/production_evidence_validation/execution_feedback_audit.py',
  'tools/production_evidence_validation/source_attribution.py',
  'tools/production_evidence_validation/ga_audit.py',
  'tools/production_evidence_validation/burn_in.py',
  'tools/production_evidence_validation/report.py',
  'tools/production_evidence_validation/telegram_text.py',
  'Dashboard/production_evidence_validation_api_routes.js',
];

test('P4-6 sources are readable and not compressed into one line', () => {
  for (const file of files) {
    const text = readFileSync(file, 'utf8');
    const lines = text.split(/\r?\n/);
    assert.ok(lines.length >= 8, `${file} should be multi-line`);
    const longest = Math.max(...lines.map((line) => line.length));
    assert.ok(longest <= 220, `${file} has too long line: ${longest}`);
    assert.equal(/import .* def /.test(text), false, `${file} contains compressed Python`);
    assert.equal(/;\s*def\s+/.test(text), false, `${file} contains semicolon-def compression`);
  }
});

test('P4-9 exposes burn-in and source attribution markers', () => {
  const maintenance = readFileSync('tools/run_mac_agent_v25_maintenance.py', 'utf8');
  const route = readFileSync('Dashboard/production_evidence_validation_api_routes.js', 'utf8');
  const burnIn = readFileSync('tools/production_evidence_validation/burn_in.py', 'utf8');
  const attribution = readFileSync('tools/production_evidence_validation/source_attribution.py', 'utf8');
  assert.ok(route.includes('/api/production-evidence-validation/burn-in'), 'missing burn-in API route');
  assert.ok(maintenance.includes('build_agent_ops_health'), 'missing AgentOpsHealth refresh');
  assert.ok(maintenance.includes('build_burn_in_report'), 'missing burn-in maintenance runner');
  assert.ok(maintenance.includes('QG_PRODUCTION_BURN_IN_INTERVAL_SECONDS'), 'missing burn-in throttle');
  assert.ok(readFileSync('tools/run_mac_agent_v25_loop.sh', 'utf8').includes('--force-burn-in'));
  assert.ok(readFileSync('tools/run_mac_agent_v25_loop.sh', 'utf8').includes('QG_AGENT_V25_LOCK_DIR'));
  assert.ok(readFileSync('tools/production_evidence_validation/execution_feedback_audit.py', 'utf8').includes('sourceKind'));
  assert.ok(burnIn.includes('PRODUCTION_BURN_IN_REPORT'), 'missing burn-in report');
  assert.ok(burnIn.includes('PRODUCTION_BURN_IN_LEDGER'), 'missing burn-in ledger');
  for (const tier of ['live_real_fill', 'mt5_close_history', 'ea_shadow', 'strategy_shadow', 'backfilled_history']) {
    assert.ok(attribution.includes(tier), `missing source tier ${tier}`);
  }
});

test('P4-6 guard blocks trading verbs and direct wallet semantics', () => {
  const joined = files.map((file) => readFileSync(file, 'utf8')).join('\n');
  for (const forbidden of ['OrderSend(', 'CTrade', 'TRADE_ACTION_DEAL', 'PositionClose(', 'livePresetMutationAllowed: true', 'polymarketRealMoneyAllowed: true']) {
    assert.equal(joined.includes(forbidden), false, `forbidden token ${forbidden}`);
  }
});

test('P4-8A parity audit consumes backtest coverage and EA shadow evidence', () => {
  const text = readFileSync('tools/production_evidence_validation/parity_audit.py', 'utf8');
  for (const required of [
    'strategyJsonBacktest',
    'mql5EaShadowAdapter',
    'SHADOW_RESEARCH_ONLY',
    'QuantGod_StrategyJsonEAShadowEvaluationLedger.jsonl',
    'quantgod.strategy_backtest_coverage_matrix.v1',
  ]) {
    assert.ok(text.includes(required), `missing parity matrix marker ${required}`);
  }
});
