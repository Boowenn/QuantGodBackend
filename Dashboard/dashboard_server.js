const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const phase1ApiRoutes = require('./phase1_api_routes');
const phase2ApiRoutes = require('./phase2_api_routes');
const phase3ApiRoutes = require('./phase3_api_routes');
const automationChainApiRoutes = require('./automation_chain_api_routes');
const usdjpyStrategyLabApiRoutes = require('./usdjpy_strategy_lab_api_routes');
const caseMemoryApiRoutes = require('./case_memory_api_routes');
const stateApiRoutes = require('./state_api_routes');
const os = require('os');
const { spawn } = require('child_process');

const rootDir = __dirname;
const repoRoot = path.resolve(rootDir, '..');

function loadEnvFile(envPath) {
  if (!fs.existsSync(envPath)) return;
  const lines = fs.readFileSync(envPath, 'utf8').replace(/^\uFEFF/, '').split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const match = trimmed.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match || process.env[match[1]] !== undefined) continue;
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    process.env[match[1]] = value;
  }
}

loadEnvFile(path.join(repoRoot, '.env.local'));
loadEnvFile(path.join(repoRoot, '.env'));

const host = process.env.QG_DASHBOARD_HOST || '127.0.0.1';
const port = Number.parseInt(process.env.QG_DASHBOARD_PORT || '8080', 10) || 8080;
const pythonBin = process.env.QG_PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3');
const configuredRuntimeDir = process.env.QG_RUNTIME_DIR
  || process.env.QG_MT5_FILES_DIR
  || 'C:\\Program Files\\HFM Metatrader 5\\MQL5\\Files';
const configuredRuntimeDirResolved = path.isAbsolute(configuredRuntimeDir)
  ? configuredRuntimeDir
  : path.resolve(repoRoot, configuredRuntimeDir);

function isMacImportSnapshotDir(dir) {
  return String(dir || '').replace(/\\/g, '/').includes('/runtime/mac_import/mt5_files_snapshot');
}

function getMacMt5RootDir() {
  return path.join(
    os.homedir(),
    'Library',
    'Application Support',
    'net.metaquotes.wine.metatrader5',
    'drive_c',
    'Program Files',
    'MetaTrader 5'
  );
}

function getMacMt5FilesDir() {
  return path.join(getMacMt5RootDir(), 'MQL5', 'Files');
}

function isWindowsAbsolutePath(value) {
  return /^[A-Za-z]:[\\/]/.test(String(value || '').trim());
}

function resolveRuntimeDir() {
  const sourceMode = String(process.env.QG_MAC_RUNTIME_SOURCE || 'auto').trim().toLowerCase();
  const macMt5FilesDir = getMacMt5FilesDir();
  if (
    process.platform === 'darwin'
    && fs.existsSync(macMt5FilesDir)
    && (sourceMode === 'mt5' || (sourceMode === 'auto' && isWindowsAbsolutePath(configuredRuntimeDir)))
  ) {
    return macMt5FilesDir;
  }
  if (
    process.platform === 'darwin'
    && fs.existsSync(macMt5FilesDir)
    && (
      sourceMode === 'mt5'
      || (sourceMode === 'auto' && isMacImportSnapshotDir(configuredRuntimeDirResolved))
    )
  ) {
    return macMt5FilesDir;
  }
  return configuredRuntimeDirResolved;
}

const defaultRuntimeDir = resolveRuntimeDir();
const singleMarketRequestName = 'QuantGod_PolymarketSingleMarketRequest.json';
const polymarketRadarName = 'QuantGod_PolymarketMarketRadar.json';
const polymarketRadarWorkerName = 'QuantGod_PolymarketRadarWorkerV2.json';
const polymarketAiScoreName = 'QuantGod_PolymarketAiScoreV1.json';
const polymarketSingleMarketAnalysisName = 'QuantGod_PolymarketSingleMarketAnalysis.json';
const polymarketCrossMarketLinkageName = 'QuantGod_PolymarketCrossMarketLinkage.json';
const polymarketCanaryExecutorContractName = 'QuantGod_PolymarketCanaryExecutorContract.json';
const polymarketAutoGovernanceName = 'QuantGod_PolymarketAutoGovernance.json';
const polymarketCanaryExecutorRunName = 'QuantGod_PolymarketCanaryExecutorRun.json';
const polymarketRealTradeLedgerName = 'QuantGod_PolymarketRealTradeLedger.json';
const polymarketMarketCatalogName = 'QuantGod_PolymarketMarketCatalog.json';
const polymarketAssetOpportunitiesName = 'QuantGod_PolymarketAssetOpportunities.json';
const polymarketHistoryApiScript = path.join(repoRoot, 'tools', 'query_polymarket_history_api.py');
const mt5ReadonlyBridgeScript = path.join(repoRoot, 'tools', 'mt5_readonly_bridge.py');
const mt5SymbolRegistryScript = path.join(repoRoot, 'tools', 'mt5_symbol_registry.py');
const mt5BackendBacktestScript = path.join(repoRoot, 'tools', 'run_mt5_backend_backtest_loop.py');
const mt5TradingClientScript = path.join(repoRoot, 'tools', 'mt5_trading_client.py');
const mt5PendingWorkerScript = path.join(repoRoot, 'tools', 'mt5_pending_order_worker.py');
const mt5PlatformStoreScript = path.join(repoRoot, 'tools', 'mt5_platform_store.py');
const mt5AdaptiveControlScript = path.join(repoRoot, 'tools', 'mt5_adaptive_control_executor.py');
const paramLabAutoTesterScript = path.join(repoRoot, 'tools', 'run_param_lab_auto_tester_window.py');
const dailyReviewScript = path.join(repoRoot, 'tools', 'build_daily_review.py');
const polymarketHistoryTables = new Set([
  'all',
  'opportunities',
  'analyses',
  'simulations',
  'runs',
  'snapshots',
  'worker-runs',
  'worker-trends',
  'worker-queue',
  'cross-linkage',
  'canary-contracts',
  'auto-governance',
  'canary-executor-runs',
  'canary-order-audit',
  'markets',
  'related-assets',
]);
const mt5ReadonlyEndpoints = new Set(['status', 'account', 'positions', 'orders', 'symbols', 'quote', 'snapshot']);
const mt5SymbolRegistryEndpoints = new Set(['registry', 'resolve']);
const mt5TradingEndpoints = new Set(['status', 'profiles', 'save-profile', 'login', 'order', 'close', 'cancel']);
const mt5PlatformEndpoints = new Set([
  'status',
  'operator',
  'credentials',
  'credential',
  'connect',
  'disconnect',
  'strategies',
  'strategy',
  'queue',
  'enqueue',
  'quick-trade',
  'dispatch',
  'queue-retry',
  'queue-cancel',
  'queue-archive',
  'worker-run',
  'ledger',
  'quick-trades',
  'task-runs',
  'positions',
  'trades',
  'symbols',
  'reconcile'
]);
const mt5BackendBacktestName = 'QuantGod_MT5BackendBacktest.json';
const mt5PendingWorkerName = 'QuantGod_MT5PendingOrderWorker.json';
const mt5PlatformStateName = 'QuantGod_MT5PlatformState.json';
const mt5AdaptiveControlName = 'QuantGod_MT5AdaptiveControlActions.json';
const paramLabAutoTesterName = 'QuantGod_AutoTesterWindow.json';
const paramLabAutoTesterLockName = 'QuantGod_AutoTesterWindow.lock.json';
const paramLabAutoTesterLaunchName = 'QuantGod_AutoTesterWindowLaunch.json';
const dailyReviewName = 'QuantGod_DailyReview.json';
const dailyAutopilotName = 'QuantGod_DailyAutopilot.json';
const configuredParamLabHfmRoot = process.env.QG_PARAMLAB_HFM_ROOT
  || path.join(repoRoot, 'runtime', 'ParamLab_Tester_Sandbox', 'live_hfm_placeholder');
const configuredParamLabTesterRoot = process.env.QG_PARAMLAB_TESTER_ROOT
  || process.env.QG_MT5_TESTER_ROOT
  || path.join(repoRoot, 'runtime', 'HFM_MT5_Tester_Isolated');
const defaultParamLabHfmRoot = path.isAbsolute(configuredParamLabHfmRoot)
  ? configuredParamLabHfmRoot
  : path.resolve(repoRoot, configuredParamLabHfmRoot);
const defaultParamLabTesterRoot = path.isAbsolute(configuredParamLabTesterRoot)
  ? configuredParamLabTesterRoot
  : path.resolve(repoRoot, configuredParamLabTesterRoot);
const polymarketReadOnlyJsonFiles = new Set([
  polymarketRadarName,
  polymarketRadarWorkerName,
  polymarketAiScoreName,
  polymarketSingleMarketAnalysisName,
  polymarketCrossMarketLinkageName,
  polymarketCanaryExecutorContractName,
  polymarketAutoGovernanceName,
  polymarketCanaryExecutorRunName,
  polymarketRealTradeLedgerName,
  polymarketMarketCatalogName,
  polymarketAssetOpportunitiesName
]);
const dailyReadOnlyJsonFiles = new Set([
  dailyReviewName,
  dailyAutopilotName
]);
const quantGodReadOnlyJsonFiles = new Set([
  ...polymarketReadOnlyJsonFiles,
  ...dailyReadOnlyJsonFiles
]);

const contentTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.csv': 'text/csv; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const runtimeTextExtensions = new Set(['.json', '.csv', '.txt']);
const utf8Decoder = new TextDecoder('utf-8', { fatal: true });
const shiftJisDecoder = new TextDecoder('shift_jis');

const ALLOWED_ORIGINS = new Set([
  'http://127.0.0.1:5173',
  'http://localhost:5173',
  'http://127.0.0.1:8080',
  'http://localhost:8080',
]);

function corsHeadersFor(req) {
  const origin = (req.headers.origin || '').replace(/\/+$/, '');
  if (ALLOWED_ORIGINS.has(origin)) {
    return {
      'Access-Control-Allow-Origin': origin,
      'Vary': 'Origin'
    };
  }
  return {};
}

function corsPreflightHeadersFor(req) {
  const origin = (req.headers.origin || '').replace(/\/+$/, '');
  if (ALLOWED_ORIGINS.has(origin)) {
    return {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-QuantGod-Local',
      'Vary': 'Origin'
    };
  }
  return {};
}

const CSRF_SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

function isCsrfSafe(req) {
  if (CSRF_SAFE_METHODS.has((req.method || 'GET').toUpperCase())) {
    return true;
  }
  return (req.headers['x-quantgod-local'] || '').trim() === '1';
}

function send(res, statusCode, headers, body) {
  for (const [k, v] of Object.entries(headers)) {
    res.setHeader(k, v);
  }
  res.writeHead(statusCode);
  res.end(body);
}

function sendJson(res, statusCode, payload, req) {
  const cors = req ? corsHeadersFor(req) : {};
  send(res, statusCode, Object.assign({
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    Pragma: 'no-cache',
    Expires: '0',
  }, cors), JSON.stringify(payload, null, 2));
}

function readRequestBody(req, maxBytes = 64 * 1024) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on('data', (chunk) => {
      total += chunk.length;
      if (total > maxBytes) {
        reject(new Error('Request body too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function safeJsonPayload(text) {
  try {
    let normalized = String(text || '{}').replace(/^\uFEFF/, '').trim();
    if ((normalized.startsWith("'") && normalized.endsWith("'")) || (normalized.startsWith('"') && normalized.endsWith('"'))) {
      normalized = normalized.slice(1, -1);
    }
    normalized = normalized.replace(/\\"/g, '"');
    let payload = JSON.parse(normalized || '{}');
    if (typeof payload === 'string') {
      payload = JSON.parse(payload);
    }
    return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
  } catch (_) {
    return {};
  }
}

function cleanSingleMarketQuery(value) {
  return String(value || '').replace(/\s+/g, ' ').trim().slice(0, 800);
}

function writeSingleMarketRequest(payload) {
  const query = cleanSingleMarketQuery(
    payload.query || payload.url || payload.marketUrl || payload.marketId || payload.title || payload.question
  );
  if (!query) {
    throw new Error('query is required');
  }

  const request = {
    mode: 'POLYMARKET_SINGLE_MARKET_REQUEST_V1',
    generatedAt: new Date().toISOString(),
    source: 'dashboard_local_input',
    query,
    url: cleanSingleMarketQuery(payload.url || ''),
    marketId: cleanSingleMarketQuery(payload.marketId || ''),
    title: cleanSingleMarketQuery(payload.title || ''),
    note: 'Research-only request. The analyzer may read Gamma API but cannot write wallet orders or mutate MT5.'
  };
  const text = JSON.stringify(request, null, 2);
  const targets = [path.join(rootDir, singleMarketRequestName)];
  if (fs.existsSync(defaultRuntimeDir)) {
    targets.push(path.join(defaultRuntimeDir, singleMarketRequestName));
  }
  const written = [];
  for (const target of targets) {
    fs.writeFileSync(target, text, 'utf8');
    written.push(target);
  }
  return { request, written };
}

function runSingleMarketAnalyzer() {
  return new Promise((resolve) => {
    const script = path.join(repoRoot, 'tools', 'analyze_polymarket_single_market.py');
    if (!fs.existsSync(script)) {
      resolve({ skipped: true, reason: 'analyzer_not_found' });
      return;
    }
    const child = spawn(pythonBin, [
      script,
      '--runtime-dir',
      defaultRuntimeDir,
      '--dashboard-dir',
      rootDir
    ], {
      cwd: repoRoot,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      resolve({ skipped: false, exitCode: -1, stdout, stderr: error.message });
    });
    child.on('close', (code) => {
      resolve({ skipped: false, exitCode: code, stdout: stdout.trim(), stderr: stderr.trim() });
    });
  });
}

function runJsonPython(script, args = [], timeoutMs = 15000) {
  return new Promise((resolve) => {
    if (!fs.existsSync(script)) {
      resolve({ ok: false, skipped: true, reason: 'script_not_found', script });
      return;
    }
    const child = spawn(pythonBin, [script, ...args], {
      cwd: repoRoot,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });
    let settled = false;
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill();
      resolve({ ok: false, skipped: false, exitCode: -1, stdout, stderr: 'timeout' });
    }, timeoutMs);
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ ok: false, skipped: false, exitCode: -1, stdout, stderr: error.message });
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (code !== 0) {
        resolve({ ok: false, skipped: false, exitCode: code, stdout, stderr: stderr.trim() });
        return;
      }
      try {
        resolve({ ok: true, skipped: false, exitCode: code, payload: JSON.parse(stdout) });
      } catch (error) {
        resolve({ ok: false, skipped: false, exitCode: code, stdout, stderr: `json_parse_failed: ${error.message}` });
      }
    });
  });
}

function runPlainPython(script, args = [], timeoutMs = 15000) {
  return new Promise((resolve) => {
    if (!fs.existsSync(script)) {
      resolve({ ok: false, skipped: true, reason: 'script_not_found', script });
      return;
    }
    const child = spawn(pythonBin, [script, ...args], {
      cwd: repoRoot,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });
    let settled = false;
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill();
      resolve({ ok: false, skipped: false, exitCode: -1, stdout, stderr: 'timeout' });
    }, timeoutMs);
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ ok: false, skipped: false, exitCode: -1, stdout, stderr: error.message });
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({
        ok: code === 0,
        skipped: false,
        exitCode: code,
        stdout: stdout.trim(),
        stderr: stderr.trim()
      });
    });
  });
}

async function runJsonPythonPayload(script, args = [], payload = {}, timeoutMs = 15000) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qg-mt5-payload-'));
  const payloadPath = path.join(tempDir, 'payload.json');
  fs.writeFileSync(payloadPath, JSON.stringify(payload || {}, null, 2), 'utf8');
  try {
    return await runJsonPython(script, [...args, '--payload-file', payloadPath], timeoutMs);
  } finally {
    try { fs.unlinkSync(payloadPath); } catch (_) {}
    try { fs.rmdirSync(tempDir); } catch (_) {}
  }
}

function readQuantGodJsonFile(fileName) {
  const base = path.basename(fileName || '');
  if (!quantGodReadOnlyJsonFiles.has(base)) {
    throw new Error(`unsupported read-only json file: ${base}`);
  }
  const candidates = [path.join(rootDir, base)];
  if (fs.existsSync(defaultRuntimeDir)) {
    candidates.push(path.join(defaultRuntimeDir, base));
  }
  const existing = candidates
    .filter((candidate) => fs.existsSync(candidate))
    .map((candidate) => ({ candidate, mtimeMs: fs.statSync(candidate).mtimeMs }))
    .sort((a, b) => b.mtimeMs - a.mtimeMs);
  let lastError = null;
  for (const item of existing) {
    try {
      const text = fs.readFileSync(item.candidate, 'utf8').replace(/^\uFEFF/, '');
      return { payload: JSON.parse(text), filePath: item.candidate };
    } catch (error) {
      lastError = error;
    }
  }
  if (lastError) throw lastError;
  throw new Error(`file not found: ${base}`);
}

function withServiceMeta(payload, endpoint, filePath) {
  const source = {
    service: 'quantgod_dashboard_local_api',
    endpoint,
    filePath,
    readOnly: true,
    walletWriteAllowed: false,
    orderSendAllowed: false,
    mutatesMt5: false
  };
  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    return { ...payload, _api: source };
  }
  return { payload, _api: source };
}

