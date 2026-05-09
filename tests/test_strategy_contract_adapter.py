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
)


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


if __name__ == "__main__":
    unittest.main()

