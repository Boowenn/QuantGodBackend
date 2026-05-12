const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    Pragma: 'no-cache',
    Expires: '0',
  });
  res.end(JSON.stringify(payload, null, 2));
}

function sendError(res, statusCode, requestUrl, error) {
  sendJson(res, statusCode, {
    ok: false,
    endpoint: requestUrl,
    error: error && error.message ? error.message : String(error),
    safety: {
      orderSendAllowed: false,
      closeAllowed: false,
      cancelAllowed: false,
      livePresetMutationAllowed: false,
      writesMt5OrderRequest: false,
      telegramCommandExecutionAllowed: false,
    },
  });
}

function isCaseMemoryPath(requestUrl) {
  const pathname = String(requestUrl || '').split('?')[0];
  return pathname === '/api/case-memory' || pathname.startsWith('/api/case-memory/');
}

function runPythonJson(repoRoot, args, timeoutMs = 120000) {
  return new Promise((resolve) => {
    const pythonBin = process.env.QG_PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3');
    const script = path.join(repoRoot, 'tools', 'run_case_memory.py');
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
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        const parsed = stdout.trim() ? JSON.parse(stdout) : {};
        resolve({ exitCode: code, stderr, ...parsed });
      } catch (error) {
        resolve({ ok: false, exitCode: code, stdout, stderr, parseError: error.message });
      }
    });
  });
}

function statusCodeFor(payload) {
  if (!payload) return 500;
  if (payload.skipped || payload.parseError) return 500;
  if (payload.exitCode != null && payload.exitCode !== 0) return 500;
  return 200;
}

async function handle(req, res, ctx) {
  const requestUrl = req.url || '';
  const url = new URL(requestUrl, 'http://127.0.0.1');
  const pathname = url.pathname;
  const runtimeDir = ctx.defaultRuntimeDir;
  if (req.method === 'GET' && (pathname === '/api/case-memory' || pathname === '/api/case-memory/status')) {
    const payload = await runPythonJson(ctx.repoRoot, ['--runtime-dir', runtimeDir, 'status']);
    sendJson(res, statusCodeFor(payload), payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/case-memory/build') {
    const payload = await runPythonJson(ctx.repoRoot, ['--runtime-dir', runtimeDir, 'build', '--write']);
    sendJson(res, statusCodeFor(payload), payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/case-memory/telegram-text') {
    const args = ['--runtime-dir', runtimeDir, 'telegram-text'];
    if (url.searchParams.get('refresh') === '1') args.push('--refresh');
    const payload = await runPythonJson(ctx.repoRoot, args);
    sendJson(res, statusCodeFor(payload), payload);
    return;
  }
  sendJson(res, 404, { ok: false, error: 'CASE_MEMORY_NOT_FOUND', endpoint: pathname });
}

module.exports = {
  handle,
  isCaseMemoryPath,
  sendError,
};
