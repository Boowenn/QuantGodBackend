from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.case_memory.report import build_case_memory_report
from tools.run_case_memory import write_sample_runtime
from tools.strategy_ga.seed_generator import case_memory_seed_pool
from tools.strategy_structure_lab.report import build_report as build_strategy_structure_report


class CaseMemoryCandidateTests(unittest.TestCase):
    def test_builds_shadow_strategy_json_candidates_from_case_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            write_sample_runtime(runtime, overwrite=True)

            report = build_case_memory_report(runtime, write=True)

            self.assertEqual(report["status"], "READY")
            self.assertGreaterEqual(report["candidateCount"], 1)
            self.assertGreaterEqual(report["gaSeedCount"], 1)
            candidate = report["candidates"][0]
            self.assertEqual(candidate["status"], "SHADOW_STRATEGY_JSON_CANDIDATE")
            self.assertTrue(candidate["validation"]["valid"])
            self.assertEqual(candidate["strategyJson"]["lane"], "MT5_SHADOW")
            self.assertFalse(candidate["safety"]["orderSendAllowed"])
            self.assertTrue((runtime / "case_memory" / "QuantGod_CaseMemoryStrategyCandidates.json").exists())
            self.assertTrue(
                (runtime / "case_memory" / "QuantGod_CaseMemoryStrategyCandidateLedger.jsonl").exists()
            )

    def test_case_memory_preserves_non_rsi_strategy_family_for_ga_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            evidence_dir = runtime / "evidence_os"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "QuantGod_CaseMemorySummary.json").write_text(
                json.dumps(
                    {
                        "schema": "quantgod.case_memory_summary.v1",
                        "gaSeedHints": [
                            {
                                "caseId": "USDJPY-BB-SHADOW-001",
                                "caseType": "STRATEGY_CONTRACT_SHADOW_SIGNAL",
                                "status": "QUEUED_FOR_GA",
                                "strategyFamily": "BB_Triple",
                                "direction": "LONG",
                                "mutationHint": "promote_contract_candidate_to_tester",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            seeds = case_memory_seed_pool(runtime)

            self.assertEqual(len(seeds), 1)
            self.assertEqual(seeds[0]["strategyFamily"], "BB_Triple")
            self.assertIn("BB_TRIPLE", seeds[0]["strategyId"])

    def test_case_memory_skips_governance_only_live_lane_hints_for_ga_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            evidence_dir = runtime / "evidence_os"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "QuantGod_CaseMemorySummary.json").write_text(
                json.dumps(
                    {
                        "schema": "quantgod.case_memory_summary.v1",
                        "gaSeedHints": [
                            {
                                "caseId": "USDJPY-POLICY-MISMATCH-001",
                                "caseType": "POLICY_MISMATCH",
                                "status": "QUEUED_FOR_GA",
                                "mutationHint": "verify_live_lane_strategy_lock",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            self.assertEqual(case_memory_seed_pool(runtime), [])

    def test_parity_fail_blocks_candidate_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            write_sample_runtime(runtime, overwrite=True)
            parity_path = runtime / "parity" / "QuantGod_StrategyParityReport.json"
            parity_path.write_text(
                json.dumps(
                    {
                        "status": "PARITY_FAIL",
                        "promotionGate": {"status": "BLOCKED", "promotionAllowed": False},
                        "reasonZh": "Strategy JSON 与 EA 不一致。",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = build_case_memory_report(runtime, write=True)

            self.assertFalse(report["ok"])
            self.assertEqual(report["status"], "BLOCKED_BY_PARITY")
            self.assertEqual(report["candidateCount"], 0)
            self.assertTrue(report["parityGate"]["blocked"])

    def test_strategy_structure_lab_wraps_existing_case_memory_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            write_sample_runtime(runtime, overwrite=True)

            report = build_strategy_structure_report(runtime, write=True)

            self.assertTrue(report["strategyStructureProduction"])
            self.assertEqual(report["p4Stage"], "P4-7")
            self.assertGreaterEqual(report["candidateCount"], 1)
            self.assertTrue(report["safety"]["strategyStructureProductionOnly"])
            self.assertFalse(report["safety"]["orderSendAllowed"])
            self.assertFalse(report["safety"]["livePresetMutationAllowed"])


if __name__ == "__main__":
    unittest.main()
