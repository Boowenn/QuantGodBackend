import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();
const MIN_READABLE_LINES = 5;
const MAX_READABLE_LINE_LENGTH = 160;

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

function listFiles(relDir) {
  return fs.readdirSync(path.join(repo, relDir))
    .filter((name) => name.endsWith('.py'))
    .map((name) => path.join(relDir, name));
}

function assertReadableSource(file) {
  const text = read(file);
  const lines = text.split(/\r?\n/);
  assert.ok(lines.length >= MIN_READABLE_LINES, `${file} should stay readable`);
  lines.forEach((line, index) => {
    assert.ok(
      line.length <= MAX_READABLE_LINE_LENGTH,
      `${file}:${index + 1} should not exceed ${MAX_READABLE_LINE_LENGTH} characters`,
    );
  });
  if (file.endsWith('.py')) {
    assert.doesNotMatch(text, /;\s*(def|class)\s+/);
    assert.doesNotMatch(text, /\bimport\b[^\n]+;\s*(def|class)\s+/);
    assert.doesNotMatch(text, /;\s*if\s+__name__\s*==/);
  }
}

test('Strategy GA Factory exposes P4-4 API endpoints', () => {
  const server = read('Dashboard/dashboard_server.js');
  const routes = read('Dashboard/strategy_ga_factory_api_routes.js');
  const runner = read('tools/run_strategy_ga_factory.py');
  for (const marker of [
    "require('./strategy_ga_factory_api_routes')",
    'isStrategyGAFactoryPath',
    '/api/strategy-ga-factory/status',
    '/api/strategy-ga-factory/build',
    '/api/strategy-ga-factory/telegram-text',
    'run_strategy_ga_factory.py',
    'GA Factory',
  ]) {
    assert.match(`${server}\n${routes}\n${runner}`, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('Strategy GA Factory sources remain shadow-only and readable', () => {
  const sourceFiles = [
    ...listFiles('tools/strategy_ga_factory'),
    'tools/run_strategy_ga_factory.py',
    'tools/run_ga_factory.py',
    'Dashboard/strategy_ga_factory_api_routes.js',
    'Dashboard/ga_factory_api_routes.js',
  ];
  const readableFiles = [
    ...sourceFiles,
    'tests/test_strategy_ga_factory.py',
    'tests/test_ga_factory.py',
    'tests/node/test_strategy_ga_factory_guard.mjs',
    'tests/node/test_ga_factory_guard.mjs',
  ];
  const source = sourceFiles.map(read).join('\n');
  for (const marker of [
    'QuantGod_GAFactoryState.json',
    'QuantGod_GAEliteArchive.json',
    'QuantGod_GAStrategyGraveyard.json',
    'QuantGod_GALineageTree.json',
    'QuantGod_GAFactoryLedger.csv',
    'ALLOWED_PROMOTION_STAGES',
    'PAPER_LIVE_SIM',
    'gaFactoryDirectLiveAllowed',
    'writesMt5OrderRequest',
  ]) {
    assert.match(source, new RegExp(marker));
  }
  assert.doesNotMatch(source, /OrderSend|OrderSendAsync|PositionClose|TRADE_ACTION_DEAL|CTrade/);
  assert.doesNotMatch(source, /livePresetMutationAllowed["']?\s*:\s*True/);
  for (const file of readableFiles) {
    assertReadableSource(file);
  }
});
