import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();
const FORBIDDEN_EXECUTION_PATTERN = /OrderSend|PositionClose|TRADE_ACTION_DEAL|CTrade/;

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

test('GA Factory alias routes point at Strategy GA Factory safely', () => {
  const server = read('Dashboard/dashboard_server.js');
  const routes = read('Dashboard/ga_factory_api_routes.js');
  const runner = read('tools/run_ga_factory.py');
  for (const marker of [
    "require('./ga_factory_api_routes')",
    'isGAFactoryPath',
    '/api/ga-factory',
    '/api/strategy-ga-factory',
    'run_strategy_ga_factory',
    'sendError',
  ]) {
    assert.match(`${server}\n${routes}\n${runner}`, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.doesNotMatch(routes + runner, FORBIDDEN_EXECUTION_PATTERN);
});
