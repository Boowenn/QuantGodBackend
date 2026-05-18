from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.production_evidence_validation.execution_feedback_audit import audit_execution_feedback


class ExecutionFeedbackSamplingCoverageTests(unittest.TestCase):
    def test_no_samples_warns_without_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_execution_feedback(Path(tmp))
            self.assertEqual(report["status"], "WARN")
            self.assertEqual(report["coverageGrade"], "NO_SAMPLES")
            self.assertEqual(report["evidenceUsability"], "NOT_USABLE")

    def test_complete_samples_report_production_usable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            execution_dir = runtime / "execution"
            execution_dir.mkdir(parents=True)
            rows = []
            for index in range(20):
                rows.append(
                    {
                        "strategyId": "USDJPY_RSI_REVERSAL_LONG_V1",
                        "eventType": "EXIT",
                        "executionMode": "LIVE" if index % 2 == 0 else "SHADOW",
                        "expectedPrice": 155.1,
                        "fillPrice": 155.11,
                        "slippagePips": 0.1,
                        "latencyMs": 200 + index,
                        "spreadAtEntry": 0.8,
                        "profitR": 0.2,
                        "mfeR": 0.5,
                        "maeR": -0.2,
                    }
                )
            with (execution_dir / "QuantGod_LiveExecutionFeedback.jsonl").open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row) + "\n")
            report = audit_execution_feedback(runtime)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["coverageGrade"], "PRODUCTION_READY")
            self.assertEqual(report["evidenceUsability"], "PRODUCTION_USABLE")
            self.assertEqual(report["sampleCount"], 20)
            self.assertEqual(report["fieldCoverage"], 1.0)
            self.assertIn("USDJPY_RSI_REVERSAL_LONG_V1", report["strategyCoverage"])

    def test_missing_core_fields_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            execution_dir = runtime / "execution"
            execution_dir.mkdir(parents=True)
            with (execution_dir / "QuantGod_LiveExecutionFeedback.jsonl").open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({"strategyId": "USDJPY_RSI_REVERSAL_LONG_V1", "eventType": "ENTRY"}) + "\n")
            report = audit_execution_feedback(runtime)
            self.assertEqual(report["status"], "WARN")
            self.assertIn(report["coverageGrade"], {"CORE_FIELD_GAPS", "FIELD_GAPS"})
            self.assertGreater(report["missingFieldCounts"].get("profitR", 0), 0)

    def test_advisory_sources_get_event_and_source_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            execution_dir = runtime / "execution"
            execution_dir.mkdir(parents=True)
            rows = []
            for index in range(10):
                rows.append(
                    {
                        "source": "QuantGod_USDJPYLiveLoopLedger.csv",
                        "strategyId": "RSI_Reversal",
                        "expectedPrice": 155.1,
                        "fillPrice": 155.1,
                        "slippagePips": 0.0,
                        "latencyMs": 0,
                        "spreadAtEntry": 0.0,
                        "profitR": 0.0,
                        "mfeR": 0.0,
                        "maeR": 0.0,
                    }
                )
                rows.append(
                    {
                        "source": "QuantGod_USDJPYEADryRunDecisionLedger.csv",
                        "strategyId": "RSI_Reversal",
                        "expectedPrice": 155.1,
                        "fillPrice": 155.1,
                        "slippagePips": 0.0,
                        "latencyMs": 0,
                        "spreadAtEntry": 0.0,
                        "profitR": 0.0,
                        "mfeR": 0.0,
                        "maeR": 0.0,
                    }
                )
            with (execution_dir / "QuantGod_LiveExecutionFeedback.jsonl").open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row) + "\n")

            report = audit_execution_feedback(runtime)

            self.assertEqual(report["missingFieldCounts"].get("eventType"), 0)
            self.assertEqual(report["sourceAttribution"]["tierCounts"].get("ea_shadow"), 20)
            self.assertEqual(report["sourceAttribution"]["sourceKindCounts"].get("unknown"), None)


if __name__ == "__main__":
    unittest.main()
