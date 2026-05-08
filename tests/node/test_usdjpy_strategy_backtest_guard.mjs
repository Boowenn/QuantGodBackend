import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const repo = process.cwd();

function read(rel) {
  return fs.readFileSync(path.join(repo, rel), 'utf8');
}

function listFiles(relDir) {
  return fs.readdirSync(path.join(repo, relDir))
    .filter((name) => name.endsWith('.py'))
    .map((name) => path.join(relDir, name));
}

test('USDJPY Strategy JSON backtest exposes USDJPY-scoped API endpoints', () => {
  const routes = read('Dashboard/usdjpy_strategy_lab_api_routes.js');
  for (const endpoint of [
    '/api/usdjpy-strategy-lab/strategy-backtest/status',
    '/api/usdjpy-strategy-lab/strategy-backtest/sample',
    '/api/usdjpy-strategy-lab/strategy-backtest/run',
    '/api/usdjpy-strategy-lab/strategy-backtest/sync-klines',
    '/api/usdjpy-strategy-lab/strategy-backtest/telegram-text',
  ]) {
    assert.match(routes, new RegExp(endpoint.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('USDJPY Strategy JSON backtest writes SQLite, trades, equity, and report artifacts', () => {
  const schema = read('tools/usdjpy_strategy_backtest/schema.py');
  const report = read('tools/usdjpy_strategy_backtest/report.py');
  const store = read('tools/usdjpy_strategy_backtest/sqlite_store.py');
  const historySync = read('tools/usdjpy_strategy_backtest/history_sync.py');
  const runnerSource = read('tools/usdjpy_strategy_backtest/strategy_runner.py');
  const runner = read('tools/run_usdjpy_strategy_backtest.py');
  for (const marker of [
    'usdjpy.sqlite',
    'QuantGod_StrategyBacktestReport.json',
    'QuantGod_StrategyTrades.csv',
    'QuantGod_StrategyEquityCurve.csv',
    'QuantGod_USDJPYHistoricalKlineSyncReport.json',
    'STRATEGY_JSON_USDJPY_SQLITE_BACKTEST',
    'MT5_COPY_RATES_RANGE',
    'MQL5_COPYRATES_EXPORT_FALLBACK',
    'quantgod.mql5_copyrates_export_ingest_report.v1',
    'QuantGod_USDJPY_KlineExportManifest.json',
    '_rates.csv',
    'copy_rates_range',
    'QG_USDJPY_HISTORY_LOOKBACK_DAYS',
    'QG_USDJPY_HISTORY_TIMEFRAMES',
    'strategy_runs',
    'strategy_trades',
    'equity_curves',
    'write_strategy_run',
    'ALL_SUPPORTED_USDJPY_SHADOW_FAMILIES',
    'quantgod.usdjpy_sqlite_history_coverage.v1',
    'quantgod.strategy_backtest_coverage_matrix.v1',
    'historyCoverage',
    'strategyCoverageMatrix',
    'bar_coverage_summary',
    '_multi_strategy_coverage_matrix',
    'BacktestCostModel',
    'QG_TELEGRAM_COMMANDS_ALLOWED',
  ]) {
    assert.match(schema + report + store + historySync + runnerSource + runner, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('MT5 EA exports USDJPY CopyRates CSVs for macOS history fallback', () => {
  const ea = read('MQL5/Experts/QuantGod_MultiStrategy.mq5');
  for (const marker of [
    'EnableUsdJpyKlineExporter',
    'UsdJpyKlineExportIntervalMinutes',
    'UsdJpyKlineExportMonths',
    'ExportUsdJpyKlinesIfDue',
    'ExportUsdJpyKlineTimeframe',
    'CopyRates(symbol, timeframe, fromTime, toTime, rates)',
    'backtest\\\\exported_klines',
    'QuantGod_USDJPY_KlineExportManifest.json',
    'QuantGod_USDJPYKlineExportManifest.json',
    'PERIOD_M1',
    'PERIOD_M5',
    'PERIOD_M15',
    'PERIOD_H1',
  ]) {
    assert.match(ea, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
});

test('USDJPY Strategy JSON backtest covers all USDJPY shadow strategy families', () => {
  const runnerSource = read('tools/usdjpy_strategy_backtest/strategy_runner.py');
  const source = [
    runnerSource,
    read('tools/usdjpy_strategy_backtest/report.py'),
  ].join('\n');
  for (const family of [
    'RSI_Reversal',
    'MA_Cross',
    'BB_Triple',
    'MACD_Divergence',
    'SR_Breakout',
    'USDJPY_TOKYO_RANGE_BREAKOUT',
    'USDJPY_NIGHT_REVERSION_SAFE',
    'USDJPY_H4_TREND_PULLBACK',
  ]) {
    assert.match(source, new RegExp(family.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.match(source, /SUPPORTED_BACKTEST_FAMILIES/);
  assert.match(source, /ALLOWED_STRATEGY_FAMILIES/);
  assert.match(source, /for direction in \("LONG", "SHORT"\)/);
  assert.match(source, /parityVectorRouteCount/);
  assert.doesNotMatch(runnerSource, /暂未接入高保真 runner[\s\S]*SUPPORTED_BACKTEST_FAMILIES/);
});

test('GA seed scoring skips expensive full coverage matrix while audit backtest keeps core metrics', () => {
  const fitness = read('tools/strategy_ga/fitness.py');
  const generationRunner = read('tools/strategy_ga/generation_runner.py');
  const report = read('tools/usdjpy_strategy_backtest/report.py');

  assert.match(report, /include_coverage_matrix:\s*bool\s*=\s*True/);
  assert.match(fitness, /include_coverage_matrix=False/);
  assert.match(generationRunner, /include_coverage_matrix=False/);
  assert.match(report, /_coverage_matrix_skipped/);
});

test('USDJPY Strategy JSON backtest does not introduce live execution or wallets', () => {
  const source = [
    ...listFiles('tools/usdjpy_strategy_backtest'),
    'tools/run_usdjpy_strategy_backtest.py',
  ].map(read).join('\n');

  assert.doesNotMatch(source, /TRADE_ACTION_DEAL|PositionClose|OrderSendAsync|CTrade/);
  assert.doesNotMatch(source, /privateKeyAllowed\s*["']?\s*:\s*true|polymarketRealMoneyAllowed\s*["']?\s*:\s*true/i);
  assert.match(source, /orderSendAllowed["']?\s*:\s*False/);
  assert.match(source, /livePresetMutationAllowed["']?\s*:\s*False/);
});

test('USDJPY Strategy JSON backtest Python sources stay readable and multi-line', () => {
  for (const file of [...listFiles('tools/usdjpy_strategy_backtest'), 'tools/run_usdjpy_strategy_backtest.py']) {
    const source = read(file);
    const lines = source.split(/\r?\n/);
    if (!file.endsWith('__init__.py')) {
      assert.ok(lines.length >= 20, `${file} should stay readable and multi-line`);
    }
    lines.forEach((line, index) => {
      assert.ok(line.length <= 180, `${file}:${index + 1} should not exceed 180 characters`);
    });
  }
});
