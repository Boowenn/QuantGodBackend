from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.execution_feedback_producer import producer


class ExecutionFeedbackProducerTests(unittest.TestCase):
    def test_sample_generates_complete_shadow_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            producer.write_sample(runtime, overwrite=True)
            with patch.object(producer, "_source_dirs", return_value=[runtime]):
                report = producer.build_feedback(runtime, write=True)
            self.assertEqual(report["status"], "WARN")
            self.assertEqual(report["generatedCount"], 2)
            self.assertEqual(report["completeSampleCount"], 2)
            ledger = runtime / "execution" / "QuantGod_LiveExecutionFeedback.jsonl"
            self.assertTrue(ledger.exists())
            self.assertIn("USDJPY_RSI_REVERSAL_LONG_V1", ledger.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
