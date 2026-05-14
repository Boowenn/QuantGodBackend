const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { runCached, stringifyJson } = require('./api_perf_cache');

const readonlyRunCache = new Map();
const READONLY_RUN_CACHE_TTL_MS = (() => {
  const parsed = Number.parseInt(process.env.QG_API_READONLY_RUN_CACHE_TTL_MS || '5000', 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 5000;
})();

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    Pragma: 'no-cache',
    Expires: '0',
  });
  res.end(stringifyJson(payload));
}

function sendError(res, statusCode, requestUrl, error) {
  sendJson(res, statusCode, {
    ok: false,
    endpoint: requestUrl,
    error: error && error.message ? error.message : String(error),
    safety: {
      readOnlyDataPlane: true,
      advisoryOnly: true,
      dryRunOnly: true,
      orderSendAllowed: false,
      closeAllowed: false,
      cancelAllowed: false,
      livePresetMutationAllowed: false,
      writesMt5OrderRequest: false,
    },
  });
}

function isUSDJPYStrategyLabPath(requestUrl) {
  const pathname = String(requestUrl || '').split('?')[0];
  return pathname === '/api/usdjpy-strategy-lab' || pathname.startsWith('/api/usdjpy-strategy-lab/');
}

function runPythonJson(repoRoot, args, timeoutMs = 45000, scriptName = 'run_usdjpy_strategy_lab.py') {
  return new Promise((resolve) => {
    const pythonBin = process.env.QG_PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3');
    const script = path.join(repoRoot, 'tools', scriptName);
    if (!fs.existsSync(script)) {
      resolve({ ok: false, skipped: true, reason: 'script_not_found', script });
      return;
    }
    const child = spawn(pythonBin, [script, ...args], {
      cwd: repoRoot,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    let settled = false;
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill();
      resolve({ ok: false, exitCode: -1, stdout, stderr: 'timeout' });
    }, timeoutMs);
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ ok: false, exitCode: -1, stdout, stderr: error.message });
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (code !== 0) {
        resolve({ ok: false, exitCode: code, stdout, stderr: stderr.trim() });
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        resolve({ ok: false, exitCode: code, stdout, stderr: `json_parse_failed: ${error.message}` });
      }
    });
  });
}

function canReuseReadonlyRun(req, url, args) {
  if ((req.method || 'GET').toUpperCase() !== 'GET') return false;
  if (url.searchParams.get('write') === '1') return false;
  if (url.searchParams.get('refresh') === '1') return false;
  if (url.searchParams.get('send') === '1') return false;
  return !args.includes('--write') && !args.includes('--refresh') && !args.includes('--send');
}

function runReadonlyPythonJson(req, url, repoRoot, args, timeoutMs = 45000, scriptName = 'run_usdjpy_strategy_lab.py') {
  if (!canReuseReadonlyRun(req, url, args)) {
    return runPythonJson(repoRoot, args, timeoutMs, scriptName);
  }
  const key = JSON.stringify([repoRoot, scriptName, args]);
  return runCached(
    readonlyRunCache,
    key,
    () => runPythonJson(repoRoot, args, timeoutMs, scriptName),
    { ttlMs: READONLY_RUN_CACHE_TTL_MS },
  );
}

function readFreshAgentOpsHealth(runtimeDir, maxAgeSeconds = 360) {
  try {
    const filePath = path.join(runtimeDir, 'agent', 'QuantGod_AgentOpsHealth.json');
    if (!fs.existsSync(filePath)) return null;
    const payload = JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
    const generatedAt = Date.parse(payload.generatedAtIso || payload.generatedAt || '');
    if (!Number.isFinite(generatedAt)) return null;
    const ageSeconds = Math.max(0, (Date.now() - generatedAt) / 1000);
    if (ageSeconds > maxAgeSeconds) return null;
    return {
      ...payload,
      _cache: {
        source: 'QuantGod_AgentOpsHealth.json',
        ageSeconds,
        maxAgeSeconds,
      },
    };
  } catch {
    return null;
  }
}

function readJsonBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk.toString();
      if (body.length > 1024 * 1024) req.destroy();
    });
    req.on('end', () => {
      if (!body.trim()) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch (error) {
        resolve({ __jsonError: error.message });
      }
    });
    req.on('error', () => resolve({}));
  });
}

