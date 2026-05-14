const fs = require('fs');

function readEnvInt(name, fallback) {
  const parsed = Number.parseInt(process.env[name] || String(fallback), 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

const DEFAULT_JSON_TTL_MS = readEnvInt('QG_API_JSON_CACHE_TTL_MS', 1500);
const DEFAULT_RUN_TTL_MS = readEnvInt('QG_API_RUN_CACHE_TTL_MS', 5000);
const MAX_JSON_ENTRIES = readEnvInt('QG_API_JSON_CACHE_MAX', 32);
const MAX_RUN_ENTRIES = readEnvInt('QG_API_RUN_CACHE_MAX', 64);

const jsonFileCache = new Map();

function nowMs() {
  return Date.now();
}

function trimMap(map, maxEntries) {
  const limit = Math.max(1, maxEntries || 1);
  while (map.size > limit) {
    const oldestKey = map.keys().next().value;
    map.delete(oldestKey);
  }
}

function stringifyJson(payload) {
  const spaces = process.env.QG_API_PRETTY_JSON === '1' ? 2 : 0;
  return JSON.stringify(payload, null, spaces);
}

function readJsonFileCached(filePath, options = {}) {
  const ttlMs = Number.isFinite(options.ttlMs) ? options.ttlMs : DEFAULT_JSON_TTL_MS;
  const stat = fs.statSync(filePath);
  const cached = jsonFileCache.get(filePath);
  const expiresAt = nowMs() + Math.max(0, ttlMs);
  if (
    cached &&
    cached.expiresAt > nowMs() &&
    cached.mtimeMs === stat.mtimeMs &&
    cached.size === stat.size
  ) {
    jsonFileCache.delete(filePath);
    jsonFileCache.set(filePath, { ...cached, expiresAt, stat });
    return { payload: cached.payload, stat, filePath };
  }

  const text = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  const payload = JSON.parse(text);
  jsonFileCache.set(filePath, {
    payload,
    mtimeMs: stat.mtimeMs,
    size: stat.size,
    stat,
    expiresAt,
  });
  trimMap(jsonFileCache, MAX_JSON_ENTRIES);
  return { payload, stat, filePath };
}

function runCached(cache, key, load, options = {}) {
  const ttlMs = Number.isFinite(options.ttlMs) ? options.ttlMs : DEFAULT_RUN_TTL_MS;
  const maxEntries = Number.isFinite(options.maxEntries) ? options.maxEntries : MAX_RUN_ENTRIES;
  const existing = cache.get(key);
  const timestamp = nowMs();
  if (existing) {
    if (existing.inflight) return existing.inflight;
    if (existing.expiresAt > timestamp) {
      cache.delete(key);
      cache.set(key, existing);
      return Promise.resolve(existing.value);
    }
  }

  const inflight = Promise.resolve()
    .then(load)
    .then((value) => {
      cache.set(key, {
        value,
        expiresAt: nowMs() + Math.max(0, ttlMs),
      });
      trimMap(cache, maxEntries);
      return value;
    })
    .catch((error) => {
      cache.delete(key);
      throw error;
    });
  cache.set(key, { inflight, expiresAt: timestamp + Math.max(0, ttlMs) });
  trimMap(cache, maxEntries);
  return inflight;
}

function clearApiPerfCaches() {
  jsonFileCache.clear();
}

module.exports = {
  clearApiPerfCaches,
  readJsonFileCached,
  runCached,
  stringifyJson,
};