function jstDateKey(date = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date);
}

function dateKeyFromValue(value) {
  if (!value) return '';
  const text = String(value).trim();
  const match = text.match(/(\d{4})[./-](\d{2})[./-](\d{2})/);
  if (match) return `${match[1]}-${match[2]}-${match[3]}`;
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return '';
  return jstDateKey(new Date(parsed));
}

function dailyReviewDateKeys(payload = {}) {
  return [
    payload.generatedAtIso,
    payload.generatedAt,
    payload.timestamp,
    payload.summary?.dailyReviewGeneratedAtIso,
    payload.summary?.generatedAtIso,
    payload.dailyPnl?.date,
    payload.summary?.dailyReviewDateJst
  ].map(dateKeyFromValue).filter(Boolean);
}

function isDailyReviewFresh(payload = {}, filePath = '') {
  const today = jstDateKey();
  const keys = dailyReviewDateKeys(payload);
  if (keys.includes(today)) return true;
  if (keys.length) return false;
  if (filePath && fs.existsSync(filePath)) {
    return jstDateKey(fs.statSync(filePath).mtime) === today;
  }
  return false;
}

function recentMt5LogDateNames(days = 3) {
  const names = [];
  for (let offset = 0; offset < days; offset += 1) {
    const date = new Date();
    date.setDate(date.getDate() - offset);
    const y = String(date.getFullYear());
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    names.push(`${y}${m}${d}`);
  }
  return names;
}

function readTailLines(filePath, maxBytes = 256 * 1024) {
  const stat = fs.statSync(filePath);
  const size = Math.min(stat.size, maxBytes);
  const buffer = Buffer.alloc(size);
  const fd = fs.openSync(filePath, 'r');
  try {
    fs.readSync(fd, buffer, 0, size, Math.max(0, stat.size - size));
  } finally {
    fs.closeSync(fd);
  }
  const hasUtf16Nuls = buffer.includes(0);
  const text = buffer
    .toString(hasUtf16Nuls ? 'utf16le' : 'utf8')
    .replace(/^\uFEFF/, '')
    .replace(/\u0000/g, '');
  return text.split(/\r?\n/).filter(Boolean);
}

function logDatePrefix(dateName) {
  const match = String(dateName || '').match(/^(\d{4})(\d{2})(\d{2})$/);
  return match ? `${match[1]}.${match[2]}.${match[3]}` : '';
}

function parseMt5AuthorizationLine(line, dateName = '') {
  const accountRejected = String(line || '').match(/(?:^|\s)(?:(\d{4}\.\d{2}\.\d{2} )?(\d{2}:\d{2}:\d{2}\.\d+)\s+)?Accounts\s+deleted due security reason/i);
  if (accountRejected) {
    const prefix = accountRejected[1] ? accountRejected[1].trim() : logDatePrefix(dateName);
    return {
      type: 'AUTH_CONFIG_REJECTED',
      logTime: [prefix, accountRejected[2]].filter(Boolean).join(' '),
      login: '',
      server: '',
      reason: 'accounts.dat deleted due security reason',
      message: 'copied MT5 account store was rejected by terminal security'
    };
  }
  const failure = String(line || '').match(/^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+Network\s+'([^']+)':\s+authorization on ([^\s]+) failed \(([^)]+)\)/i);
  const shortFailure = failure || String(line || '').match(/(?:^|\s)(\d{2}:\d{2}:\d{2}\.\d+)\s+Network\s+'([^']+)':\s+authorization on ([^\s]+) failed \(([^)]+)\)/i);
  if (shortFailure) {
    const hasDate = /^\d{4}\./.test(shortFailure[1]);
    const logTime = hasDate ? shortFailure[1] : [logDatePrefix(dateName), shortFailure[1]].filter(Boolean).join(' ');
    return {
      type: 'AUTH_FAILED',
      logTime,
      login: shortFailure[2],
      server: shortFailure[3],
      reason: shortFailure[4],
      message: `authorization failed: ${shortFailure[4]}`
    };
  }
  const success = String(line || '').match(/^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+Network\s+'([^']+)':\s+(?:authorized|authorization).*\b(?:on|to)\s+([^\s]+)/i);
  const shortSuccess = success || String(line || '').match(/(?:^|\s)(\d{2}:\d{2}:\d{2}\.\d+)\s+Network\s+'([^']+)':\s+(?:authorized|authorization).*\b(?:on|to)\s+([^\s]+)/i);
  if (shortSuccess && !/failed/i.test(line)) {
    const hasDate = /^\d{4}\./.test(shortSuccess[1]);
    const logTime = hasDate ? shortSuccess[1] : [logDatePrefix(dateName), shortSuccess[1]].filter(Boolean).join(' ');
    return {
      type: 'AUTHORIZED',
      logTime,
      login: shortSuccess[2],
      server: shortSuccess[3],
      reason: '',
      message: 'authorized'
    };
  }
  return null;
}

function readMt5TerminalStatus() {
  if (process.platform !== 'darwin') return null;
  const root = getMacMt5RootDir();
  if (!fs.existsSync(root)) return null;
  const candidates = recentMt5LogDateNames(4).flatMap((dateName) => [
    path.join(root, 'logs', `${dateName}.log`),
    path.join(root, 'Logs', `${dateName}.log`),
    path.join(root, 'MQL5', 'logs', `${dateName}.log`),
    path.join(root, 'MQL5', 'Logs', `${dateName}.log`)
  ].map((filePath) => ({ filePath, dateName })));
  const files = candidates
    .filter((candidate) => fs.existsSync(candidate.filePath))
    .map((candidate) => ({ ...candidate, stat: fs.statSync(candidate.filePath) }))
    .sort((a, b) => b.stat.mtimeMs - a.stat.mtimeMs);
  const events = [];
  for (const file of files) {
    try {
      for (const line of readTailLines(file.filePath)) {
        const event = parseMt5AuthorizationLine(line, file.dateName);
        if (event) events.push({ ...event, filePath: file.filePath });
      }
    } catch (_) {
      // Ignore unreadable Wine log tails; this endpoint must stay read-only and best-effort.
    }
  }
  events.sort((a, b) => String(a.logTime).localeCompare(String(b.logTime)));
  const lastAuthorization = [...events].reverse().find((event) => event.type === 'AUTHORIZED') || null;
  const lastAuthFailure = [...events].reverse().find((event) => event.type === 'AUTH_FAILED') || null;
  const latestEvent = events[events.length - 1] || null;
  return {
    status: latestEvent?.type || 'NO_AUTH_EVENT',
    lastAuthFailure,
    lastAuthorization,
    logFile: latestEvent?.filePath || files[0]?.filePath || '',
    logMtimeIso: files[0]?.stat?.mtime ? files[0].stat.mtime.toISOString() : '',
    readOnly: true,
    orderSendAllowed: false,
    mutatesMt5: false
  };
}

async function queryPolymarketHistory(table, query = '', limit = '50', offset = '0') {
  return runJsonPython(polymarketHistoryApiScript, [
    '--repo-root',
    repoRoot,
    '--table',
    table,
    '--q',
    query,
    '--limit',
    String(limit),
    '--offset',
    String(offset)
  ], 15000);
}

function cleanMt5ReadonlyParam(value, maxLength = 160) {
  return String(value || '').replace(/\s+/g, ' ').trim().slice(0, maxLength);
}

function clampMt5ReadonlyLimit(value, fallback = 120, max = 2000) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(0, Math.min(parsed, max));
}

function buildMt5ReadonlyArgs(endpoint, parsedUrl) {
  const params = parsedUrl.searchParams;
  const args = ['--endpoint', endpoint];
  const symbol = cleanMt5ReadonlyParam(params.get('symbol') || params.get('focusSymbol') || '');
  const group = cleanMt5ReadonlyParam(params.get('group') || '*', 120) || '*';
  const query = cleanMt5ReadonlyParam(params.get('q') || params.get('query') || '', 120);
  const limit = clampMt5ReadonlyLimit(params.get('limit'), 120);
  const symbolsLimit = clampMt5ReadonlyLimit(params.get('symbolsLimit') || params.get('symbols_limit'), 120);

  if (symbol) args.push('--symbol', symbol);
  args.push('--group', group);
  if (query) args.push('--query', query);
  args.push('--limit', String(limit));
  args.push('--symbols-limit', String(symbolsLimit));
  return args;
}

async function handleMt5Readonly(req, res, endpoint) {
  if (!mt5ReadonlyEndpoints.has(endpoint)) {
    sendJson(res, 404, {
      ok: false,
      status: 'NOT_FOUND',
      endpoint,
      error: 'unsupported_mt5_readonly_endpoint',
      supportedEndpoints: Array.from(mt5ReadonlyEndpoints).sort(),
      safety: {
        readOnly: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        credentialStorageAllowed: false,
        livePresetMutationAllowed: false,
        mutatesMt5: false
      }
    });
    return;
  }
  const normalizedEndpoint = endpoint;
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const result = await runJsonPython(mt5ReadonlyBridgeScript, buildMt5ReadonlyArgs(normalizedEndpoint, parsed), 12000);
    if (!result.ok) {
      const terminal = readMt5TerminalStatus();
      sendJson(res, 200, {
        ok: false,
        status: 'UNAVAILABLE',
        endpoint: normalizedEndpoint,
        error: result.stderr || result.reason || 'mt5_readonly_bridge_failed',
        detail: result,
        ...(terminal ? { terminal } : {}),
        safety: {
          readOnly: true,
          orderSendAllowed: false,
          closeAllowed: false,
          cancelAllowed: false,
          credentialStorageAllowed: false,
          livePresetMutationAllowed: false,
          mutatesMt5: false
        }
      });
      return;
    }
    const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};
    const terminal = payload?.ok === false || String(payload?.status || '').toUpperCase() === 'UNAVAILABLE'
      ? readMt5TerminalStatus()
      : null;
    sendJson(res, 200, {
      ...payload,
      ...(terminal ? { terminal } : {}),
      _api: {
        service: 'quantgod_dashboard_mt5_readonly_bridge',
        endpoint: `/api/mt5-readonly/${normalizedEndpoint}`,
        script: mt5ReadonlyBridgeScript,
        readOnly: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        mutatesMt5: false
      }
    });
  } catch (error) {
    sendJson(res, 200, {
      ok: false,
      status: 'UNAVAILABLE',
      endpoint: normalizedEndpoint,
      error: error.message || String(error),
      safety: {
        readOnly: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        credentialStorageAllowed: false,
        livePresetMutationAllowed: false,
        mutatesMt5: false
      }
    });
  }
}

function buildMt5SymbolRegistryArgs(endpoint, parsedUrl) {
  const params = parsedUrl.searchParams;
  const args = ['--endpoint', endpoint];
  const symbol = cleanMt5ReadonlyParam(params.get('symbol') || params.get('canonical') || params.get('brokerSymbol') || '', 160);
  const group = cleanMt5ReadonlyParam(params.get('group') || '*', 120) || '*';
  const query = cleanMt5ReadonlyParam(params.get('q') || params.get('query') || '', 120);
  const limit = clampMt5ReadonlyLimit(params.get('limit'), 2000, 5000);

  if (symbol) args.push('--symbol', symbol);
  args.push('--group', group);
  if (query) args.push('--query', query);
  args.push('--limit', String(limit));
  return args;
}

async function handleMt5SymbolRegistry(req, res, endpoint) {
  if (!mt5SymbolRegistryEndpoints.has(endpoint)) {
    sendJson(res, 404, {
      ok: false,
      status: 'NOT_FOUND',
      endpoint,
      error: 'unsupported_mt5_symbol_registry_endpoint',
      supportedEndpoints: Array.from(mt5SymbolRegistryEndpoints).sort(),
      safety: {
        readOnly: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        symbolSelectAllowed: false,
        credentialStorageAllowed: false,
        livePresetMutationAllowed: false,
        mutatesMt5: false
      }
    });
    return;
  }
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const result = await runJsonPython(mt5SymbolRegistryScript, buildMt5SymbolRegistryArgs(endpoint, parsed), 15000);
    if (!result.ok) {
      sendJson(res, 200, {
        ok: false,
        status: 'UNAVAILABLE',
        endpoint,
        error: result.stderr || result.reason || 'mt5_symbol_registry_failed',
        detail: result,
        safety: {
          readOnly: true,
          orderSendAllowed: false,
          closeAllowed: false,
          cancelAllowed: false,
          symbolSelectAllowed: false,
          credentialStorageAllowed: false,
          livePresetMutationAllowed: false,
          mutatesMt5: false
        }
      });
      return;
    }
    const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};
    sendJson(res, 200, {
      ...payload,
      _api: {
        service: 'quantgod_dashboard_mt5_symbol_registry',
        endpoint: endpoint === 'resolve' ? '/api/mt5-symbol-registry/resolve' : '/api/mt5-symbol-registry',
        script: mt5SymbolRegistryScript,
        readOnly: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        symbolSelectAllowed: false,
        mutatesMt5: false
      }
    });
  } catch (error) {
    sendJson(res, 200, {
      ok: false,
      status: 'UNAVAILABLE',
      endpoint,
      error: error.message || String(error),
      safety: {
        readOnly: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        symbolSelectAllowed: false,
        credentialStorageAllowed: false,
        livePresetMutationAllowed: false,
        mutatesMt5: false
      }
    });
  }
}

function clampMt5BackendDays(value, fallback = 180) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(7, Math.min(parsed, 730));
}

function clampMt5BackendTasks(value, fallback = 20) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(1, Math.min(parsed, 80));
}

function clampParamLabAutoTesterTasks(value, fallback = 8) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(1, Math.min(parsed, 12));
}

function clampParamLabAutoTesterMinutes(value, fallback = 90) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(15, Math.min(parsed, 180));
}

function clampParamLabTesterLookbackDays(value, fallback = 2) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(1, Math.min(parsed, 14));
}

function clampParamLabTesterTimeout(value, fallback = 900) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(300, Math.min(parsed, 3600));
}

function formatTesterDateJst(date) {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  return `${year}.${month}.${day}`;
}

function buildDailyTesterBounds(options = {}) {
  const lookbackDays = clampParamLabTesterLookbackDays(
    options.testerLookbackDays || options.tester_lookback_days || process.env.QG_DAILY_AUTOPILOT_TESTER_LOOKBACK_DAYS,
    2
  );
  const terminalTimeoutSeconds = clampParamLabTesterTimeout(
    options.terminalTimeoutSeconds || options.terminal_timeout_seconds || process.env.QG_DAILY_AUTOPILOT_TESTER_TIMEOUT_SECONDS,
    900
  );
  const nowJst = new Date(Date.now() + 9 * 60 * 60 * 1000);
  const startJst = new Date(nowJst.getTime() - lookbackDays * 24 * 60 * 60 * 1000);
  const fromDate = cleanMt5ReadonlyParam(options.fromDate || options.from || '', 32) || formatTesterDateJst(startJst);
  const toDate = cleanMt5ReadonlyParam(options.toDate || options.to || '', 32) || formatTesterDateJst(nowJst);
  return { fromDate, toDate, lookbackDays, terminalTimeoutSeconds };
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
}

function paramLabAutoTesterPaths() {
  return {
    output: path.join(defaultRuntimeDir, paramLabAutoTesterName),
    lock: path.join(defaultRuntimeDir, paramLabAutoTesterLockName),
    launch: path.join(defaultRuntimeDir, paramLabAutoTesterLaunchName)
  };
}

function buildParamLabAutoTesterArgs(options = {}) {
  const maxTasks = clampParamLabAutoTesterTasks(options.maxTasks || options.max_tasks, 8);
  const dailyBounds = buildDailyTesterBounds(options);
  const args = [
    '--repo-root',
    repoRoot,
    '--runtime-dir',
    defaultRuntimeDir,
    '--hfm-root',
    defaultParamLabHfmRoot,
    '--tester-root',
    defaultParamLabTesterRoot,
    '--max-tasks',
    String(maxTasks),
    '--login',
    String(process.env.QG_MT5_LOGIN || process.env.QG_HFM_LOGIN || '186054398'),
    '--server',
    String(process.env.QG_MT5_SERVER || process.env.QG_HFM_SERVER || 'HFMarketsGlobal-Live12'),
    '--from-date',
    dailyBounds.fromDate,
    '--to-date',
    dailyBounds.toDate,
    '--terminal-timeout-seconds',
    String(dailyBounds.terminalTimeoutSeconds)
  ];
  if (options.continuousWatch) {
    args.push('--continuous-watch');
  }
  if (options.runTerminal) {
    args.push('--run-terminal', '--authorized-strategy-tester');
  }
  return args;
}

