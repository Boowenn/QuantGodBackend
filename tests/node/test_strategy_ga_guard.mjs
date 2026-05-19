import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

function listFiles(relDir) {
  const dir = path.join(repo, relDir);
  return fs.readdirSync(dir)
    .filter((name) => name.endsWith('.py'))
    .map((name) => path.join(relDir, name));
}

test('Strategy JSON GA exposes USDJPY-scoped API endpoints', () => {
  const routes = read('Dashboard/usdjpy_strategy_lab_api_routes.js');
  for (const endpoint of [
    '/api/usdjpy-strategy-lab/ga/status',
    '/api/usdjpy-strategy-lab/ga/run-generation',
    '/api/usdjpy-strategy-lab/ga/generations',
    '/api/usdjpy-strategy-lab/ga/candidates',
    '/api/usdjpy-strategy-lab/ga/candidate/',
    '/api/usdjpy-strategy-lab/ga/evolution-path',
    '/api/usdjpy-strategy-lab/ga/blockers',
    '/api/usdjpy-strategy-lab/ga/telegram-text',
  ]) {
    assert.match(routes, new RegExp(endpoint.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('Strategy JSON validator rejects code, secrets, and direct execution permissions', () => {
  const validator = read('tools/strategy_json/validator.py');
  const safety = read('tools/strategy_json/safety.py');
  const schema = read('tools/strategy_json/schema.py');

  for (const marker of [
    'OrderSend',
    'CTrade',
    'privateKey',
    'wallet',
    'eval(',
    'exec(',
    'MAX_LOT_TOO_HIGH',
    'LIVE_STAGE_REJECTED',
    'NON_USDJPY_REJECTED',
  ]) {
    assert.match(validator + safety, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'));
  }
  assert.match(schema, /orderSendAllowed["']?\s*:\s*False/);
  assert.match(schema, /livePresetMutationAllowed["']?\s*:\s*False/);
  assert.match(schema, /polymarketRealMoneyAllowed["']?\s*:\s*False/);
});

test('GA trace records process details rather than final result only', () => {
  const runner = read('tools/strategy_ga/generation_runner.py');
  const fitness = read('tools/strategy_ga/fitness.py');
  const mutation = read('tools/strategy_ga/mutation.py');
  const crossover = read('tools/strategy_ga/crossover.py');
  const schema = read('tools/strategy_ga/schema.py');
  const cache = read('tools/strategy_ga/cache.py');
  const lineage = read('tools/strategy_ga/lineage.py');
  const seedGenerator = read('tools/strategy_ga/seed_generator.py');
  const seedWalkForward = read('tools/usdjpy_strategy_backtest/walk_forward.py');

  for (const marker of [
    'generationId',
    'seedId',
    'strategyJson',
    'fitnessBreakdown',
    'strategyBacktest',
    'walkForward',
    'train',
    'validation',
    'forward',
    'stabilityScore',
    'walkForwardPenalty',
    'walkForwardStabilityBonus',
    'profitFactor',
    'winRate',
    'maxDrawdownR',
    'sharpe',
    'sortino',
    'tradeCount',
    'STRATEGY_BACKTEST_FAILED',
    'STRATEGY_BACKTEST_NO_TRADES',
    'WALK_FORWARD_INSUFFICIENT',
    'WALK_FORWARD_UNSTABLE',
    'blockerCode',
    'ELITE_SELECTED',
    'NEEDS_MORE_DATA',
    'PROMOTED_TO_SHADOW',
    'mutationCount',
    'crossoverCount',
    'caseMemorySeedCount',
    'qualityRepairCount',
    'searchExpansion',
    'QUALITY_REPAIR',
    'qualityProfile',
    'repairTargetBlocker',
    'BB_SHORT_RECLAIM_STABILIZER',
    'BB_SHORT_SAMPLE_EXPANDER',
    'RSI_REVERSAL_STABILITY_REPAIR',
    'RSI_REVERSAL_REGIME_EVENT_FILTER',
    'RSI_REVERSAL_20_TRADE_GATE_BALANCER',
    'RSI_REVERSAL_SEGMENT_OVERFIT_CLOSURE',
    'RSI_REVERSAL_FORWARD_DRAWDOWN_CLIPPER',
    'RSI_REVERSAL_VALIDATION_FORWARD_BALANCER',
    'RSI_REVERSAL_ADVERSE_EXCURSION_CLOSURE',
    'RSI_REVERSAL_EARLY_KILL_SWITCH',
    'RSI_REVERSAL_VOLATILITY_CAP',
    'RSI_REVERSAL_OVERFIT_SAMPLE_EXPANDER',
    'RSI_REVERSAL_WALK_FORWARD_BALANCER',
    'RSI_REVERSAL_SEGMENT_SAMPLE_BALANCER',
    'RSI_MIN_TRADE_GATE',
    'rsiMinTradeGatePenalty',
    'rsiSegmentOverfitPenalty',
    'P4_10E_RSI_BEARISH_STRETCH',
    'MACD_HISTOGRAM_STABILIZER',
    'H4_PULLBACK_STABILIZER',
    'TOKYO_RANGE_SESSION_STABILIZER',
    'TOKYO_RANGE_SAMPLE_EXPANDER',
    'explorationMode',
    'explorationSeedCount',
    'NO_ELITE_EXPAND_SEARCH',
    'EXPLORATION_GRID',
    'EXPLORATION_MUTATION',
    'ma_fast_periods',
    'bb_deviations',
    'tokyo_trade_windows',
    'night_windows',
    'h4_fast_periods',
    'strategyContractShadow',
    'strategyContractShadowBonus',
    'genericAdapterStableFamilies',
    'cacheHit',
    'evidenceSignature',
    'CASE_MEMORY',
    'QuantGod_GAFitnessCache.json',
    'QuantGod_GALineage.json',
    'QuantGod_GACandidateRuns.jsonl',
    'candidate_audit',
    'lineage_tree',
    'lineageTree',
    'lineage_path',
    'lineagePath',
    'bestFitnessEnd',
    'fitnessDelta',
    'evidenceChain',
    'sourceTrace',
    'equityCurve',
    'relativeDepth',
    'generationSpan',
    'elitePathSeedIds',
    'onElitePath',
    'foldedByDefault',
    'COLLAPSE_REMOTE_BRANCHES',
    'parentCount',
    'childCount',
  ]) {
    assert.match(
      runner + fitness + mutation + crossover + schema + cache + lineage + seedGenerator + seedWalkForward,
      new RegExp(marker),
    );
  }
});

test('GA modules do not introduce live execution, wallets, or Telegram commands', () => {
  const files = [
    ...listFiles('tools/strategy_json'),
    ...listFiles('tools/strategy_ga'),
    'tools/run_strategy_ga.py',
    'tools/usdjpy_evidence_os/telegram_gateway.py',
  ];
  const source = files.map(read).join('\n');

  assert.doesNotMatch(source, /TRADE_ACTION_DEAL|PositionClose|OrderSendAsync|CTrade/);
  assert.doesNotMatch(source, /privateKeyAllowed\s*["']?\s*:\s*true|polymarketRealMoneyAllowed\s*["']?\s*:\s*true/i);
  assert.match(source, /QG_TELEGRAM_COMMANDS_ALLOWED/);
  assert.match(source, /gaDirectLiveAllowed/);
});

test('GA Python sources stay readable and multi-line', () => {
  for (const file of [...listFiles('tools/strategy_json'), ...listFiles('tools/strategy_ga')]) {
    const source = read(file);
    const lines = source.split(/\r?\n/);
    if (!file.endsWith('__init__.py')) {
      assert.ok(lines.length >= 20, `${file} should stay readable and multi-line`);
    }
    lines.forEach((line, index) => {
      assert.ok(line.length <= 160, `${file}:${index + 1} should not exceed 160 characters`);
    });
    assert.doesNotMatch(source, /;\s*(def|class)\s+/m, `${file} contains compressed definitions`);
  }
});
