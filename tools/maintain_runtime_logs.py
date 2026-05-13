#!/usr/bin/env python3
"""Rotate and prune repo-local runtime logs without interrupting writers."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = REPO_ROOT / "runtime"
DEFAULT_ARCHIVE_DIR_NAME = "log_archive"
DEFAULT_MAX_ACTIVE_MB = 128
DEFAULT_RETENTION_DAYS = 2
DEFAULT_GZIP_LEVEL = 3
STATUS_FILE_NAME = "QuantGod_RuntimeLogMaintenanceStatus.json"
ARCHIVED_LOG_RE = re.compile(r"^.+\.\d{8}T\d{4}(?:\d{2})?[A-Z]{0,5}\.log(?:\.gz)?$")


def _tokyo_now() -> datetime:
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo("Asia/Tokyo"))
    return datetime.now().astimezone()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_stamp(now: datetime | None = None) -> str:
    current = now or _tokyo_now()
    return current.strftime("%Y%m%dT%H%M%S%Z")


def _is_archived_log(path: Path) -> bool:
    return bool(ARCHIVED_LOG_RE.match(path.name))


def _stream_gzip_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, gzip.open(target, "wb", compresslevel=DEFAULT_GZIP_LEVEL) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def _truncate_in_place(path: Path) -> None:
    with path.open("r+b") as handle:
        handle.truncate(0)


def _unique_archive_path(archive_dir: Path, stem: str, stamp: str) -> Path:
    candidate = archive_dir / f"{stem}.{stamp}.log.gz"
    if not candidate.exists():
        return candidate
    for index in range(1, 1000):
        fallback = archive_dir / f"{stem}.{stamp}.{index}.log.gz"
        if not fallback.exists():
            return fallback
    raise RuntimeError(f"could not find unique archive path for {stem}")


def _expired(path: Path, *, now: datetime, retention_days: int) -> bool:
    cutoff = now - timedelta(days=max(0, retention_days))
    return datetime.fromtimestamp(path.stat().st_mtime, tz=now.tzinfo) < cutoff


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def maintain_logs(
    runtime_root: Path,
    *,
    archive_dir: Path | None = None,
    max_active_bytes: int = DEFAULT_MAX_ACTIVE_MB * 1024 * 1024,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict[str, Any]:
    runtime_root = runtime_root.resolve()
    archive_dir = (archive_dir or (runtime_root / DEFAULT_ARCHIVE_DIR_NAME)).resolve()
    archive_dir.mkdir(parents=True, exist_ok=True)

    now = _tokyo_now()
    stamp = _timestamp_stamp(now)
    rotated: list[dict[str, Any]] = []
    compressed_legacy: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []

    active_logs = sorted(path for path in runtime_root.glob("*.log") if path.is_file() and not _is_archived_log(path))
    for path in active_logs:
        size = path.stat().st_size
        if size <= max_active_bytes:
            continue
        archive_path = _unique_archive_path(archive_dir, path.stem, stamp)
        _stream_gzip_copy(path, archive_path)
        _truncate_in_place(path)
        rotated.append(
            {
                "source": str(path),
                "archive": str(archive_path),
                "sizeBytes": size,
            }
        )

    legacy_archives = sorted(path for path in runtime_root.glob("*.log*") if path.is_file() and _is_archived_log(path))
    for path in legacy_archives:
        size = path.stat().st_size
        if _expired(path, now=now, retention_days=retention_days):
            path.unlink(missing_ok=True)
            deleted.append({"path": str(path), "sizeBytes": size, "reason": "expired_legacy_archive"})
            continue
        if path.suffix == ".gz":
            target = archive_dir / path.name
            if path.resolve() != target.resolve():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    target.unlink()
                shutil.move(str(path), str(target))
                compressed_legacy.append(
                    {
                        "source": str(path),
                        "archive": str(target),
                        "sizeBytes": size,
                        "action": "moved_gzip_archive",
                    }
                )
            continue
        target = archive_dir / f"{path.name}.gz"
        if target.exists():
            target.unlink()
        _stream_gzip_copy(path, target)
        path.unlink(missing_ok=True)
        compressed_legacy.append(
            {
                "source": str(path),
                "archive": str(target),
                "sizeBytes": size,
                "action": "compressed_legacy_archive",
            }
        )

    archive_candidates = sorted(path for path in archive_dir.glob("*.log*") if path.is_file() and _is_archived_log(path))
    for path in archive_candidates:
        if not _expired(path, now=now, retention_days=retention_days):
            continue
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        deleted.append({"path": str(path), "sizeBytes": size, "reason": "expired_archive"})

    archive_files = sorted(path for path in archive_dir.glob("*.log*") if path.is_file())
    status = {
        "schema": "quantgod.runtime_log_maintenance_status.v1",
        "generatedAtIso": _utc_now_iso(),
        "runtimeRoot": str(runtime_root),
        "archiveDir": str(archive_dir),
        "maxActiveBytes": int(max_active_bytes),
        "retentionDays": int(retention_days),
        "activeLogCount": len(active_logs),
        "archiveCount": len(archive_files),
        "rotated": rotated,
        "compressedLegacy": compressed_legacy,
        "deleted": deleted,
    }
    _write_status(runtime_root / STATUS_FILE_NAME, status)
    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rotate/compress repo runtime logs and prune old archives.")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--archive-dir", default="")
    parser.add_argument(
        "--max-active-mb",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_LOG_MAX_MB", DEFAULT_MAX_ACTIVE_MB)),
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_LOG_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_root = Path(args.runtime_root)
    archive_dir = Path(args.archive_dir) if args.archive_dir else runtime_root / DEFAULT_ARCHIVE_DIR_NAME
    status = maintain_logs(
        runtime_root,
        archive_dir=archive_dir,
        max_active_bytes=max(1, int(args.max_active_mb)) * 1024 * 1024,
        retention_days=max(0, int(args.retention_days)),
    )
    print(
        json.dumps(
            {
                "runtimeRoot": status["runtimeRoot"],
                "archiveDir": status["archiveDir"],
                "rotatedCount": len(status["rotated"]),
                "compressedLegacyCount": len(status["compressedLegacy"]),
                "deletedCount": len(status["deleted"]),
                "archiveCount": status["archiveCount"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