function writeParamLabAutoTesterLock(options = {}) {
  const paths = paramLabAutoTesterPaths();
  const minutes = clampParamLabAutoTesterMinutes(options.minutes, 90);
  const maxTasks = clampParamLabAutoTesterTasks(options.maxTasks || options.max_tasks, 8);
  const now = new Date();
  const expires = new Date(now.getTime() + minutes * 60 * 1000);
  const lock = {
    schemaVersion: 1,
    purpose: 'PARAM_LAB_STRATEGY_TESTER_ONLY',
    authorized: true,
    testerOnly: true,
    allowRunTerminal: true,
    livePresetMutation: false,
    allowOutsideWindow: false,
    createdAtIso: now.toISOString(),
    expiresAtIso: expires.toISOString(),
    runtimeDir: defaultRuntimeDir,
    hfmRoot: defaultParamLabTesterRoot,
    maxTasks,
    source: 'dashboard_paramlab_auto_tester_button'
  };
  fs.mkdirSync(path.dirname(paths.lock), { recursive: true });
  fs.writeFileSync(paths.lock, JSON.stringify(lock, null, 2), 'utf8');
  return { lock, lockPath: paths.lock };
}

async function evaluateParamLabAutoTester(payload = {}) {
  const args = buildParamLabAutoTesterArgs({
    maxTasks: payload.maxTasks || payload.max_tasks
  });
  const processResult = await runPlainPython(paramLabAutoTesterScript, args, 120000);
  const paths = paramLabAutoTesterPaths();
  let status = null;
  try {
    status = readJsonIfExists(paths.output);
  } catch (error) {
    status = { parseError: error.message || String(error) };
  }
  return {
    ok: processResult.ok,
    action: 'evaluate',
    status,
    process: processResult,
    safety: {
      testerOnly: true,
      guardRequired: true,
      runTerminalRequested: false,
      orderSendAllowed: false,
      livePresetMutationAllowed: false,
      mutatesLiveMt5: false
    }
  };
}

async function handleParamLabAutoTester(req, res, action) {
  const body = req.method === 'POST' ? await readRequestBody(req) : '{}';
  const payload = safeJsonPayload(body);
  if (action === 'lock') {
    const lockResult = writeParamLabAutoTesterLock(payload);
    const evalResult = await evaluateParamLabAutoTester(payload);
    sendJson(res, 200, {
      ok: evalResult.ok,
      action,
      lock: lockResult.lock,
      lockPath: lockResult.lockPath,
      status: evalResult.status,
      process: evalResult.process,
      safety: {
        testerOnly: true,
        shortLivedAuthorization: true,
        runTerminalRequested: false,
        orderSendAllowed: false,
        livePresetMutationAllowed: false,
        mutatesLiveMt5: false
      }
    });
    return;
  }
  if (action === 'evaluate') {
    sendJson(res, 200, await evaluateParamLabAutoTester(payload));
    return;
  }
  if (action !== 'run') {
    sendJson(res, 404, { ok: false, error: 'unsupported_paramlab_auto_tester_action', action });
    return;
  }

  const preflight = await evaluateParamLabAutoTester(payload);
  const summary = preflight.status && preflight.status.summary ? preflight.status.summary : {};
  const gate = preflight.status && preflight.status.gate ? preflight.status.gate : {};
  if (!summary.canRunTerminal) {
    sendJson(res, 200, {
      ok: false,
      action,
      started: false,
      status: preflight.status,
      process: preflight.process,
      blockers: Array.isArray(gate.blockers) ? gate.blockers : [],
      error: 'AUTO_TESTER_WINDOW_BLOCKED',
      safety: {
        testerOnly: true,
        guardRequired: true,
        runTerminalRequested: true,
        runTerminalStarted: false,
        orderSendAllowed: false,
        livePresetMutationAllowed: false,
        mutatesLiveMt5: false
      }
    });
    return;
  }

  const args = buildParamLabAutoTesterArgs({
    maxTasks: payload.maxTasks || payload.max_tasks,
    runTerminal: true,
    continuousWatch: true
  });
  const paths = paramLabAutoTesterPaths();
  const launch = {
    ok: true,
    action,
    started: true,
    launchedAtIso: new Date().toISOString(),
    script: paramLabAutoTesterScript,
    args,
    runtimeDir: defaultRuntimeDir,
    testerRoot: defaultParamLabTesterRoot,
    statusPath: paths.output,
    logPath: paths.launch,
    safety: {
      testerOnly: true,
      guardRequired: true,
      runTerminalRequested: true,
      orderSendAllowed: false,
      livePresetMutationAllowed: false,
      mutatesLiveMt5: false
    }
  };
  fs.mkdirSync(path.dirname(paths.launch), { recursive: true });
  fs.writeFileSync(paths.launch, JSON.stringify(launch, null, 2), 'utf8');
  const child = spawn(pythonBin, [paramLabAutoTesterScript, ...args], {
    cwd: repoRoot,
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
  });
  child.unref();
  sendJson(res, 202, launch);
}

function buildMt5BackendBacktestArgs(parsedUrl) {
  const params = parsedUrl.searchParams;
  const args = [
    '--repo-root',
    repoRoot,
    '--runtime-dir',
    defaultRuntimeDir,
    '--days',
    String(clampMt5BackendDays(params.get('days'), 180)),
    '--max-tasks',
    String(clampMt5BackendTasks(params.get('maxTasks') || params.get('max_tasks'), 20)),
  ];
  const fromDate = cleanMt5ReadonlyParam(params.get('from') || params.get('fromDate') || '', 32);
  const toDate = cleanMt5ReadonlyParam(params.get('to') || params.get('toDate') || '', 32);
  const route = cleanMt5ReadonlyParam(params.get('route') || '', 80);
  if (fromDate) args.push('--from-date', fromDate);
  if (toDate) args.push('--to-date', toDate);
  if (route) args.push('--route', route);
  return args;
}

async function handleMt5BackendBacktest(req, res, forceRun = false) {
  const parsed = new URL(req.url || '/', `http://${host}:${port}`);
  const refresh = forceRun || ['1', 'true', 'yes'].includes(String(parsed.searchParams.get('refresh') || parsed.searchParams.get('run') || '').toLowerCase());
  const target = path.join(defaultRuntimeDir, mt5BackendBacktestName);
  if (!refresh && fs.existsSync(target)) {
    try {
      const payload = JSON.parse(fs.readFileSync(target, 'utf8').replace(/^\uFEFF/, ''));
      sendJson(res, 200, {
        ...payload,
        _api: {
          service: 'quantgod_dashboard_mt5_backend_backtest',
          endpoint: '/api/mt5-backtest-loop',
          filePath: target,
          readOnly: true,
          pythonBacktestOnly: true,
          orderSendAllowed: false,
          closeAllowed: false,
          cancelAllowed: false,
          livePresetMutationAllowed: false,
          mutatesMt5: false
        }
      });
      return;
    } catch (error) {
      sendJson(res, 200, {
        ok: false,
        status: 'UNAVAILABLE',
        error: `mt5_backend_backtest_artifact_unreadable: ${error.message}`,
        safety: {
          readOnly: true,
          pythonBacktestOnly: true,
          orderSendAllowed: false,
          closeAllowed: false,
          cancelAllowed: false,
          livePresetMutationAllowed: false,
          mutatesMt5: false
        }
      });
      return;
    }
  }

  const result = await runJsonPython(mt5BackendBacktestScript, buildMt5BackendBacktestArgs(parsed), 120000);
  if (!result.ok) {
    sendJson(res, 200, {
      ok: false,
      status: 'UNAVAILABLE',
      error: result.stderr || result.reason || 'mt5_backend_backtest_failed',
      detail: result,
      safety: {
        readOnly: true,
        pythonBacktestOnly: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        livePresetMutationAllowed: false,
        mutatesMt5: false
      }
    });
    return;
  }
  const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};
  sendJson(res, 200, {
    ...payload,
    _api: {
      service: 'quantgod_dashboard_mt5_backend_backtest',
      endpoint: '/api/mt5-backtest-loop/run',
      script: mt5BackendBacktestScript,
      readOnly: true,
      pythonBacktestOnly: true,
      orderSendAllowed: false,
      closeAllowed: false,
      cancelAllowed: false,
      livePresetMutationAllowed: false,
      mutatesMt5: false
    }
  });
}

function mt5TradingEndpointFromPath(pathPart) {
  const base = pathPart.replace(/^\/api\/mt5-trading\/?/, '').replace(/^\/api\/mt5\/?/, '');
  if (!base || base === 'status') return 'status';
  if (base === 'profile') return 'save-profile';
  if (base === 'account-profiles') return 'profiles';
  const first = base.split('/').filter(Boolean)[0] || 'status';
  return first === 'profile' ? 'save-profile' : first;
}

function buildMt5TradingArgs(endpoint) {
  return ['--endpoint', endpoint, '--runtime-dir', defaultRuntimeDir];
}

async function handleMt5Trading(req, res, endpoint, extraPayload = {}) {
  const normalized = endpoint === 'profile' ? 'save-profile' : endpoint;
  if (!mt5TradingEndpoints.has(normalized)) {
    sendJson(res, 404, {
      ok: false,
      status: 'NOT_FOUND',
      endpoint: normalized,
      error: 'unsupported_mt5_trading_endpoint',
      supportedEndpoints: Array.from(mt5TradingEndpoints).sort(),
      safety: {
        readOnly: false,
        dryRun: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        credentialStorageAllowed: false,
        livePresetMutationAllowed: false,
        auditLedgerRequired: true,
        mutatesMt5: false
      }
    });
    return;
  }

  try {
    let payload = { ...extraPayload };
    if (req.method === 'POST' || req.method === 'DELETE') {
      const raw = await readRequestBody(req, 128 * 1024).catch(() => '');
      payload = { ...safeJsonPayload(raw), ...payload };
    }
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    if (['1', 'true', 'yes'].includes(String(parsed.searchParams.get('dryRun') || '').toLowerCase())) {
      payload.dryRun = true;
    }
    const result = ['status', 'profiles'].includes(normalized)
      ? await runJsonPython(mt5TradingClientScript, buildMt5TradingArgs(normalized), 15000)
      : await runJsonPythonPayload(mt5TradingClientScript, buildMt5TradingArgs(normalized), payload, 20000);
    if (!result.ok) {
      sendJson(res, 200, {
        ok: false,
        status: 'UNAVAILABLE',
        endpoint: normalized,
        error: result.stderr || result.reason || 'mt5_trading_bridge_failed',
        detail: result,
        safety: {
          readOnly: false,
          dryRun: true,
          orderSendAllowed: false,
          closeAllowed: false,
          cancelAllowed: false,
          credentialStorageAllowed: false,
          livePresetMutationAllowed: false,
          auditLedgerRequired: true,
          mutatesMt5: false
        }
      });
      return;
    }
    const body = result.payload && typeof result.payload === 'object' ? result.payload : {};
    sendJson(res, 200, {
      ...body,
      _api: {
        service: 'quantgod_dashboard_mt5_trading_bridge',
        endpoint: `/api/mt5/${normalized}`,
        script: mt5TradingClientScript,
        readOnly: false,
        guardedMutation: true,
        auditLedgerRequired: true,
        credentialStorageAllowed: false,
        livePresetMutationAllowed: false
      }
    });
  } catch (error) {
    sendJson(res, 200, {
      ok: false,
      status: 'UNAVAILABLE',
      endpoint: normalized,
      error: error.message || String(error),
      safety: {
        readOnly: false,
        dryRun: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        credentialStorageAllowed: false,
        livePresetMutationAllowed: false,
        auditLedgerRequired: true,
        mutatesMt5: false
      }
    });
  }
}

function buildMt5PendingWorkerArgs(parsedUrl, payloadPath = '') {
  const params = parsedUrl.searchParams;
  const maxIntents = clampMt5ReadonlyLimit(params.get('maxIntents') || params.get('max_intents'), 20, 100);
  const args = ['--runtime-dir', defaultRuntimeDir, '--max-intents', String(maxIntents)];
  if (['1', 'true', 'yes'].includes(String(params.get('dryRun') || '').toLowerCase())) {
    args.push('--dry-run');
  }
  if (payloadPath) {
    args.push('--intents', payloadPath);
  }
  return args;
}

async function handleMt5PendingWorker(req, res, forceRun = false) {
  const parsed = new URL(req.url || '/', `http://${host}:${port}`);
  const useDbWorker = ['1', 'true', 'yes'].includes(String(parsed.searchParams.get('dbWorker') || parsed.searchParams.get('platformDb') || '').toLowerCase());
  if (useDbWorker) {
    const result = await runJsonPythonPayload(
      mt5PlatformStoreScript,
      ['--runtime-dir', defaultRuntimeDir, '--endpoint', 'worker-run'],
      { maxOrders: clampMt5ReadonlyLimit(parsed.searchParams.get('maxIntents') || parsed.searchParams.get('maxOrders'), 20, 100), dryRun: true, source: 'dashboard_pending_worker_db_mode' },
      60000
    );
    const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};
    sendJson(res, 200, {
      ...payload,
      _api: {
        service: 'quantgod_dashboard_mt5_platform_db_worker',
        endpoint: '/api/mt5-pending-worker/run?dbWorker=true',
        script: mt5PlatformStoreScript,
        guardedMutation: true,
        dryRunRequired: true,
        auditLedgerRequired: true
      }
    });
    return;
  }
  const target = path.join(defaultRuntimeDir, mt5PendingWorkerName);
  if (!forceRun && req.method === 'GET' && fs.existsSync(target)) {
    try {
      const payload = JSON.parse(fs.readFileSync(target, 'utf8').replace(/^\uFEFF/, ''));
      sendJson(res, 200, {
        ...payload,
        _api: {
          service: 'quantgod_dashboard_mt5_pending_order_worker',
          endpoint: '/api/mt5-pending-worker/status',
          filePath: target,
          guardedMutation: true,
          auditLedgerRequired: true
        }
      });
      return;
    } catch (_) {}
  }

  let tempDir = '';
  let intentsPath = '';
  try {
    if (req.method === 'POST') {
      const body = safeJsonPayload(await readRequestBody(req, 256 * 1024).catch(() => ''));
      if (Array.isArray(body.intents) || Array.isArray(body.orders)) {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qg-mt5-intents-'));
        intentsPath = path.join(tempDir, 'intents.json');
        fs.writeFileSync(intentsPath, JSON.stringify(body, null, 2), 'utf8');
      }
    }
    const result = await runJsonPython(mt5PendingWorkerScript, buildMt5PendingWorkerArgs(parsed, intentsPath), 60000);
    if (!result.ok) {
      sendJson(res, 200, {
        ok: false,
        status: 'UNAVAILABLE',
        endpoint: '/api/mt5-pending-worker/run',
        error: result.stderr || result.reason || 'mt5_pending_worker_failed',
        detail: result,
        safety: {
          readOnly: false,
          dryRun: true,
          orderSendAllowed: false,
          closeAllowed: false,
          cancelAllowed: false,
          auditLedgerRequired: true,
          mutatesMt5: false
        }
      });
      return;
    }
    const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};
    sendJson(res, 200, {
      ...payload,
      _api: {
        service: 'quantgod_dashboard_mt5_pending_order_worker',
        endpoint: '/api/mt5-pending-worker/run',
        script: mt5PendingWorkerScript,
        guardedMutation: true,
        auditLedgerRequired: true
      }
    });
  } finally {
    if (intentsPath) {
      try { fs.unlinkSync(intentsPath); } catch (_) {}
    }
    if (tempDir) {
      try { fs.rmdirSync(tempDir); } catch (_) {}
    }
  }
}

function mt5PlatformEndpointFromPath(pathPart) {
  if (pathPart === '/api/mt5-platform') return 'status';
  const endpoint = path.basename(pathPart);
  return endpoint || 'status';
}

async function handleMt5PlatformStore(req, res, endpoint = 'status') {
  const normalized = mt5PlatformEndpoints.has(endpoint) ? endpoint : 'status';
  try {
    let requestPayload = {};
    if (req.method === 'POST' || req.method === 'DELETE') {
      requestPayload = safeJsonPayload(await readRequestBody(req, 256 * 1024).catch(() => ''));
    }
    const args = ['--runtime-dir', defaultRuntimeDir, '--endpoint', normalized];
    const result = (req.method === 'POST' || req.method === 'DELETE')
      ? await runJsonPythonPayload(mt5PlatformStoreScript, args, requestPayload, normalized === 'dispatch' || normalized === 'worker-run' || normalized === 'symbols' || normalized === 'reconcile' ? 60000 : 20000)
      : await runJsonPython(mt5PlatformStoreScript, args, normalized === 'symbols' || normalized === 'reconcile' ? 60000 : 20000);
    if (!result.ok) {
      sendJson(res, 200, {
        ok: false,
        status: 'UNAVAILABLE',
        endpoint: normalized,
        error: result.stderr || result.reason || 'mt5_platform_store_failed',
        detail: result,
        safety: {
          readOnly: false,
          controlPlaneOnly: true,
          orderSendAllowed: false,
          closeAllowed: false,
          cancelAllowed: false,
          credentialStorageAllowed: false,
          rawPasswordStorageAllowed: false,
          dryRunRequired: true,
          mutatesMt5: false
        }
      });
      return;
    }
    const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};
    sendJson(res, 200, {
      ...payload,
      _api: {
        service: 'quantgod_dashboard_mt5_platform_store',
        endpoint: `/api/mt5-platform/${normalized}`,
        script: mt5PlatformStoreScript,
        controlPlaneOnly: true,
        orderSendAllowed: false,
        rawPasswordStorageAllowed: false,
        dryRunRequired: true
      }
    });
  } catch (error) {
    sendJson(res, 200, {
      ok: false,
      status: 'UNAVAILABLE',
      endpoint: normalized,
      error: error.message || String(error)
    });
  }
}

