"""Regression tests for Strategy JSON GA Factory archive creation."""

import tempfile
import unittest
from pathlib import Path

from tools.run_strategy_ga_factory import write_sample_runtime
from tools.strategy_ga_factory.factory_runner import (
    build_factory_state,
    read_factory_state,
)


class StrategyGAFactoryTests(unittest.TestCase):
    def test_factory_archives_ga_outputs_without_live_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            sample = write_sample_runtime(runtime_dir, overwrite=True)
            self.assertTrue(sample["ok"])

            state = build_factory_state(runtime_dir, write=True)
            self.assertEqual(state["schema"], "quantgod.strategy_ga_factory.state.v1")
            self.assertEqual(state["status"], "FACTORY_READY")
            self.assertGreater(state["candidateCount"], 0)
            self.assertIn(state["nextGeneration"]["status"], {
                "READY_FOR_ELITE_GUIDED_NEXT_GENERATION",
                "NO_ELITE_EXPAND_SEARCH",
            })
            self.assertFalse(state["safety"]["orderSendAllowed"])
            self.assertFalse(state["safety"]["livePresetMutationAllowed"])
            self.assertFalse(state["safety"]["gaFactoryDirectLiveAllowed"])
            self.assertEqual(
                state["safety"]["allowedPromotionStages"],
                ["SHADOW", "FAST_SHADOW", "TESTER_ONLY", "PAPER_LIVE_SIM"],
            )

            factory_dir = runtime_dir / "ga_factory"
            for name in [
                "QuantGod_GAFactoryState.json",
                "QuantGod_GAEliteArchive.json",
                "QuantGod_GAStrategyGraveyard.json",
                "QuantGod_GALineageTree.json",
                "QuantGod_GAFactoryLedger.csv",
            ]:
                self.assertTrue((factory_dir / name).exists(), name)

            status = read_factory_state(runtime_dir)
            self.assertTrue(status["ok"])
            self.assertEqual(status["candidateCount"], state["candidateCount"])

    def test_empty_runtime_waits_for_ga_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = build_factory_state(Path(tmp), write=False)
            self.assertEqual(state["status"], "WAITING_GA_TRACE")
            self.assertEqual(state["candidateCount"], 0)
            self.assertEqual(state["nextGeneration"]["status"], "WAITING_GA_TRACE")


if __name__ == "__main__":
    unittest.main()
