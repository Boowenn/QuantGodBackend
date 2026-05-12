from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.production_evidence_validation.report import build_report, write_reports
from tools.production_evidence_validation.schema import REQUIRED_STRATEGY_FAMILIES


class ProductionEvidenceValidationTests(unittest.TestCase):
    def test_builds_warn_report_without_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = build_report(Path(tmp))
            self.assertEqual(report["schema"], "quantgod.production_evidence_validation.v1")
            self.assertIn(report["status"], {"WARN", "FAIL"})
            self.assertFalse(report["safety"]["orderSendAllowed"])

    def test_writes_reports_with_sqlite_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "backtest" / "usdjpy.sqlite"
            db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db))
            conn.execute("CREATE TABLE bars_m1 (time TEXT, close REAL)")
            conn.execute("CREATE TABLE bars_m5 (time TEXT, close REAL)")
            conn.execute("INSERT INTO bars_m1 VALUES ('2026-05-12T00:00:00Z', 155.0)")
            conn.execute("INSERT INTO bars_m5 VALUES ('2026-05-12T00:00:00Z', 155.0)")
            conn.commit()
            conn.close()
            report = build_report(root)
            paths = write_reports(root, report)
            self.assertTrue(Path(paths["latest"]).exists())
            saved = json.loads(Path(paths["latest"]).read_text(encoding="utf-8"))
            self.assertIn("historyProduction", saved)

    def test_strategy_family_parity_uses_backtest_coverage_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            for family in REQUIRED_STRATEGY_FAMILIES:
                for direction in ("LONG", "SHORT"):
                    rows.append(
                        {
                            "strategyFamily": family,
                            "direction": direction,
                            "ok": True,
                            "status": "PASS",
                            "tradeCount": 0,
                            "parityVectorPresent": True,
                        }
                    )

            report_path = root / "backtest" / "QuantGod_StrategyBacktestReport.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(
                    {
                        "strategyCoverageMatrix": {
                            "schema": "quantgod.strategy_backtest_coverage_matrix.v1",
                            "status": "PASS",
                            "rows": rows,
                            "summary": {
                                "familyCount": len(REQUIRED_STRATEGY_FAMILIES),
                                "routeCount": len(rows),
                                "coveredFamilyCount": len(REQUIRED_STRATEGY_FAMILIES),
                                "okRouteCount": len(rows),
                                "parityVectorRouteCount": len(rows),
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            parity_dir = root / "parity"
            parity_dir.mkdir(parents=True, exist_ok=True)
            (parity_dir / "QuantGod_StrategyParityReport.json").write_text(
                json.dumps(
                    {
                        "families": [
                            {
                                "strategyFamily": "RSI_Reversal",
                                "status": "PARITY_PASS",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = build_report(root)
            parity = report["strategyFamilyParity"]
            statuses = {row["strategyFamily"]: row["parityStatus"] for row in parity["matrix"]}
            self.assertEqual(parity["missingCount"], 0)
            self.assertEqual(parity["status"], "PASS")
            self.assertEqual(statuses["RSI_Reversal"], "PASS")
            self.assertIn("SHADOW_RESEARCH_ONLY", set(statuses.values()))


if __name__ == "__main__":
    unittest.main()
