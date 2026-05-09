from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.strategy_contract_adapter.builder import build_strategy_contract, read_strategy_contract_status
from tools.strategy_contract_adapter.schema import (
    CONTRACT_EA_FILE,
    CONTRACT_JSON_FILE,
    EA_STATUS_FILE,
    EA_SHADOW_EVALUATION_LEDGER_FILE,
    EA_SHADOW_EVALUATION_STATUS_FILE,
)
from tools.strategy_ga.seed_generator import case_memory_seed_pool
from tools.usdjpy_evidence_os.case_memory import build_case_memory


class StrategyContractAdapterTests(unittest.TestCase):
    def test_build_writes_shadow_only_contract_and_ea_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            payload = build_strategy_contract(runtime, write=True)

            self.assertTrue(payload["ok"])
            contract = payload["contract"]
            self.assertEqual(contract["contractMode"], "SHADOW_EVALUATION_ONLY")
            self.assertEqual(contract["focusSymbol"], "USDJPYc")
            self.assertFalse(contract["safety"]["orderSendAllowed"])
            self.assertFalse(contract["safety"]["livePresetMutationAllowed"])
            self.assertTrue((runtime / CONTRACT_JSON_FILE).exists())
            self.assertTrue((runtime / CONTRACT_EA_FILE).exists())
            ea_text = (runtime / CONTRACT_EA_FILE).read_text(encoding="utf-8")
            self.assertIn("orderSendAllowed=false", ea_text)
            self.assertIn("shadowOnly=true", ea_text)
            self.assertIn("strategyFamily=RSI_Reversal", ea_text)

    def test_status_reads_ea_ack_without_granting_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            build_strategy_contract(runtime, write=True)
            (runtime / EA_STATUS_FILE).write_text(
                json.dumps(
                    {
                        "status": "SHADOW_CONTRACT_READY",
                        "loaded": True,
                        "orderSendAllowed": False,
                        "livePresetMutationAllowed": False,
                        "reasonZh": "EA 已加载只读 Strategy JSON contract。",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            status = read_strategy_contract_status(runtime)
            self.assertEqual(status["eaStatus"]["status"], "SHADOW_CONTRACT_READY")
            self.assertFalse(status["safety"]["orderSendAllowed"])

    def test_status_reads_ea_shadow_evaluation_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            build_strategy_contract(runtime, write=True)
            evaluation = {
                "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                "evaluationId": "eval-1",
                "status": "SHADOW_WOULD_ENTER",
                "blocker": "NONE",
                "selectedSeedId": "GA-USDJPY-001",
                "fingerprint": "abc123",
                "strategyId": "USDJPY_RSI_REVERSAL_LONG_CASE",
                "strategyFamily": "RSI_Reversal",
                "direction": "LONG",
                "lane": "MT5_SHADOW",
                "wouldEnter": True,
                "hardGuardsPass": True,
                "reasonZh": "EA shadow saw a contract signal.",
            }
            (runtime / EA_SHADOW_EVALUATION_STATUS_FILE).write_text(
                json.dumps(evaluation, ensure_ascii=False),
                encoding="utf-8",
            )
            (runtime / EA_SHADOW_EVALUATION_LEDGER_FILE).write_text(
                json.dumps(evaluation, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            status = read_strategy_contract_status(runtime)

            self.assertEqual(status["eaShadowEvaluation"]["status"], "SHADOW_WOULD_ENTER")
            self.assertEqual(status["eaShadowEvaluationRecent"][-1]["evaluationId"], "eval-1")

    def test_ea_shadow_evaluation_feeds_case_memory_and_ga_seed_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            evaluation = {
                "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                "evaluationId": "eval-ga",
                "status": "SHADOW_WOULD_ENTER",
                "blocker": "NONE",
                "selectedSeedId": "GA-USDJPY-CASE",
                "fingerprint": "fp-case",
                "strategyId": "USDJPY_RSI_REVERSAL_LONG_CASE",
                "strategyFamily": "RSI_Reversal",
                "direction": "LONG",
                "lane": "MT5_SHADOW",
                "wouldEnter": True,
                "hardGuardsPass": True,
                "rsiClosed1": 32.5,
                "rsiClosed2": 29.5,
                "spreadPips": 0.4,
            }
            (runtime / EA_SHADOW_EVALUATION_LEDGER_FILE).write_text(
                json.dumps(evaluation, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            cases = build_case_memory(runtime, write=True)
            seeds = case_memory_seed_pool(runtime)

            self.assertIn("STRATEGY_CONTRACT_SHADOW_SIGNAL", cases["caseTypeCounts"])
            self.assertGreaterEqual(cases["caseMemoryToGA"]["queuedHintCount"], 1)
            self.assertTrue(any(seed.get("mutationHint") == "promote_contract_candidate_to_tester" for seed in seeds))


if __name__ == "__main__":
    unittest.main()
