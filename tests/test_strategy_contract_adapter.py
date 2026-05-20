from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.strategy_contract_adapter.builder import (
    build_rsi_opportunity_layer_audit,
    build_rsi_shadow_contract_observation,
    build_strategy_contract,
    read_strategy_contract_status,
)
from tools.strategy_contract_adapter.schema import (
    CONTRACT_EA_FILE,
    CONTRACT_JSON_FILE,
    EA_STATUS_FILE,
    EA_SHADOW_EVALUATION_LEDGER_FILE,
    EA_SHADOW_EVALUATION_STATUS_FILE,
    FROZEN_RSI_LINEAGE_FILE,
    RSI_OPPORTUNITY_LAYER_AUDIT_REPORT_FILE,
    RSI_SHADOW_OBSERVATION_REPORT_FILE,
)
from tools.strategy_ga.fitness import score_seed
from tools.strategy_ga.schema import CANDIDATE_RUNS_FILE, ga_dir
from tools.strategy_ga.seed_generator import case_memory_seed_pool
from tools.strategy_json.schema import base_strategy_seed
from tools.usdjpy_evidence_os.case_memory import build_case_memory


class StrategyContractAdapterTests(unittest.TestCase):
    def _write_frozen_rsi_lineage(self, runtime: Path, seed_id: str = "GA-USDJPY-FROZEN-RSI") -> dict:
        seed = base_strategy_seed(seed_id)
        seed["qualityProfile"] = "RSI_REVERSAL_GUARDED_SAMPLE_RECOVERY"
        seed["indicators"]["rsi"]["adverseExcursionGuard"] = {
            "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
            "maxEarlyAdverseR": 0.96,
            "maxEntryRangePips": 64,
            "confirmationBars": 3,
            "lookaheadBars": 3,
            "minConfirmR": 0.03,
            "rangeLookbackBars": 5,
        }
        frozen = {
            "schema": "quantgod.rsi_frozen_elite_lineage.v1",
            "frozenAt": "2026-05-19T00:00:00Z",
            "selectedSeedId": seed_id,
            "selectedGeneration": 79,
            "selectedFingerprint": "fp-frozen-rsi",
            "selectedProfile": seed["qualityProfile"],
            "strategyJson": seed,
            "criteria": {
                "allPass": True,
                "fitness": 3.48,
                "rank": 1,
                "sampleCount": 30,
                "tradeCount": 23,
                "netR": 3.69,
                "validationNetR": 1.56,
                "forwardNetR": 2.05,
                "maxAdverseR": -0.96,
                "walkForwardStatus": "PASS",
            },
            "productionEvidenceAlignment": {"allPass": True},
            "replayAlignment": {"allPass": True},
            "lineagePath": {"lineageDepth": 11},
        }
        path = ga_dir(runtime) / FROZEN_RSI_LINEAGE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(frozen, ensure_ascii=False), encoding="utf-8")
        return frozen

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
            self.assertIn("familyParameters=", ea_text)
            self.assertIn("maFastPeriod=", ea_text)
            self.assertIn("bbDeviations=", ea_text)
            self.assertIn("macdFastPeriod=", ea_text)
            self.assertIn("srLookbackBars=", ea_text)
            self.assertIn("tokyoTradeStartHourUtc=", ea_text)
            self.assertIn("nightBollingerPeriod=", ea_text)
            self.assertIn("h4FastEmaPeriod=", ea_text)

    def test_contract_preserves_family_specific_parameters_for_ea_shadow_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            seed = base_strategy_seed("GA-USDJPY-FAMILY-PARAMS", family="USDJPY_TOKYO_RANGE_BREAKOUT")
            indicators = seed["indicators"]
            indicators["ma"]["fastPeriod"] = 13
            indicators["ma"]["slowPeriod"] = 34
            indicators["bollinger"]["period"] = 24
            indicators["bollinger"]["deviations"] = 2.35
            indicators["macd"]["fastPeriod"] = 8
            indicators["macd"]["slowPeriod"] = 21
            indicators["macd"]["signalPeriod"] = 5
            indicators["supportResistance"]["lookbackBars"] = 48
            indicators["tokyoRange"]["tradeStartHourUtc"] = 4
            indicators["tokyoRange"]["bufferPips"] = 1.5
            indicators["nightReversion"]["bollingerPeriod"] = 28
            indicators["nightReversion"]["entryBufferPips"] = 0.75
            indicators["h4Pullback"]["fastEmaPeriod"] = 30
            indicators["h4Pullback"]["slowEmaPeriod"] = 80

            ga_path = ga_dir(runtime) / CANDIDATE_RUNS_FILE
            ga_path.parent.mkdir(parents=True, exist_ok=True)
            ga_path.write_text(
                json.dumps(
                    {
                        "seedId": seed["seedId"],
                        "status": "PROMOTED_TO_SHADOW",
                        "promotionStage": "FAST_SHADOW",
                        "fitness": 9.0,
                        "strategyJson": seed,
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            payload = build_strategy_contract(runtime, write=True)
            family_parameters = payload["contract"]["strategy"]["familyParameters"]
            ea_text = (runtime / CONTRACT_EA_FILE).read_text(encoding="utf-8")

            self.assertEqual(family_parameters["ma"]["fastPeriod"], 13)
            self.assertEqual(family_parameters["tokyoRange"]["tradeStartHourUtc"], 4)
            self.assertEqual(family_parameters["h4Pullback"]["slowEmaPeriod"], 80)
            self.assertIn("maFastPeriod=13", ea_text)
            self.assertIn("maSlowPeriod=34", ea_text)
            self.assertIn("bbPeriod=24", ea_text)
            self.assertIn("bbDeviations=2.35", ea_text)
            self.assertIn("macdFastPeriod=8", ea_text)
            self.assertIn("macdSlowPeriod=21", ea_text)
            self.assertIn("macdSignalPeriod=5", ea_text)
            self.assertIn("srLookbackBars=48", ea_text)
            self.assertIn("tokyoTradeStartHourUtc=4", ea_text)
            self.assertIn("tokyoBufferPips=1.5", ea_text)
            self.assertIn("nightBollingerPeriod=28", ea_text)
            self.assertIn("nightEntryBufferPips=0.75", ea_text)
            self.assertIn("h4FastEmaPeriod=30", ea_text)
            self.assertIn("h4SlowEmaPeriod=80", ea_text)

    def test_build_can_force_valid_family_for_shadow_contract_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            sr_seed = base_strategy_seed("GA-USDJPY-SR-TOP", family="SR_Breakout")
            ma_seed = base_strategy_seed("GA-USDJPY-MA-ROTATE", family="MA_Cross")
            ga_path = ga_dir(runtime) / CANDIDATE_RUNS_FILE
            ga_path.parent.mkdir(parents=True, exist_ok=True)
            rows = [
                {
                    "seedId": sr_seed["seedId"],
                    "status": "ELITE_SELECTED",
                    "promotionStage": "TESTER_ONLY",
                    "fitness": 10.0,
                    "strategyJson": sr_seed,
                },
                {
                    "seedId": ma_seed["seedId"],
                    "status": "NEEDS_MORE_DATA",
                    "promotionStage": "SHADOW",
                    "fitness": 0.1,
                    "strategyJson": ma_seed,
                },
            ]
            ga_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            payload = build_strategy_contract(runtime, write=True, forced_family="MA_Cross")
            contract = payload["contract"]

            self.assertTrue(payload["ok"])
            self.assertEqual(contract["selectionSource"], "GA_CANDIDATE_FORCED_FAMILY")
            self.assertEqual(contract["forcedFamily"], "MA_Cross")
            self.assertEqual(contract["strategy"]["strategyFamily"], "MA_Cross")
            self.assertEqual(contract["selectedSeedId"], "GA-USDJPY-MA-ROTATE")
            self.assertEqual(contract["contractMode"], "SHADOW_EVALUATION_ONLY")
            self.assertFalse(contract["safety"]["orderSendAllowed"])
            self.assertFalse(contract["safety"]["livePresetMutationAllowed"])

    def test_build_can_force_valid_seed_for_shadow_contract_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            sr_seed = base_strategy_seed("GA-USDJPY-SR-TOP", family="SR_Breakout")
            bb_seed = base_strategy_seed("GA-USDJPY-BB-ROTATE", family="BB_Triple")
            ga_path = ga_dir(runtime) / CANDIDATE_RUNS_FILE
            ga_path.parent.mkdir(parents=True, exist_ok=True)
            rows = [
                {
                    "seedId": sr_seed["seedId"],
                    "status": "ELITE_SELECTED",
                    "promotionStage": "TESTER_ONLY",
                    "fitness": 10.0,
                    "strategyJson": sr_seed,
                },
                {
                    "seedId": bb_seed["seedId"],
                    "status": "NEEDS_MORE_DATA",
                    "promotionStage": "SHADOW",
                    "fitness": 0.1,
                    "strategyJson": bb_seed,
                },
            ]
            ga_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            payload = build_strategy_contract(runtime, write=True, forced_seed_id="GA-USDJPY-BB-ROTATE")
            contract = payload["contract"]

            self.assertEqual(contract["selectionSource"], "GA_CANDIDATE_FORCED_SEED")
            self.assertEqual(contract["forcedSeedId"], "GA-USDJPY-BB-ROTATE")
            self.assertEqual(contract["strategy"]["strategyFamily"], "BB_Triple")
            self.assertEqual(contract["selectedSeedId"], "GA-USDJPY-BB-ROTATE")
            self.assertFalse(contract["safety"]["gaDirectLiveAllowed"])

    def test_build_can_force_frozen_rsi_lineage_for_shadow_contract_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            self._write_frozen_rsi_lineage(runtime)

            payload = build_strategy_contract(runtime, write=True, force_frozen_rsi=True)
            contract = payload["contract"]
            ea_text = (runtime / CONTRACT_EA_FILE).read_text(encoding="utf-8")

            self.assertEqual(contract["selectionSource"], "P4_10J_FROZEN_RSI_SEED")
            self.assertTrue(contract["forceFrozenRsi"])
            self.assertEqual(contract["selectedSeedId"], "GA-USDJPY-FROZEN-RSI")
            self.assertEqual(contract["strategy"]["qualityProfile"], "RSI_REVERSAL_GUARDED_SAMPLE_RECOVERY")
            self.assertEqual(contract["strategy"]["rsi"]["adverseExcursionGuard"]["maxEntryRangePips"], 64)
            self.assertIn("qualityProfile=RSI_REVERSAL_GUARDED_SAMPLE_RECOVERY", ea_text)
            self.assertIn("rsiAdverseGuardMode=P4_10G_RSI_ADVERSE_EXCURSION", ea_text)
            self.assertIn("rsiAdverseGuardMaxEntryRangePips=64", ea_text)
            self.assertFalse(contract["safety"]["orderSendAllowed"])

    def test_forced_rotation_rejects_missing_family_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            with self.assertRaises(ValueError):
                build_strategy_contract(runtime, write=True, forced_family="MA_Cross")

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

    def test_rsi_shadow_contract_observation_reads_frozen_seed_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            self._write_frozen_rsi_lineage(runtime)
            build_strategy_contract(runtime, write=True, force_frozen_rsi=True)
            row = {
                "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                "evaluationId": "eval-frozen-rsi",
                "status": "SHADOW_WOULD_ENTER",
                "blocker": "NONE",
                "selectedSeedId": "GA-USDJPY-FROZEN-RSI",
                "fingerprint": "fp-frozen-rsi",
                "strategyFamily": "RSI_Reversal",
                "direction": "LONG",
                "wouldEnter": True,
                "hardGuardsPass": True,
                "indicatorReady": True,
                "rsiLongSignal": True,
                "maeR": -0.42,
                "rsiAdverseGuard": {
                    "loaded": True,
                    "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
                    "rangePass": True,
                },
            }
            (runtime / EA_SHADOW_EVALUATION_LEDGER_FILE).write_text(
                json.dumps(row, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            report = build_rsi_shadow_contract_observation(runtime, write=True)

            self.assertEqual(report["status"], "PASS")
            self.assertTrue(report["contractRotation"]["matchesFrozenSeed"])
            self.assertEqual(report["entryQuality"]["status"], "PASS")
            self.assertEqual(report["adverseExcursion"]["status"], "PASS")
            self.assertEqual(report["adverseExcursion"]["worstObservedAdverseR"], -0.42)
            self.assertTrue((runtime / "strategy_contract" / RSI_SHADOW_OBSERVATION_REPORT_FILE).exists())

    def test_rsi_shadow_observation_uses_contract_snapshot_when_lineage_file_rolls_forward(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            self._write_frozen_rsi_lineage(runtime, seed_id="GA-USDJPY-G0077-C0002")
            build_strategy_contract(runtime, write=True, force_frozen_rsi=True)
            self._write_frozen_rsi_lineage(runtime, seed_id="GA-USDJPY-G0107-C0002")
            frozen_path = ga_dir(runtime) / FROZEN_RSI_LINEAGE_FILE
            drifted = json.loads(frozen_path.read_text(encoding="utf-8"))
            drifted["selectedFingerprint"] = "fp-next-rsi"
            frozen_path.write_text(json.dumps(drifted, ensure_ascii=False), encoding="utf-8")
            row = {
                "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                "evaluationId": "eval-g0077-after-lineage-roll",
                "status": "SHADOW_GUARD_BLOCKED",
                "blocker": "SPREAD_BLOCK",
                "selectedSeedId": "GA-USDJPY-G0077-C0002",
                "fingerprint": "fp-frozen-rsi",
                "strategyFamily": "RSI_Reversal",
                "direction": "LONG",
                "wouldEnter": False,
                "hardGuardsPass": False,
                "indicatorReady": True,
                "rsiLongSignal": False,
                "rsiAdverseGuard": {
                    "loaded": True,
                    "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
                    "rangePass": True,
                },
            }
            (runtime / EA_SHADOW_EVALUATION_LEDGER_FILE).write_text(
                json.dumps(row, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            report = build_rsi_shadow_contract_observation(runtime, write=True)

            self.assertEqual(report["status"], "WATCH")
            self.assertEqual(report["lineageSource"], "EA_CONTRACT_FROZEN_RSI_SNAPSHOT")
            self.assertEqual(report["frozenSeedId"], "GA-USDJPY-G0077-C0002")
            self.assertTrue(report["lineageFile"]["driftedFromActiveContract"])
            self.assertEqual(report["lineageFile"]["selectedSeedId"], "GA-USDJPY-G0107-C0002")
            self.assertTrue(report["contractRotation"]["matchesFrozenSeed"])
            self.assertGreaterEqual(report["shadowEvaluation"]["matchingRowCount"], 1)
            self.assertEqual(report["shadowEvaluation"]["latest"]["selectedSeedId"], "GA-USDJPY-G0077-C0002")
            self.assertNotIn(
                "FROZEN_RSI_CONTRACT_NOT_ROTATED",
                {blocker.get("code") for blocker in report["blockers"]},
            )

    def test_rsi_opportunity_layer_audit_separates_live_spread_block_from_no_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            self._write_frozen_rsi_lineage(runtime, seed_id="GA-USDJPY-G0077-C0002")
            build_strategy_contract(runtime, write=True, force_frozen_rsi=True)
            rows = [
                {
                    "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                    "evaluationId": "eval-g0077-research-observable-no-rsi",
                    "generatedAtLocal": "2026-05-20T00:00:00Z",
                    "status": "SHADOW_GUARD_BLOCKED",
                    "blocker": "SPREAD_BLOCK",
                    "selectedSeedId": "GA-USDJPY-G0077-C0002",
                    "fingerprint": "fp-frozen-rsi",
                    "strategyFamily": "RSI_Reversal",
                    "direction": "LONG",
                    "wouldEnter": False,
                    "hardGuardsPass": False,
                    "indicatorReady": True,
                    "rsiLongSignal": False,
                    "spreadPips": 2.6,
                    "liveSpreadAllowed": False,
                    "shadowResearchSpreadAllowed": True,
                    "rsiClosed1": 41.2,
                    "rsiBuyBand": 34.0,
                    "rsiAdverseGuard": {
                        "loaded": True,
                        "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
                        "entryRangePips": 36.0,
                        "rangePass": True,
                    },
                },
                {
                    "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                    "evaluationId": "eval-g0077-research-observable-rsi-live-blocked",
                    "generatedAtLocal": "2026-05-20T00:05:00Z",
                    "status": "SHADOW_GUARD_BLOCKED",
                    "blocker": "SPREAD_BLOCK",
                    "selectedSeedId": "GA-USDJPY-G0077-C0002",
                    "fingerprint": "fp-frozen-rsi",
                    "strategyFamily": "RSI_Reversal",
                    "direction": "LONG",
                    "wouldEnter": False,
                    "hardGuardsPass": False,
                    "indicatorReady": True,
                    "rsiLongSignal": True,
                    "spreadPips": 2.4,
                    "liveSpreadAllowed": False,
                    "shadowResearchSpreadAllowed": True,
                    "rsiClosed1": 32.1,
                    "rsiBuyBand": 34.0,
                    "rsiAdverseGuard": {
                        "loaded": True,
                        "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
                        "entryRangePips": 34.0,
                        "rangePass": True,
                    },
                },
            ]
            (runtime / EA_SHADOW_EVALUATION_LEDGER_FILE).write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            (runtime / EA_SHADOW_EVALUATION_STATUS_FILE).write_text(
                json.dumps(rows[-1], ensure_ascii=False),
                encoding="utf-8",
            )

            report = build_rsi_opportunity_layer_audit(runtime, write=True)

            classification = report["classification"]
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["phase"], "P4_10K_RSI_SHADOW_ONLY_OPPORTUNITY_LAYER_AUDIT")
            self.assertEqual(classification["researchObservableLiveBlockedCount"], 2)
            self.assertEqual(classification["researchObservableLiveBlockedWithRsiSignalCount"], 1)
            self.assertEqual(classification["trueNoRsiOpportunityCount"], 1)
            self.assertEqual(
                classification["decision"]["label"],
                "RESEARCH_SPREAD_PASS_LIVE_SPREAD_BLOCKED_RSI_SIGNAL",
            )
            self.assertTrue((runtime / "strategy_contract" / RSI_OPPORTUNITY_LAYER_AUDIT_REPORT_FILE).exists())

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
            self.assertTrue(any(case.get("strategy") == "RSI_Reversal" for case in cases["cases"]))
            self.assertGreaterEqual(cases["caseMemoryToGA"]["queuedHintCount"], 1)
            self.assertTrue(any(seed.get("mutationHint") == "promote_contract_candidate_to_tester" for seed in seeds))

    def test_generic_shadow_evaluation_feeds_case_memory_summary_and_ga_fitness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            rows = [
                {
                    "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                    "evaluationId": "eval-ma-observe",
                    "status": "SHADOW_OBSERVE",
                    "blocker": "NONE",
                    "selectedSeedId": "GA-USDJPY-MA-OBSERVE",
                    "fingerprint": "fp-ma-observe",
                    "strategyId": "USDJPY_MA_CROSS_LONG_SHADOW",
                    "strategyFamily": "MA_Cross",
                    "direction": "LONG",
                    "lane": "MT5_SHADOW",
                    "contractFamilyImplemented": True,
                    "wouldEnter": False,
                    "hardGuardsPass": True,
                    "reasonZh": "MA shadow adapter observed the contract.",
                },
                {
                    "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                    "evaluationId": "eval-ma-would-enter",
                    "status": "SHADOW_WOULD_ENTER",
                    "blocker": "NONE",
                    "selectedSeedId": "GA-USDJPY-MA-SIGNAL",
                    "fingerprint": "fp-ma-signal",
                    "strategyId": "USDJPY_MA_CROSS_LONG_SIGNAL",
                    "strategyFamily": "MA_Cross",
                    "direction": "LONG",
                    "lane": "MT5_SHADOW",
                    "contractFamilyImplemented": True,
                    "wouldEnter": True,
                    "hardGuardsPass": True,
                    "reasonZh": "MA shadow adapter saw a would-enter signal.",
                },
            ]
            (runtime / EA_SHADOW_EVALUATION_LEDGER_FILE).write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            cases = build_case_memory(runtime, write=True)
            shadow = cases["strategyContractShadowEvaluation"]
            ma_summary = shadow["genericAdapterSummary"]["MA_Cross"]

            self.assertIn("MA_Cross", shadow["genericAdapterStableFamilies"])
            self.assertEqual(ma_summary["shadowObserveCount"], 2)
            self.assertEqual(ma_summary["shadowWouldEnterCount"], 1)
            self.assertIn("STRATEGY_CONTRACT_SHADOW_SIGNAL", cases["caseTypeCounts"])
            self.assertTrue(any(case.get("strategy") == "MA_Cross" for case in cases["cases"]))

            score = score_seed(base_strategy_seed("GA-USDJPY-MA-SCORE", family="MA_Cross"), runtime)
            self.assertTrue(score["strategyContractShadow"]["adapterStable"])
            self.assertEqual(score["strategyContractShadow"]["strategyFamily"], "MA_Cross")
            self.assertGreater(score["strategyContractShadowBonus"], 0.0)

    def test_case_memory_uses_latest_shadow_evaluation_for_same_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            old_gap = {
                "schema": "quantgod.strategy_json_ea_shadow_evaluation.v1",
                "evaluationId": "eval-old-gap",
                "selectedSeedId": "GA-USDJPY-TOKYO",
                "fingerprint": "fp-tokyo",
                "strategyId": "USDJPY_TOKYO_RANGE_BREAKOUT_SHORT",
                "strategyFamily": "USDJPY_TOKYO_RANGE_BREAKOUT",
                "direction": "SHORT",
                "status": "UNSUPPORTED_STRATEGY_FAMILY_SHADOW_OBSERVE",
                "blocker": "EA_CONTRACT_FAMILY_NOT_IMPLEMENTED",
                "reasonZh": "old adapter gap",
            }
            latest_waiting = {
                **old_gap,
                "evaluationId": "eval-latest-wait",
                "status": "SHADOW_WAIT_INDICATORS",
                "blocker": "TOKYO_RANGE_WAIT_WINDOW",
                "reasonZh": "Tokyo adapter now evaluates the contract.",
            }
            (runtime / EA_SHADOW_EVALUATION_LEDGER_FILE).write_text(
                json.dumps(old_gap, ensure_ascii=False) + "\n" + json.dumps(latest_waiting, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            cases = build_case_memory(runtime, write=True)

            self.assertNotIn("STRATEGY_CONTRACT_EA_ADAPTER_GAP", cases["caseTypeCounts"])


if __name__ == "__main__":
    unittest.main()
