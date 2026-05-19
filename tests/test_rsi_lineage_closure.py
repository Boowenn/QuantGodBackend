from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.production_evidence_validation.rsi_lineage_closure import build_rsi_lineage_closure
from tools.production_evidence_validation.schema import RSI_FROZEN_ELITE_LINEAGE, RSI_LINEAGE_CLOSURE_REPORT


def _rsi_seed(seed_id: str, *, profile: str, parents: list[str] | None = None) -> dict:
    return {
        "seedId": seed_id,
        "strategyId": f"USDJPY_RSI_{seed_id}",
        "symbol": "USDJPYc",
        "lane": "MT5_SHADOW",
        "strategyFamily": "RSI_Reversal",
        "direction": "LONG",
        "qualityProfile": profile,
        "parentSeedIds": parents or [],
        "entry": {
            "mode": "OPPORTUNITY_ENTRY",
            "conditions": [
                "rsi.adverseExcursionGuard == P4_10G_RSI_ADVERSE_EXCURSION",
                "rsi.guardedSampleRecovery == true",
            ],
        },
        "indicators": {
            "rsi": {
                "period": 20,
                "timeframe": "H1",
                "buyBand": 31.0,
                "crossbackThreshold": 0.5,
                "adverseExcursionGuard": {
                    "mode": "P4_10G_RSI_ADVERSE_EXCURSION",
                    "maxEarlyAdverseR": 0.96,
                    "maxEntryRangePips": 64,
                    "confirmationBars": 3,
                },
            }
        },
        "exit": {"trailStartR": 0.8, "breakevenDelayR": 0.55, "mfeGivebackPct": 0.4},
        "risk": {"stage": "SHADOW", "maxLot": 2.0},
        "safety": {"orderSendAllowed": False, "livePresetMutationAllowed": False},
    }


def _candidate(seed_id: str, generation: int, rank: int, *, parents: list[str] | None = None) -> dict:
    profile = "RSI_REVERSAL_GUARDED_SAMPLE_RECOVERY"
    seed = _rsi_seed(seed_id, profile=profile, parents=parents)
    return {
        "schema": "quantgod.ga.candidate_run.v1",
        "generation": generation,
        "generationId": f"G{generation:04d}",
        "seedId": seed_id,
        "strategyId": seed["strategyId"],
        "strategyFamily": "RSI_Reversal",
        "direction": "LONG",
        "source": "CROSSOVER" if parents else "QUALITY_REPAIR",
        "fingerprint": "stable-guarded-rsi",
        "strategyJson": seed,
        "fitness": 3.5 - rank / 100,
        "rank": rank,
        "status": "ELITE_SELECTED",
        "promotionStage": "TESTER_ONLY",
        "blockerCode": None,
        "fitnessBreakdown": {
            "sampleCount": 30,
            "netR": 3.69,
            "maxAdverseR": -0.96,
            "strategyBacktest": {"present": True, "ok": True, "tradeCount": 23, "netR": 3.69},
            "walkForward": {
                "schema": "quantgod.usdjpy_seed_walk_forward.v1",
                "summary": {
                    "promotionGateStatus": "PASS",
                    "validationNetR": 1.56,
                    "forwardNetR": 2.05,
                    "stabilityScore": 0.91,
                },
                "segments": [
                    {"segment": "train", "netR": 4.9},
                    {"segment": "validation", "netR": 1.56},
                    {"segment": "forward", "netR": 2.05},
                ],
            },
        },
    }


class RSILineageClosureTests(unittest.TestCase):
    def test_closes_and_freezes_repeated_guarded_rsi_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            ga = runtime / "ga"
            replay = runtime / "replay" / "usdjpy"
            ga.mkdir(parents=True)
            replay.mkdir(parents=True)
            rows = [
                _candidate("g75-root", 75, 1),
                _candidate("g76-parent", 76, 1, parents=["g75-root"]),
                _candidate("g77-selected", 77, 1, parents=["g76-parent"]),
                _candidate("g77-selected", 78, 1, parents=["g76-parent"]),
                _candidate("g77-selected", 79, 1, parents=["g76-parent"]),
            ]
            (ga / "QuantGod_GACandidateRuns.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            (replay / "QuantGod_USDJPYBarReplayReport.json").write_text(
                json.dumps(
                    {
                        "status": "BAR_REPLAY_READY",
                        "summary": {"sampleCount": 254, "currentEntryCount": 23},
                        "causalReplay": {
                            "posteriorMayAffectTrigger": False,
                            "posteriorUsedForScoringOnly": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            production = {
                "overall": {"status": "PASS"},
                "history": {"status": "PASS"},
                "parity": {"status": "PASS"},
                "executionFeedback": {"status": "PASS"},
                "ga": {"status": "PASS", "stabilityGrade": "PRODUCTION_READY", "closureMode": "ELITE_STABILITY"},
            }

            report = build_rsi_lineage_closure(runtime, production_sections=production, write=True)

            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["closureStage"], "P4_10I_RSI_STABILITY_LINEAGE_CLOSED")
            self.assertEqual(report["selectedSeedId"], "g77-selected")
            self.assertTrue(report["criteria"]["allPass"])
            self.assertGreaterEqual(report["eliteRepeat"]["profileRepeatCount"], 3)
            self.assertEqual(report["shadowPromotion"]["decision"], "READY_FOR_TESTER_ONLY_SHADOW_PROMOTION")
            self.assertFalse(report["shadowPromotion"]["directLiveAllowed"])
            self.assertGreaterEqual(report["lineagePath"]["lineageDepth"], 3)
            self.assertEqual(report["frozenLineage"]["strategyJson"]["seedId"], "g77-selected")
            self.assertTrue((runtime / "production_validation" / RSI_LINEAGE_CLOSURE_REPORT).exists())
            self.assertTrue((runtime / "ga" / RSI_FROZEN_ELITE_LINEAGE).exists())


if __name__ == "__main__":
    unittest.main()
