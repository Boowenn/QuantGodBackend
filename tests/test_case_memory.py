from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.case_memory.report import build_case_memory_report
from tools.run_case_memory import write_sample_runtime


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


if __name__ == "__main__":
    unittest.main()
