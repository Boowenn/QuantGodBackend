import tempfile
import json
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tools.strategy_json.schema import ALLOWED_STRATEGY_FAMILIES
from tools.strategy_ga.fitness import evidence_metrics, score_seed
from tools.strategy_json.schema import base_strategy_seed
from tools.usdjpy_strategy_backtest.history_sync import sync_historical_klines
from tools.usdjpy_strategy_backtest.historical_news import classify_historical_news, load_historical_news_events
from tools.usdjpy_strategy_backtest.report import build_sample, run_backtest, status
from tools.usdjpy_strategy_backtest.schema import (
    backtest_cache_path,
    equity_path,
    history_sync_report_path,
    production_status_path,
    quality_report_path,
    report_path,
    trades_path,
)
from tools.usdjpy_strategy_backtest.sqlite_store import connect, count_bars, load_bars


class USDJPYStrategyBacktestTests(unittest.TestCase):
    def test_sample_and_run_write_usdjpy_backtest_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            sample = build_sample(runtime_dir, overwrite=True)
            self.assertEqual(sample["symbol"], "USDJPYc")
            self.assertGreaterEqual(sample["barCount"], 100)

            report = run_backtest(runtime_dir, write=True)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["symbol"], "USDJPYc")
            self.assertEqual(report["singleSourceOfTruth"], "STRATEGY_JSON_USDJPY_SQLITE_BACKTEST")
            self.assertFalse(report["safety"]["orderSendAllowed"])
            self.assertFalse(report["safety"]["livePresetMutationAllowed"])
            self.assertIn("netR", report["metrics"])
            self.assertIn("profitFactor", report["metrics"])
            self.assertIn("maxDrawdownR", report["metrics"])
            self.assertIn("historyCoverage", report)
            self.assertIn("strategyCoverageMatrix", report)
            self.assertIn("historicalNews", report)
            self.assertIn("cache", report)
            self.assertEqual(report["historyCoverage"]["schema"], "quantgod.usdjpy_sqlite_history_coverage.v1")
            self.assertEqual(report["strategyCoverageMatrix"]["schema"], "quantgod.strategy_backtest_coverage_matrix.v1")
            self.assertEqual(report["strategyCoverageMatrix"]["summary"]["routeCount"], len(ALLOWED_STRATEGY_FAMILIES) * 2)
            self.assertEqual(report["strategyCoverageMatrix"]["summary"]["parityVectorRouteCount"], len(ALLOWED_STRATEGY_FAMILIES) * 2)
            self.assertTrue(report["engine"]["costModel"]["dynamicSpreadFromBars"])
            self.assertEqual(report["engine"]["newsGateBacktest"]["schema"], "quantgod.strategy_backtest_news_gate_stats.v1")
            self.assertTrue(report_path(runtime_dir).exists())
            self.assertTrue(trades_path(runtime_dir).exists())
            self.assertTrue(equity_path(runtime_dir).exists())
            self.assertTrue(quality_report_path(runtime_dir).exists())
            self.assertTrue(backtest_cache_path(runtime_dir).exists())

            current = status(runtime_dir)
            self.assertEqual(current["barCounts"]["H1"], sample["barCount"])
            self.assertEqual(current["historyCoverage"]["primaryTimeframe"], "H1")
            self.assertEqual(current["latestReport"]["schema"], "quantgod.strategy_backtest.report.v1")
            self.assertEqual(current["qualityReport"]["schema"], "quantgod.strategy_backtest_quality.v1")
            with connect(runtime_dir) as conn:
                run_rows = conn.execute("SELECT COUNT(*) AS count FROM strategy_runs").fetchone()
                self.assertGreaterEqual(int(run_rows["count"]), 1)
                self.assertEqual(report["engine"]["coverage"], "ALL_SUPPORTED_USDJPY_SHADOW_FAMILIES")
                self.assertIn("costModel", report["engine"])
                self.assertIn("parityVector", report["engine"])

            cached = run_backtest(runtime_dir, write=False)
            self.assertTrue(cached["cache"]["hit"])

    def test_backtest_rejects_non_usdjpy_strategy_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            bad = base_strategy_seed("BAD")
            bad["symbol"] = "EURUSDc"
            report = run_backtest(runtime_dir, bad, write=False)
            self.assertFalse(report["ok"])
            self.assertEqual(report["validation"]["blockerCode"], "NON_USDJPY_REJECTED")
            self.assertEqual(report["metrics"], {})

    def test_ga_fitness_consumes_strategy_backtest_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            seed = base_strategy_seed("FITNESS")
            run_backtest(runtime_dir, seed, write=True)

            metrics = evidence_metrics(runtime_dir)
            self.assertTrue(metrics["strategyBacktest"]["present"])
            self.assertIn("profitFactor", metrics["strategyBacktest"])

            score = score_seed(seed, runtime_dir)
            self.assertIn("strategyBacktest", score)
            self.assertTrue(score["strategyBacktest"]["present"])
            self.assertEqual(score["strategyBacktest"]["strategyId"], seed["strategyId"])
            self.assertEqual(score["strategyBacktest"]["engine"].get("coverage"), "ALL_SUPPORTED_USDJPY_SHADOW_FAMILIES")
            self.assertIn("backtestQuality", score)
            self.assertTrue(score["backtestQuality"]["present"])

    def test_historical_news_classifier_keeps_soft_news_soft_and_high_impact_hard(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            news_dir = runtime_dir / "news"
            news_dir.mkdir(parents=True)
            (news_dir / "QuantGod_USDJPYNewsEvents.json").write_text(
                """
                {
                  "events": [
                    {"timeIso":"2026-05-07T12:00:00Z","title":"USDJPY liquidity note","impact":"medium"},
                    {"timeIso":"2026-05-07T18:00:00Z","title":"FOMC rate decision","impact":"high"}
                  ]
                }
                """,
                encoding="utf-8",
            )
            events = load_historical_news_events(runtime_dir)
            self.assertTrue(events["sourceAvailable"])
            self.assertEqual(events["eventCount"], 2)

            soft = classify_historical_news("2026-05-07T12:10:00Z", events)
            self.assertEqual(soft["riskLevel"], "SOFT")
            self.assertFalse(soft["hardBlock"])
            self.assertLess(soft["lotMultiplier"], 1.0)

            hard = classify_historical_news("2026-05-07T17:45:00Z", events)
            self.assertEqual(hard["riskLevel"], "HARD")
            self.assertTrue(hard["hardBlock"])

    def test_all_usdjpy_strategy_families_have_backtest_runner_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            build_sample(runtime_dir, overwrite=True)
            for family in sorted(ALLOWED_STRATEGY_FAMILIES):
                with self.subTest(family=family):
                    seed = base_strategy_seed(f"BT-{family}", family=family, direction="LONG")
                    report = run_backtest(runtime_dir, seed, write=False)
                    self.assertTrue(report["ok"], report)
                    self.assertEqual(report["strategyFamily"], family)
                    self.assertEqual(report["engine"]["coverage"], "ALL_SUPPORTED_USDJPY_SHADOW_FAMILIES")
                    self.assertIn(family, report["engine"]["supportedFamilies"])
                    self.assertIn("netR", report["metrics"])
                    self.assertNotIn("暂未接入", str(report.get("reasonZh")))

    def test_backtest_loads_latest_sqlite_window_when_history_expands(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            build_sample(runtime_dir, overwrite=True)
            with connect(runtime_dir) as conn:
                bars = conn.execute(
                    "SELECT timestamp FROM bars_h1 WHERE symbol = ? ORDER BY timestamp ASC",
                    ("USDJPYc",),
                ).fetchall()
                self.assertGreaterEqual(len(bars), 100)
                oldest = str(bars[0]["timestamp"])
                newest = str(bars[-1]["timestamp"])

            report = run_backtest(runtime_dir, write=True)
            coverage = report["historyCoverage"]
            self.assertEqual(coverage["timeframes"]["H1"]["earliestBar"], oldest)
            self.assertEqual(coverage["timeframes"]["H1"]["latestBar"], newest)
            self.assertEqual(report["multiTimeframe"]["contexts"]["H1"]["latestBar"], newest)

    def test_ga_fitness_backtests_each_seed_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            build_sample(runtime_dir, overwrite=True)
            rsi_seed = base_strategy_seed("GA-RSI", family="RSI_Reversal", direction="LONG")
            ma_seed = base_strategy_seed("GA-MA", family="MA_Cross", direction="LONG")

            rsi_score = score_seed(rsi_seed, runtime_dir)
            ma_score = score_seed(ma_seed, runtime_dir)

            self.assertEqual(rsi_score["strategyBacktest"]["strategyFamily"], "RSI_Reversal")
            self.assertEqual(ma_score["strategyBacktest"]["strategyFamily"], "MA_Cross")
            self.assertNotEqual(
                rsi_score["strategyBacktest"]["strategyId"],
                ma_score["strategyBacktest"]["strategyId"],
            )

    def test_history_sync_pulls_incremental_usdjpy_bars_from_mt5(self):
        class FakeMT5(types.SimpleNamespace):
            TIMEFRAME_M1 = "M1"
            TIMEFRAME_M5 = "M5"
            TIMEFRAME_M15 = "M15"
            TIMEFRAME_H1 = "H1"

            def __init__(self):
                super().__init__()
                self.calls = []

            def initialize(self, path=""):
                self.initialized_path = path
                return True

            def shutdown(self):
                self.shutdown_called = True

            def symbol_select(self, symbol, enabled):
                self.selected = (symbol, enabled)
                return True

            def last_error(self):
                return (0, "ok")

            def copy_rates_range(self, symbol, timeframe, from_dt, to_dt):
                self.calls.append((symbol, timeframe, from_dt, to_dt))
                step = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}[timeframe]
                rows = []
                cursor = from_dt.astimezone(timezone.utc)
                for index in range(12):
                    if cursor >= to_dt:
                        break
                    rows.append(
                        {
                            "time": int(cursor.timestamp()),
                            "open": 156.0 + index * 0.01,
                            "high": 156.03 + index * 0.01,
                            "low": 155.98 + index * 0.01,
                            "close": 156.01 + index * 0.01,
                            "tick_volume": 1000 + index,
                        }
                    )
                    cursor += timedelta(seconds=step)
                return rows

        fake = FakeMT5()
        old_module = sys.modules.get("MetaTrader5")
        sys.modules["MetaTrader5"] = fake
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runtime_dir = Path(tmp)
                report = sync_historical_klines(runtime_dir, lookback_days=3, timeframes=("M1", "M5", "M15", "H1"))
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["source"], "MT5_COPY_RATES_RANGE")
                self.assertEqual(report["sourceSymbol"], "USDJPYc")
                self.assertTrue(history_sync_report_path(runtime_dir).exists())
                self.assertGreaterEqual(len(fake.calls), 4)
                self.assertEqual({call[1] for call in fake.calls}, {"M1", "M5", "M15", "H1"})
                with connect(runtime_dir) as conn:
                    for timeframe in ("M1", "M5", "M15", "H1"):
                        self.assertGreater(count_bars(conn, timeframe), 0)
                current = status(runtime_dir)
                self.assertEqual(current["historySyncReport"]["schema"], "quantgod.usdjpy_historical_kline_sync_report.v1")
                self.assertIn("historyCoverage", current["historySyncReport"])
        finally:
            if old_module is None:
                sys.modules.pop("MetaTrader5", None)
            else:
                sys.modules["MetaTrader5"] = old_module

    def test_history_sync_ingests_mql5_copyrates_exports_when_mt5_python_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            export_dir = runtime_dir / "backtest" / "exported_klines"
            export_dir.mkdir(parents=True)
            base_epoch = int(datetime(2026, 5, 7, tzinfo=timezone.utc).timestamp())
            steps = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}
            for timeframe, step in steps.items():
                rows = ["epoch,timestamp,open,high,low,close,tick_volume,spread,real_volume"]
                for index in range(3):
                    epoch = base_epoch + index * step
                    rows.append(
                        f"{epoch},2026.05.07 00:0{index}:00,156.{index},156.{index + 1},"
                        f"155.{index},156.{index + 1},100{index},10,0"
                    )
                (export_dir / f"QuantGod_USDJPYc_{timeframe}_rates.csv").write_text("\n".join(rows), encoding="utf-8")
            (export_dir / "QuantGod_USDJPY_KlineExportManifest.json").write_text(
                '{"schema":"quantgod.mql5_kline_export_manifest.v1","source":"MQL5_COPYRATES_EXPORT"}',
                encoding="utf-8",
            )

            with patch("tools.usdjpy_strategy_backtest.history_sync.importlib.import_module", side_effect=ImportError("no mt5")):
                report = sync_historical_klines(runtime_dir, lookback_days=3, timeframes=("M1", "M5", "M15", "H1"))

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["source"], "MQL5_COPYRATES_EXPORT_FALLBACK")
            self.assertTrue(report["fallback"]["mql5Export"]["ok"])
            self.assertEqual(report["fallback"]["mql5Export"]["source"], "MQL5_COPYRATES_EXPORT")
            self.assertEqual(report["productionStatus"]["schema"], "quantgod.usdjpy_history_production_status.v1")
            self.assertTrue(production_status_path(runtime_dir).exists())
            with connect(runtime_dir) as conn:
                for timeframe in ("M1", "M5", "M15", "H1"):
                    self.assertEqual(count_bars(conn, timeframe), 3)
                m1_bars = load_bars(conn, "M1", limit=1)
                self.assertEqual(m1_bars[0].spread, 10.0)

    def test_history_sync_discovers_external_mt5_files_export_and_marks_production_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_dir = root / "repo_runtime"
            mt5_files_dir = root / "MetaTrader 5" / "MQL5" / "Files"
            export_dir = mt5_files_dir / "backtest" / "exported_klines"
            export_dir.mkdir(parents=True)
            latest = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            start = latest - timedelta(days=3)
            steps = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}
            for timeframe, step in steps.items():
                rows = ["epoch,timestamp,open,high,low,close,tick_volume,spread,real_volume"]
                cursor = start
                index = 0
                while cursor <= latest:
                    epoch = int(cursor.timestamp())
                    price = 156.0 + (index % 40) * 0.001
                    rows.append(
                        f"{epoch},{cursor.strftime('%Y.%m.%d %H:%M:%S')},"
                        f"{price:.3f},{price + 0.015:.3f},{price - 0.015:.3f},{price + 0.004:.3f},"
                        f"{1000 + index},10,0"
                    )
                    cursor += timedelta(seconds=step)
                    index += 1
                (export_dir / f"QuantGod_USDJPYc_{timeframe}_rates.csv").write_text("\n".join(rows), encoding="utf-8")
            (export_dir / "QuantGod_USDJPY_KlineExportManifest.json").write_text(
                json.dumps({"schema": "quantgod.mql5_kline_export_manifest.v1", "source": "MQL5_COPYRATES_EXPORT"}),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"QG_MT5_FILES_DIR": str(mt5_files_dir)}):
                with patch("tools.usdjpy_strategy_backtest.history_sync.importlib.import_module", side_effect=ImportError("no mt5")):
                    report = sync_historical_klines(
                        runtime_dir,
                        lookback_days=3,
                        timeframes=("M1", "M5", "M15", "H1"),
                        max_latest_lag_hours=2,
                    )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["source"], "MQL5_COPYRATES_EXPORT_FALLBACK")
            self.assertEqual(report["fallback"]["mql5Export"]["exportDir"], str(export_dir.resolve()))
            production = report["productionStatus"]
            self.assertEqual(production["schema"], "quantgod.usdjpy_history_production_status.v1")
            self.assertTrue(production["historyTargetSatisfied"], production)
            self.assertEqual(production["status"], "PASS")
            self.assertEqual(production["source"]["mql5ExportDir"], str(export_dir.resolve()))
            current = status(runtime_dir)
            self.assertEqual(current["historyProductionStatus"]["status"], "PASS")
            with connect(runtime_dir) as conn:
                self.assertGreaterEqual(count_bars(conn, "M1"), 3 * 24 * 60)


if __name__ == "__main__":
    unittest.main()