async function handleMt5AdaptiveControl(req, res, forceRun = false) {
  const target = path.join(defaultRuntimeDir, mt5AdaptiveControlName);
  if (!forceRun && req.method === 'GET' && fs.existsSync(target)) {
    try {
      const payload = JSON.parse(fs.readFileSync(target, 'utf8').replace(/^\uFEFF/, ''));
      sendJson(res, 200, {
        ...payload,
        _api: {
          service: 'quantgod_dashboard_mt5_adaptive_control',
          endpoint: '/api/mt5-adaptive-control/status',
          filePath: target,
          guardedMutation: true,
          livePresetMutationAllowed: false
        }
      });
      return;
    } catch (_) {}
  }
  const parsed = new URL(req.url || '/', `http://${host}:${port}`);
  const applyStaging = forceRun || ['1', 'true', 'yes'].includes(String(parsed.searchParams.get('applyStaging') || parsed.searchParams.get('staging') || '').toLowerCase());
  const applyLive = ['1', 'true', 'yes'].includes(String(parsed.searchParams.get('applyLive') || parsed.searchParams.get('live') || '').toLowerCase());
  const args = ['--runtime-dir', defaultRuntimeDir, '--repo-root', repoRoot];
  if (applyStaging) args.push('--apply-staging');
  if (applyLive) args.push('--apply-live');
  const result = await runJsonPython(mt5AdaptiveControlScript, args, 30000);
  if (!result.ok) {
    sendJson(res, 200, {
      ok: false,
      status: 'UNAVAILABLE',
      error: result.stderr || result.reason || 'mt5_adaptive_control_failed',
      detail: result,
      safety: {
        readOnly: false,
        adaptiveControlExecutor: true,
        orderSendAllowed: false,
        closeAllowed: false,
        cancelAllowed: false,
        livePresetMutationAllowed: false,
        mutatesMt5: false
      }
    });
    return;
  }
  const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};
  sendJson(res, 200, {
    ...payload,
    _api: {
      service: 'quantgod_dashboard_mt5_adaptive_control',
      endpoint: applyStaging ? '/api/mt5-adaptive-control/run' : '/api/mt5-adaptive-control/status',
      script: mt5AdaptiveControlScript,
      guardedMutation: true,
      auditLedgerRequired: true
    }
  });
}

function firstDefined(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && value !== '') return value;
  }
  return '';
}

function toBoolean(value) {
  if (typeof value === 'boolean') return value;
  const normalized = String(value ?? '').trim().toLowerCase();
  return normalized === 'true' || normalized === '1' || normalized === 'yes' || normalized === 'y';
}

function normalizeAnalyzeHistoryRows(rows = []) {
  return rows.map((row, index) => ({
    rowId: index + 1,
    generatedAt: firstDefined(row.generatedAt, row.lastSeenAt, row.seenAt),
    status: firstDefined(row.status, 'OK'),
    decision: firstDefined(row.decision, 'RESEARCH_ONLY_SINGLE_MARKET_NO_BETTING'),
    query: firstDefined(row.query, row.question, row.marketId),
    querySource: firstDefined(row.querySource, row.source, 'history_api'),
    marketId: firstDefined(row.marketId),
    question: firstDefined(row.question, row.eventTitle),
    category: firstDefined(row.category),
    marketProbability: firstDefined(row.marketProbability, row.marketProbabilityPct),
    aiProbability: firstDefined(row.aiProbability, row.aiProbabilityPct),
    divergence: firstDefined(row.divergence, row.divergencePct),
    confidence: firstDefined(row.confidence, row.confidencePct),
    recommendation: firstDefined(row.recommendation, row.recommendedAction),
    risk: firstDefined(row.risk),
    shadowTrack: firstDefined(row.suggestedShadowTrack, row.shadowTrack),
    url: firstDefined(row.polymarketUrl, row.url),
    walletWrite: toBoolean(firstDefined(row.walletWrite, row.walletWriteAllowed)),
    orderSend: toBoolean(firstDefined(row.orderSend, row.orderSendAllowed)),
    historyType: firstDefined(row.historyType, 'analyses'),
    source: 'sqlite_history_api'
  }));
}

function clampSearchLimit(value, fallback = 36) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(8, Math.min(120, parsed));
}

function clampApiLimit(value, fallback = 60) {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(1, Math.min(120, parsed));
}

function searchHaystack(value) {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return value.map(searchHaystack).join(' ');
  if (typeof value === 'object') {
    return Object.values(value).map(searchHaystack).join(' ');
  }
  return String(value);
}

function matchesSearchQuery(value, query) {
  const normalized = String(query || '').trim().toLowerCase();
  if (!normalized) return true;
  return searchHaystack(value).toLowerCase().includes(normalized);
}

function numericScore(...values) {
  for (const value of values) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function clobDetailFields(item = {}) {
  return {
    probabilitySource: firstDefined(item.probabilitySource),
    outcomeTokens: firstDefined(item.outcomeTokens, item.outcomeTokensJson),
    yesTokenId: firstDefined(item.yesTokenId),
    noTokenId: firstDefined(item.noTokenId),
    yesPrice: firstDefined(item.yesPrice),
    noPrice: firstDefined(item.noPrice),
    clobStatus: firstDefined(item.clobStatus),
    clobBestBid: firstDefined(item.clobBestBid),
    clobBestAsk: firstDefined(item.clobBestAsk),
    clobMidpoint: firstDefined(item.clobMidpoint),
    clobSpread: firstDefined(item.clobSpread),
    clobLiquidityUsd: firstDefined(item.clobLiquidityUsd),
    clobDepthScore: firstDefined(item.clobDepthScore)
  };
}

function compactRadarResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'radar',
    sourceLabel: '机会雷达',
    title: firstDefined(item.question, item.slug, item.marketId, '--'),
    subtitle: firstDefined(item.eventTitle, item.category, item.slug),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, item.seenAt, generatedAt),
    risk: firstDefined(item.risk),
    recommendation: firstDefined(item.recommendedAction, 'SHADOW_REVIEW'),
    track: firstDefined(item.suggestedShadowTrack),
    probability: firstDefined(item.probability),
    divergence: firstDefined(item.divergence),
    score: numericScore(item.aiRuleScore, item.ruleScore),
    detail: {
      rank: item.rank,
      volume: firstDefined(item.volume, item.volume24h),
      liquidity: item.liquidity,
      riskFlags: firstDefined(item.riskFlags, item.riskFlagsJson, []),
      ...clobDetailFields(item)
    }
  };
}

function compactMarketCatalogResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'market-catalog',
    sourceLabel: '市场目录',
    title: firstDefined(item.question, item.eventTitle, item.slug, item.marketId, '--'),
    subtitle: firstDefined(item.category, item.recommendedAction, item.risk),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, item.seenAt, item.lastSeenAt, generatedAt),
    risk: firstDefined(item.risk),
    recommendation: firstDefined(item.recommendedAction, 'OBSERVE'),
    track: firstDefined(item.suggestedShadowTrack),
    probability: firstDefined(item.probability),
    divergence: firstDefined(item.divergence),
    score: numericScore(item.aiRuleScore, item.ruleScore),
    detail: {
      historyType: firstDefined(item.historyType, 'markets'),
      rawType: 'market-catalog',
      catalogRank: firstDefined(item.catalogRank, item.rank),
      category: firstDefined(item.category),
      volume: firstDefined(item.volume),
      volume24h: firstDefined(item.volume24h),
      liquidity: firstDefined(item.liquidity),
      spread: firstDefined(item.spread),
      relatedAssetCount: firstDefined(item.relatedAssetCount),
      relatedAssets: firstDefined(item.relatedAssets, item.relatedAssetsJson),
      riskFlags: firstDefined(item.riskFlags, item.riskFlagsJson),
      acceptingOrders: firstDefined(item.acceptingOrders),
      endDate: firstDefined(item.endDate),
      ...clobDetailFields(item)
    }
  };
}

function compactRelatedAssetResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'related-assets',
    sourceLabel: '关联资产机会',
    title: firstDefined(item.question, item.marketId, item.opportunityId, '--'),
    subtitle: `${firstDefined(item.assetSymbol, '--')} · ${firstDefined(item.suggestedAction, item.directionalHint, 'OBSERVE')}`,
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, item.seenAt, item.lastSeenAt, generatedAt),
    risk: firstDefined(item.marketRisk, item.risk),
    recommendation: firstDefined(item.suggestedAction, 'OBSERVE_ONLY'),
    track: firstDefined(item.suggestedShadowTrack),
    probability: firstDefined(item.probability),
    divergence: null,
    score: numericScore(item.confidence, item.marketScore),
    detail: {
      historyType: firstDefined(item.historyType, 'related-assets'),
      rawType: 'related-asset-opportunity',
      opportunityId: firstDefined(item.opportunityId),
      assetSymbol: firstDefined(item.assetSymbol),
      assetMarket: firstDefined(item.assetMarket),
      assetFamily: firstDefined(item.assetFamily),
      bias: firstDefined(item.bias),
      directionalHint: firstDefined(item.directionalHint),
      confidence: firstDefined(item.confidence),
      marketScore: firstDefined(item.marketScore),
      matchedKeywords: firstDefined(item.matchedKeywords, item.matchedKeywordsJson),
      rationale: firstDefined(item.rationale),
      walletWriteAllowed: firstDefined(item.walletWriteAllowed),
      orderSendAllowed: firstDefined(item.orderSendAllowed),
      mt5ExecutionAllowed: firstDefined(item.mt5ExecutionAllowed)
    }
  };
}

function compactAiScoreResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'ai-score',
    sourceLabel: 'AI 评分',
    title: firstDefined(item.question, item.eventTitle, item.marketId, '--'),
    subtitle: firstDefined(item.action, item.nextStep, item.executionMode),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, item.seenAt, generatedAt),
    risk: firstDefined(item.color, item.risk),
    recommendation: firstDefined(item.action, item.recommendedAction),
    track: firstDefined(item.track, item.suggestedShadowTrack),
    probability: firstDefined(item.probability),
    divergence: firstDefined(item.divergence),
    score: numericScore(item.score, item.aiRuleScore),
    detail: {
      reasons: item.reasons || [],
      components: item.components || {},
      nextStep: item.nextStep || '',
      semanticScore: item.semanticScore,
      semanticConfidence: item.semanticConfidence,
      semanticRecommendation: item.semanticRecommendation,
      semanticRisk: item.semanticRisk,
      llmReviewed: item.llmReviewed,
      llmReason: item.llmReview?.reason || '',
      ...clobDetailFields(item)
    }
  };
}

function compactAnalysisResult(row = {}) {
  return {
    sourceType: 'analysis',
    sourceLabel: '单市场分析',
    title: firstDefined(row.question, row.query, row.marketId, '--'),
    subtitle: firstDefined(row.recommendation, row.status, row.decision),
    marketId: firstDefined(row.marketId),
    url: firstDefined(row.url, row.polymarketUrl),
    generatedAt: firstDefined(row.generatedAt, row.seenAt),
    risk: firstDefined(row.risk),
    recommendation: firstDefined(row.recommendation, row.decision, row.status),
    track: firstDefined(row.shadowTrack, row.suggestedShadowTrack),
    probability: firstDefined(row.marketProbability, row.marketProbabilityPct, row.probability),
    divergence: firstDefined(row.divergence, row.divergencePct),
    score: numericScore(row.confidence, row.confidencePct, row.aiRuleScore),
    detail: {
      aiProbability: firstDefined(row.aiProbability, row.aiProbabilityPct),
      confidence: firstDefined(row.confidence, row.confidencePct),
      relatedAssets: firstDefined(row.relatedAssets, row.relatedAssetsJson),
      keyFactors: firstDefined(row.keyFactors, row.keyFactorsJson),
      riskNotes: firstDefined(row.riskNotes, row.riskNotesJson),
      historyType: firstDefined(row.historyType, 'analyses'),
      ...clobDetailFields(row)
    }
  };
}

function compactCrossLinkageResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'cross-linkage',
    sourceLabel: '跨市场联动',
    title: firstDefined(item.question, item.eventTitle, item.marketId, '--'),
    subtitle: firstDefined(item.primaryRiskTag, item.macroRiskState, item.category),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, generatedAt),
    risk: firstDefined(item.macroRiskState, item.sourceRisk),
    recommendation: firstDefined(item.primaryRiskTag, item.macroRiskState, 'AWARENESS_ONLY'),
    track: firstDefined(item.suggestedShadowTrack),
    probability: firstDefined(item.probability),
    divergence: firstDefined(item.divergence),
    score: numericScore(item.confidence, item.sourceScore),
    detail: {
      historyType: 'cross-linkage',
      rawType: 'cross-market-linkage',
      primaryRiskTag: firstDefined(item.primaryRiskTag),
      riskTags: firstDefined(item.riskTags),
      matchedKeywords: firstDefined(item.matchedKeywords),
      linkedMt5Symbols: firstDefined(item.linkedMt5Symbols),
      macroRiskState: firstDefined(item.macroRiskState),
      sourceTypes: firstDefined(item.sourceTypes),
      mt5ExecutionAllowed: firstDefined(item.mt5ExecutionAllowed),
      walletWriteAllowed: firstDefined(item.walletWriteAllowed),
      orderSendAllowed: firstDefined(item.orderSendAllowed)
    }
  };
}

function compactCanaryContractResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'canary-contract',
    sourceLabel: 'Canary 契约',
    title: firstDefined(item.question, item.marketId, item.canaryContractId, '--'),
    subtitle: firstDefined(item.canaryState, item.track, item.side),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, generatedAt),
    risk: firstDefined(item.crossRiskTag, item.macroRiskState, item.aiColor),
    recommendation: firstDefined(item.decision, item.canaryState, 'CANARY_CONTRACT_ONLY_NO_WALLET_WRITE'),
    track: firstDefined(item.track),
    probability: null,
    divergence: null,
    score: numericScore(item.aiScore, item.sourceScore),
    detail: {
      historyType: 'canary-contracts',
      rawType: 'canary-contract',
      canaryContractId: firstDefined(item.canaryContractId),
      canaryEligibleNow: firstDefined(item.canaryEligibleNow),
      referenceStakeUSDC: firstDefined(item.referenceStakeUSDC),
      canaryStakeUSDC: firstDefined(item.canaryStakeUSDC),
      maxSingleBetUSDC: firstDefined(item.maxSingleBetUSDC),
      maxDailyLossUSDC: firstDefined(item.maxDailyLossUSDC),
      takeProfitPct: firstDefined(item.takeProfitPct),
      stopLossPct: firstDefined(item.stopLossPct),
      trailingProfitPct: firstDefined(item.trailingProfitPct),
      dryRunState: firstDefined(item.dryRunState),
      outcomeState: firstDefined(item.outcomeState),
      blockers: firstDefined(item.blockers, item.blockersJson),
      walletWriteAllowed: firstDefined(item.walletWriteAllowed),
      orderSendAllowed: firstDefined(item.orderSendAllowed),
      startsExecutor: firstDefined(item.startsExecutor)
    }
  };
}

function compactCanaryExecutorRunResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'canary-executor-run',
    sourceLabel: '真钱执行守卫',
    title: firstDefined(item.runId, item.executionMode, '--'),
    subtitle: firstDefined(item.decision, item.status, item.executionMode),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, generatedAt),
    risk: firstDefined(item.decision, item.executionMode),
    recommendation: firstDefined(item.decision, 'NO_REAL_ORDER_SENT'),
    track: firstDefined(item.track),
    probability: null,
    divergence: null,
    score: numericScore(item.plannedOrders, item.ordersSent),
    detail: {
      historyType: 'canary-executor-runs',
      rawType: 'canary-executor-run',
      runId: firstDefined(item.runId),
      executionMode: firstDefined(item.executionMode),
      status: firstDefined(item.status),
      plannedOrders: firstDefined(item.summary?.plannedOrders, item.plannedOrders),
      ordersSent: firstDefined(item.summary?.ordersSent, item.ordersSent),
      walletWriteAllowed: firstDefined(item.summary?.walletWriteAllowed, item.walletWriteAllowed),
      orderSendAllowed: firstDefined(item.summary?.orderSendAllowed, item.orderSendAllowed),
      preflightBlockers: firstDefined(item.preflightBlockers, item.preflightBlockersJson),
      lockFile: firstDefined(item.envPreflight?.lockFile, item.lockFile),
      adapter: firstDefined(item.envPreflight?.walletAdapter, item.walletAdapter)
    }
  };
}

function compactCanaryOrderAuditResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'canary-order-audit',
    sourceLabel: '真钱订单审计',
    title: firstDefined(item.question, item.marketId, item.candidateId, item.runId, '--'),
    subtitle: firstDefined(item.decision, item.adapterStatus, item.side),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, generatedAt),
    risk: firstDefined(item.decision, item.adapterStatus),
    recommendation: firstDefined(item.decision, item.adapterStatus, 'BLOCKED_PRE_ORDER'),
    track: firstDefined(item.track),
    probability: firstDefined(item.limitPrice),
    divergence: null,
    score: numericScore(item.stakeUSDC, item.size),
    detail: {
      historyType: 'canary-order-audit',
      rawType: 'canary-order-audit',
      runId: firstDefined(item.runId),
      candidateId: firstDefined(item.candidateId),
      governanceId: firstDefined(item.governanceId),
      side: firstDefined(item.side),
      tokenIdPresent: firstDefined(item.tokenIdPresent),
      limitPrice: firstDefined(item.limitPrice),
      stakeUSDC: firstDefined(item.stakeUSDC),
      size: firstDefined(item.size),
      orderSent: firstDefined(item.orderSent),
      walletWriteAllowed: firstDefined(item.walletWriteAllowed),
      orderSendAllowed: firstDefined(item.orderSendAllowed),
      blockers: firstDefined(item.blockers, item.blockersJson),
      adapterStatus: firstDefined(item.adapterStatus),
      responseId: firstDefined(item.responseId)
    }
  };
}

function compactAutoGovernanceResult(item = {}, generatedAt = '') {
  return {
    sourceType: 'auto-governance',
    sourceLabel: '自动治理',
    title: firstDefined(item.question, item.marketId, item.governanceId, '--'),
    subtitle: firstDefined(item.governanceState, item.track, item.riskLevel),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.polymarketUrl, item.url),
    generatedAt: firstDefined(item.generatedAt, generatedAt),
    risk: firstDefined(item.riskLevel, item.crossRiskTag, item.macroRiskState, item.aiColor),
    recommendation: firstDefined(item.recommendedAction, item.governanceState, 'AUTO_GOVERNANCE_RECOMMENDATIONS_ONLY_NO_WALLET_WRITE'),
    track: firstDefined(item.track),
    probability: null,
    divergence: null,
    score: numericScore(item.score, item.aiScore, item.sourceScore),
    detail: {
      historyType: 'auto-governance',
      rawType: 'auto-governance',
      governanceId: firstDefined(item.governanceId),
      currentState: firstDefined(item.currentState),
      governanceState: firstDefined(item.governanceState),
      recommendedAction: firstDefined(item.recommendedAction),
      riskLevel: firstDefined(item.riskLevel),
      aiScore: firstDefined(item.aiScore),
      sourceScore: firstDefined(item.sourceScore),
      canaryState: firstDefined(item.canaryState),
      dryRunState: firstDefined(item.dryRunState),
      outcomeState: firstDefined(item.outcomeState),
      wouldExitReason: firstDefined(item.wouldExitReason),
      crossRiskTag: firstDefined(item.crossRiskTag),
      macroRiskState: firstDefined(item.macroRiskState),
      blockers: firstDefined(item.blockers, item.blockersJson),
      sourceTypes: firstDefined(item.sourceTypes, item.sourceTypesJson),
      nextTest: firstDefined(item.nextTest),
      walletWriteAllowed: firstDefined(item.walletWriteAllowed),
      orderSendAllowed: firstDefined(item.orderSendAllowed),
      startsExecutor: firstDefined(item.startsExecutor),
      mutatesMt5: firstDefined(item.mutatesMt5),
      canPromoteToLiveExecution: firstDefined(item.canPromoteToLiveExecution)
    }
  };
}
function isWorkerHistoryType(historyType = '') {
  return ['worker-runs', 'worker-trends', 'worker-queue'].includes(String(historyType || '').trim());
}

function isWorkerHistoryRow(row = {}) {
  return isWorkerHistoryType(row.historyType);
}

function isCrossLinkageHistoryRow(row = {}) {
  return String(row.historyType || '').trim() === 'cross-linkage';
}

function isCanaryContractHistoryRow(row = {}) {
  return String(row.historyType || '').trim() === 'canary-contracts';
}

function isAutoGovernanceHistoryRow(row = {}) {
  return String(row.historyType || '').trim() === 'auto-governance';
}

function isCanaryExecutorRunHistoryRow(row = {}) {
  return String(row.historyType || '').trim() === 'canary-executor-runs';
}

function isCanaryOrderAuditHistoryRow(row = {}) {
  return String(row.historyType || '').trim() === 'canary-order-audit';
}

function isMarketCatalogHistoryRow(row = {}) {
  return String(row.historyType || '').trim() === 'markets';
}

function isRelatedAssetHistoryRow(row = {}) {
  return String(row.historyType || '').trim() === 'related-assets';
}

/*
function getHistorySourceLabel(historyType = '') {
  const normalized = String(historyType || '').trim();
  if (normalized === 'worker-runs') return 'Worker 批次';
  if (normalized === 'worker-trends') return '趋势缓存';
  if (normalized === 'worker-queue') return '雷达队列';
  if (normalized === 'cross-linkage') return '跨市场联动';
  if (normalized === 'canary-contracts') return 'Canary 契约';
  if (normalized === 'auto-governance') return '自动治理';
  if (normalized === 'opportunities') return '机会历史';
  if (normalized === 'analyses') return '分析历史';
  if (normalized === 'simulations') return '模拟历史';
  if (normalized === 'runs') return '构建批次';
  if (normalized === 'snapshots') return '研究快照';
  return '历史库';
}

*/
/*
function getHistorySourceLabel(historyType = '') {
  const normalized = String(historyType || '').trim();
  if (normalized === 'markets') return '市场目录';
  if (normalized === 'related-assets') return '相关资产机会';
  if (normalized === 'worker-runs') return 'Worker 批次';
  if (normalized === 'worker-trends') return '趋势缓存';
  if (normalized === 'worker-queue') return '雷达队列';
  if (normalized === 'cross-linkage') return '跨市场联动';
  if (normalized === 'canary-contracts') return 'Canary 契约';
  if (normalized === 'auto-governance') return '自动治理';
  if (normalized === 'opportunities') return '机会历史';
  if (normalized === 'analyses') return '分析历史';
  if (normalized === 'simulations') return '模拟历史';
  if (normalized === 'runs') return '历史批次';
  if (normalized === 'snapshots') return '研究快照';
  return '历史库';
}

*/
function getHistorySourceLabel(historyType = '') {
  const normalized = String(historyType || '').trim();
  if (normalized === 'markets') return '市场目录';
  if (normalized === 'related-assets') return '相关资产机会';
  if (normalized === 'worker-runs') return 'Worker 批次';
  if (normalized === 'worker-trends') return '趋势缓存';
  if (normalized === 'worker-queue') return '雷达队列';
  if (normalized === 'cross-linkage') return '跨市场联动';
  if (normalized === 'canary-contracts') return 'Canary 契约';
  if (normalized === 'auto-governance') return '自动治理';
  if (normalized === 'canary-executor-runs') return '真钱预检';
  if (normalized === 'canary-order-audit') return '真钱订单审计';
  if (normalized === 'opportunities') return '机会历史';
  if (normalized === 'analyses') return '分析历史';
  if (normalized === 'simulations') return '模拟历史';
  if (normalized === 'runs') return '历史批次';
  if (normalized === 'snapshots') return '研究快照';
  return '历史库';
}

function compactHistoryResult(row = {}) {
  const historyType = firstDefined(row.historyType, 'history');
  const workerRow = isWorkerHistoryType(historyType);
  const crossRow = isCrossLinkageHistoryRow(row);
  const canaryRow = isCanaryContractHistoryRow(row);
  const autoGovernanceRow = isAutoGovernanceHistoryRow(row);
  const executorRunRow = isCanaryExecutorRunHistoryRow(row);
  const orderAuditRow = isCanaryOrderAuditHistoryRow(row);
  const marketCatalogRow = isMarketCatalogHistoryRow(row);
  const relatedAssetRow = isRelatedAssetHistoryRow(row);
  const workerSubtitle = firstDefined(
    row.nextAction,
    row.queueState,
    row.trendDirection,
    row.status,
    row.decision,
    row.schemaVersion
  );
  return {
    sourceType: workerRow || crossRow || canaryRow || autoGovernanceRow || executorRunRow || orderAuditRow || marketCatalogRow || relatedAssetRow ? historyType : firstDefined(row.historyType, 'history'),
    sourceLabel: getHistorySourceLabel(historyType),
    title: firstDefined(row.question, row.query, row.topMarket, row.marketId, row.runId, row.mode, '--'),
    subtitle: marketCatalogRow
      ? firstDefined(row.category, row.risk, row.recommendedAction)
      : relatedAssetRow
      ? `${firstDefined(row.assetSymbol, '--')} · ${firstDefined(row.suggestedAction, row.directionalHint, 'OBSERVE')}`
      : crossRow
      ? firstDefined(row.primaryRiskTag, row.macroRiskState, row.category)
      : canaryRow
      ? firstDefined(row.canaryState, row.track, row.side)
      : autoGovernanceRow
      ? firstDefined(row.governanceState, row.recommendedAction, row.riskLevel)
      : executorRunRow
      ? firstDefined(row.decision, row.executionMode, row.status)
      : orderAuditRow
      ? firstDefined(row.decision, row.adapterStatus, row.side)
      : workerRow
      ? workerSubtitle
      : firstDefined(row.recommendation, row.state, row.decision, row.schemaVersion),
    marketId: firstDefined(row.marketId),
    url: firstDefined(row.polymarketUrl, row.url),
    generatedAt: firstDefined(row.generatedAt, row.seenAt, row.lastSeenAt, row.firstSeenAt),
    risk: firstDefined(row.risk, row.marketRisk, row.topRisk, row.crossRiskTag, row.macroRiskState, row.aiColor),
    recommendation: marketCatalogRow
      ? firstDefined(row.recommendedAction, 'MARKET_CATALOG_READ_ONLY')
      : relatedAssetRow
      ? firstDefined(row.suggestedAction, 'RELATED_ASSET_READ_ONLY')
      : crossRow
      ? firstDefined(row.primaryRiskTag, row.macroRiskState, 'AWARENESS_ONLY')
      : canaryRow
      ? firstDefined(row.decision, row.canaryState, 'CANARY_CONTRACT_ONLY_NO_WALLET_WRITE')
      : autoGovernanceRow
      ? firstDefined(row.recommendedAction, row.governanceState, 'AUTO_GOVERNANCE_RECOMMENDATIONS_ONLY_NO_WALLET_WRITE')
      : executorRunRow
      ? firstDefined(row.decision, 'NO_REAL_ORDER_SENT')
      : orderAuditRow
      ? firstDefined(row.decision, row.adapterStatus, 'BLOCKED_PRE_ORDER')
      : workerRow
      ? firstDefined(row.nextAction, row.queueState, row.status, row.decision, 'WORKER_EVIDENCE')
      : firstDefined(row.recommendation, row.recommendedAction, row.state, row.decision),
    track: firstDefined(row.suggestedShadowTrack, row.track, row.source),
    probability: firstDefined(row.probability, row.marketProbability, row.lastProbability),
    divergence: firstDefined(row.divergence, row.probabilityDelta),
    score: numericScore(row.score, row.priorityScore, row.aiRuleScore, row.ruleScore, row.bestAiRuleScore, row.lastAiRuleScore, row.topScore, row.confidence, row.sourceScore, row.aiScore, row.marketScore, row.executedPf),
    detail: {
      historyType,
      source: firstDefined(row.source),
      rawType: marketCatalogRow ? 'market-catalog-history' : (relatedAssetRow ? 'related-asset-history' : (workerRow ? 'worker-history' : (orderAuditRow ? 'canary-order-audit-history' : (executorRunRow ? 'canary-executor-run-history' : (autoGovernanceRow ? 'auto-governance-history' : (canaryRow ? 'canary-history' : 'history')))))),
      catalogRank: firstDefined(row.catalogRank),
      relatedAssetCount: firstDefined(row.relatedAssetCount),
      relatedAssets: firstDefined(row.relatedAssets, row.relatedAssetsJson),
      assetSymbol: firstDefined(row.assetSymbol),
      assetMarket: firstDefined(row.assetMarket),
      assetFamily: firstDefined(row.assetFamily),
      directionalHint: firstDefined(row.directionalHint),
      confidence: firstDefined(row.confidence),
      marketScore: firstDefined(row.marketScore),
      suggestedAction: firstDefined(row.suggestedAction),
      rationale: firstDefined(row.rationale),
      runId: firstDefined(row.runId),
      candidateId: firstDefined(row.candidateId),
      queueState: firstDefined(row.queueState),
      executionMode: firstDefined(row.executionMode),
      nextAction: firstDefined(row.nextAction),
      trendDirection: firstDefined(row.trendDirection),
      seenCount: firstDefined(row.seenCount),
      staleCycles: firstDefined(row.staleCycles),
      probabilityDelta: firstDefined(row.probabilityDelta),
      aiRuleScoreDelta: firstDefined(row.aiRuleScoreDelta),
      volume24hDelta: firstDefined(row.volume24hDelta),
      probabilitySource: firstDefined(row.probabilitySource),
      outcomeTokens: firstDefined(row.outcomeTokens, row.outcomeTokensJson),
      yesTokenId: firstDefined(row.yesTokenId),
      noTokenId: firstDefined(row.noTokenId),
      yesPrice: firstDefined(row.yesPrice),
      noPrice: firstDefined(row.noPrice),
      clobStatus: firstDefined(row.clobStatus),
      clobBestBid: firstDefined(row.clobBestBid),
      clobBestAsk: firstDefined(row.clobBestAsk),
      clobMidpoint: firstDefined(row.clobMidpoint),
      clobSpread: firstDefined(row.clobSpread),
      clobLiquidityUsd: firstDefined(row.clobLiquidityUsd),
      clobDepthScore: firstDefined(row.clobDepthScore),
      candidateQueueSize: firstDefined(row.candidateQueueSize),
      uniqueMarkets: firstDefined(row.uniqueMarkets),
      recurringMarkets: firstDefined(row.recurringMarkets),
      newMarkets: firstDefined(row.newMarkets),
      primaryRiskTag: firstDefined(row.primaryRiskTag),
      riskTags: firstDefined(row.riskTagsJson),
      matchedKeywords: firstDefined(row.matchedKeywordsJson),
      linkedMt5Symbols: firstDefined(row.linkedMt5SymbolsJson),
      macroRiskState: firstDefined(row.macroRiskState),
      sourceTypes: firstDefined(row.sourceTypesJson),
      mt5ExecutionAllowed: firstDefined(row.mt5ExecutionAllowed),
      canaryContractId: firstDefined(row.canaryContractId),
      canaryEligibleNow: firstDefined(row.canaryEligibleNow),
      referenceStakeUSDC: firstDefined(row.referenceStakeUSDC),
      canaryStakeUSDC: firstDefined(row.canaryStakeUSDC),
      governanceId: firstDefined(row.governanceId),
      currentState: firstDefined(row.currentState),
      governanceState: firstDefined(row.governanceState),
      recommendedAction: firstDefined(row.recommendedAction),
      riskLevel: firstDefined(row.riskLevel),
      nextTest: firstDefined(row.nextTest),
      canPromoteToLiveExecution: firstDefined(row.canPromoteToLiveExecution),
      preflightBlockers: firstDefined(row.preflightBlockersJson),
      plannedOrders: firstDefined(row.plannedOrders),
      ordersSent: firstDefined(row.ordersSent),
      tokenIdPresent: firstDefined(row.tokenIdPresent),
      limitPrice: firstDefined(row.limitPrice),
      stakeUSDC: firstDefined(row.stakeUSDC),
      size: firstDefined(row.size),
      orderSent: firstDefined(row.orderSent),
      adapterStatus: firstDefined(row.adapterStatus),
      responseId: firstDefined(row.responseId),
      maxSingleBetUSDC: firstDefined(row.maxSingleBetUSDC),
      maxDailyLossUSDC: firstDefined(row.maxDailyLossUSDC),
      takeProfitPct: firstDefined(row.takeProfitPct),
      stopLossPct: firstDefined(row.stopLossPct),
      trailingProfitPct: firstDefined(row.trailingProfitPct),
      dryRunState: firstDefined(row.dryRunState),
      outcomeState: firstDefined(row.outcomeState),
      blockers: firstDefined(row.blockersJson),
      walletWriteAllowed: firstDefined(row.walletWriteAllowed),
      orderSendAllowed: firstDefined(row.orderSendAllowed),
      startsExecutor: firstDefined(row.startsExecutor)
    }
  };
}

function sortSearchResults(results = []) {
  return results
    .slice()
    .sort((a, b) => {
      const scoreDelta = numericScore(b.score) - numericScore(a.score);
      if (scoreDelta) return scoreDelta;
      const rightTime = Date.parse(b.generatedAt || '') || 0;
      const leftTime = Date.parse(a.generatedAt || '') || 0;
      return rightTime - leftTime;
    });
}

function normalizeMarketGroupValue(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .slice(0, 260);
}

function normalizeMarketGroupKey(item = {}) {
  const marketId = normalizeMarketGroupValue(item.marketId);
  if (marketId) return `market:${marketId}`;

  const url = normalizeMarketGroupValue(item.url);
  if (url) {
    try {
      const parsed = new URL(url);
      const slug = parsed.pathname.replace(/\/+$/g, '').split('/').filter(Boolean).pop();
      return `url:${slug || `${parsed.origin}${parsed.pathname}`}`;
    } catch (_error) {
      return `url:${url}`;
    }
  }

  const title = normalizeMarketGroupValue(item.title);
  if (title) return `title:${title}`;

  const fallback = normalizeMarketGroupValue(firstDefined(item.subtitle, item.sourceType, 'unknown'));
  return `fallback:${fallback}`;
}

