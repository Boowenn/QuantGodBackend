'use strict';

/**
 * QuantGod Phase 2 local dashboard API routes.
 *
 * The module is deliberately self-contained so it can be inserted into the
 * existing single-file dashboard server without reworking that server.  All
 * data endpoints are local-first and read-only.  Notification endpoints are
 * push-only and never expose trading, close, cancel, credential, or preset
 * mutation capabilities.
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const MAX_BODY_BYTES = 128 * 1024;
const JSON_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
  Pragma: 'no-cache',
  Expires: '0',
};
const CSV_FULL_READ_BYTES = 1024 * 1024;
const CSV_TAIL_MIN_BYTES = 256 * 1024;
const CSV_TAIL_BYTES_PER_ROW = 2048;

const PHASE2_API_SAFETY = Object.freeze({
  mode: 'QUANTGOD_PHASE2_API_V1',
  localOnly: true,
  readOnlyDataPlane: true,
  notificationPushOnly: true,
  orderSendAllowed: false,
  closeAllowed: false,
  cancelAllowed: false,
  credentialStorageAllowed: false,
  livePresetMutationAllowed: false,
  canOverrideKillSwitch: false,
  canMutateGovernanceDecision: false,
  canPromoteOrDemoteRoute: false,
  telegramCommandExecutionAllowed: false,
});

const JSON_ENDPOINTS = Object.freeze({
  '/api/governance/advisor': 'QuantGod_GovernanceAdvisor.json',
  '/api/governance/version-registry': 'QuantGod_StrategyVersionRegistry.json',
  '/api/governance/promotion-gate': 'QuantGod_VersionPromotionGate.json',
  '/api/governance/optimizer-v2': 'QuantGod_OptimizerV2Plan.json',
  '/api/paramlab/status': 'QuantGod_ParamLabStatus.json',
  '/api/paramlab/results': 'QuantGod_ParamLabResults.json',
  '/api/paramlab/scheduler': 'QuantGod_ParamLabAutoScheduler.json',
  '/api/paramlab/recovery': 'QuantGod_ParamLabRunRecovery.json',
  '/api/paramlab/report-watcher': 'QuantGod_ParamLabReportWatcher.json',
  '/api/paramlab/tester-window': 'QuantGod_AutoTesterWindow.json',
  '/api/research/stats': 'QuantGod_MT5ResearchStats.json',
  '/api/research/entry-blockers': 'QuantGod_MT5EntryBlockers.json',
  '/api/dashboard/state': 'QuantGod_Dashboard.json',
  '/api/dashboard/backtest-summary': 'QuantGod_BacktestSummary.json',
  '/api/polymarket/single-market-analysis': 'QuantGod_PolymarketSingleMarketAnalysis.json',
});

const CSV_ENDPOINTS = Object.freeze({
  '/api/trades/journal': 'QuantGod_TradeJournal.csv',
  '/api/trades/close-history': 'QuantGod_CloseHistory.csv',
  '/api/trades/outcome-labels': 'QuantGod_TradeOutcomeLabels.csv',
  '/api/trades/trading-audit': 'QuantGod_MT5TradingAuditLedger.csv',
  '/api/shadow/signals': 'QuantGod_ShadowSignalLedger.csv',
  '/api/shadow/outcomes': 'QuantGod_ShadowOutcomeLedger.csv',
  '/api/shadow/candidates': 'QuantGod_ShadowCandidateLedger.csv',
  '/api/shadow/candidate-outcomes': 'QuantGod_ShadowCandidateOutcomeLedger.csv',
  '/api/paramlab/results-ledger': 'QuantGod_ParamLabResultsLedger.csv',
  '/api/paramlab/scheduler-ledger': 'QuantGod_ParamLabAutoSchedulerLedger.csv',
  '/api/paramlab/report-watcher-ledger': 'QuantGod_ParamLabReportWatcherLedger.csv',
  '/api/paramlab/recovery-ledger': 'QuantGod_ParamLabRunRecoveryLedger.csv',
  '/api/paramlab/tester-window-ledger': 'QuantGod_AutoTesterWindowLedger.csv',
  '/api/research/stats-ledger': 'QuantGod_MT5ResearchStatsLedger.csv',
  '/api/research/entry-blockers-ledger': 'QuantGod_MT5EntryBlockersLedger.csv',
  '/api/research/strategy-evaluation': 'QuantGod_StrategyEvaluationReport.csv',
  '/api/research/regime-evaluation': 'QuantGod_RegimeEvaluationReport.csv',
  '/api/research/manual-alpha': 'QuantGod_ManualAlphaLedger.csv',
  '/api/polymarket/radar-ledger': 'QuantGod_PolymarketMarketRadar.csv',
  '/api/polymarket/ai-score-ledger': 'QuantGod_PolymarketAiScoreV1.csv',
  '/api/polymarket/canary-executor-ledger': 'QuantGod_PolymarketCanaryExecutorLedger.csv',
  '/api/polymarket/canary-position-ledger': 'QuantGod_PolymarketCanaryPositionLedger.csv',
  '/api/polymarket/canary-order-audit-ledger': 'QuantGod_PolymarketCanaryOrderAuditLedger.csv',
  '/api/polymarket/canary-exit-ledger': 'QuantGod_PolymarketCanaryExitLedger.csv',
  '/api/polymarket/auto-governance-ledger': 'QuantGod_PolymarketAutoGovernanceLedger.csv',
  '/api/polymarket/cross-market-linkage-ledger': 'QuantGod_PolymarketCrossMarketLinkage.csv',
  '/api/polymarket/single-market-analysis-ledger': 'QuantGod_PolymarketSingleMarketAnalysisLedger.csv',
  '/api/polymarket/radar-worker-ledger': 'QuantGod_PolymarketRadarWorkerV2.csv',
});

const SECONDARY_SCOPE_CSV_ENDPOINTS = new Set(['/api/trades/journal', '/api/trades/close-history']);

const NOTIFY_ENDPOINTS = new Set([
  '/api/notify/config',
  '/api/notify/history',
  '/api/notify/test',
  '/api/notify/daily-digest',
  '/api/notify/runtime-scan',
  '/api/notify/mt5-ai-monitor/config',
  '/api/notify/mt5-ai-monitor/run',
]);

function urlPathOf(urlValue) {
  const url = new URL(urlValue || '/', 'http://127.0.0.1');
  return url.pathname.replace(/\/+$/, '') || '/';
}

function isPhase2Path(urlValue) {
  const urlPath = urlPathOf(urlValue);
  return (
    Object.prototype.hasOwnProperty.call(JSON_ENDPOINTS, urlPath) ||
    Object.prototype.hasOwnProperty.call(CSV_ENDPOINTS, urlPath) ||
    NOTIFY_ENDPOINTS.has(urlPath)
  );
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, JSON_HEADERS);
  res.end(JSON.stringify(payload, null, 2));
}

function sendError(res, statusCode, endpoint, error, extra = {}) {
  sendJson(res, statusCode, {
    ok: false,
    endpoint,
    error: error && error.message ? error.message : String(error),
    safety: PHASE2_API_SAFETY,
    ...extra,
  });
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error('Request body is too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (!chunks.length) {
        resolve({});
        return;
      }
      const raw = Buffer.concat(chunks).toString('utf8');
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(new Error(`Invalid JSON body: ${error.message}`));
      }
    });
    req.on('error', reject);
  });
}

function safeBaseDirs(ctx = {}) {
  const rootDir = ctx.rootDir || __dirname;
  const repoRoot = ctx.repoRoot || path.resolve(rootDir, '..');
  const runtimeDir = ctx.defaultRuntimeDir || ctx.runtimeDir || process.env.QG_RUNTIME_DIR || process.env.QG_MT5_FILES_DIR || process.env.QG_HFM_FILES || process.env.QG_HFM_FILES_DIR;
  const hfmFiles = process.env.QG_HFM_FILES || process.env.QG_HFM_FILES_DIR;
  const dirs = [rootDir, repoRoot];
  if (runtimeDir) dirs.unshift(runtimeDir);
  if (hfmFiles) dirs.unshift(hfmFiles);
  return [...new Set(dirs.filter(Boolean).map((dir) => path.resolve(dir)))];
}

function secondaryRuntimeDir(ctx = {}) {
  const candidates = [
    ctx.secondaryRuntimeDir,
    process.env.QG_MT5_SECONDARY_FILES_DIR,
    process.env.QG_MT5_SECONDARY_ROOT ? path.join(process.env.QG_MT5_SECONDARY_ROOT, 'MQL5', 'Files') : '',
    process.env.QG_MT5_SECONDARY_WINE_PREFIX
      ? path.join(process.env.QG_MT5_SECONDARY_WINE_PREFIX, 'drive_c', 'Program Files', 'MetaTrader 5', 'MQL5', 'Files')
      : '',
    path.join(
      require('os').homedir(),
      'Library',
      'Application Support',
      'net.metaquotes.wine.metatrader5-live16',
      'drive_c',
      'Program Files',
      'MetaTrader 5',
      'MQL5',
      'Files',
    ),
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate)) || '';
}

function csvScope(searchParams) {
  const scope = String(searchParams.get('scope') || searchParams.get('accountScope') || 'primary').trim().toLowerCase();
  if (scope === 'secondary' || scope === 'live16') return 'secondary';
  return 'primary';
}

function resolveRuntimeFile(fileName, ctx = {}) {
  const baseName = path.basename(fileName || '');
  const candidates = safeBaseDirs(ctx).map((baseDir, priority) => ({
    priority,
    filePath: path.join(baseDir, baseName),
  }));
  const existing = candidates
    .filter((candidate) => fs.existsSync(candidate.filePath))
    .map((candidate) => ({ ...candidate, stat: fs.statSync(candidate.filePath) }))
    .filter((item) => item.stat.isFile())
    .sort((a, b) => a.priority - b.priority || b.stat.mtimeMs - a.stat.mtimeMs);
  return existing[0] || { filePath: candidates[0]?.filePath || baseName, stat: null };
}

function fileMeta(filePath, stat, format) {
  return {
    fileName: path.basename(filePath || ''),
    filePath,
    format,
    exists: Boolean(stat),
    mtimeIso: stat ? stat.mtime.toISOString() : null,
    mtimeMs: stat ? stat.mtimeMs : null,
  };
}

function withEnvelope(payload, endpoint, filePath, stat, format, extra = {}) {
  return {
    ok: true,
    endpoint,
    data: payload,
    source: fileMeta(filePath, stat, format),
    safety: PHASE2_API_SAFETY,
    ...extra,
  };
}

function stripBom(text) {
  return String(text || '').replace(/^\uFEFF/, '');
}

function parseCsv(text) {
  const source = stripBom(text);
  if (!source.trim()) return { headers: [], rows: [] };
  const records = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < source.length; i += 1) {
    const char = source[i];
    const next = source[i + 1];
    if (quoted) {
      if (char === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ',') {
      row.push(field);
      field = '';
    } else if (char === '\n') {
      row.push(field);
      records.push(row);
      row = [];
      field = '';
    } else if (char !== '\r') {
      field += char;
    }
  }
  row.push(field);
  records.push(row);
  const headers = (records.shift() || []).map((header) => String(header || '').trim());
  const rows = records
    .filter((values) => values.some((value) => String(value || '').trim() !== ''))
    .map((values) => Object.fromEntries(headers.map((header, index) => [header || `column_${index}`, values[index] ?? ''])));
  return { headers, rows };
}

function positiveLimit(searchParams) {
  const value = Number.parseInt(searchParams.get('limit') || '', 10);
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.min(value, 5000);
}

function readCsvHeader(filePath) {
  const fd = fs.openSync(filePath, 'r');
  try {
    const buffer = Buffer.alloc(64 * 1024);
    const bytesRead = fs.readSync(fd, buffer, 0, buffer.length, 0);
    const head = buffer.toString('utf8', 0, bytesRead);
    const newline = head.indexOf('\n');
    return (newline >= 0 ? head.slice(0, newline) : head).replace(/\r$/, '');
  } finally {
    fs.closeSync(fd);
  }
}

function readCsvTextForRequest(filePath, stat, searchParams) {
  const limit = positiveLimit(searchParams);
  if (!limit || !stat || stat.size <= CSV_FULL_READ_BYTES) {
    return { text: fs.readFileSync(filePath, 'utf8'), partial: false, bytesRead: stat?.size || 0 };
  }

  const bytesToRead = Math.min(
    stat.size,
    Math.max(CSV_TAIL_MIN_BYTES, limit * CSV_TAIL_BYTES_PER_ROW),
  );
  if (bytesToRead >= stat.size) {
    return { text: fs.readFileSync(filePath, 'utf8'), partial: false, bytesRead: stat.size };
  }

  const fd = fs.openSync(filePath, 'r');
  try {
    const start = Math.max(0, stat.size - bytesToRead);
    const buffer = Buffer.alloc(bytesToRead);
    const bytesRead = fs.readSync(fd, buffer, 0, bytesToRead, start);
    let tail = buffer.toString('utf8', 0, bytesRead);
    const firstNewline = tail.indexOf('\n');
    if (firstNewline >= 0) tail = tail.slice(firstNewline + 1);
    const header = readCsvHeader(filePath);
    return {
      text: `${header}\n${tail}`,
      partial: true,
      bytesRead,
      requestedLimit: limit,
    };
  } finally {
    fs.closeSync(fd);
  }
}

function parseTimeMs(row) {
  const keys = [
    'timestamp', 'Timestamp', 'time', 'Time', 'timeIso', 'TimeIso', 'EventTimeIso', 'OpenTime', 'CloseTime',
    'ServerTime', 'serverTime', 'generatedAt', 'GeneratedAt', 'Date', 'date'
  ];
  for (const key of keys) {
    const raw = row && row[key];
    if (raw === undefined || raw === null || raw === '') continue;
    if (typeof raw === 'number') return raw > 10_000_000_000 ? raw : raw * 1000;
    const str = String(raw).trim();
    if (/^\d{13}$/.test(str)) return Number(str);
    if (/^\d{10}$/.test(str)) return Number(str) * 1000;
    const mt5 = str.match(/^(\d{4})[./-](\d{2})[./-](\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/);
    if (mt5) {
      const parsed = Date.UTC(
        Number(mt5[1]),
        Number(mt5[2]) - 1,
        Number(mt5[3]),
        Number(mt5[4] || 0),
        Number(mt5[5] || 0),
        Number(mt5[6] || 0),
      );
      if (Number.isFinite(parsed)) return parsed;
    }
    const parsed = Date.parse(str);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function rowSymbol(row) {
  return String(
    row?.symbol ?? row?.Symbol ?? row?.BrokerSymbol ?? row?.brokerSymbol ?? row?.CanonicalSymbol ?? row?.canonicalSymbol ?? ''
  ).trim();
}

function filterRows(rows, searchParams) {
  let filtered = Array.isArray(rows) ? [...rows] : [];
  const symbol = String(searchParams.get('symbol') || '').trim().toLowerCase();
  if (symbol) {
    filtered = filtered.filter((row) => rowSymbol(row).toLowerCase() === symbol);
  }
  const route = String(searchParams.get('route') || '').trim().toLowerCase();
  if (route) {
    filtered = filtered.filter((row) => String(row?.Route ?? row?.route ?? row?.Strategy ?? row?.strategy ?? '').toLowerCase() === route);
  }
  const days = Number.parseInt(searchParams.get('days') || '', 10);
  if (Number.isFinite(days) && days > 0) {
    const threshold = Date.now() - days * 24 * 60 * 60 * 1000;
    filtered = filtered.filter((row) => {
      const timeMs = parseTimeMs(row);
      return timeMs === null || timeMs >= threshold;
    });
  }
  const limit = Number.parseInt(searchParams.get('limit') || '', 10);
  if (Number.isFinite(limit) && limit > 0) {
    filtered = filtered.slice(-Math.min(limit, 5000));
  }
  return filtered;
}

function handleJsonEndpoint(req, res, ctx, endpoint, fileName) {
  const resolved = resolveRuntimeFile(fileName, ctx);
  if (!resolved.stat) {
    sendError(res, 404, endpoint, 'file_not_found', { fileName: path.basename(fileName) });
    return true;
  }
  try {
    const text = stripBom(fs.readFileSync(resolved.filePath, 'utf8'));
    const payload = JSON.parse(text || '{}');
    sendJson(res, 200, withEnvelope(payload, endpoint, resolved.filePath, resolved.stat, 'json'));
  } catch (error) {
    sendError(res, 500, endpoint, `json_parse_failed: ${error.message}`, fileMeta(resolved.filePath, resolved.stat, 'json'));
  }
  return true;
}

function handleCsvEndpoint(req, res, ctx, endpoint, fileName) {
  const url = new URL(req.url || '/', 'http://127.0.0.1');
  const scope = csvScope(url.searchParams);
  if (scope === 'secondary' && !SECONDARY_SCOPE_CSV_ENDPOINTS.has(endpoint)) {
    sendError(res, 400, endpoint, 'secondary_scope_not_supported_for_endpoint', { scope });
    return true;
  }
  const secondaryDir = scope === 'secondary' ? secondaryRuntimeDir(ctx) : '';
  const scopedCtx = scope === 'secondary' ? { ...ctx, defaultRuntimeDir: secondaryDir, runtimeDir: secondaryDir } : ctx;
  if (scope === 'secondary' && !secondaryDir) {
    sendError(res, 404, endpoint, 'secondary_runtime_dir_not_found', { scope, fileName: path.basename(fileName) });
    return true;
  }
  const resolved = resolveRuntimeFile(fileName, scopedCtx);
  if (!resolved.stat) {
    sendError(res, 404, endpoint, 'file_not_found', { scope, fileName: path.basename(fileName), rows: [] });
    return true;
  }
  try {
    const csvRead = readCsvTextForRequest(resolved.filePath, resolved.stat, url.searchParams);
    const parsed = parseCsv(csvRead.text);
    const rows = filterRows(parsed.rows, url.searchParams);
    sendJson(
      res,
      200,
      withEnvelope(
        {
          headers: parsed.headers,
          rows,
          totalRows: parsed.rows.length,
          returnedRows: rows.length,
          partialRead: csvRead.partial,
        },
        endpoint,
        resolved.filePath,
        resolved.stat,
        'csv',
        { scope },
      ),
    );
  } catch (error) {
    sendError(res, 500, endpoint, `csv_parse_failed: ${error.message}`, fileMeta(resolved.filePath, resolved.stat, 'csv'));
  }
  return true;
}

function runPythonJson(repoRoot, args, envOverrides = {}, timeoutMs = 20000) {
  return new Promise((resolve) => {
    const pythonBin = process.env.QG_PYTHON_BIN || process.env.QG_PYTHON || process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
    const child = spawn(pythonBin, args, {
      cwd: repoRoot,
      env: { ...process.env, ...envOverrides, PYTHONIOENCODING: 'utf-8' },
      shell: false,
      windowsHide: true,
    });
    let settled = false;
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill();
      resolve({ ok: false, error: 'timeout', stdout, stderr });
    }, timeoutMs);
    child.stdout.on('data', (chunk) => { stdout += chunk.toString('utf8'); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString('utf8'); });
    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ ok: false, error: error.message, stdout, stderr });
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (code !== 0) {
        resolve({ ok: false, exitCode: code, error: stderr.trim() || stdout.trim() || `python exited ${code}`, stdout, stderr });
        return;
      }
      try {
        resolve(JSON.parse(stdout || '{}'));
      } catch (error) {
        resolve({ ok: false, exitCode: code, error: `python returned non-JSON output: ${error.message}`, stdout, stderr });
      }
    });
  });
}

function notifyEnv(ctx = {}) {
  const overrides = {};
  const runtimeDir = ctx.defaultRuntimeDir || ctx.runtimeDir;
  if (runtimeDir) overrides.QG_RUNTIME_DIR = String(runtimeDir);
  return overrides;
}

async function handleNotify(req, res, ctx, endpoint) {
  const method = String(req.method || 'GET').toUpperCase();
  const repoRoot = ctx.repoRoot || path.resolve(ctx.rootDir || __dirname, '..');
  if (endpoint === '/api/notify/config') {
    if (method !== 'GET') {
      sendError(res, 405, endpoint, 'GET required');
      return true;
    }
    const payload = await runPythonJson(repoRoot, [path.join('tools', 'run_notify.py'), 'config'], notifyEnv(ctx));
    sendJson(res, payload.ok === false ? 500 : 200, { ...payload, endpoint, safety: PHASE2_API_SAFETY });
    return true;
  }
  if (endpoint === '/api/notify/history') {
    if (method !== 'GET') {
      sendError(res, 405, endpoint, 'GET required');
      return true;
    }
    const url = new URL(req.url || '/', 'http://127.0.0.1');
    const limit = Math.max(1, Math.min(200, Number.parseInt(url.searchParams.get('limit') || '50', 10) || 50));
    const payload = await runPythonJson(repoRoot, [path.join('tools', 'run_notify.py'), 'history', '--limit', String(limit)], notifyEnv(ctx));
    sendJson(res, payload.ok === false ? 500 : 200, { ...payload, endpoint, safety: PHASE2_API_SAFETY });
    return true;
  }
  if (endpoint === '/api/notify/test') {
    if (method !== 'POST') {
      sendError(res, 405, endpoint, 'POST required');
      return true;
    }
    const body = await readJsonBody(req);
    const message = String(body.message || body.text || 'QuantGod Telegram notification test').slice(0, 1500);
    const eventType = String(body.eventType || body.event_type || 'TEST').toUpperCase().replace(/[^A-Z0-9_]/g, '').slice(0, 48) || 'TEST';
    const args = [path.join('tools', 'run_notify.py'), 'test', '--message', message, '--event-type', eventType];
    if (body.dryRun === true || body.dry_run === true) args.push('--dry-run');
    const payload = await runPythonJson(repoRoot, args, notifyEnv(ctx), 30000);
    sendJson(res, payload.ok === false ? 500 : 200, { ...payload, endpoint, safety: PHASE2_API_SAFETY });
    return true;
  }
  if (endpoint === '/api/notify/daily-digest') {
    if (method !== 'POST') {
      sendError(res, 405, endpoint, 'POST required');
      return true;
    }
    const body = await readJsonBody(req);
    const args = [path.join('tools', 'run_notify.py'), 'daily-digest'];
    if (body.dryRun === true || body.dry_run === true) args.push('--dry-run');
    const payload = await runPythonJson(repoRoot, args, notifyEnv(ctx), 45000);
    sendJson(res, payload.ok === false ? 500 : 200, { ...payload, endpoint, safety: PHASE2_API_SAFETY });
    return true;
  }
  if (endpoint === '/api/notify/runtime-scan') {
    if (method !== 'POST') {
      sendError(res, 405, endpoint, 'POST required');
      return true;
    }
    const body = await readJsonBody(req);
    const args = [path.join('tools', 'run_notify.py'), 'scan-once'];
    if (body.dryRun === true || body.dry_run === true) args.push('--dry-run');
    const payload = await runPythonJson(repoRoot, args, notifyEnv(ctx), 45000);
    sendJson(res, payload.ok === false ? 500 : 200, { ...payload, endpoint, safety: PHASE2_API_SAFETY });
    return true;
  }
  if (endpoint === '/api/notify/mt5-ai-monitor/config') {
    if (method !== 'GET') {
      sendError(res, 405, endpoint, 'GET required');
      return true;
    }
    const payload = await runPythonJson(
      repoRoot,
      [path.join('tools', 'run_mt5_ai_telegram_monitor.py'), 'config'],
      notifyEnv(ctx),
      30000,
    );
    sendJson(res, payload.ok === false ? 500 : 200, { ...payload, endpoint, safety: PHASE2_API_SAFETY });
    return true;
  }
  if (endpoint === '/api/notify/mt5-ai-monitor/run') {
    if (method !== 'POST') {
      sendError(res, 405, endpoint, 'POST required');
      return true;
    }
    const body = await readJsonBody(req);
    const args = [
      path.join('tools', 'run_mt5_ai_telegram_monitor.py'),
      'scan-once',
      '--repo-root',
      repoRoot,
      '--force',
    ];
    const symbols = String(body.symbols || '').trim();
    const timeframes = String(body.timeframes || '').trim();
    const minInterval = Number.parseInt(String(body.minIntervalSeconds || body.min_interval_seconds || ''), 10);
    const minConfidence = Number.parseInt(String(body.minConfidencePct || body.min_confidence_pct || ''), 10);
    if (symbols) args.push('--symbols', symbols);
    if (timeframes) args.push('--timeframes', timeframes);
    if (Number.isFinite(minInterval) && minInterval >= 0) args.push('--min-interval-seconds', String(minInterval));
    if (Number.isFinite(minConfidence) && minConfidence >= 1 && minConfidence <= 100) {
      args.push('--min-confidence-pct', String(minConfidence));
    }
    if (body.send === true && body.dryRun !== true && body.dry_run !== true) args.push('--send');
    if (body.disableNotification === true || body.disable_notification === true) args.push('--disable-notification');
    if (body.noDeepseek === true || body.no_deepseek === true) args.push('--no-deepseek');
    const payload = await runPythonJson(repoRoot, args, notifyEnv(ctx), 120000);
    sendJson(res, payload.ok === false ? 500 : 200, { ...payload, endpoint, safety: PHASE2_API_SAFETY });
    return true;
  }
  return false;
}

async function handle(req, res, ctx = {}) {
  const endpoint = urlPathOf(req.url || '/');
  try {
    if (Object.prototype.hasOwnProperty.call(JSON_ENDPOINTS, endpoint)) {
      if (String(req.method || 'GET').toUpperCase() !== 'GET') {
        sendError(res, 405, endpoint, 'GET required');
        return true;
      }
      return handleJsonEndpoint(req, res, ctx, endpoint, JSON_ENDPOINTS[endpoint]);
    }
    if (Object.prototype.hasOwnProperty.call(CSV_ENDPOINTS, endpoint)) {
      if (String(req.method || 'GET').toUpperCase() !== 'GET') {
        sendError(res, 405, endpoint, 'GET required');
        return true;
      }
      return handleCsvEndpoint(req, res, ctx, endpoint, CSV_ENDPOINTS[endpoint]);
    }
    if (NOTIFY_ENDPOINTS.has(endpoint)) {
      return await handleNotify(req, res, ctx, endpoint);
    }
    sendError(res, 404, endpoint, 'Unsupported Phase 2 endpoint');
    return true;
  } catch (error) {
    sendError(res, 500, endpoint, error);
    return true;
  }
}

module.exports = {
  CSV_ENDPOINTS,
  JSON_ENDPOINTS,
  NOTIFY_ENDPOINTS,
  PHASE2_API_SAFETY,
  handle,
  isPhase2Path,
  parseCsv,
  filterRows,
  sendError,
};
