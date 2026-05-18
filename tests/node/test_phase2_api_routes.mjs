import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const routes = require('../../Dashboard/phase2_api_routes.js');

function makeResponse() {
  let resolveResponse;
  const promise = new Promise((resolve) => {
    resolveResponse = resolve;
  });
  const res = {
    statusCode: 0,
    headers: {},
    writeHead(statusCode, headers) {
      this.statusCode = statusCode;
      this.headers = headers;
    },
    end(body) {
      resolveResponse({ statusCode: this.statusCode, headers: this.headers, body: body ? JSON.parse(body) : {} });
    },
  };
  promise.res = res;
  return promise;
}

async function invoke(url, ctx = {}, method = 'GET') {
  const response = makeResponse();
  await routes.handle({ url, method }, response.res, ctx);
  return await response;
}

test('parseCsv handles quoted commas', () => {
  const parsed = routes.parseCsv('Symbol,Reason\nEURUSDc,"a,b"\n');
  assert.deepEqual(parsed.headers, ['Symbol', 'Reason']);
  assert.equal(parsed.rows[0].Reason, 'a,b');
});

test('phase2 path registry includes required API domains', () => {
  assert.equal(routes.isPhase2Path('/api/governance/advisor'), true);
  assert.equal(routes.isPhase2Path('/api/paramlab/status'), true);
  assert.equal(routes.isPhase2Path('/api/trades/journal'), true);
  assert.equal(routes.isPhase2Path('/api/research/stats'), true);
  assert.equal(routes.isPhase2Path('/api/research/entry-blockers'), true);
  assert.equal(routes.isPhase2Path('/api/research/entry-blockers-ledger'), true);
  assert.equal(routes.isPhase2Path('/api/shadow/signals'), true);
  assert.equal(routes.isPhase2Path('/api/notify/config'), true);
  assert.equal(routes.isPhase2Path('/api/notify/daily-digest'), true);
  assert.equal(routes.isPhase2Path('/api/notify/runtime-scan'), true);
  assert.equal(routes.isPhase2Path('/api/notify/mt5-ai-monitor/config'), true);
  assert.equal(routes.isPhase2Path('/api/notify/mt5-ai-monitor/run'), true);
  assert.equal(routes.PHASE2_API_SAFETY.orderSendAllowed, false);
  assert.equal(routes.PHASE2_API_SAFETY.telegramCommandExecutionAllowed, false);
});

test('JSON endpoint returns envelope from runtime dir', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-json-'));
  try {
    await writeFile(path.join(dir, 'QuantGod_GovernanceAdvisor.json'), JSON.stringify({ status: 'ok' }), 'utf8');
    const res = await invoke('/api/governance/advisor', { defaultRuntimeDir: dir, repoRoot: dir, rootDir: dir });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.ok, true);
    assert.equal(res.body.data.status, 'ok');
    assert.equal(res.body.safety.readOnlyDataPlane, true);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('JSON endpoint prefers configured MT5 runtime over fresher Dashboard copies', async () => {
  const runtimeDir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-runtime-'));
  const dashboardDir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-dashboard-'));
  try {
    await writeFile(
      path.join(runtimeDir, 'QuantGod_MT5ResearchStats.json'),
      JSON.stringify({ summary: { shadowRows: 671, source: 'mt5-files' } }),
      'utf8',
    );
    await new Promise((resolve) => setTimeout(resolve, 10));
    await writeFile(
      path.join(dashboardDir, 'QuantGod_MT5ResearchStats.json'),
      JSON.stringify({ summary: { shadowRows: 0, source: 'dashboard-copy' } }),
      'utf8',
    );
    const res = await invoke('/api/research/stats', {
      defaultRuntimeDir: runtimeDir,
      repoRoot: dashboardDir,
      rootDir: dashboardDir,
    });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.data.summary.source, 'mt5-files');
    assert.equal(res.body.source.filePath, path.join(runtimeDir, 'QuantGod_MT5ResearchStats.json'));
  } finally {
    await rm(runtimeDir, { recursive: true, force: true });
    await rm(dashboardDir, { recursive: true, force: true });
  }
});

test('CSV endpoint filters by symbol and limit', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-csv-'));
  try {
    await writeFile(
      path.join(dir, 'QuantGod_TradeJournal.csv'),
      'Timestamp,Symbol,Route\n2026-05-01 00:00:00,EURUSDc,MA_Cross\n2026-05-01 00:01:00,XAUUSDc,RSI_Reversal\n',
      'utf8',
    );
    const res = await invoke('/api/trades/journal?symbol=XAUUSDc&limit=1', { defaultRuntimeDir: dir, repoRoot: dir, rootDir: dir });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.data.returnedRows, 1);
    assert.equal(res.body.data.rows[0].Symbol, 'XAUUSDc');
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('CSV trade endpoints can read secondary MT5 runtime by scope', async () => {
  const primaryDir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-primary-'));
  const secondaryDir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-secondary-'));
  try {
    await writeFile(
      path.join(primaryDir, 'QuantGod_TradeJournal.csv'),
      'EventTime,Symbol,AccountLogin\n2026-05-18 10:00:00,USDJPYc,186054398\n',
      'utf8',
    );
    await writeFile(
      path.join(secondaryDir, 'QuantGod_TradeJournal.csv'),
      'EventTime,Symbol,AccountLogin\n2026-05-18 10:01:00,USDJPY,198135388\n',
      'utf8',
    );

    const res = await invoke('/api/trades/journal?scope=secondary&limit=10', {
      defaultRuntimeDir: primaryDir,
      secondaryRuntimeDir: secondaryDir,
      repoRoot: primaryDir,
      rootDir: primaryDir,
    });

    assert.equal(res.statusCode, 200);
    assert.equal(res.body.scope, 'secondary');
    assert.equal(res.body.data.returnedRows, 1);
    assert.equal(res.body.data.rows[0].AccountLogin, '198135388');
    assert.equal(res.body.source.filePath, path.join(secondaryDir, 'QuantGod_TradeJournal.csv'));
  } finally {
    await rm(primaryDir, { recursive: true, force: true });
    await rm(secondaryDir, { recursive: true, force: true });
  }
});

test('CSV endpoint uses partial tail read for large limited ledgers', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-csv-tail-'));
  try {
    const rows = ['Timestamp,Symbol,Route,Note'];
    for (let index = 0; index < 2200; index += 1) {
      rows.push(`2026-05-01 00:${String(index % 60).padStart(2, '0')}:00,USDJPYc,RSI_Reversal,${'x'.repeat(700)}-${index}`);
    }
    await writeFile(path.join(dir, 'QuantGod_TradeJournal.csv'), `${rows.join('\n')}\n`, 'utf8');
    const res = await invoke('/api/trades/journal?symbol=USDJPYc&limit=3', {
      defaultRuntimeDir: dir,
      repoRoot: dir,
      rootDir: dir,
    });
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.data.partialRead, true);
    assert.equal(res.body.data.returnedRows, 3);
    assert.match(res.body.data.rows[2].Note, /2199$/);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('missing files produce safe 404 envelope', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'qg-phase2-missing-'));
  try {
    await mkdir(dir, { recursive: true });
    const res = await invoke('/api/dashboard/state', { defaultRuntimeDir: dir, repoRoot: dir, rootDir: dir });
    assert.equal(res.statusCode, 404);
    assert.equal(res.body.ok, false);
    assert.equal(res.body.safety.orderSendAllowed, false);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
