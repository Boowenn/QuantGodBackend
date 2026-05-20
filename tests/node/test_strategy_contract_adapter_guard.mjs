import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

test('Strategy JSON EA contract adapter exposes read-only USDJPY API endpoints', () => {
  const routes = read('Dashboard/usdjpy_strategy_lab_api_routes.js');
  for (const endpoint of [
    '/api/usdjpy-strategy-lab/strategy-contract/status',
    '/api/usdjpy-strategy-lab/strategy-contract/build',
    '/api/usdjpy-strategy-lab/strategy-contract/telegram-text',
  ]) {
    assert.match(routes, new RegExp(endpoint.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.match(routes, /run_strategy_contract_adapter\.py/);
});

test('Strategy JSON contract backend writes only shadow/tester/paper adapter files', () => {
  const source = [
    read('tools/strategy_contract_adapter/schema.py'),
    read('tools/strategy_contract_adapter/builder.py'),
    read('tools/run_strategy_contract_adapter.py'),
  ].join('\n');
  for (const marker of [
    'SHADOW_EVALUATION_ONLY',
    'QuantGod_StrategyJsonEAContract_EA.txt',
    'QuantGod_StrategyJsonEAContractEAStatus.json',
    'QuantGod_StrategyJsonEAShadowEvaluationStatus.json',
    'QuantGod_StrategyJsonEAShadowEvaluationLedger.jsonl',
    'orderSendAllowed": False',
    'livePresetMutationAllowed": False',
    'gaDirectLiveAllowed": False',
    'readOnlyAdapter',
    'strategy_fingerprint',
    'familyParameters',
    'maFastPeriod',
    'bbDeviations',
    'macdFastPeriod',
    'srLookbackBars',
    'tokyoTradeStartHourUtc',
    'nightBollingerPeriod',
    'h4FastEmaPeriod',
    'forced_seed_id',
    'forced_family',
    'GA_CANDIDATE_FORCED_SEED',
    'GA_CANDIDATE_FORCED_FAMILY',
    'P4_10J_FROZEN_RSI_SEED',
    'FROZEN_RSI_LINEAGE_FILE',
    'RSI_SHADOW_OBSERVATION_REPORT_FILE',
    'RSI_OPPORTUNITY_LAYER_AUDIT_REPORT_FILE',
    'rsi-opportunity-layer-audit',
    'force_frozen_rsi',
    'rsiAdverseGuardMode',
  ]) {
    assert.match(source, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.doesNotMatch(source, /\bOrderSend\s*\(|\bCTrade\b|TRADE_ACTION_DEAL|PositionClose\s*\(|privateKey\s*[:=]|wallet\s*[:=]/i);
});

test('MQL5 adapter is read-only and cannot affect live execution', () => {
  const mq5 = read('MQL5/Experts/QuantGod_MultiStrategy.mq5');
  const begin = mq5.indexOf('Strategy JSON EA Contract Adapter BEGIN');
  const end = mq5.indexOf('Strategy JSON EA Contract Adapter END');
  assert.ok(begin > 0 && end > begin, 'MQL5 adapter markers must exist');
  const block = mq5.slice(begin, end);
  for (const marker of [
    'EnableStrategyJsonEAContractAdapter',
    'StrategyJsonEAContractFile',
    'QuantGod_StrategyJsonEAContractEAStatus.json',
    'QuantGod_StrategyJsonEAShadowEvaluationStatus.json',
    'QuantGod_StrategyJsonEAShadowEvaluationLedger.jsonl',
    'SHADOW_WOULD_ENTER',
    'shadowEvaluationOnly',
    'MA_Cross',
    'BB_Triple',
    'MACD_Divergence',
    'SR_Breakout',
    'USDJPY_TOKYO_RANGE_BREAKOUT',
    'USDJPY_NIGHT_REVERSION_SAFE',
    'USDJPY_H4_TREND_PULLBACK',
    'genericStrategy',
    'tokyoRange',
    'nightReversion',
    'h4Pullback',
    'contractParameters',
    'maFastPeriod',
    'maSlowPeriod',
    'bbPeriod',
    'bbDeviations',
    'macdFastPeriod',
    'macdSlowPeriod',
    'macdSignalPeriod',
    'srLookbackBars',
    'srBreakoutBufferPips',
    'tokyoTradeStartHourUtc',
    'tokyoBufferPips',
    'nightBollingerPeriod',
    'nightEntryBufferPips',
    'h4FastEmaPeriod',
    'h4SlowEmaPeriod',
    'GENERIC_CONTRACT_OPPOSITE_DIRECTION_SIGNAL',
    'StrategyJsonGenericAdapterFamily',
    'StrategyJsonEvaluateGenericAdapterFamily',
    'TOKYO_RANGE_SIGNAL_NOT_READY',
    'TOKYO_RANGE_BOX_NOT_READY',
    'NIGHT_REVERSION_SIGNAL_NOT_READY',
    'H4_PULLBACK_SIGNAL_NOT_READY',
    'H4_PULLBACK_TREND_NOT_READY',
    'H4_PULLBACK_INDICATORS_NOT_READY',
    'SHADOW_CONTRACT_READY',
    'orderSendAllowed',
    'livePresetMutationAllowed',
    'wouldAffectLive',
    'rsiAdverseGuard',
    'RSI_ADVERSE_GUARD_RANGE_BLOCK',
  ]) {
    assert.match(block, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.doesNotMatch(block, /\bOrderSend\s*\(|\bCTrade\b|TRADE_ACTION_DEAL|PositionClose\s*\(|OrderRequest\s*\(/i);
});

test('Frontend shows Strategy JSON to EA contract status without direct file reads', () => {
  const frontendRoot = path.join(repo, '../QuantGodFrontend');
  const servicePath = path.join(frontendRoot, 'src/services/usdjpyStrategyLabApi.js');
  const panelPath = path.join(frontendRoot, 'src/components/USDJPYEvolutionPanel.vue');
  if (!fs.existsSync(servicePath) || !fs.existsSync(panelPath)) {
    assert.ok(true, 'QuantGodFrontend sibling checkout is not available in backend-only CI');
    return;
  }
  const service = fs.readFileSync(servicePath, 'utf8');
  const panel = fs.readFileSync(panelPath, 'utf8');
  for (const marker of [
    '/strategy-contract/status',
    '/strategy-contract/build',
    'fetchUSDJPYStrategyContractStatus',
    'buildUSDJPYStrategyContract',
  ]) {
    assert.match(service, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  for (const marker of [
    'Strategy JSON → EA 契约',
    '只读评估',
    'EA 回执',
    'EA 影子评估',
    'eaShadowEvaluationRecent',
    'strategyContractPayload',
  ]) {
    assert.match(panel, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.doesNotMatch(service + panel, /\/QuantGod_.*\.(json|csv)|OrderSend|quick-trade|fetch\s*\(/i);
});