function marketRiskRank(risk) {
  const normalized = String(risk || '').trim().toLowerCase();
  if (['red', 'danger', 'high', 'blocked'].includes(normalized)) return 3;
  if (['yellow', 'watch', 'medium', 'warn', 'warning'].includes(normalized)) return 2;
  if (['green', 'good', 'low', 'ok'].includes(normalized)) return 1;
  return 0;
}

function newerTimestamp(left, right) {
  const leftTime = Date.parse(left || '') || 0;
  const rightTime = Date.parse(right || '') || 0;
  return rightTime > leftTime ? right : left;
}

function toSearchEvidenceItem(item = {}) {
  return {
    sourceType: firstDefined(item.sourceType),
    sourceLabel: firstDefined(item.sourceLabel, item.sourceType),
    title: firstDefined(item.title),
    subtitle: firstDefined(item.subtitle),
    marketId: firstDefined(item.marketId),
    url: firstDefined(item.url),
    generatedAt: firstDefined(item.generatedAt),
    risk: firstDefined(item.risk),
    recommendation: firstDefined(item.recommendation),
    track: firstDefined(item.track),
    probability: firstDefined(item.probability),
    divergence: firstDefined(item.divergence),
    score: numericScore(item.score),
    detail: item.detail || {}
  };
}

function mergeMarketSearchGroup(group, item = {}) {
  const itemScore = numericScore(item.score);
  const currentScore = numericScore(group.score);
  const itemTime = item.generatedAt || '';
  const nextTime = newerTimestamp(group.generatedAt, itemTime);
  const itemIsNewer = nextTime === itemTime && itemTime !== group.generatedAt;
  const itemIsHigherScore = itemScore > currentScore;

  group.title = firstDefined(group.title, item.title, item.marketId, item.url, '--');
  group.subtitle = firstDefined(group.subtitle, item.subtitle, item.url, '多源聚合结果');
  group.marketId = firstDefined(group.marketId, item.marketId);
  group.url = firstDefined(group.url, item.url);
  group.generatedAt = nextTime;
  group.score = Math.max(currentScore, itemScore);

  if (marketRiskRank(item.risk) > marketRiskRank(group.risk)) {
    group.risk = item.risk;
  } else {
    group.risk = firstDefined(group.risk, item.risk);
  }

  if (itemIsHigherScore || itemIsNewer || !group.recommendation) {
    group.recommendation = firstDefined(item.recommendation, group.recommendation);
    group.track = firstDefined(item.track, group.track);
  }
  group.probability = firstDefined(group.probability, item.probability);
  group.divergence = firstDefined(group.divergence, item.divergence);

  if (item.sourceType && !group.sourceTypes.includes(item.sourceType)) group.sourceTypes.push(item.sourceType);
  const sourceLabel = firstDefined(item.sourceLabel, item.sourceType);
  if (sourceLabel && !group.sourceLabels.includes(sourceLabel)) group.sourceLabels.push(sourceLabel);

  group.evidence.push(toSearchEvidenceItem(item));
  group.evidence = sortSearchResults(group.evidence);
  group.evidenceCount += 1;
  group.summaryLine = `${group.evidenceCount} 条证据 · ${group.sourceLabels.join(' / ') || '未分类来源'}`;
  return group;
}

function groupSearchResultsByMarket(results = [], limit = 36) {
  const grouped = new Map();
  for (const item of sortSearchResults(results)) {
    const key = normalizeMarketGroupKey(item);
    if (!grouped.has(key)) {
      grouped.set(key, {
        sourceType: 'market-group',
        sourceLabel: '综合证据',
        groupKey: key,
        title: '',
        subtitle: '',
        marketId: '',
        url: '',
        generatedAt: '',
        risk: '',
        recommendation: '',
        track: '',
        probability: '',
        divergence: '',
        score: 0,
        sourceTypes: [],
        sourceLabels: [],
        evidenceCount: 0,
        evidence: [],
        detail: { grouped: true }
      });
    }
    mergeMarketSearchGroup(grouped.get(key), item);
  }

  return Array.from(grouped.values())
    .sort((a, b) => {
      const scoreDelta = numericScore(b.score) - numericScore(a.score);
      if (scoreDelta) return scoreDelta;
      const evidenceDelta = numericScore(b.evidenceCount) - numericScore(a.evidenceCount);
      if (evidenceDelta) return evidenceDelta;
      const rightTime = Date.parse(b.generatedAt || '') || 0;
      const leftTime = Date.parse(a.generatedAt || '') || 0;
      return rightTime - leftTime;
    })
    .slice(0, limit);
}

async function handleSingleMarketRequest(req, res) {
  try {
    const text = await readRequestBody(req);
    const payload = safeJsonPayload(text);
    const saved = writeSingleMarketRequest(payload);
    const analyzer = await runSingleMarketAnalyzer();
    sendJson(res, 200, {
      ok: analyzer.skipped || analyzer.exitCode === 0,
      written: saved.written,
      request: saved.request,
      analyzer
    });
  } catch (error) {
    sendJson(res, 400, { ok: false, error: error.message || String(error) });
  }
}

async function handlePolymarketHistory(req, res) {
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const table = parsed.searchParams.get('table') || 'all';
    if (!polymarketHistoryTables.has(table)) {
      sendJson(res, 400, { ok: false, error: `unsupported table: ${table}` });
      return;
    }
    const query = parsed.searchParams.get('q') || '';
    const limit = parsed.searchParams.get('limit') || '50';
    const offset = parsed.searchParams.get('offset') || '0';
    const result = await queryPolymarketHistory(table, query, limit, offset);
    if (!result.ok) {
      sendJson(res, 500, { ok: false, error: result.stderr || result.reason || 'history_query_failed', detail: result });
      return;
    }
    sendJson(res, 200, result.payload);
  } catch (error) {
    sendJson(res, 400, { ok: false, error: error.message || String(error) });
  }
}

async function handlePolymarketRealTrades(req, res) {
  try {
    const { payload, filePath } = readQuantGodJsonFile(polymarketRealTradeLedgerName);
    const servicePayload = withServiceMeta(payload, '/api/polymarket/real-trades', filePath);
    sendJson(res, 200, {
      ...servicePayload,
      endpoint: '/api/polymarket/real-trades',
      decision: 'READ_ONLY_REAL_TRADE_LEDGER_NO_WALLET_WRITE',
      safety: {
        readOnly: true,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        mutatesMt5: false,
        privateKeysRead: false,
        ...(servicePayload.safety || {})
      }
    });
  } catch (error) {
    sendJson(res, 200, {
      schemaVersion: 'POLYMARKET_REAL_TRADE_LEDGER_V1',
      generatedAt: new Date().toISOString(),
      status: 'SOURCE_MISSING',
      endpoint: '/api/polymarket/real-trades',
      sourceRoot: 'D:\\polymarket',
      sourceFound: false,
      sourceCandidates: [],
      rowsImported: 0,
      summary: {
        realTradeRows: 0,
        closedRows: 0,
        openRows: 0,
        wins: 0,
        winRatePct: null,
        realizedPnlUSDC: 0
      },
      rows: [],
      errors: [{ source: polymarketRealTradeLedgerName, error: error.message || String(error) }],
      note: 'Run tools/import_polymarket_real_trade_ledger.py after restoring D:\\polymarket evidence.',
      decision: 'READ_ONLY_REAL_TRADE_LEDGER_SOURCE_MISSING',
      safety: {
        readOnly: true,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        mutatesMt5: false,
        privateKeysRead: false
      }
    });
  }
}

async function handlePolymarketReadOnlyJson(req, res, fileName, endpoint) {
  try {
    const { payload, filePath } = readQuantGodJsonFile(fileName);
    sendJson(res, 200, withServiceMeta(payload, endpoint, filePath));
  } catch (error) {
    sendJson(res, 404, {
      ok: false,
      error: error.message || String(error),
      endpoint,
      safety: {
        walletWriteAllowed: false,
        orderSendAllowed: false,
        mutatesMt5: false,
        readOnly: true
      }
    });
  }
}

async function handleDailyReviewJson(req, res) {
  let refreshResult = null;
  let shouldRefresh = false;
  try {
    const requestUrl = new URL(req.url || '/api/daily-review', 'http://localhost');
    shouldRefresh = requestUrl.searchParams.get('refresh') === '1';
  } catch (_) {
    shouldRefresh = false;
  }
  try {
    const current = readQuantGodJsonFile(dailyReviewName);
    if (!isDailyReviewFresh(current.payload, current.filePath)) shouldRefresh = true;
  } catch (_) {
    shouldRefresh = true;
  }
  if (shouldRefresh) {
    refreshResult = await runPlainPython(dailyReviewScript, ['--runtime-dir', defaultRuntimeDir], 90000);
  }
  try {
    const { payload, filePath } = readQuantGodJsonFile(dailyReviewName);
    sendJson(res, 200, {
      ...withServiceMeta(payload, '/api/daily-review', filePath),
      _dailyReviewFresh: isDailyReviewFresh(payload, filePath),
      _dailyReviewRefresh: refreshResult || { ok: true, skipped: true, reason: 'fresh' }
    });
  } catch (error) {
    sendJson(res, 404, {
      ok: false,
      error: error.message || String(error),
      endpoint: '/api/daily-review',
      refresh: refreshResult,
      safety: {
        walletWriteAllowed: false,
        orderSendAllowed: false,
        mutatesMt5: false,
        readOnly: true
      }
    });
  }
}

function requestPublicJson(url, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: {
        'accept': 'application/json',
        'user-agent': 'QuantGod-Polymarket-ReadOnly/1.0'
      },
    }, (response) => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => {
        body += chunk;
        if (body.length > 2_000_000) {
          req.destroy(new Error('response_too_large'));
        }
      });
      response.on('end', () => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`HTTP ${response.statusCode}: ${body.slice(0, 240)}`));
          return;
        }
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(new Error(`invalid_json: ${error.message || error}`));
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error(`timeout_${timeoutMs}ms`));
    });
  });
}

function summarizePolymarketBookSide(side = [], depth = 8) {
  const rows = Array.isArray(side) ? side : [];
  return rows.slice(0, depth).reduce((acc, row) => {
    const price = Number(row.price ?? row.px ?? row[0]);
    const size = Number(row.size ?? row.sz ?? row[1]);
    if (Number.isFinite(price) && Number.isFinite(size)) {
      acc.notional += price * size;
      acc.size += size;
      acc.levels += 1;
    }
    return acc;
  }, { notional: 0, size: 0, levels: 0 });
}

function summarizePolymarketOrderBook(book = {}) {
  const bids = Array.isArray(book.bids) ? book.bids : [];
  const asks = Array.isArray(book.asks) ? book.asks : [];
  const bestBid = bids.length ? Number(bids[0].price ?? bids[0].px ?? bids[0][0]) : null;
  const bestAsk = asks.length ? Number(asks[0].price ?? asks[0].px ?? asks[0][0]) : null;
  const spread = Number.isFinite(bestBid) && Number.isFinite(bestAsk) ? Math.max(0, bestAsk - bestBid) : null;
  const bidDepth = summarizePolymarketBookSide(bids);
  const askDepth = summarizePolymarketBookSide(asks);
  const liquidityUsd = bidDepth.notional + askDepth.notional;
  const depthScore = Math.max(0, Math.min(100,
    (bidDepth.levels + askDepth.levels) * 3 +
    Math.min(30, liquidityUsd / 200) +
    (spread !== null ? Math.max(0, 30 - spread * 300) : 0)
  ));
  return {
    bestBid: Number.isFinite(bestBid) ? bestBid : null,
    bestAsk: Number.isFinite(bestAsk) ? bestAsk : null,
    midpoint: Number.isFinite(bestBid) && Number.isFinite(bestAsk) ? (bestBid + bestAsk) / 2 : null,
    spread,
    bidLevels: bidDepth.levels,
    askLevels: askDepth.levels,
    bidDepthUsd: bidDepth.notional,
    askDepthUsd: askDepth.notional,
    liquidityUsd,
    depthScore
  };
}

async function handlePolymarketBook(req, res) {
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const tokenId = String(parsed.searchParams.get('token_id') || parsed.searchParams.get('tokenId') || '').trim();
    if (!tokenId || !/^[A-Za-z0-9_-]{8,140}$/.test(tokenId)) {
      sendJson(res, 400, { ok: false, error: 'token_id_required', endpoint: '/api/polymarket/book' });
      return;
    }
    const timeoutMs = Math.max(1000, Math.min(10000, Number(parsed.searchParams.get('timeoutMs') || 5000)));
    const url = `https://clob.polymarket.com/book?token_id=${encodeURIComponent(tokenId)}`;
    const book = await requestPublicJson(url, timeoutMs);
    const summary = summarizePolymarketOrderBook(book);
    sendJson(res, 200, {
      mode: 'POLYMARKET_PUBLIC_CLOB_BOOK_API_V1',
      status: 'OK',
      generatedAt: new Date().toISOString(),
      source: 'clob.polymarket.com/book',
      tokenId,
      summary,
      book,
      safety: {
        readsPrivateKey: false,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        startsExecutor: false,
        mutatesMt5: false,
        readOnly: true
      }
    });
  } catch (error) {
    sendJson(res, 502, {
      ok: false,
      error: error.message || String(error),
      endpoint: '/api/polymarket/book',
      safety: {
        readsPrivateKey: false,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        startsExecutor: false,
        mutatesMt5: false,
        readOnly: true
      }
    });
  }
}

function sortPolymarketMarketRows(rows = [], sortKey = 'score') {
  const key = String(sortKey || 'score').trim();
  return rows.slice().sort((a, b) => {
    if (key === 'volume') return numericScore(b.volume, b.volume24h) - numericScore(a.volume, a.volume24h);
    if (key === 'liquidity') return numericScore(b.liquidity) - numericScore(a.liquidity);
    if (key === 'probability') return numericScore(b.probability) - numericScore(a.probability);
    if (key === 'related') return numericScore(b.relatedAssetCount) - numericScore(a.relatedAssetCount);
    return numericScore(b.aiRuleScore, b.ruleScore, b.score) - numericScore(a.aiRuleScore, a.ruleScore, a.score);
  });
}

async function handlePolymarketMarkets(req, res) {
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const query = String(parsed.searchParams.get('q') || '').trim().slice(0, 240);
    const category = String(parsed.searchParams.get('category') || '').trim();
    const risk = String(parsed.searchParams.get('risk') || '').trim();
    const sort = String(parsed.searchParams.get('sort') || 'score').trim();
    const limit = clampApiLimit(parsed.searchParams.get('limit'), 60);
    const read = readQuantGodJsonFile(polymarketMarketCatalogName);
    const payload = withServiceMeta(read.payload, '/api/polymarket/markets', read.filePath);
    const rows = Array.isArray(payload.marketCatalog) ? payload.marketCatalog : (Array.isArray(payload.markets) ? payload.markets : []);
    const filtered = sortPolymarketMarketRows(
      rows.filter((row) => {
        if (query && !matchesSearchQuery(row, query)) return false;
        if (category && String(row.category || '') !== category) return false;
        if (risk && String(row.risk || '') !== risk) return false;
        return true;
      }),
      sort
    ).slice(0, limit);
    sendJson(res, 200, {
      ...payload,
      mode: 'POLYMARKET_MARKETS_API_V1',
      status: payload.status || 'OK',
      query,
      filters: { category, risk, sort, limit },
      markets: filtered,
      marketCatalog: filtered,
      summary: {
        ...(payload.summary || {}),
        filteredMarkets: filtered.length,
        sourceMarkets: rows.length,
      },
      safety: {
        readsPrivateKey: false,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        startsExecutor: false,
        mutatesMt5: false,
        readOnly: true,
      },
    });
  } catch (error) {
    sendJson(res, 404, { ok: false, error: error.message || String(error), endpoint: '/api/polymarket/markets' });
  }
}

async function handlePolymarketAssetOpportunities(req, res) {
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const query = String(parsed.searchParams.get('q') || '').trim().slice(0, 240);
    const asset = String(parsed.searchParams.get('asset') || '').trim().toUpperCase();
    const limit = clampApiLimit(parsed.searchParams.get('limit'), 60);
    const read = readQuantGodJsonFile(polymarketAssetOpportunitiesName);
    const payload = withServiceMeta(read.payload, '/api/polymarket/asset-opportunities', read.filePath);
    const rows = Array.isArray(payload.relatedAssetOpportunities)
      ? payload.relatedAssetOpportunities
      : (Array.isArray(payload.assetOpportunities) ? payload.assetOpportunities : []);
    const filtered = rows
      .filter((row) => {
        if (query && !matchesSearchQuery(row, query)) return false;
        if (asset && String(row.assetSymbol || '').toUpperCase() !== asset) return false;
        return true;
      })
      .sort((a, b) => numericScore(b.confidence, b.marketScore) - numericScore(a.confidence, a.marketScore))
      .slice(0, limit);
    sendJson(res, 200, {
      ...payload,
      mode: 'POLYMARKET_ASSET_OPPORTUNITIES_API_V1',
      status: payload.status || 'OK',
      query,
      filters: { asset, limit },
      relatedAssetOpportunities: filtered,
      assetOpportunities: filtered,
      summary: {
        ...(payload.summary || {}),
        filteredOpportunities: filtered.length,
        sourceOpportunities: rows.length,
      },
      safety: {
        readsPrivateKey: false,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        startsExecutor: false,
        mutatesMt5: false,
        readOnly: true,
      },
    });
  } catch (error) {
    sendJson(res, 404, { ok: false, error: error.message || String(error), endpoint: '/api/polymarket/asset-opportunities' });
  }
}

