const { spawn } = require('child_process');
const path = require('path');

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
  });
}

function isProductionEvidenceValidationPath(requestUrl) {
  const pathname = String(requestUrl || '').split('?')[0];
  return pathname === '/api/production-evidence-validation'
    || pathname.startsWith('/api/production-evidence-validation/');
}

function runPython(repoRoot, defaultRuntimeDir, command, extraArgs = []) {
  return new Promise((resolve, reject) => {
    const pythonBin = process.env.QG_PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3');
    const script = path.join(repoRoot, 'tools', 'run_production_evidence_validation.py');
    const args = [script, '--runtime-dir', defaultRuntimeDir, command, ...extraArgs];
    const child = spawn(pythonBin, args, {
      cwd: repoRoot,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `production evidence validation exited ${code}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        reject(new Error(`json_parse_failed: ${error.message}; stdout=${stdout.slice(0, 200)}`));
      }
    });
  });
}

async function handle(req, res, context) {
  const requestUrl = req.url || '/';
  const pathname = requestUrl.split('?')[0];
  if (req.method === 'GET' && (pathname === '/api/production-evidence-validation' || pathname === '/api/production-evidence-validation/status')) {
    const payload = await runPython(context.repoRoot, context.defaultRuntimeDir, 'status');
    sendJson(res, 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/production-evidence-validation/run') {
    const payload = await runPython(context.repoRoot, context.defaultRuntimeDir, 'build', ['--write']);
    sendJson(res, 200, payload);
    return;
  }
  if (
    req.method === 'GET' &&
    (pathname === '/api/production-evidence-validation/burn-in' ||
      pathname === '/api/production-evidence-validation/burn-in/status')
  ) {
    const refresh = requestUrl.includes('refresh=1') || requestUrl.includes('refresh=true');
    const payload = await runPython(context.repoRoot, context.defaultRuntimeDir, 'burn-in', refresh ? ['--refresh'] : []);
    sendJson(res, 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/production-evidence-validation/burn-in/run') {
    const payload = await runPython(context.repoRoot, context.defaultRuntimeDir, 'burn-in', ['--write']);
    sendJson(res, 200, payload);
    return;
  }
  if (
    req.method === 'GET' &&
    (pathname === '/api/production-evidence-validation/rsi-lineage-closure' ||
      pathname === '/api/production-evidence-validation/rsi-lineage-closure/status')
  ) {
    const refresh = requestUrl.includes('refresh=1') || requestUrl.includes('refresh=true');
    const payload = await runPython(context.repoRoot, context.defaultRuntimeDir, 'rsi-lineage-closure', refresh ? ['--refresh'] : []);
    sendJson(res, 200, payload);
    return;
  }
  if (req.method === 'POST' && pathname === '/api/production-evidence-validation/rsi-lineage-closure/run') {
    const payload = await runPython(context.repoRoot, context.defaultRuntimeDir, 'rsi-lineage-closure', ['--write']);
    sendJson(res, 200, payload);
    return;
  }
  if (req.method === 'GET' && pathname === '/api/production-evidence-validation/telegram-text') {
    const refresh = requestUrl.includes('refresh=1') || requestUrl.includes('refresh=true');
    const payload = await runPython(context.repoRoot, context.defaultRuntimeDir, 'telegram-text', refresh ? ['--refresh', '--write'] : []);
    sendJson(res, 200, payload);
    return;
  }
  sendJson(res, 404, { ok: false, error: 'not_found', endpoint: requestUrl });
}

module.exports = {
  isProductionEvidenceValidationPath,
  handle,
  sendError,
};
