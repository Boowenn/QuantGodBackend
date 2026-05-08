import tempfile
import unittest
import os
from pathlib import Path

from tools.strategy_ga.generation_runner import read_candidate, read_candidates, run_generation
from tools.strategy_ga.telegram_text import ga_to_chinese_text
from tools.strategy_json.schema import base_strategy_seed
from tools.strategy_json.validator import validate_strategy_json


class StrategyJsonGATests(unittest.TestCase):
    def test_validator_rejects_execution_primitives_and_live_privileges(self):
        seed = base_strategy_seed("GA-USDJPY-TEST")
        seed["entry"]["conditions"].append("OrderSend()")
        self.assertFalse(validate_strategy_json(seed)["valid"])

        seed = base_strategy_seed("GA-USDJPY-TEST")
        seed["risk"]["maxLot"] = 2.1
        self.assertEqual(validate_strategy_json(seed)["blockerCode"], "MAX_LOT_TOO_HIGH")

        seed = base_strategy_seed("GA-USDJPY-TEST")
        seed["risk"]["stage"] = "MICRO_LIVE"
        self.assertEqual(validate_strategy_json(seed)["blockerCode"], "LIVE_STAGE_REJECTED")

        seed = base_strategy_seed("GA-USDJPY-TEST")
        seed["symbol"] = "EURUSDc"
        self.assertEqual(validate_strategy_json(seed)["blockerCode"], "NON_USDJPY_REJECTED")

    def test_validator_allows_explicit_false_safety_boundary_fields(self):
        seed = base_strategy_seed("GA-USDJPY-SAFE")
        result = validate_strategy_json(seed)
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["normalized"]["safety"]["orderSendAllowed"])
        self.assertFalse(result["normalized"]["safety"]["telegramCommandExecutionAllowed"])

    def test_generation_writes_trace_files_and_never_promotes_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            result = run_generation(runtime_dir, write=True)
            ga_dir = runtime_dir / "ga"

            for name in [
                "QuantGod_GAStatus.json",
                "QuantGod_GAGenerationLatest.json",
                "QuantGod_GACandidateRuns.jsonl",
                "QuantGod_GAEliteStrategies.json",
                "QuantGod_GABlockerSummary.json",
                "QuantGod_GAEvolutionPath.json",
                "QuantGod_GAFitnessCache.json",
                "QuantGod_GALineage.json",
                "QuantGod_GARunLimiter.json",
            ]:
                self.assertTrue((ga_dir / name).exists(), name)

            self.assertTrue(result["candidates"])
            self.assertTrue(result["generation"]["strategyBacktest"]["required"])
            self.assertEqual(
                result["generation"]["strategyBacktest"]["scoredCount"],
                len(result["candidates"]),
            )
            for row in result["candidates"]:
                self.assertEqual(row["strategyJson"]["symbol"], "USDJPYc")
                self.assertIn("generationId", row)
                self.assertIn("seedId", row)
                self.assertIn("fitness", row)
                self.assertIn("blockerCode", row)
                backtest = row["fitnessBreakdown"]["strategyBacktest"]
                for field in [
                    "required",
                    "present",
                    "ok",
                    "netR",
                    "profitFactor",
                    "winRate",
                    "maxDrawdownR",
                    "sharpe",
                    "sortino",
                    "tradeCount",
                ]:
                    self.assertIn(field, backtest)
                self.assertTrue(backtest["required"])
                self.assertTrue(backtest["present"])
                self.assertNotIn(row["promotionStage"], {"MICRO_LIVE", "LIVE_LIMITED"})
                self.assertFalse(row["safety"]["orderSendAllowed"])
                self.assertFalse(row["safety"]["livePresetMutationAllowed"])

            latest = read_candidates(runtime_dir)
            self.assertEqual(len(latest["candidates"]), len(result["candidates"]))

            detail = read_candidate(runtime_dir, result["candidates"][0]["seedId"])
            self.assertTrue(detail["ok"], detail)
            audit = detail["candidate"]["audit"]
            self.assertEqual(audit["schema"], "quantgod.ga.candidate_audit.v1")
            self.assertIn("lineage", audit)
            self.assertIn("lineageTree", audit)
            self.assertIn("sourceTrace", audit)
            self.assertIn("backtest", audit)
            self.assertIn("evidenceChain", audit)
            self.assertTrue(audit["backtest"]["present"])
            self.assertIn("equityCurve", audit["backtest"])
            self.assertEqual(audit["lineageTree"]["schema"], "quantgod.ga.lineage_tree.v1")
            self.assertGreaterEqual(audit["lineageTree"]["nodeCount"], 1)
            self.assertIsInstance(audit["lineageTree"]["nodes"], list)
            self.assertIsInstance(audit["lineageTree"]["edges"], list)
            self.assertIn("elitePathSeedIds", audit["lineageTree"])
            self.assertIn("fold", audit["lineageTree"])
            self.assertIn("canExpand", audit["lineageTree"]["fold"])
            self.assertTrue(any(node.get("selected") for node in audit["lineageTree"]["nodes"]))
            self.assertIn("lineagePath", audit)
            self.assertEqual(audit["lineagePath"]["schema"], "quantgod.ga.lineage_path.v1")
            self.assertIsInstance(audit["lineagePath"]["nodes"], list)
            self.assertIn("bestFitnessEnd", audit["lineagePath"])
            self.assertIn("fitnessDelta", audit["lineagePath"])
            self.assertIsInstance(audit["evidenceChain"], list)
            self.assertTrue(any(item["step"] == "USDJPY SQLite 回测" for item in audit["evidenceChain"]))

    def test_case_memory_seeds_cache_and_lineage_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            evidence_dir = runtime_dir / "evidence_os"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "QuantGod_CaseMemorySummary.json").write_text(
                """
                {
                  "schema": "quantgod.case_memory_summary.v1",
                  "cases": [
                    {
                      "caseId": "USDJPY-MISSED-001",
                      "status": "QUEUED_FOR_GA",
                      "proposedAction": {"mutationHint": "relax_rsi_crossback"}
                    },
                    {
                      "caseId": "USDJPY-EARLY-001",
                      "status": "QUEUED_FOR_GA",
                      "proposedAction": {"mutationHint": "let_profit_run"}
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )
            first = run_generation(runtime_dir, write=True, force=True)
            self.assertTrue(any(row["source"] == "CASE_MEMORY" for row in first["candidates"]))
            self.assertGreater(first["generation"]["caseMemorySeedCount"], 0)
            self.assertEqual(first["generation"]["cache"]["hits"], 0)
            self.assertIn("lineage", first)
            self.assertTrue(any(edge["type"] == "CASE_MEMORY" for edge in first["lineage"]["edges"]))

            second = run_generation(runtime_dir, write=True, force=True)
            self.assertTrue(any(row.get("cacheHit") for row in second["candidates"]), second["candidates"])
            self.assertGreaterEqual(second["generation"]["cache"]["hits"], 1)

    def test_generation_frequency_limiter_can_skip_without_losing_status(self):
        old = os.environ.get("QG_GA_MIN_RUN_INTERVAL_SECONDS")
        os.environ["QG_GA_MIN_RUN_INTERVAL_SECONDS"] = "3600"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runtime_dir = Path(tmp)
                first = run_generation(runtime_dir, write=True, force=True)
                self.assertTrue(first["ok"])
                skipped = run_generation(runtime_dir, write=True, force=False)
                self.assertFalse(skipped["ok"])
                self.assertTrue(skipped["skipped"])
                self.assertFalse(skipped["runLimiter"]["allowed"])
        finally:
            if old is None:
                os.environ.pop("QG_GA_MIN_RUN_INTERVAL_SECONDS", None)
            else:
                os.environ["QG_GA_MIN_RUN_INTERVAL_SECONDS"] = old

    def test_generation_rejects_only_dangerous_seed_fields_not_safe_field_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_generation(Path(tmp), write=False)
            self.assertNotIn("SAFETY_REJECTED", {row["blockerCode"] for row in result["candidates"]})

    def test_telegram_text_is_chinese_push_only_and_no_execution_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_generation(Path(tmp), write=True)
            text = ga_to_chinese_text(result)
            self.assertIn("GA 进化报告", text)
            self.assertIn("安全边界", text)
            self.assertIn("不直接实盘", text)
            self.assertNotIn("OrderSend", text)


if __name__ == "__main__":
    unittest.main()
