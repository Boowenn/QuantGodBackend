import gzip
import importlib.util
import os
import time
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "maintain_runtime_logs.py"
SPEC = importlib.util.spec_from_file_location("maintain_runtime_logs", MODULE_PATH)
runtime_logs = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runtime_logs)


class RuntimeLogMaintenanceTests(unittest.TestCase):
    def test_rotates_large_active_log_and_truncates_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime_root.mkdir(parents=True)
            active_log = runtime_root / "agent_v25_screen.log"
            active_log.write_text("line\n" * 64, encoding="utf-8")

            status = runtime_logs.maintain_logs(
                runtime_root,
                max_active_bytes=32,
                retention_days=7,
            )

            self.assertEqual(active_log.stat().st_size, 0)
            self.assertEqual(len(status["rotated"]), 1)
            archive_path = Path(status["rotated"][0]["archive"])
            self.assertTrue(archive_path.exists())
            with gzip.open(archive_path, "rt", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "line\n" * 64)

    def test_compresses_legacy_archives_and_prunes_expired_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            archive_dir = runtime_root / "log_archive"
            runtime_root.mkdir(parents=True)
            legacy = runtime_root / "agent_v25_screen.20260512T1459JST.log"
            legacy.write_text("legacy\n" * 8, encoding="utf-8")
            old_archive = archive_dir / "agent_v25_screen.20260510T1459JST.log.gz"
            archive_dir.mkdir(parents=True)
            with gzip.open(old_archive, "wt", encoding="utf-8") as handle:
                handle.write("expired\n")

            old_time = (datetime.now().timestamp() - timedelta(days=5).total_seconds(),) * 2
            os.utime(old_archive, old_time)

            status = runtime_logs.maintain_logs(
                runtime_root,
                archive_dir=archive_dir,
                max_active_bytes=1024 * 1024,
                retention_days=2,
            )

            self.assertFalse(legacy.exists())
            self.assertTrue(any(item["action"] == "compressed_legacy_archive" for item in status["compressedLegacy"]))
            self.assertFalse(old_archive.exists())
            self.assertTrue(any(item["reason"] == "expired_archive" for item in status["deleted"]))

    def test_prunes_log_archives_over_size_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            archive_dir = runtime_root / "log_archive"
            archive_dir.mkdir(parents=True)
            old_archive = archive_dir / "agent_v25_screen.20260510T1459JST.log.gz"
            new_archive = archive_dir / "agent_v25_screen.20260511T1459JST.log.gz"
            for archive in (old_archive, new_archive):
                with gzip.open(archive, "wt", encoding="utf-8") as handle:
                    handle.write("x" * 128)
            now = time.time()
            os.utime(old_archive, (now - 2, now - 2))
            os.utime(new_archive, (now - 1, now - 1))

            status = runtime_logs.maintain_logs(
                runtime_root,
                archive_dir=archive_dir,
                max_active_bytes=1024 * 1024,
                archive_max_bytes=1,
                retention_days=30,
                maintain_jsonl=False,
            )

            self.assertTrue(any(item["reason"] == "archive_size_cap" for item in status["deleted"]))
            self.assertFalse(old_archive.exists())

    def test_compacts_large_jsonl_and_archives_full_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            ledger = runtime_root / "execution" / "QuantGod_LiveExecutionFeedback.jsonl"
            ledger.parent.mkdir(parents=True)
            ledger.write_text("".join(f'{{"i":{i},"text":"{"x" * 20}"}}\n' for i in range(10)), encoding="utf-8")

            status = runtime_logs.maintain_logs(
                runtime_root,
                max_active_bytes=1024 * 1024,
                jsonl_max_active_bytes=90,
                jsonl_keep_lines=3,
                jsonl_min_age_seconds=0,
                maintain_jsonl=True,
            )

            self.assertEqual(len(status["jsonl"]["compacted"]), 1)
            self.assertLessEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 3)
            archive_path = Path(status["jsonl"]["compacted"][0]["archive"])
            self.assertTrue(archive_path.exists())
            with gzip.open(archive_path, "rt", encoding="utf-8") as handle:
                self.assertIn('"i":0', handle.read())


if __name__ == "__main__":
    unittest.main()