async function handle(req, res, ctx) {
  const requestUrl = req.url || '/';
  const url = new URL(requestUrl, 'http://127.0.0.1');
  const pathname = url.pathname;
  const runtimeDir = url.searchParams.get('runtimeDir') || ctx.defaultRuntimeDir;
  const baseArgs = ['--runtime-dir', runtimeDir, '--symbol', 'USDJPYc'];

  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab' || pathname === '/api/usdjpy-strategy-lab/status')) {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'status']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/scoreboard') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'scoreboard']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/catalog') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'catalog']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/signals') {
    const limit = url.searchParams.get('limit') || '50';
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'signals', '--limit', limit]);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/signals/run') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'signals', '--limit', '100']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/risk-check') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'risk-check']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/backtest-plan') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'backtest-plan']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/backtest-plan/build') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'backtest-plan']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/imported-backtests') {
    const limit = url.searchParams.get('limit') || '50';
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'imported-backtests', '--limit', limit]);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/import-backtest') {
    const body = await readJsonBody(req);
    if (body.__jsonError) {
      sendJson(res, 400, { ok: false, error: 'INVALID_JSON_BODY', detail: body.__jsonError });
      return;
    }
    const source = String(body.source || body.sourceFile || '').trim();
    if (!source) {
      sendJson(res, 400, { ok: false, error: 'BACKTEST_SOURCE_REQUIRED' });
      return;
    }
    const args = [...baseArgs, 'import-backtest', '--source', source];
    if (body.strategy) args.push('--strategy', String(body.strategy));
    const payload = await runPythonJson(ctx.repoRoot, args);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/candidate-policy') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'candidate-policy']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/candidate-policy/build') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'candidate-policy', '--write']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evidence') {
    const scoreboard = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'scoreboard']);
    const signals = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'signals', '--limit', '50']);
    sendJson(res, scoreboard && scoreboard.ok === false ? 500 : 200, {
      ok: !(scoreboard && scoreboard.ok === false),
      scoreboard,
      signals,
    });
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/dry-run') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'dry-run', '--write']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/live-loop') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'status'];
    if (url.searchParams.get('write') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 45000, 'run_usdjpy_live_loop.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/live-loop/run') {
    const payload = await runPythonJson(ctx.repoRoot, ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'once', '--write'], 90000, 'run_usdjpy_live_loop.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/live-loop/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_live_loop.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/evolution' || pathname === '/api/usdjpy-strategy-lab/evolution/status')) {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, [...baseArgs, 'status'], 90000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/evolution/build') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'status', '--write'], 120000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evolution/replay') {
    const args = [...baseArgs, 'replay'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/evolution/replay') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'replay', '--write'], 90000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evolution/tune') {
    const args = [...baseArgs, 'tune'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/evolution/tune') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'tune', '--write'], 90000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evolution/proposal') {
    const args = [...baseArgs, 'proposal'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/evolution/proposal') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'proposal', '--write'], 90000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evolution/telegram-text') {
    const args = [...baseArgs, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_runtime_dataset.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/bar-replay' || pathname === '/api/usdjpy-strategy-lab/bar-replay/status')) {
    const args = [...baseArgs, 'status'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_bar_replay.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/bar-replay/build') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'build', '--write'], 120000, 'run_usdjpy_bar_replay.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/bar-replay/entry') {
    const args = [...baseArgs, 'entry'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_bar_replay.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/bar-replay/exit') {
    const args = [...baseArgs, 'exit'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_bar_replay.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/bar-replay/telegram-text') {
    const args = [...baseArgs, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_bar_replay.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/walk-forward' || pathname === '/api/usdjpy-strategy-lab/walk-forward/status')) {
    const args = [...baseArgs, 'status'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_walk_forward.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/walk-forward/build') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'build', '--write'], 120000, 'run_usdjpy_walk_forward.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/walk-forward/selection') {
    const args = [...baseArgs, 'selection'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_walk_forward.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/walk-forward/proposal') {
    const args = [...baseArgs, 'proposal'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_walk_forward.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/walk-forward/telegram-text') {
    const args = [...baseArgs, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_walk_forward.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/autonomous-agent' || pathname === '/api/usdjpy-strategy-lab/autonomous-agent/state')) {
    const args = [...baseArgs, 'state'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/run') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'build', '--write'], 120000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/decision') {
    const args = [...baseArgs, 'decision'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/patch') {
    const args = [...baseArgs, 'patch'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/lifecycle') {
    const args = [...baseArgs, '--repo-root', ctx.repoRoot, 'lifecycle'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/lanes') {
    const args = [...baseArgs, '--repo-root', ctx.repoRoot, 'lanes'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/mt5-shadow') {
    const args = [...baseArgs, 'mt5-shadow'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/polymarket-shadow') {
    const args = [...baseArgs, 'polymarket-shadow'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/ea-repro') {
    const args = [...baseArgs, '--repo-root', ctx.repoRoot, 'ea-repro'];
    if (url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 90000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/telegram-text') {
    const args = [...baseArgs, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_autonomous_agent.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/autonomous-agent/daily-autopilot-v2' || pathname === '/api/usdjpy-strategy-lab/autonomous-agent/daily-autopilot-v2/status')) {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'status'];
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/daily-autopilot-v2/run') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'run-cycle', '--write'];
    const payload = await runPythonJson(ctx.repoRoot, args, 360000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/autonomous-agent/daily-autopilot-v2/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/daily-todo' || pathname === '/api/usdjpy-strategy-lab/daily-todo/status')) {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'daily-todo'];
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/daily-todo/run') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'run-cycle', '--write', '--view', 'daily-todo'];
    const payload = await runPythonJson(ctx.repoRoot, args, 360000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/daily-todo/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'daily-todo-telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/daily-review' || pathname === '/api/usdjpy-strategy-lab/daily-review/status')) {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'daily-review'];
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/daily-review/run') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'run-cycle', '--write', '--view', 'daily-review'];
    const payload = await runPythonJson(ctx.repoRoot, args, 360000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/daily-review/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'daily-review-telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_daily_autopilot_v2.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/telegram-text') {
    const args = [...baseArgs, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/strategy-backtest' || pathname === '/api/usdjpy-strategy-lab/strategy-backtest/status')) {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'status'], 120000, 'run_usdjpy_strategy_backtest.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/strategy-backtest/sample') {
    const args = ['--runtime-dir', runtimeDir, 'sample'];
    if (url.searchParams.get('overwrite') === '1') args.push('--overwrite');
    const payload = await runPythonJson(ctx.repoRoot, args, 120000, 'run_usdjpy_strategy_backtest.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/strategy-backtest/run') {
    const payload = await runPythonJson(ctx.repoRoot, ['--runtime-dir', runtimeDir, 'run', '--write'], 120000, 'run_usdjpy_strategy_backtest.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/strategy-backtest/quality') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'quality'], 120000, 'run_usdjpy_strategy_backtest.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/strategy-backtest/production-status') {
    const args = ['--runtime-dir', runtimeDir, 'production-status'];
    if (url.searchParams.get('months')) args.push('--months', url.searchParams.get('months'));
    if (url.searchParams.get('lookbackDays')) args.push('--lookback-days', url.searchParams.get('lookbackDays'));
    if (url.searchParams.get('maxLatestLagHours')) args.push('--max-latest-lag-hours', url.searchParams.get('maxLatestLagHours'));
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_strategy_backtest.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/strategy-backtest/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_strategy_backtest.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/strategy-backtest/sync-klines') {
    const args = ['--runtime-dir', runtimeDir, 'sync-klines'];
    if (url.searchParams.get('months')) args.push('--months', url.searchParams.get('months'));
    if (url.searchParams.get('lookbackDays')) args.push('--lookback-days', url.searchParams.get('lookbackDays'));
    if (url.searchParams.get('timeframes')) args.push('--timeframes', url.searchParams.get('timeframes'));
    if (url.searchParams.get('maxLatestLagHours')) args.push('--max-latest-lag-hours', url.searchParams.get('maxLatestLagHours'));
    const payload = await runPythonJson(ctx.repoRoot, args, 300000, 'run_usdjpy_strategy_backtest.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/evidence-os' || pathname === '/api/usdjpy-strategy-lab/evidence-os/status')) {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'status'], 120000, 'run_usdjpy_evidence_os.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/evidence-os/run') {
    const payload = await runPythonJson(ctx.repoRoot, ['--runtime-dir', runtimeDir, 'once', '--write'], 120000, 'run_usdjpy_evidence_os.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evidence-os/parity') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'parity'], 120000, 'run_usdjpy_evidence_os.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evidence-os/execution-feedback') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'execution-feedback'], 120000, 'run_usdjpy_evidence_os.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evidence-os/case-memory') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'case-memory'], 120000, 'run_usdjpy_evidence_os.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/evidence-os/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_usdjpy_evidence_os.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/telegram-gateway' || pathname === '/api/usdjpy-strategy-lab/telegram-gateway/status')) {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'status'], 45000, 'run_telegram_gateway.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/telegram-gateway/test-event') {
    const body = await readJsonBody(req);
    if (body.__jsonError) {
      sendJson(res, 400, { ok: false, error: 'INVALID_JSON_BODY', detail: body.__jsonError });
      return;
    }
    const text = String(body.text || '【QuantGod Telegram Gateway 测试】独立 Gateway 已接入队列、去重、限频和投递账本；不会接收交易命令。');
    const payload = await runPythonJson(
      ctx.repoRoot,
      [
        '--runtime-dir',
        runtimeDir,
        'enqueue',
        '--source',
        'frontend_usdjpy_evolution',
        '--topic',
        'GATEWAY_TEST',
        '--severity',
        'INFO',
        '--text',
        text,
      ],
      45000,
      'run_telegram_gateway.py',
    );
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/telegram-gateway/dispatch') {
    const args = ['--runtime-dir', runtimeDir, 'dispatch'];
    if (url.searchParams.get('send') === '1') args.push('--send');
    const limit = url.searchParams.get('limit');
    if (limit) args.push('--limit', String(limit));
    const payload = await runPythonJson(ctx.repoRoot, args, 45000, 'run_telegram_gateway.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (
    req.method === 'GET' &&
    (pathname === '/api/usdjpy-strategy-lab/agent-ops-health' || pathname === '/api/usdjpy-strategy-lab/agent-ops-health/status')
  ) {
    const forceRefresh = url.searchParams.get('write') === '1' || url.searchParams.get('refresh') === '1';
    if (!forceRefresh) {
      const cached = readFreshAgentOpsHealth(runtimeDir);
      if (cached) {
        sendJson(res, cached && cached.ok === false ? 500 : 200, cached);
        return;
      }
    }
    const args = ['--runtime-dir', runtimeDir, '--repo-root', ctx.repoRoot, 'status'];
    if (forceRefresh || !readFreshAgentOpsHealth(runtimeDir)) args.push('--write');
    const payload = await runPythonJson(ctx.repoRoot, args, 120000, 'run_agent_ops_health.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && (pathname === '/api/usdjpy-strategy-lab/ga' || pathname === '/api/usdjpy-strategy-lab/ga/status')) {
    const args = ['--runtime-dir', runtimeDir, 'status'];
    if (url.searchParams.get('write') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/ga/run-generation') {
    const payload = await runPythonJson(ctx.repoRoot, ['--runtime-dir', runtimeDir, 'run-generation', '--write'], 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/ga/generations') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'generations'], 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/ga/candidates') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'candidates'], 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname.startsWith('/api/usdjpy-strategy-lab/ga/candidate/')) {
    const seedId = decodeURIComponent(pathname.split('/').pop() || '');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'candidate', '--seed-id', seedId], 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/ga/evolution-path') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'evolution-path'], 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/ga/blockers') {
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, ['--runtime-dir', runtimeDir, 'blockers'], 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/ga/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 120000, 'run_strategy_ga.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (
    req.method === 'GET' &&
    (pathname === '/api/usdjpy-strategy-lab/strategy-contract' ||
      pathname === '/api/usdjpy-strategy-lab/strategy-contract/status')
  ) {
    const args = ['--runtime-dir', runtimeDir, 'status'];
    if (url.searchParams.get('write') === '1') args.push('--write');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 45000, 'run_strategy_contract_adapter.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/strategy-contract/build') {
    const payload = await runPythonJson(ctx.repoRoot, ['--runtime-dir', runtimeDir, 'build'], 45000, 'run_strategy_contract_adapter.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/usdjpy-strategy-lab/strategy-contract/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    if (url.searchParams.get('send') === '1') args.push('--send');
    const payload = await runReadonlyPythonJson(req, url, ctx.repoRoot, args, 45000, 'run_strategy_contract_adapter.py');
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/usdjpy-strategy-lab/run') {
    const payload = await runPythonJson(ctx.repoRoot, [...baseArgs, 'build', '--write']);
    sendJson(res, payload && payload.ok === false ? 500 : 200, payload);
    return;
  }
  sendJson(res, 404, { ok: false, error: 'USDJPY_STRATEGY_LAB_NOT_FOUND', endpoint: pathname });
}

module.exports = {
  isUSDJPYStrategyLabPath,
  handle,
  sendError,
};
