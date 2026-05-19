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
from tools.strategy_ga.mutation import mutate_seed
from tools.strategy_ga.population import _recent_rejected_seeds, build_population
from tools.strategy_ga.seed_generator import exploration_seed_pool, quality_repair_seed_pool
from tools.strategy_json.fingerprint import strategy_fingerprint
from tools.strategy_json.schema import base_strategy_seed
from tools.strategy_json.validator import validate_strategy_json
from tools.usdjpy_strategy_backtest.cost_model import BacktestCostModel
from tools.usdjpy_strategy_backtest.history_sync import build_history_production_status, sync_historical_klines
from tools.usdjpy_strategy_backtest.historical_news import classify_historical_news, load_historical_news_events
from tools.usdjpy_strategy_backtest.report import build_sample, run_backtest, status
from tools.usdjpy_strategy_backtest.strategy_runner import _event_filter_blocks, _rsi_regime_decision, _simulate_exit
from tools.usdjpy_strategy_backtest.schema import (
    backtest_cache_path,
    equity_path,
    history_sync_report_path,
    production_status_path,
    quality_report_path,
    report_path,
    trades_path,
)
from tools.usdjpy_strategy_backtest.sqlite_store import Bar, connect, count_bars, load_bars, upsert_bars
from tools.usdjpy_strategy_backtest.walk_forward import build_seed_walk_forward


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

    def test_ga_fitness_blocks_promotion_when_history_production_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            seed = base_strategy_seed("FITNESS-HISTORY-PRODUCTION")
            run_backtest(runtime_dir, seed, write=True)
            production_status_path(runtime_dir).write_text(
                json.dumps(
                    {
                        "schema": "quantgod.usdjpy_history_production_status.v1",
                        "status": "WARN",
                        "historyTargetSatisfied": False,
                        "failedCount": 1,
                        "reasonZh": "M1 历史深度不足，不能作为生产级 GA 评分样本。",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            score = score_seed(seed, runtime_dir)
            self.assertEqual(score["blockerCode"], "HISTORY_PRODUCTION_NOT_READY")
            self.assertEqual(score["historyProductionStatus"]["promotionGateStatus"], "BLOCKED")
            self.assertFalse(score["historyProductionStatus"]["promotionAllowed"])

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

    def test_p4_10e_event_filter_blocks_known_soft_news_but_allows_unknown_history(self):
        event_filter = {
            "mode": "P4_10E_RSI_AVOID_KNOWN_EVENT_RISK",
            "allowedRiskLevels": ["NONE", "UNKNOWN"],
            "blockSoftRisk": True,
            "allowUnknownRisk": True,
        }

        self.assertTrue(_event_filter_blocks({"riskLevel": "SOFT"}, event_filter))
        self.assertFalse(_event_filter_blocks({"riskLevel": "UNKNOWN"}, event_filter))

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

    def test_strategy_json_family_parameters_are_validated_and_exposed_to_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            build_sample(runtime_dir, overwrite=True)
            seed = base_strategy_seed("BT-FAMILY-PARAMS", family="MA_Cross", direction="LONG")
            seed["indicators"]["ma"] = {"timeframe": "H1", "fastPeriod": 5, "slowPeriod": 34}

            validation = validate_strategy_json(seed)
            self.assertTrue(validation["valid"], validation)
            report = run_backtest(runtime_dir, seed, write=False)
            parity = report["engine"]["parityVector"]

            self.assertEqual(parity["familyParameters"]["ma"]["fastPeriod"], 5)
            self.assertEqual(parity["familyParameters"]["ma"]["slowPeriod"], 34)
            self.assertIn("signalCount", parity)

    def test_strategy_json_rejects_invalid_family_specific_parameters(self):
        seed = base_strategy_seed("BT-BAD-MA", family="MA_Cross", direction="LONG")
        seed["indicators"]["ma"] = {"timeframe": "H1", "fastPeriod": 55, "slowPeriod": 21}

        validation = validate_strategy_json(seed)

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["blockerCode"], "PARAM_RANGE_INVALID")
        self.assertIn("fastPeriod", validation["reasonZh"])

    def test_ga_exploration_and_mutation_change_family_specific_parameters(self):
        seed = exploration_seed_pool(8, 8)[0]
        mutated = mutate_seed(seed, "MUT-FAMILY-PARAMS", generation=9, offset=4)

        self.assertIn("ma", seed["indicators"])
        self.assertIn("tokyoRange", seed["indicators"])
        self.assertIn("nightReversion", seed["indicators"])
        self.assertIn("h4Pullback", seed["indicators"])
        self.assertNotEqual(
            seed["indicators"]["ma"]["fastPeriod"],
            mutated["indicators"]["ma"]["fastPeriod"],
        )
        self.assertNotEqual(
            seed["indicators"]["supportResistance"]["lookbackBars"],
            mutated["indicators"]["supportResistance"]["lookbackBars"],
        )

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

    def test_seed_walk_forward_splits_train_validation_forward_for_each_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            build_sample(runtime_dir, overwrite=True)
            seed = base_strategy_seed("WF-SEED", family="MA_Cross", direction="LONG")

            report = build_seed_walk_forward(runtime_dir, seed, write=True)

            self.assertEqual(report["schema"], "quantgod.usdjpy_seed_walk_forward.v1")
            self.assertEqual(report["symbol"], "USDJPYc")
            self.assertEqual(report["seedId"], seed["seedId"])
            self.assertEqual(report["splitPolicy"]["trainPct"], 60)
            self.assertFalse(report["splitPolicy"]["posteriorMayAffectTrigger"])
            self.assertEqual([item["segment"] for item in report["segments"]], ["train", "validation", "forward"])
            for segment in report["segments"]:
                self.assertIn("netR", segment)
                self.assertIn("profitFactor", segment)
                self.assertIn("winRate", segment)
                self.assertIn("maxDrawdownR", segment)
                self.assertIn("sharpe", segment)
                self.assertIn("sortino", segment)
                self.assertIn("tradeCount", segment)
                self.assertIn("parityStatus", segment)
                self.assertIn("executionFeedbackPenalty", segment)
            self.assertIn(report["summary"]["promotionGateStatus"], {"PASS", "WARN", "BLOCKED"})
            self.assertIn("stabilityScore", report["summary"])
            self.assertTrue((runtime_dir / "replay" / "usdjpy" / "QuantGod_USDJPYSeedWalkForwardReport.json").exists())

            score = score_seed(seed, runtime_dir)
            self.assertIn("walkForward", score)
            self.assertEqual(score["walkForward"]["seedId"], seed["seedId"])
            self.assertIn("walkForwardPenalty", score)
            self.assertIn("walkForwardStabilityBonus", score)

    def test_seed_walk_forward_uses_family_timeframe_for_tokyo_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            build_sample(runtime_dir, overwrite=True)
            start = datetime(2026, 4, 28, 0, 0, tzinfo=timezone.utc)
            bars = []
            price = 156.2
            for index in range(360):
                direction = -1 if index % 32 < 16 else 1
                close = price + direction * 0.01
                timestamp = (start + timedelta(minutes=15 * index)).isoformat().replace("+00:00", "Z")
                bars.append(
                    Bar(
                        timestamp=timestamp,
                        open=round(price, 5),
                        high=round(max(price, close) + 0.03, 5),
                        low=round(min(price, close) - 0.03, 5),
                        close=round(close, 5),
                        volume=1000 + index,
                        spread=12,
                    )
                )
                price = close
            with connect(runtime_dir) as conn:
                upsert_bars(conn, "M15", bars)
            seed = base_strategy_seed("WF-TOKYO", family="USDJPY_TOKYO_RANGE_BREAKOUT", direction="SHORT")

            report = build_seed_walk_forward(runtime_dir, seed, write=False)

            self.assertEqual(report["primaryTimeframe"], "M15")
            self.assertEqual(report["summary"]["primaryTimeframe"], "M15")
            self.assertTrue(all(item["primaryTimeframe"] == "M15" for item in report["segments"]))

    def test_ga_expands_search_space_when_no_elite_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            first = build_population(1, [], runtime_dir=runtime_dir)
            second = build_population(2, [], runtime_dir=runtime_dir)
            third = build_population(3, [], runtime_dir=runtime_dir)

            self.assertTrue(any(seed.get("source") == "EXPLORATION_GRID" for seed in second))
            self.assertTrue(any(seed.get("explorationMode") == "NO_ELITE_EXPAND_SEARCH" for seed in second))
            first_fingerprints = {strategy_fingerprint(seed) for seed in first}
            second_fingerprints = {strategy_fingerprint(seed) for seed in second}
            third_fingerprints = {strategy_fingerprint(seed) for seed in third}
            self.assertFalse(second_fingerprints.issubset(first_fingerprints))
            self.assertNotEqual(second_fingerprints, third_fingerprints)

    def test_ga_mutates_best_rejected_seed_when_no_elite_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-REJECTED", family="RSI_Reversal", direction="LONG")
            row = {
                "generation": 1,
                "rank": 1,
                "fitness": -0.5,
                "blockerCode": "WALK_FORWARD_UNSTABLE",
                "strategyJson": parent,
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            population = build_population(2, [], runtime_dir=runtime_dir)
            mutation = next((seed for seed in population if seed.get("source") == "EXPLORATION_MUTATION"), None)

            self.assertIsNotNone(mutation)
            self.assertEqual(mutation["parentSeedId"], parent["seedId"])
            self.assertEqual(mutation["explorationMode"], "NO_ELITE_EXPAND_SEARCH")

    def test_ga_mutation_parent_selection_deprioritizes_sparse_bb_short(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            sparse_bb = base_strategy_seed("PARENT-BB-SPARSE", family="BB_Triple", direction="SHORT")
            rsi_parent = base_strategy_seed("PARENT-RSI", family="RSI_Reversal", direction="LONG")
            macd_parent = base_strategy_seed("PARENT-MACD", family="MACD_Divergence", direction="LONG")
            rows = [
                {
                    "generation": 17,
                    "rank": 1,
                    "fitness": -3.1,
                    "blockerCode": "STRATEGY_BACKTEST_NO_TRADES",
                    "strategyJson": sparse_bb,
                    "fitnessBreakdown": {"sampleCount": 5, "strategyBacktest": {"tradeCount": 0}},
                },
                {
                    "generation": 17,
                    "rank": 2,
                    "fitness": -8.0,
                    "blockerCode": "WALK_FORWARD_UNSTABLE",
                    "strategyJson": rsi_parent,
                    "fitnessBreakdown": {"sampleCount": 80, "strategyBacktest": {"tradeCount": 40}},
                },
                {
                    "generation": 17,
                    "rank": 3,
                    "fitness": -9.0,
                    "blockerCode": "WALK_FORWARD_UNSTABLE",
                    "strategyJson": macd_parent,
                    "fitnessBreakdown": {"sampleCount": 60, "strategyBacktest": {"tradeCount": 30}},
                },
            ]
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )

            parents = _recent_rejected_seeds(runtime_dir, limit=2)

            self.assertEqual([seed["seedId"] for seed in parents], ["PARENT-RSI", "PARENT-MACD"])

    def test_ga_quality_repair_targets_blocked_promising_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-MAE", family="SR_Breakout", direction="LONG")
            parent["risk"]["riskPips"] = 10.0
            parent["exit"]["timeStopBars"]["H1"] = 6
            row = {
                "generation": 5,
                "rank": 1,
                "fitness": 1.2,
                "blockerCode": "MAX_ADVERSE_TOO_HIGH",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "strategyBacktest": {"netR": 5.0, "tradeCount": 12},
                    "walkForward": {"summary": {"stabilityScore": 0.4}},
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repairs = quality_repair_seed_pool(runtime_dir, generation_number=6, limit=4)
            population = build_population(6, [], runtime_dir=runtime_dir)
            repair = repairs[0]

            self.assertTrue(repairs)
            self.assertEqual(repair["source"], "QUALITY_REPAIR")
            self.assertEqual(repair["parentSeedId"], parent["seedId"])
            self.assertEqual(repair["repairTargetBlocker"], "MAX_ADVERSE_TOO_HIGH")
            self.assertIn("MAX_ADVERSE_REPAIR", repair["qualityProfile"])
            self.assertGreaterEqual(repair["risk"]["riskPips"], parent["risk"]["riskPips"])
            self.assertLessEqual(repair["exit"]["timeStopBars"]["H1"], parent["exit"]["timeStopBars"]["H1"])
            self.assertEqual(repair["risk"]["stage"], "SHADOW")
            self.assertLessEqual(repair["risk"]["maxLot"], 2.0)
            self.assertTrue(validate_strategy_json(repair)["valid"])
            self.assertTrue(any(seed.get("source") == "QUALITY_REPAIR" for seed in population))

    def test_ga_quality_repair_adds_bb_short_family_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-BB-SHORT", family="BB_Triple", direction="SHORT")
            parent["indicators"]["bollinger"]["deviations"] = 2.0
            parent["indicators"]["bollinger"]["reclaimBufferPips"] = 0.0
            row = {
                "generation": 7,
                "rank": 1,
                "fitness": -2.5,
                "blockerCode": "WALK_FORWARD_UNSTABLE",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "strategyBacktest": {"netR": 2.0, "tradeCount": 64},
                    "walkForward": {"summary": {"stabilityScore": 0.12}},
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repair = quality_repair_seed_pool(runtime_dir, generation_number=8, limit=3)[0]
            bollinger = repair["indicators"]["bollinger"]

            self.assertEqual(repair["qualityProfile"], "BB_SHORT_RECLAIM_STABILIZER")
            self.assertEqual(repair["direction"], "SHORT")
            self.assertGreaterEqual(bollinger["deviations"], 2.15)
            self.assertGreaterEqual(bollinger["reclaimBufferPips"], 1.0)
            self.assertLessEqual(repair["exit"]["timeStopBars"]["H1"], 3)
            self.assertTrue(validate_strategy_json(repair)["valid"])

    def test_ga_quality_repair_expands_bb_short_samples_after_stability_tightening(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-BB-SAMPLE", family="BB_Triple", direction="SHORT")
            parent["indicators"]["bollinger"]["deviations"] = 2.4
            parent["indicators"]["bollinger"]["reclaimBufferPips"] = 2.0
            row = {
                "generation": 10,
                "rank": 2,
                "fitness": -2.3,
                "blockerCode": "INSUFFICIENT_SAMPLES",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "strategyBacktest": {"netR": 1.2, "tradeCount": 4},
                    "walkForward": {"summary": {"stabilityScore": 0.2}},
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repair = quality_repair_seed_pool(runtime_dir, generation_number=11, limit=3)[0]
            bollinger = repair["indicators"]["bollinger"]

            self.assertEqual(repair["qualityProfile"], "BB_SHORT_SAMPLE_EXPANDER")
            self.assertLessEqual(bollinger["deviations"], parent["indicators"]["bollinger"]["deviations"])
            self.assertLessEqual(bollinger["reclaimBufferPips"], 3.0)
            self.assertGreaterEqual(repair["exit"]["timeStopBars"]["H1"], 3)
            self.assertTrue(validate_strategy_json(repair)["valid"])

    def test_ga_quality_repair_adds_tokyo_range_family_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-TOKYO", family="USDJPY_TOKYO_RANGE_BREAKOUT", direction="SHORT")
            parent["indicators"]["tokyoRange"]["bufferPips"] = 0.0
            row = {
                "generation": 7,
                "rank": 2,
                "fitness": -10.2,
                "blockerCode": "WALK_FORWARD_UNSTABLE",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "strategyBacktest": {"netR": -1.0, "tradeCount": 120},
                    "walkForward": {"summary": {"stabilityScore": 0.08}},
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repair = quality_repair_seed_pool(runtime_dir, generation_number=8, limit=3)[0]
            tokyo = repair["indicators"]["tokyoRange"]

            self.assertEqual(repair["qualityProfile"], "TOKYO_RANGE_SESSION_STABILIZER")
            self.assertEqual(tokyo["timeframe"], "M15")
            self.assertEqual(tokyo["rangeStartHourUtc"], 0)
            self.assertEqual(tokyo["rangeEndHourUtc"], 2)
            self.assertGreaterEqual(tokyo["bufferPips"], 1.0)
            self.assertLessEqual(tokyo["tradeEndHourUtc"] - tokyo["tradeStartHourUtc"], 2)
            self.assertTrue(validate_strategy_json(repair)["valid"])

    def test_ga_quality_repair_expands_rsi_macd_and_h4_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parents = [
                base_strategy_seed("PARENT-RSI-QUALITY", family="RSI_Reversal", direction="LONG"),
                base_strategy_seed("PARENT-MACD-QUALITY", family="MACD_Divergence", direction="LONG"),
                base_strategy_seed("PARENT-H4-QUALITY", family="USDJPY_H4_TREND_PULLBACK", direction="SHORT"),
            ]
            rows = []
            for index, parent in enumerate(parents, start=1):
                rows.append(
                    {
                        "generation": 17,
                        "rank": index,
                        "fitness": -5.0 - index,
                        "blockerCode": "WALK_FORWARD_UNSTABLE",
                        "strategyJson": parent,
                        "fitnessBreakdown": {
                            "strategyBacktest": {"netR": -1.0, "tradeCount": 30 + index},
                            "walkForward": {"summary": {"stabilityScore": 0.1}},
                        },
                    }
                )
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )

            repairs = quality_repair_seed_pool(runtime_dir, generation_number=18, limit=6)
            profiles = {seed.get("qualityProfile") for seed in repairs}

            self.assertIn("RSI_REVERSAL_STABILITY_REPAIR", profiles)
            self.assertIn("MACD_HISTOGRAM_STABILIZER", profiles)
            self.assertIn("H4_PULLBACK_STABILIZER", profiles)
            self.assertTrue(all(validate_strategy_json(seed)["valid"] for seed in repairs))

    def test_ga_quality_repair_expands_rsi_overfit_samples_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-RSI-OVERFIT", family="RSI_Reversal", direction="LONG")
            parent["indicators"]["rsi"]["timeframe"] = "H1"
            parent["indicators"]["rsi"]["buyBand"] = 33
            parent["indicators"]["rsi"]["crossbackThreshold"] = 0.9
            row = {
                "generation": 43,
                "rank": 1,
                "fitness": 1.86,
                "blockerCode": "OVERFIT_RISK",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "sampleCount": 14,
                    "strategyBacktest": {"netR": 2.78, "tradeCount": 13},
                    "walkForward": {
                        "summary": {
                            "promotionGateStatus": "PASS",
                            "stabilityScore": 0.95,
                            "sampleCount": 14,
                        }
                    },
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repair = quality_repair_seed_pool(runtime_dir, generation_number=44, limit=4)[0]
            rsi = repair["indicators"]["rsi"]

            self.assertEqual(repair["qualityProfile"], "RSI_REVERSAL_REGIME_EVENT_FILTER")
            self.assertEqual(repair["repairTargetBlocker"], "OVERFIT_RISK")
            self.assertEqual(rsi["timeframe"], "H1")
            self.assertEqual(rsi["regimeFilter"]["mode"], "P4_10E_RSI_BEARISH_STRETCH")
            self.assertTrue(repair["entry"]["eventFilter"]["blockSoftRisk"])
            self.assertLessEqual(rsi["buyBand"], 29)
            self.assertGreaterEqual(repair["exit"]["timeStopBars"]["H1"], 3)
            self.assertTrue(validate_strategy_json(repair)["valid"])

    def test_ga_quality_repair_adds_rsi_segment_overfit_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-RSI-SEGMENT", family="RSI_Reversal", direction="LONG")
            parent["indicators"]["rsi"]["timeframe"] = "H1"
            parent["indicators"]["rsi"]["period"] = 21
            parent["indicators"]["rsi"]["buyBand"] = 29
            parent["indicators"]["rsi"]["crossbackThreshold"] = 0.7
            parent["indicators"]["rsi"]["regimeFilter"] = {
                "mode": "P4_10E_RSI_BEARISH_STRETCH",
                "allowedHoursUtc": [0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 16, 17, 18],
                "emaFastPeriod": 20,
                "emaSlowPeriod": 50,
                "slopeLookbackBars": 3,
                "minFastMinusSlowPips": -260,
                "maxFastMinusSlowPips": -6,
                "minDistanceFromSlowPips": -280,
                "maxDistanceFromSlowPips": -45,
                "minSlowSlopePips": -50,
                "maxSlowSlopePips": -4,
            }
            row = {
                "generation": 60,
                "rank": 1,
                "fitness": 1.45,
                "blockerCode": "WALK_FORWARD_UNSTABLE",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "sampleCount": 22,
                    "strategyBacktest": {"netR": 4.89, "tradeCount": 19},
                    "walkForward": {
                        "summary": {
                            "promotionGateStatus": "BLOCKED",
                            "blockerCode": "WALK_FORWARD_UNSTABLE",
                            "trainNetR": 5.52,
                            "validationNetR": 1.45,
                            "forwardNetR": -0.05,
                            "overfitPenalty": 0.72,
                            "stabilityScore": 0.54,
                            "sampleCount": 22,
                        }
                    },
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repair = quality_repair_seed_pool(runtime_dir, generation_number=61, limit=4)[0]
            rsi = repair["indicators"]["rsi"]

            self.assertEqual(repair["qualityProfile"], "RSI_REVERSAL_SEGMENT_OVERFIT_CLOSURE")
            self.assertEqual(repair["repairTargetBlocker"], "WALK_FORWARD_UNSTABLE")
            self.assertLessEqual(rsi["maxCrossbackRsi"], 38.0)
            self.assertEqual(rsi["regimeFilter"]["mode"], "P4_10E_RSI_BEARISH_STRETCH")
            self.assertLessEqual(repair["exit"]["trailStartR"], 0.85)
            self.assertIn("rsi.segmentOverfitClosure == true", repair["entry"]["conditions"])
            self.assertTrue(validate_strategy_json(repair)["valid"])

    def test_p4_10e_rsi_regime_filter_allows_only_bearish_stretch_hours(self):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        bars = []
        price = 160.0
        for index in range(80):
            close = price - 0.08
            bars.append(
                Bar(
                    timestamp=(start + timedelta(hours=index)).isoformat().replace("+00:00", "Z"),
                    open=round(price, 5),
                    high=round(price + 0.02, 5),
                    low=round(close - 0.02, 5),
                    close=round(close, 5),
                    volume=1000 + index,
                    spread=12,
                )
            )
            price = close
        from tools.usdjpy_strategy_backtest.indicators import ema_values

        closes = [bar.close for bar in bars]
        fast = ema_values(closes, 20)
        slow = ema_values(closes, 50)
        cfg = {
            "mode": "P4_10E_RSI_BEARISH_STRETCH",
            "allowedHoursUtc": [7],
            "emaFastPeriod": 20,
            "emaSlowPeriod": 50,
            "slopeLookbackBars": 3,
            "minFastMinusSlowPips": -260,
            "maxFastMinusSlowPips": -6,
            "minDistanceFromSlowPips": -280,
            "maxDistanceFromSlowPips": -45,
            "minSlowSlopePips": -50,
            "maxSlowSlopePips": -4,
        }

        blocked_cfg = {**cfg, "allowedHoursUtc": [8]}
        allowed = _rsi_regime_decision(bars, 55, "LONG", cfg, fast, slow)
        blocked = _rsi_regime_decision(bars, 55, "LONG", blocked_cfg, fast, slow)

        self.assertTrue(allowed["allowed"], allowed)
        self.assertFalse(blocked["allowed"], blocked)
        self.assertEqual(blocked["reason"], "HOUR_FILTER")

    def test_p4_10e_rsi_positive_edge_requires_twenty_trades(self):
        seed = base_strategy_seed("RSI-MIN-TRADE-GATE", family="RSI_Reversal", direction="LONG")
        metrics = {
            "sampleCount": 5,
            "netR": 3.8,
            "maxAdverseR": 0.0,
            "profitCaptureRatio": 0.0,
            "missedOpportunityReduction": 0.0,
            "validationNetRDelta": 0.2,
            "forwardNetRDelta": 0.2,
            "walkForward": {
                "summary": {
                    "promotionGateStatus": "PASS",
                    "stabilityScore": 0.8,
                    "validSegmentCount": 3,
                    "validationNetR": 1.0,
                    "forwardNetR": 1.0,
                    "sampleCount": 5,
                }
            },
            "strategyBacktest": {
                "present": True,
                "ok": True,
                "tradeCount": 5,
                "profitFactor": 2.5,
                "winRate": 80.0,
                "maxDrawdownR": 0.1,
                "sharpe": 1.0,
                "sortino": 1.0,
            },
            "parity": {"promotionGateStatus": "PASS"},
            "executionFeedback": {"promotionGateStatus": "PASS"},
            "strategyContractShadow": {},
            "evidencePenalty": 0.0,
            "historyProductionStatus": {"promotionGateStatus": "PASS"},
        }
        with patch("tools.strategy_ga.fitness.evidence_metrics", return_value=metrics):
            score = score_seed(seed, Path("/tmp"))

        self.assertEqual(score["blockerCode"], "RSI_MIN_TRADE_GATE")
        self.assertGreater(score["rsiMinTradeGatePenalty"], 0)
        self.assertLess(score["fitness"], 0)

    def test_p4_10f_rsi_segment_overfit_penalty_flags_train_dominance(self):
        seed = base_strategy_seed("RSI-SEGMENT-OVERFIT", family="RSI_Reversal", direction="LONG")
        metrics = {
            "sampleCount": 30,
            "netR": 4.7,
            "maxAdverseR": 0.0,
            "profitCaptureRatio": 0.0,
            "missedOpportunityReduction": 0.0,
            "validationNetRDelta": -3.7,
            "forwardNetRDelta": -0.4,
            "walkForward": {
                "summary": {
                    "promotionGateStatus": "PASS",
                    "stabilityScore": 0.91,
                    "validSegmentCount": 3,
                    "trainNetR": 5.1,
                    "validationNetR": 1.3,
                    "forwardNetR": 0.9,
                    "sampleCount": 30,
                    "overfitPenalty": 0.08,
                }
            },
            "strategyBacktest": {
                "present": True,
                "ok": True,
                "tradeCount": 21,
                "profitFactor": 2.5,
                "winRate": 65.0,
                "maxDrawdownR": 0.4,
                "sharpe": 1.0,
                "sortino": 1.0,
            },
            "parity": {"promotionGateStatus": "PASS"},
            "executionFeedback": {"promotionGateStatus": "PASS"},
            "strategyContractShadow": {},
            "evidencePenalty": 0.0,
            "historyProductionStatus": {"promotionGateStatus": "PASS"},
        }
        with patch("tools.strategy_ga.fitness.evidence_metrics", return_value=metrics):
            score = score_seed(seed, Path("/tmp"))

        self.assertGreater(score["rsiSegmentOverfitPenalty"], 0)
        self.assertLess(score["overfitPenalty"], 0.2)
        self.assertIsNone(score["blockerCode"])

    def test_p4_10g_rsi_max_adverse_repair_adds_path_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-RSI-MAE", family="RSI_Reversal", direction="LONG")
            parent["indicators"]["rsi"]["regimeFilter"] = {
                "mode": "P4_10E_RSI_BEARISH_STRETCH",
                "allowedHoursUtc": [0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 16, 17, 18],
                "emaFastPeriod": 20,
                "emaSlowPeriod": 50,
                "slopeLookbackBars": 3,
                "minFastMinusSlowPips": -260,
                "maxFastMinusSlowPips": -6,
                "minDistanceFromSlowPips": -280,
                "maxDistanceFromSlowPips": -45,
                "minSlowSlopePips": -50,
                "maxSlowSlopePips": -4,
            }
            row = {
                "generation": 69,
                "rank": 1,
                "fitness": 3.6248,
                "blockerCode": "MAX_ADVERSE_TOO_HIGH",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "sampleCount": 21,
                    "maxAdverseR": -1.82,
                    "strategyBacktest": {"netR": 4.353, "tradeCount": 18},
                    "walkForward": {
                        "summary": {
                            "promotionGateStatus": "PASS",
                            "stabilityScore": 0.9421,
                            "trainNetR": 3.7799,
                            "validationNetR": 1.6302,
                            "forwardNetR": 1.189,
                            "overfitPenalty": 0.0176,
                            "sampleCount": 21,
                        }
                    },
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repair = quality_repair_seed_pool(runtime_dir, generation_number=70, limit=3)[0]
            rsi = repair["indicators"]["rsi"]
            guard = rsi["adverseExcursionGuard"]

            self.assertEqual(repair["qualityProfile"], "RSI_REVERSAL_ADVERSE_EXCURSION_CLOSURE")
            self.assertEqual(repair["repairTargetBlocker"], "MAX_ADVERSE_TOO_HIGH")
            self.assertEqual(guard["mode"], "P4_10G_RSI_ADVERSE_EXCURSION")
            self.assertLessEqual(guard["maxEarlyAdverseR"], 0.8)
            self.assertLessEqual(rsi["maxCrossbackRsi"], 35.5)
            self.assertIn("rsi.adverseExcursionGuard == P4_10G_RSI_ADVERSE_EXCURSION", repair["entry"]["conditions"])
            self.assertTrue(validate_strategy_json(repair)["valid"])

    def test_p4_10g_rsi_adverse_guard_caps_early_mae(self):
        strategy = base_strategy_seed("RSI-ADVERSE-GUARD", family="RSI_Reversal", direction="LONG")
        strategy["indicators"]["rsi"]["adverseExcursionGuard"] = {
            "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
            "lookaheadBars": 2,
            "maxEarlyAdverseR": 0.6,
            "confirmationBars": 2,
            "minConfirmR": 0.05,
            "rangeLookbackBars": 3,
            "maxEntryRangePips": 80,
        }
        bars = [
            Bar("2026-01-01T00:00:00Z", 150.0, 150.02, 149.80, 149.85, 1000, 0),
            Bar("2026-01-01T01:00:00Z", 149.85, 149.90, 149.70, 149.80, 1000, 0),
            Bar("2026-01-01T02:00:00Z", 149.80, 150.05, 149.75, 150.00, 1000, 0),
        ]

        trade, exit_index = _simulate_exit(
            strategy,
            bars,
            entry_index=0,
            direction="LONG",
            hold_bars=3,
            risk_pips=20.0,
            trail_start_r=1.5,
            giveback_pct=0.6,
            trade_no=1,
            signal={"reason": "RSI_CROSSBACK", "evidence": {}},
            cost_model=BacktestCostModel(spread_pips=0, slippage_pips=0, dynamic_spread_from_bars=False),
            news_decision={"lotMultiplier": 1.0},
        )

        self.assertEqual(exit_index, 0)
        self.assertEqual(trade["exitReason"], "RSI_EARLY_ADVERSE_KILL")
        self.assertEqual(trade["maeR"], -0.6)
        self.assertGreater(trade["rawProfitR"], -1.0)

    def test_p4_10h_guarded_rsi_sample_recovery_keeps_adverse_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            ga_dir = runtime_dir / "ga"
            ga_dir.mkdir(parents=True)
            parent = base_strategy_seed("PARENT-RSI-GUARDED-SAMPLE", family="RSI_Reversal", direction="LONG")
            parent["indicators"]["rsi"]["adverseExcursionGuard"] = {
                "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
                "lookaheadBars": 2,
                "maxEarlyAdverseR": 0.68,
                "confirmationBars": 1,
                "minConfirmR": 0.05,
                "rangeLookbackBars": 3,
                "maxEntryRangePips": 42,
            }
            row = {
                "generation": 73,
                "rank": 1,
                "fitness": 1.5375,
                "blockerCode": "RSI_MIN_TRADE_GATE",
                "strategyJson": parent,
                "fitnessBreakdown": {
                    "sampleCount": 12,
                    "maxAdverseR": -0.68,
                    "strategyBacktest": {"netR": 5.8484, "tradeCount": 11},
                    "walkForward": {
                        "summary": {
                            "promotionGateStatus": "PASS",
                            "stabilityScore": 1.0,
                            "trainNetR": 3.8,
                            "validationNetR": 1.3044,
                            "forwardNetR": 1.6488,
                            "overfitPenalty": 0.25,
                            "sampleCount": 12,
                        }
                    },
                },
            }
            (ga_dir / "QuantGod_GACandidateRuns.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            repairs = quality_repair_seed_pool(runtime_dir, generation_number=74, limit=4)
            profiles = {seed["qualityProfile"] for seed in repairs}
            recovery = repairs[0]
            guarded_gate = next(seed for seed in repairs if seed["qualityProfile"] == "RSI_REVERSAL_GUARDED_20_TRADE_BALANCER")
            recovery_guard = recovery["indicators"]["rsi"]["adverseExcursionGuard"]
            gate_guard = guarded_gate["indicators"]["rsi"]["adverseExcursionGuard"]

            self.assertEqual(recovery["qualityProfile"], "RSI_REVERSAL_GUARDED_SAMPLE_RECOVERY")
            self.assertIn("RSI_REVERSAL_GUARDED_20_TRADE_BALANCER", profiles)
            self.assertEqual(recovery["repairTargetBlocker"], "RSI_MIN_TRADE_GATE")
            self.assertEqual(recovery_guard["mode"], "P4_10G_RSI_ADVERSE_EXCURSION")
            self.assertGreater(recovery_guard["maxEntryRangePips"], 42)
            self.assertGreaterEqual(gate_guard["maxEarlyAdverseR"], 0.82)
            self.assertIn("rsi.guardedSampleRecovery == true", recovery["entry"]["conditions"])
            self.assertTrue(validate_strategy_json(recovery)["valid"])
            self.assertTrue(validate_strategy_json(guarded_gate)["valid"])

    def test_history_sync_pulls_incremental_usdjpy_bars_from_mt5(self):
        class FakeMT5(types.SimpleNamespace):
            TIMEFRAME_M1 = "M1"
            TIMEFRAME_M5 = "M5"
            TIMEFRAME_M15 = "M15"
            TIMEFRAME_H1 = "H1"
            TIMEFRAME_H4 = "H4"

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
                step = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400}[timeframe]
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
                report = sync_historical_klines(runtime_dir, lookback_days=3, timeframes=("M1", "M5", "M15", "H1", "H4"))
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["source"], "MT5_COPY_RATES_RANGE")
                self.assertEqual(report["sourceSymbol"], "USDJPYc")
                self.assertTrue(history_sync_report_path(runtime_dir).exists())
                self.assertGreaterEqual(len(fake.calls), 5)
                self.assertEqual({call[1] for call in fake.calls}, {"M1", "M5", "M15", "H1", "H4"})
                with connect(runtime_dir) as conn:
                    for timeframe in ("M1", "M5", "M15", "H1", "H4"):
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

    def test_history_production_allows_small_mt5_server_time_skew(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            checked_at = datetime(2026, 5, 18, 2, 0, tzinfo=timezone.utc)
            latest = checked_at + timedelta(hours=3)
            start = checked_at - timedelta(days=10)
            steps = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}
            with connect(runtime_dir) as conn:
                for timeframe, step in steps.items():
                    bars = []
                    cursor = start
                    index = 0
                    while cursor <= latest:
                        price = 156.0 + (index % 20) * 0.001
                        bars.append(
                            Bar(
                                timestamp=cursor.isoformat().replace("+00:00", "Z"),
                                open=price,
                                high=price + 0.01,
                                low=price - 0.01,
                                close=price + 0.002,
                                volume=1000,
                                spread=10,
                            )
                        )
                        cursor += timedelta(seconds=step)
                        index += 1
                    upsert_bars(conn, timeframe, bars)

            report = build_history_production_status(
                runtime_dir,
                sync_report={"ok": True, "source": "MQL5_COPYRATES_EXPORT_FALLBACK"},
                target_days=10,
                max_latest_lag_hours=2,
                now=checked_at,
            )

            self.assertEqual(report["status"], "PASS", report)
            self.assertTrue(report["historyTargetSatisfied"], report)
            self.assertEqual(report["timeframes"]["M1"]["latestLagHours"], 0.0)
            self.assertEqual(report["timeframes"]["M1"]["futureSkewHours"], 3.0)


if __name__ == "__main__":
    unittest.main()
