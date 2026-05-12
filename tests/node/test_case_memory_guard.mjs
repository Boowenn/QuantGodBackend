import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

test('case memory API and runner expose P4-7 productionized endpoints', () => {
  const server = read('Dashboard/dashboard_server.js');
  const routes = read('Dashboard/case_memory_api_routes.js');
  const runner = read('tools/run_case_memory.py');
  for (const marker of [
    "require('./case_memory_api_routes')",
    'isCaseMemoryPath',
    '/api/case-memory/status',
    '/api/case-memory/build',
    '/api/case-memory/telegram-text',
    'run_case_memory.py',
    'Case Memory',
  ]) {
    assert.match(`${server}\n${routes}\n${runner}`, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('case memory candidates remain shadow-only and readable', () => {
  const files = [
    'tools/case_memory/schema.py',
    'tools/case_memory/candidate_builder.py',
    'tools/case_memory/builder.py',
    'tools/case_memory/report.py',
    'tools/case_memory/telegram_text.py',
    'tools/strategy_structure_lab/schema.py',
    'tools/strategy_structure_lab/candidate_builder.py',
    'tools/strategy_structure_lab/builder.py',
    'tools/strategy_structure_lab/report.py',
    'tools/strategy_structure_lab/telegram_text.py',
    'tools/run_case_memory.py',
  ];
  const source = files.map(read).join('\n');
  for (const marker of [
    'P4-7',
    'strategyStructureProductionOnly',
    'SHADOW_STRATEGY_JSON_CANDIDATE',
    'BLOCKED_BY_PARITY',
    'case_memory_seed_pool',
    'validate_strategy_json',
    'orderSendAllowed',
    'writesMt5OrderRequest',
  ]) {
    assert.match(source, new RegExp(marker));
  }
  assert.doesNotMatch(source, /OrderSend|OrderSendAsync|PositionClose|TRADE_ACTION_DEAL|CTrade/);
  assert.doesNotMatch(source, /livePresetMutationAllowed["']?\s*:\s*True/);
  for (const file of files) {
    const lines = read(file).split(/\r?\n/);
    assert.ok(lines.length >= 5, `${file} should stay readable`);
    lines.forEach((line, index) => {
      assert.ok(line.length <= 160, `${file}:${index + 1} should not exceed 160 characters`);
    });
  }
});
