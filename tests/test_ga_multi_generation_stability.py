from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from tools.ga_multi_generation_stability.stability import build_report


class GAMultiGenerationStabilityTests(unittest.TestCase):
    def test_build_report_detects_stable_generation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            ga = runtime / "ga"
            ga.mkdir(parents=True)
            (ga / "QuantGod_GAStatus.json").write_text(json.dumps({"currentGeneration": 3}), encoding="utf-8")
            rows = []
            for generation in (1, 2, 3):
                for index in range(6):
                    rows.append(
                        {
                            "seedId": f"g{generation}-{index}",
                            "strategyId": f"S{index}",
                            "strategyFamily": "RSI_Reversal",
                            "generation": generation,
                            "fitness": 1.0 + generation + index / 100,
                            "status": "ELITE_SELECTED" if index == 0 else "NEEDS_MORE_DATA",
                            "promotionStage": "SHADOW",
                        }
                    )
            (ga / "QuantGod_GACandidateRuns.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            (ga / "QuantGod_GALineage.json").write_text(
                json.dumps(
                    {
                        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
                        "edges": [
                            {"source": "a", "target": "b"},
                            {"source": "b", "target": "c"},
                            {"source": "c", "target": "d"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            factory = runtime / "ga_factory"
            factory.mkdir(parents=True)
            (factory / "QuantGod_GAFactoryLedger.csv").write_text(
                "generatedAt,status\n2026-01-01T00:00:00Z,FACTORY_READY\n2026-01-01T00:05:00Z,FACTORY_READY\n",
                encoding="utf-8",
            )
            report = build_report(runtime, write=True)
            self.assertEqual(report["status"], "PASS")
            self.assertGreaterEqual(report["generationCount"], 3)
            self.assertGreaterEqual(report["candidateCount"], 18)
            self.assertGreaterEqual(report["eliteCount"], 1)
            self.assertGreaterEqual(report["eliteRepeatCount"], 1)
            self.assertTrue((runtime / "production_validation" / "QuantGod_GAMultiGenerationStabilityReport.json").exists())

    def test_build_report_reads_archived_candidate_runs_after_runtime_compaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            archive = runtime / "jsonl_archive"
            archive.mkdir(parents=True)
            archived_rows = []
            for generation in (1, 2, 3):
                for index in range(6):
                    archived_rows.append(
                        {
                            "seedId": f"archived-{generation}-{index}",
                            "strategyId": f"S{index}",
                            "strategyFamily": "RSI_Reversal",
                            "generation": generation,
                            "fitness": 2.0 + generation,
                            "status": "ELITE_SELECTED" if index == 0 else "NEEDS_MORE_DATA",
                            "promotionStage": "SHADOW",
                        }
                    )
            archive_path = archive / "ga__QuantGod_GACandidateRuns.20260514T191219JST.jsonl.gz"
            with gzip.open(archive_path, "wt", encoding="utf-8") as handle:
                for row in archived_rows:
                    handle.write(json.dumps(row) + "\n")

            ga = runtime / "ga"
            ga.mkdir(parents=True)
            (ga / "QuantGod_GAStatus.json").write_text(json.dumps({"currentGeneration": 3}), encoding="utf-8")
            (ga / "QuantGod_GACandidateRuns.jsonl").write_text(
                json.dumps({"seedId": "tail-only", "generation": 3, "status": "REJECTED", "fitness": -1}) + "\n",
                encoding="utf-8",
            )
            (ga / "QuantGod_GALineage.json").write_text(
                json.dumps(
                    {
                        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
                        "edges": [
                            {"source": "a", "target": "b"},
                            {"source": "b", "target": "c"},
                            {"source": "c", "target": "d"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            factory = runtime / "ga_factory"
            factory.mkdir(parents=True)
            (factory / "QuantGod_GAFactoryLedger.csv").write_text(
                "generatedAt,status\n2026-01-01T00:00:00Z,FACTORY_READY\n2026-01-01T00:05:00Z,FACTORY_READY\n",
                encoding="utf-8",
            )

            report = build_report(runtime, write=False)
            self.assertEqual(report["status"], "PASS")
            self.assertGreaterEqual(report["candidateCount"], 18)
            self.assertGreaterEqual(report["eliteCount"], 1)

    def test_build_report_counts_from_to_lineage_depth_and_empty_elite_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            ga = runtime / "ga"
            ga.mkdir(parents=True)
            (ga / "QuantGod_GAStatus.json").write_text(json.dumps({"currentGeneration": 3}), encoding="utf-8")
            rows = [
                {
                    "seedId": "parent",
                    "strategyId": "PARENT",
                    "strategyFamily": "RSI_Reversal",
                    "generation": 1,
                    "fitness": -1,
                    "status": "REJECTED",
                },
                {
                    "seedId": "child",
                    "strategyId": "CHILD",
                    "strategyFamily": "RSI_Reversal",
                    "generation": 2,
                    "fitness": -2,
                    "status": "REJECTED",
                    "strategyJson": {"seedId": "child", "parentSeedId": "parent"},
                },
            ]
            (ga / "QuantGod_GACandidateRuns.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            (ga / "QuantGod_GAEliteStrategies.json").write_text(
                json.dumps({"schema": "quantgod.ga.elites.v1", "elites": []}),
                encoding="utf-8",
            )
            (ga / "QuantGod_GALineage.json").write_text(
                json.dumps({"nodes": [{"id": "parent"}, {"id": "child"}], "edges": [{"from": "parent", "to": "child"}]}),
                encoding="utf-8",
            )

            report = build_report(runtime, write=False)

            self.assertEqual(report["eliteCount"], 0)
            self.assertGreaterEqual(report["lineageDepth"], 2)

    def test_build_report_closes_no_elite_negative_selection_after_burn_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            ga = runtime / "ga"
            ga.mkdir(parents=True)
            (ga / "QuantGod_GAStatus.json").write_text(json.dumps({"currentGeneration": 5}), encoding="utf-8")
            rows = []
            for generation in range(1, 6):
                for index in range(16):
                    seed_id = f"g{generation}-{index}"
                    rows.append(
                        {
                            "seedId": seed_id,
                            "strategyId": f"S{index}",
                            "strategyFamily": "RSI_Reversal",
                            "generation": generation,
                            "fitness": -1.0 - generation - index / 100,
                            "status": "REJECTED",
                            "promotionStage": "REJECTED",
                            "blockerCode": "WALK_FORWARD_UNSTABLE",
                            "strategyJson": {
                                "seedId": seed_id,
                                "parentSeedId": f"g{generation - 1}-{index}" if generation > 1 else "",
                            },
                        }
                    )
            (ga / "QuantGod_GACandidateRuns.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            factory = runtime / "ga_factory"
            factory.mkdir(parents=True)
            (factory / "QuantGod_GAStrategyGraveyard.json").write_text(
                json.dumps({"strategies": rows[:64]}),
                encoding="utf-8",
            )
            (factory / "QuantGod_GAFactoryLedger.csv").write_text(
                "generatedAt,status\n2026-01-01T00:00:00Z,FACTORY_READY\n",
                encoding="utf-8",
            )

            report = build_report(runtime, write=False)

            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["stabilityGrade"], "NEGATIVE_SELECTION_CLOSED")
            self.assertEqual(report["closureMode"], "NO_ELITE_NEGATIVE_SELECTION")
            self.assertFalse(report["promotionAllowed"])
            self.assertEqual(report["eliteCount"], 0)


if __name__ == "__main__":
    unittest.main()
