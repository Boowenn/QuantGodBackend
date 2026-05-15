from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.production_evidence_validation.burn_in import build_burn_in_report
from tools.production_evidence_validation.source_attribution import (
    build_source_attribution,
    classify_source_tier,
)


class ProductionBurnInTests(unittest.TestCase):
    def test_source_attribution_separates_real_close_history_and_shadow(self) -> None:
        rows = [
            {
                "executionMode": "LIVE",
                "eventType": "LIVE_EXIT",
                "dealTicket": "123",
                "fillPrice": 155.2,
                "source": "QuantGod_LiveExecutionFeedback.jsonl",
            },
            {"sourceKind": "close_history", "source": "QuantGod_CloseHistory.csv"},
            {
                "eventType": "ORDER_FILL",
                "source": "QuantGod_LiveExecutionFeedback.jsonl",
                "strategyId": "RSI_Reversal",
                "fillPrice": 157.144,
            },
            {"sourceKind": "shadow_outcome", "source": "QuantGod_ShadowOutcomeLedger.csv"},
            {"source": "QuantGod_USDJPYEADryRunDecisionLedger.csv"},
            {"source": "QuantGod_LiveExecutionFeedbackHistory.jsonl"},
        ]
        tiers = [classify_source_tier(row) for row in rows]
        self.assertEqual(tiers[0], "live_real_fill")
        self.assertEqual(tiers[1], "mt5_close_history")
        self.assertEqual(tiers[2], "live_real_fill")
        self.assertEqual(tiers[3], "strategy_shadow")
        self.assertEqual(tiers[4], "ea_shadow")
        self.assertEqual(tiers[5], "backfilled_history")
        attribution = build_source_attribution(rows)
        self.assertEqual(attribution["liveRealFillCount"], 2)
        self.assertEqual(attribution["shadowSampleCount"], 2)

    def test_burn_in_report_writes_report_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            execution_dir = runtime / "execution"
            execution_dir.mkdir(parents=True)
            row = {
                "strategyId": "USDJPY_RSI_REVERSAL_LONG_V1",
                "eventType": "LIVE_EXIT",
                "executionMode": "LIVE",
                "dealTicket": "12345",
                "expectedPrice": 155.1,
                "fillPrice": 155.12,
                "slippagePips": 0.2,
                "latencyMs": 120,
                "spreadAtEntry": 0.8,
                "profitR": 0.3,
                "mfeR": 0.5,
                "maeR": -0.1,
                "source": "QuantGod_LiveExecutionFeedback.jsonl",
            }
            with (execution_dir / "QuantGod_LiveExecutionFeedback.jsonl").open("w", encoding="utf-8") as handle:
                for _ in range(20):
                    handle.write(json.dumps(row) + "\n")

            report = build_burn_in_report(runtime, write=True, window_hours=1, sample_interval_minutes=5)

            self.assertEqual(report["schema"], "quantgod.production_burn_in_report.v1")
            self.assertTrue((runtime / "production_validation" / "QuantGod_ProductionBurnInReport.json").exists())
            self.assertTrue((runtime / "production_validation" / "QuantGod_ProductionBurnInLedger.csv").exists())
            attribution = report["sections"]["executionFeedback"]["sourceAttribution"]
            self.assertEqual(attribution["liveRealFillCount"], 20)


if __name__ == "__main__":
    unittest.main()
