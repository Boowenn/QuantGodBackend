from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.production_evidence_validation.report import build_report, write_reports


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


if __name__ == "__main__":
    unittest.main()
