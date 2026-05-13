import gzip
import importlib.util
import os
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


if __name__ == "__main__":
    unittest.main()
