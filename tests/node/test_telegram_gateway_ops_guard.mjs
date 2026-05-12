import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

function readable(rel) {
  const lines = read(rel).split(/\r?\n/);
  assert.ok(lines.length >= 5, `${rel} should remain readable`);
  lines.forEach((line, index) => {
    assert.ok(line.length <= 160, `${rel}:${index + 1} is too long`);
  });
}

test('Telegram Gateway Ops exposes push-only observability routes', () => {
  const server = read('Dashboard/dashboard_server.js');
  const routes = read('Dashboard/telegram_gateway_ops_api_routes.js');
  const runner = read('tools/run_telegram_gateway_ops.py');
  for (const marker of [
    "require('./telegram_gateway_ops_api_routes')",
    'isTelegramGatewayOpsPath',
    '/api/telegram-gateway/status',
    '/api/telegram-gateway/collect',
    '/api/telegram-gateway/telegram-text',
    'run_telegram_gateway_ops.py',
    'telegramCommandExecutionAllowed',
    'gatewayReceivesCommands',
  ]) {
    assert.match(`${server}\n${routes}\n${runner}`, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.doesNotMatch(routes + runner, /OrderSend|OrderSendAsync|PositionClose|TRADE_ACTION_DEAL|CTrade/);
  assert.doesNotMatch(routes + runner, /telegramCommandExecutionAllowed["']?\s*:\s*true/);
});

test('Telegram Gateway Ops Python sources stay readable', () => {
  for (const rel of [
    'tools/run_telegram_gateway_ops.py',
    'tools/telegram_gateway_ops/schema.py',
    'tools/telegram_gateway_ops/io_utils.py',
    'tools/telegram_gateway_ops/status.py',
    'tools/telegram_gateway_ops/telegram_text.py',
    'tests/test_telegram_gateway_ops.py',
    'tests/node/test_telegram_gateway_ops_guard.mjs',
  ]) {
    readable(rel);
  }
});