async function handlePolymarketMarketDetail(req, res) {
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const query = String(parsed.searchParams.get('marketId') || parsed.searchParams.get('q') || parsed.searchParams.get('slug') || '').trim().slice(0, 240);
    const catalogRead = readQuantGodJsonFile(polymarketMarketCatalogName);
    const assetRead = readQuantGodJsonFile(polymarketAssetOpportunitiesName);
    const catalog = withServiceMeta(catalogRead.payload, '/api/polymarket/market', catalogRead.filePath);
    const assets = withServiceMeta(assetRead.payload, '/api/polymarket/asset-opportunities', assetRead.filePath);
    const marketRows = Array.isArray(catalog.marketCatalog) ? catalog.marketCatalog : (Array.isArray(catalog.markets) ? catalog.markets : []);
    const market = marketRows.find((row) => {
      if (!query) return false;
      const values = [row.marketId, row.slug, row.catalogId, row.polymarketUrl, row.question].map((value) => String(value || '').toLowerCase());
      return values.some((value) => value.includes(query.toLowerCase()));
    }) || marketRows[0] || {};
    const assetRows = Array.isArray(assets.relatedAssetOpportunities) ? assets.relatedAssetOpportunities : (Array.isArray(assets.assetOpportunities) ? assets.assetOpportunities : []);
    const related = assetRows.filter((row) => {
      if (!market.marketId && !market.question) return false;
      return String(row.marketId || '') === String(market.marketId || '') || String(row.question || '') === String(market.question || '');
    });
    sendJson(res, 200, {
      mode: 'POLYMARKET_MARKET_DETAIL_API_V1',
      status: market.marketId || market.question ? 'OK' : 'EMPTY',
      generatedAt: new Date().toISOString(),
      source: 'quantgod_dashboard_local_api',
      query,
      market,
      relatedAssetOpportunities: related,
      sourceFiles: {
        marketCatalog: catalogRead.filePath,
        assetOpportunities: assetRead.filePath,
      },
      safety: {
        readsPrivateKey: false,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        startsExecutor: false,
        mutatesMt5: false,
        readOnly: true,
      },
    });
  } catch (error) {
    sendJson(res, 404, { ok: false, error: error.message || String(error), endpoint: '/api/polymarket/market' });
  }
}

async function handlePolymarketAnalyzeHistory(req, res) {
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const query = parsed.searchParams.get('q') || '';
    const limit = parsed.searchParams.get('limit') || '80';
    let latest = null;
    let latestPath = '';
    let latestError = '';
    try {
      const read = readQuantGodJsonFile(polymarketSingleMarketAnalysisName);
      latest = withServiceMeta(read.payload, '/api/polymarket/analyze/history', read.filePath);
      latestPath = read.filePath;
    } catch (error) {
      latestError = error.message || String(error);
    }

    const result = await queryPolymarketHistory('analyses', query, limit, '0');
    if (!result.ok) {
      sendJson(res, 500, {
        ok: false,
        error: result.stderr || result.reason || 'analyze_history_query_failed',
        latest,
        latestError,
        detail: result
      });
      return;
    }

    const rows = normalizeAnalyzeHistoryRows(result.payload?.search?.rows || result.payload?.recent?.analyses || []);
    sendJson(res, 200, {
      mode: 'POLYMARKET_ANALYZE_HISTORY_API_V1',
      status: result.payload?.status || 'OK',
      generatedAt: new Date().toISOString(),
      source: 'quantgod_dashboard_local_api',
      decision: 'READ_ONLY_ANALYZE_HISTORY_NO_WALLET_WRITE',
      latest,
      latestPath,
      latestError,
      rows,
      summary: {
        rows: rows.length,
        matched: result.payload?.search?.count || rows.length,
        totalRows: result.payload?.summary?.marketAnalyses || rows.length
      },
      history: result.payload,
      safety: {
        readsPrivateKey: false,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        startsExecutor: false,
        mutatesMt5: false,
        readOnly: true
      }
    });
  } catch (error) {
    sendJson(res, 400, { ok: false, error: error.message || String(error) });
  }
}

async function handlePolymarketSearch(req, res) {
  try {
    const parsed = new URL(req.url || '/', `http://${host}:${port}`);
    const query = String(parsed.searchParams.get('q') || '').trim().slice(0, 240);
    const limit = clampSearchLimit(parsed.searchParams.get('limit'), 36);
    const errors = [];

    let radar = null;
    let radarPath = '';
    try {
      const read = readQuantGodJsonFile(polymarketRadarName);
      radar = withServiceMeta(read.payload, '/api/polymarket/radar', read.filePath);
      radarPath = read.filePath;
    } catch (error) {
      errors.push({ source: 'radar', error: error.message || String(error) });
    }

    let aiScore = null;
    let aiScorePath = '';
    try {
      const read = readQuantGodJsonFile(polymarketAiScoreName);
      aiScore = withServiceMeta(read.payload, '/api/polymarket/ai-score', read.filePath);
      aiScorePath = read.filePath;
    } catch (error) {
      errors.push({ source: 'ai-score', error: error.message || String(error) });
    }

    let crossLinkage = null;
    let crossLinkagePath = '';
    try {
      const read = readQuantGodJsonFile(polymarketCrossMarketLinkageName);
      crossLinkage = withServiceMeta(read.payload, '/api/polymarket/cross-linkage', read.filePath);
      crossLinkagePath = read.filePath;
    } catch (error) {
      errors.push({ source: 'cross-linkage', error: error.message || String(error) });
    }

    let canaryContract = null;
    let canaryContractPath = '';
    try {
      const read = readQuantGodJsonFile(polymarketCanaryExecutorContractName);
      canaryContract = withServiceMeta(read.payload, '/api/polymarket/canary-executor-contract', read.filePath);
      canaryContractPath = read.filePath;
    } catch (error) {
      errors.push({ source: 'canary-contract', error: error.message || String(error) });
    }

    let autoGovernance = null;
    let autoGovernancePath = '';
    try {
      const read = readQuantGodJsonFile(polymarketAutoGovernanceName);
      autoGovernance = withServiceMeta(read.payload, '/api/polymarket/auto-governance', read.filePath);
      autoGovernancePath = read.filePath;
    } catch (error) {
      errors.push({ source: 'auto-governance', error: error.message || String(error) });
    }

    let canaryExecutorRun = null;
    let canaryExecutorRunPath = '';
    try {
      const read = readQuantGodJsonFile(polymarketCanaryExecutorRunName);
      canaryExecutorRun = withServiceMeta(read.payload, '/api/polymarket/canary-executor-run', read.filePath);
      canaryExecutorRunPath = read.filePath;
    } catch (error) {
      errors.push({ source: 'canary-executor-run', error: error.message || String(error) });
    }

    let latestAnalysis = null;
    let latestAnalysisPath = '';
    try {
      const read = readQuantGodJsonFile(polymarketSingleMarketAnalysisName);
      latestAnalysis = withServiceMeta(read.payload, '/api/polymarket/analyze/history', read.filePath);
      latestAnalysisPath = read.filePath;
    } catch (error) {
      errors.push({ source: 'single-analysis-latest', error: error.message || String(error) });
    }

    let marketCatalog = null;
    let marketCatalogPath = '';
    try {
      const read = readQuantGodJsonFile(polymarketMarketCatalogName);
      marketCatalog = withServiceMeta(read.payload, '/api/polymarket/markets', read.filePath);
      marketCatalogPath = read.filePath;
    } catch (error) {
      errors.push({ source: 'market-catalog', error: error.message || String(error) });
    }

    let relatedAssets = null;
    let relatedAssetsPath = '';
    try {
      const read = readQuantGodJsonFile(polymarketAssetOpportunitiesName);
      relatedAssets = withServiceMeta(read.payload, '/api/polymarket/asset-opportunities', read.filePath);
      relatedAssetsPath = read.filePath;
    } catch (error) {
      errors.push({ source: 'related-assets', error: error.message || String(error) });
    }

    const historyResult = await queryPolymarketHistory('all', query, String(limit), '0');
    if (!historyResult.ok) {
      errors.push({ source: 'history', error: historyResult.stderr || historyResult.reason || 'history_query_failed' });
    }

    const analysisResult = await queryPolymarketHistory('analyses', query, String(limit), '0');
    if (!analysisResult.ok) {
      errors.push({ source: 'analysis-history', error: analysisResult.stderr || analysisResult.reason || 'analysis_query_failed' });
    }

    const radarItems = Array.isArray(radar?.radar)
      ? radar.radar.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : [];
    const aiScoreItems = Array.isArray(aiScore?.scores)
      ? aiScore.scores.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : [];
    const crossLinkageItems = Array.isArray(crossLinkage?.linkages)
      ? crossLinkage.linkages.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : [];
    const canaryItems = Array.isArray(canaryContract?.candidateContracts)
      ? canaryContract.candidateContracts.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : [];
    const autoGovernanceItems = Array.isArray(autoGovernance?.governanceDecisions)
      ? autoGovernance.governanceDecisions.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : [];
    const canaryExecutorRunItems = canaryExecutorRun && matchesSearchQuery(canaryExecutorRun, query)
      ? [canaryExecutorRun]
      : [];
    const canaryOrderAuditItems = Array.isArray(canaryExecutorRun?.plannedOrders)
      ? canaryExecutorRun.plannedOrders.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : [];
    const marketCatalogItems = Array.isArray(marketCatalog?.marketCatalog)
      ? marketCatalog.marketCatalog.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : (Array.isArray(marketCatalog?.markets) ? marketCatalog.markets.filter((item) => matchesSearchQuery(item, query)).slice(0, limit) : []);
    const relatedAssetItems = Array.isArray(relatedAssets?.relatedAssetOpportunities)
      ? relatedAssets.relatedAssetOpportunities.filter((item) => matchesSearchQuery(item, query)).slice(0, limit)
      : (Array.isArray(relatedAssets?.assetOpportunities) ? relatedAssets.assetOpportunities.filter((item) => matchesSearchQuery(item, query)).slice(0, limit) : []);

    const historyPayload = historyResult.payload || {};
    const rawHistoryRows = query
      ? (historyPayload.search?.rows || [])
      : [
          ...(historyPayload.recent?.opportunities || []),
          ...(historyPayload.recent?.analyses || []),
          ...(historyPayload.recent?.simulations || []),
        ].slice(0, limit);
    const workerRows = query
      ? rawHistoryRows.filter(isWorkerHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.['worker-runs'] || historyPayload.recent?.workerRuns || []),
          ...(historyPayload.recent?.['worker-trends'] || historyPayload.recent?.workerTrends || []),
          ...(historyPayload.recent?.['worker-queue'] || historyPayload.recent?.workerQueue || []),
        ].slice(0, limit);
    const crossRows = query
      ? rawHistoryRows.filter(isCrossLinkageHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.['cross-linkage'] || historyPayload.recent?.crossMarketLinkage || []),
        ].slice(0, limit);
    const canaryRows = query
      ? rawHistoryRows.filter(isCanaryContractHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.['canary-contracts'] || historyPayload.recent?.canaryContracts || []),
        ].slice(0, limit);
    const autoGovernanceRows = query
      ? rawHistoryRows.filter(isAutoGovernanceHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.['auto-governance'] || historyPayload.recent?.autoGovernance || []),
        ].slice(0, limit);
    const canaryExecutorRunRows = query
      ? rawHistoryRows.filter(isCanaryExecutorRunHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.['canary-executor-runs'] || historyPayload.recent?.canaryExecutorRuns || []),
        ].slice(0, limit);
    const canaryOrderAuditRows = query
      ? rawHistoryRows.filter(isCanaryOrderAuditHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.['canary-order-audit'] || historyPayload.recent?.canaryOrderAudit || []),
        ].slice(0, limit);
    const marketCatalogRows = query
      ? rawHistoryRows.filter(isMarketCatalogHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.markets || historyPayload.recent?.marketCatalog || []),
        ].slice(0, limit);
    const relatedAssetRows = query
      ? rawHistoryRows.filter(isRelatedAssetHistoryRow).slice(0, limit)
      : [
          ...(historyPayload.recent?.['related-assets'] || historyPayload.recent?.relatedAssetOpportunities || []),
        ].slice(0, limit);
    const historyRows = query
      ? rawHistoryRows.filter((row) => !isWorkerHistoryRow(row) && !isCrossLinkageHistoryRow(row) && !isCanaryContractHistoryRow(row) && !isAutoGovernanceHistoryRow(row) && !isCanaryExecutorRunHistoryRow(row) && !isCanaryOrderAuditHistoryRow(row) && !isMarketCatalogHistoryRow(row) && !isRelatedAssetHistoryRow(row)).slice(0, limit)
      : rawHistoryRows;
    const analysisRows = normalizeAnalyzeHistoryRows(
      analysisResult.payload?.search?.rows || analysisResult.payload?.recent?.analyses || []
    );

    const latestAnalysisRows = [];
    if (latestAnalysis && matchesSearchQuery(latestAnalysis, query)) {
      const latestMarket = latestAnalysis.market || {};
      const latestAnalysisBody = latestAnalysis.analysis || {};
      latestAnalysisRows.push({
        rowId: 0,
        generatedAt: firstDefined(latestAnalysis.generatedAt, latestAnalysisBody.generatedAt),
        status: firstDefined(latestAnalysis.status, 'OK'),
        decision: firstDefined(latestAnalysis.decision, 'RESEARCH_ONLY_SINGLE_MARKET_NO_BETTING'),
        query: firstDefined(latestAnalysis.request?.query, latestMarket.question, latestMarket.marketId),
        querySource: firstDefined(latestAnalysis.request?.source, 'latest_snapshot'),
        marketId: firstDefined(latestMarket.marketId),
        question: firstDefined(latestMarket.question, latestMarket.slug),
        category: firstDefined(latestMarket.category),
        marketProbability: firstDefined(latestAnalysisBody.marketProbabilityPct, latestMarket.probability),
        aiProbability: firstDefined(latestAnalysisBody.aiProbabilityPct),
        divergence: firstDefined(latestAnalysisBody.divergencePct),
        confidence: firstDefined(latestAnalysisBody.confidencePct),
        recommendation: firstDefined(latestAnalysisBody.recommendation, latestAnalysis.summary?.recommendation),
        risk: firstDefined(latestAnalysisBody.riskLevel, latestAnalysis.summary?.risk),
        shadowTrack: firstDefined(latestAnalysisBody.suggestedShadowTrack),
        url: firstDefined(latestMarket.polymarketUrl),
        walletWrite: toBoolean(latestAnalysis.safety?.walletWriteAllowed),
        orderSend: toBoolean(latestAnalysis.safety?.orderSendAllowed),
        historyType: 'latest_analysis',
        source: 'latest_json_api'
      });
    }

    const sections = {
      marketCatalog: [
        ...marketCatalogItems.map((item) => compactMarketCatalogResult(item, marketCatalog?.generatedAt)),
        ...marketCatalogRows.slice(0, limit).map(compactHistoryResult)
      ].slice(0, limit),
      relatedAssets: [
        ...relatedAssetItems.map((item) => compactRelatedAssetResult(item, relatedAssets?.generatedAt)),
        ...relatedAssetRows.slice(0, limit).map(compactHistoryResult)
      ].slice(0, limit),
      radar: radarItems.map((item) => compactRadarResult(item, radar?.generatedAt)),
      aiScore: aiScoreItems.map((item) => compactAiScoreResult(item, aiScore?.generatedAt)),
      analyses: [...latestAnalysisRows, ...analysisRows].slice(0, limit).map(compactAnalysisResult),
      worker: workerRows.slice(0, limit).map(compactHistoryResult),
      crossLinkage: [
        ...crossLinkageItems.map((item) => compactCrossLinkageResult(item, crossLinkage?.generatedAt)),
        ...crossRows.slice(0, limit).map(compactHistoryResult)
      ].slice(0, limit),
      canary: [
        ...canaryItems.map((item) => compactCanaryContractResult(item, canaryContract?.generatedAt)),
        ...canaryRows.slice(0, limit).map(compactHistoryResult)
      ].slice(0, limit),
      autoGovernance: [
        ...autoGovernanceItems.map((item) => compactAutoGovernanceResult(item, autoGovernance?.generatedAt)),
        ...autoGovernanceRows.slice(0, limit).map(compactHistoryResult)
      ].slice(0, limit),
      canaryExecutor: [
        ...canaryExecutorRunItems.map((item) => compactCanaryExecutorRunResult(item, canaryExecutorRun?.generatedAt)),
        ...canaryOrderAuditItems.map((item) => compactCanaryOrderAuditResult(item, canaryExecutorRun?.generatedAt)),
        ...canaryExecutorRunRows.slice(0, limit).map(compactHistoryResult),
        ...canaryOrderAuditRows.slice(0, limit).map(compactHistoryResult)
      ].slice(0, limit),
      history: historyRows.slice(0, limit).map(compactHistoryResult)
    };
    const rawSearchResults = sortSearchResults([
      ...sections.radar,
      ...sections.marketCatalog,
      ...sections.relatedAssets,
      ...sections.aiScore,
      ...sections.analyses,
      ...sections.worker,
      ...sections.crossLinkage,
      ...sections.canary,
      ...sections.autoGovernance,
      ...sections.canaryExecutor,
      ...sections.history
    ]);
    const groupedResults = groupSearchResultsByMarket(rawSearchResults, limit);

    sendJson(res, 200, {
      mode: 'POLYMARKET_SEARCH_API_V7_REAL_CANARY_GOVERNANCE_EVIDENCE_GROUPS',
      status: errors.length ? 'PARTIAL' : 'OK',
      generatedAt: new Date().toISOString(),
      source: 'quantgod_dashboard_local_api',
      decision: 'READ_ONLY_UNIFIED_SEARCH_NO_WALLET_WRITE',
      query,
      limit,
      summary: {
        totalMatches: groupedResults.length,
        marketGroups: groupedResults.length,
        rawMatches: rawSearchResults.length,
        marketCatalogMatches: sections.marketCatalog.length,
        relatedAssetMatches: sections.relatedAssets.length,
        radarMatches: sections.radar.length,
        aiScoreMatches: sections.aiScore.length,
        analysisMatches: sections.analyses.length,
        workerMatches: sections.worker.length,
        crossLinkageMatches: sections.crossLinkage.length,
        canaryMatches: sections.canary.length,
        autoGovernanceMatches: sections.autoGovernance.length,
        canaryExecutorMatches: sections.canaryExecutor.length,
        historyMatches: sections.history.length,
        historyTotalRows: historyPayload.summary?.totalRows || 0
      },
      results: groupedResults,
      groupedResults,
      rawResults: rawSearchResults,
      sections,
      sources: {
        radarPath,
        aiScorePath,
        crossLinkagePath,
        canaryContractPath,
        autoGovernancePath,
        canaryExecutorRunPath,
        marketCatalogPath,
        relatedAssetsPath,
        latestAnalysisPath,
        historyDatabase: historyPayload.database || null
      },
      errors,
      safety: {
        readsPrivateKey: false,
        walletWriteAllowed: false,
        orderSendAllowed: false,
        startsExecutor: false,
        mutatesMt5: false,
        readOnly: true
      }
    });
  } catch (error) {
    sendJson(res, 400, { ok: false, error: error.message || String(error) });
  }
}

function maybeTranscodeRuntimeText(target, ext, data) {
  const base = path.basename(target);
  if (!runtimeTextExtensions.has(ext) || !base.startsWith('QuantGod_')) {
    return data;
  }

  try {
    utf8Decoder.decode(data);
    return data;
  } catch (_) {
    // Some MT4/MT5 runtime CSV files are written in the terminal locale; keep
    // the legacy Shift-JIS compatibility path only when bytes are not UTF-8.
  }

  try {
    const utf8Text = shiftJisDecoder.decode(data);
    return Buffer.from(utf8Text, 'utf8');
  } catch (err) {
    console.warn(`QuantGod dashboard server transcode fallback for ${base}: ${err.message}`);
    return data;
  }
}

function safeResolve(urlPath) {
  const pathname = decodeURIComponent(urlPath.split('?')[0] || '/');
  const normalized = pathname;
  const target = path.resolve(rootDir, '.' + normalized);
  if (!target.startsWith(rootDir)) {
    return null;
  }
  return target;
}

function shouldRedirectToVue(urlPath) {
  const pathname = decodeURIComponent(urlPath.split('?')[0] || '/');
  return pathname === '/' || pathname === '/QuantGod_Dashboard.html';
}

function redirectToVue(urlPath, res) {
  const query = urlPath.includes('?') ? `?${urlPath.split('?').slice(1).join('?')}` : '';
  send(res, 302, {
    Location: `/vue/${query}`,
    'Content-Type': 'text/plain; charset=utf-8',
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
  }, 'Redirecting to QuantGod Vue workbench');
}

function safeResolveVue(urlPath) {
  const pathname = decodeURIComponent(urlPath.split('?')[0] || '/');
  if (pathname !== '/vue' && pathname !== '/vue/' && !pathname.startsWith('/vue/')) {
    return null;
  }

  const vueRoot = path.join(rootDir, 'vue-dist');
  const indexPath = path.join(vueRoot, 'index.html');
  if (pathname === '/vue' || pathname === '/vue/') {
    return indexPath;
  }

  const relative = pathname.slice('/vue/'.length);
  const target = path.resolve(vueRoot, relative);
  if (!target.startsWith(vueRoot)) {
    return null;
  }

  if (fs.existsSync(target)) {
    return target;
  }

  return path.extname(target) ? target : indexPath;
}

function resolveRuntimeFallback(target) {
  const base = path.basename(target || '');
  if (!base.startsWith('QuantGod_')) return null;
  const runtimeTarget = path.join(defaultRuntimeDir, base);
  if (!runtimeTarget.startsWith(defaultRuntimeDir)) return null;
  return fs.existsSync(runtimeTarget) ? runtimeTarget : null;
}

function sendStaticFile(target, res) {
  fs.stat(target, (statErr, stats) => {
    if (statErr || !stats.isFile()) {
      send(res, 404, { 'Content-Type': 'text/plain; charset=utf-8' }, 'Not Found');
      return;
    }

    const ext = path.extname(target).toLowerCase();
    const contentType = contentTypes[ext] || 'application/octet-stream';

    fs.readFile(target, (readErr, data) => {
      if (readErr) {
        send(res, 500, { 'Content-Type': 'text/plain; charset=utf-8' }, 'Read Failed');
        return;
      }

      const body = maybeTranscodeRuntimeText(target, ext, data);

      send(res, 200, {
        'Content-Type': contentType,
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        Pragma: 'no-cache',
        Expires: '0'
      }, body);
    });
  });
}

const server = http.createServer((req, res) => {
  const requestUrl = req.url || '/';

  // Set CORS origin header early so it persists through writeHead in send/sendJson
  const origin = (req.headers.origin || '').replace(/\/+$/, '');
  if (ALLOWED_ORIGINS.has(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
  }

  if (req.method === 'OPTIONS') {
    const preflightHeaders = corsPreflightHeadersFor(req);
    if (Object.keys(preflightHeaders).length > 0) {
      send(res, 204, Object.assign({ 'Content-Type': 'application/json; charset=utf-8' }, preflightHeaders), JSON.stringify({}));
    } else {
      send(res, 204, { 'Content-Type': 'application/json; charset=utf-8' }, JSON.stringify({}));
    }
    return;
  }

  // CSRF guard: non-safe methods require X-QuantGod-Local: 1 header
  if (!isCsrfSafe(req)) {
    sendJson(res, 403, { ok: false, error: 'CSRF_FORBIDDEN', detail: 'Non-safe methods require X-QuantGod-Local: 1 header' }, req);
    return;
  }

  if (usdjpyStrategyLabApiRoutes.isUSDJPYStrategyLabPath(requestUrl)) {
    usdjpyStrategyLabApiRoutes
      .handle(req, res, { repoRoot, rootDir, defaultRuntimeDir })
      .catch((error) => usdjpyStrategyLabApiRoutes.sendError(res, 500, requestUrl, error));
    return;
  }
  if (caseMemoryApiRoutes.isCaseMemoryPath(requestUrl)) {
    caseMemoryApiRoutes
      .handle(req, res, { repoRoot, rootDir, defaultRuntimeDir })
      .catch((error) => caseMemoryApiRoutes.sendError(res, 500, requestUrl, error));
    return;
  }
  if (automationChainApiRoutes.isAutomationChainPath(requestUrl)) {
    automationChainApiRoutes
      .handle(req, res, { repoRoot, rootDir, defaultRuntimeDir })
      .catch((error) => automationChainApiRoutes.sendError(res, 500, requestUrl, error));
    return;
  }
  if (stateApiRoutes.isStatePath(requestUrl)) {
    stateApiRoutes
      .handle(req, res, { repoRoot, rootDir, defaultRuntimeDir })
      .catch((error) => stateApiRoutes.sendError(res, 500, requestUrl, error));
    return;
  }
  if (phase3ApiRoutes.isPhase3Path(requestUrl)) {
    phase3ApiRoutes
      .handle(req, res, { repoRoot, rootDir, defaultRuntimeDir })
      .catch((error) => phase3ApiRoutes.sendError(res, 500, requestUrl, error));
    return;
  }
  if (phase2ApiRoutes.isPhase2Path(requestUrl)) {
    phase2ApiRoutes
      .handle(req, res, { repoRoot, rootDir, defaultRuntimeDir })
      .catch((error) => phase2ApiRoutes.sendError(res, 500, requestUrl, error));
    return;
  }
  if (phase1ApiRoutes.isPhase1Path(requestUrl)) {
    phase1ApiRoutes
      .handle(req, res, { repoRoot, defaultRuntimeDir })
      .catch((error) => phase1ApiRoutes.sendUnhandledError(res, error, requestUrl));
    return;
  }
  if (req.method === 'GET' && shouldRedirectToVue(requestUrl)) {
    redirectToVue(requestUrl, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/latest') {
    const latestDashboard = path.join(defaultRuntimeDir, 'QuantGod_Dashboard.json');
    if (fs.existsSync(latestDashboard)) {
      try {
        const text = fs.readFileSync(latestDashboard, 'utf8').replace(/^\uFEFF/, '');
        const stat = fs.statSync(latestDashboard);
        const payload = JSON.parse(text);
        const terminal = readMt5TerminalStatus();
        sendJson(res, 200, withServiceMeta({
          ...payload,
          ...(terminal ? { _terminal: terminal } : {}),
          _file: {
            path: latestDashboard,
            mtimeIso: stat.mtime.toISOString(),
            mtimeMs: stat.mtimeMs
          }
        }, '/api/latest', latestDashboard));
      } catch (error) {
        sendJson(res, 500, {
          ok: false,
          status: 'PARSE_FAILED',
          endpoint: '/api/latest',
          error: error.message,
          filePath: latestDashboard
        });
      }
      return;
    }
    send(res, 404, { 'Content-Type': 'text/plain; charset=utf-8' }, 'Not Found');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/daily-review') {
    handleDailyReviewJson(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/daily-autopilot') {
    handlePolymarketReadOnlyJson(req, res, dailyAutopilotName, '/api/daily-autopilot');
    return;
  }
  if (req.method === 'GET' && (requestUrl.split('?')[0] === '/api/mt5-readonly' || requestUrl.split('?')[0].startsWith('/api/mt5-readonly/'))) {
    const pathPart = requestUrl.split('?')[0];
    const endpoint = pathPart === '/api/mt5-readonly' ? 'snapshot' : path.basename(pathPart);
    handleMt5Readonly(req, res, endpoint);
    return;
  }
  if (req.method === 'GET' && (requestUrl.split('?')[0] === '/api/mt5-symbol-registry' || requestUrl.split('?')[0].startsWith('/api/mt5-symbol-registry/'))) {
    const pathPart = requestUrl.split('?')[0];
    const endpoint = pathPart === '/api/mt5-symbol-registry' ? 'registry' : path.basename(pathPart);
    handleMt5SymbolRegistry(req, res, endpoint);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/mt5-backtest-loop') {
    handleMt5BackendBacktest(req, res, false);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/mt5-backtest-loop/run') {
    handleMt5BackendBacktest(req, res, true);
    return;
  }
  if (req.method === 'POST' && requestUrl.split('?')[0].startsWith('/api/paramlab/auto-tester/')) {
    const action = path.basename(requestUrl.split('?')[0]);
    handleParamLabAutoTester(req, res, action);
    return;
  }
  if ((req.method === 'GET' || req.method === 'POST' || req.method === 'DELETE') && (requestUrl.split('?')[0] === '/api/mt5-platform' || requestUrl.split('?')[0].startsWith('/api/mt5-platform/'))) {
    const pathPart = requestUrl.split('?')[0];
    const endpoint = mt5PlatformEndpointFromPath(pathPart);
    handleMt5PlatformStore(req, res, endpoint);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/mt5-pending-worker/status') {
    handleMt5PendingWorker(req, res, false);
    return;
  }
  if (req.method === 'POST' && requestUrl.split('?')[0] === '/api/mt5-pending-worker/run') {
    handleMt5PendingWorker(req, res, true);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/mt5-adaptive-control/status') {
    handleMt5AdaptiveControl(req, res, false);
    return;
  }
  if (req.method === 'POST' && requestUrl.split('?')[0] === '/api/mt5-adaptive-control/run') {
    handleMt5AdaptiveControl(req, res, true);
    return;
  }
  if ((req.method === 'GET' || req.method === 'POST') && (requestUrl.split('?')[0] === '/api/mt5-trading' || requestUrl.split('?')[0].startsWith('/api/mt5-trading/'))) {
    const pathPart = requestUrl.split('?')[0];
    const endpoint = pathPart === '/api/mt5-trading' ? 'status' : mt5TradingEndpointFromPath(pathPart);
    handleMt5Trading(req, res, endpoint);
    return;
  }
  if ((req.method === 'GET' || req.method === 'POST') && (requestUrl.split('?')[0] === '/api/mt5' || requestUrl.split('?')[0].startsWith('/api/mt5/'))) {
    const pathPart = requestUrl.split('?')[0];
    const endpoint = pathPart === '/api/mt5' ? 'status' : mt5TradingEndpointFromPath(pathPart);
    handleMt5Trading(req, res, endpoint);
    return;
  }
  if (req.method === 'DELETE' && requestUrl.split('?')[0].startsWith('/api/mt5/order/')) {
    const ticket = path.basename(requestUrl.split('?')[0]);
    handleMt5Trading(req, res, 'cancel', { ticket, orderTicket: ticket });
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/history') {
    handlePolymarketHistory(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/real-trades') {
    handlePolymarketRealTrades(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/radar') {
    handlePolymarketReadOnlyJson(req, res, polymarketRadarName, '/api/polymarket/radar');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/markets') {
    handlePolymarketMarkets(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/market') {
    handlePolymarketMarketDetail(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/book') {
    handlePolymarketBook(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/asset-opportunities') {
    handlePolymarketAssetOpportunities(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/radar-worker') {
    handlePolymarketReadOnlyJson(req, res, polymarketRadarWorkerName, '/api/polymarket/radar-worker');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/cross-linkage') {
    handlePolymarketReadOnlyJson(req, res, polymarketCrossMarketLinkageName, '/api/polymarket/cross-linkage');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/canary-executor-contract') {
    handlePolymarketReadOnlyJson(req, res, polymarketCanaryExecutorContractName, '/api/polymarket/canary-executor-contract');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/auto-governance') {
    handlePolymarketReadOnlyJson(req, res, polymarketAutoGovernanceName, '/api/polymarket/auto-governance');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/canary-executor-run') {
    handlePolymarketReadOnlyJson(req, res, polymarketCanaryExecutorRunName, '/api/polymarket/canary-executor-run');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/ai-score') {
    handlePolymarketReadOnlyJson(req, res, polymarketAiScoreName, '/api/polymarket/ai-score');
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/analyze/history') {
    handlePolymarketAnalyzeHistory(req, res);
    return;
  }
  if (req.method === 'GET' && requestUrl.split('?')[0] === '/api/polymarket/search') {
    handlePolymarketSearch(req, res);
    return;
  }
  if (req.method === 'POST' && requestUrl.split('?')[0] === '/api/polymarket/single-market-request') {
    handleSingleMarketRequest(req, res);
    return;
  }
  if (req.method === 'POST' && requestUrl.split('?')[0] === '/api/polymarket/analyze') {
    handleSingleMarketRequest(req, res);
    return;
  }
  const vueTarget = safeResolveVue(req.url || '/');
  if (vueTarget) {
    sendStaticFile(vueTarget, res);
    return;
  }
  const target = safeResolve(req.url || '/');
  if (!target) {
    send(res, 403, { 'Content-Type': 'text/plain; charset=utf-8' }, 'Forbidden');
    return;
  }

  const fallback = fs.existsSync(target) ? target : resolveRuntimeFallback(target);
  sendStaticFile(fallback || target, res);
});

const LOOPBACK_IPS = new Set(['127.0.0.1', '::1', 'localhost']);
if (!LOOPBACK_IPS.has(host)) {
  if (host === '0.0.0.0' || host === '::') {
    console.warn('[WARN] QG_DASHBOARD_HOST=' + host + ' binds the dashboard to ALL network interfaces. ' +
      'This exposes the dashboard to your LAN and any reachable network. ' +
      'Set QG_DASHBOARD_HOST=127.0.0.1 unless you know what you are doing.');
  } else {
    console.warn('[WARN] QG_DASHBOARD_HOST=' + host + ' is non-loopback. ' +
      'The dashboard server will be exposed to the network.');
  }
}

server.listen(port, host, () => {
  console.log(`QuantGod Vue workbench running at http://${host}:${port}/vue/`);
  console.log(`Legacy QuantGod_Dashboard.html redirects to /vue/.`);
});

server.on('error', (err) => {
  console.error('QuantGod dashboard server failed:', err.message);
  process.exit(1);
});
