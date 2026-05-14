#!/usr/bin/env python3
"""Rotate repo-local runtime logs and compact cold JSONL ledgers."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
from collections import deque
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
DEFAULT_ARCHIVE_MAX_MB = 512
DEFAULT_RETENTION_DAYS = 2
DEFAULT_GZIP_LEVEL = 3
DEFAULT_JSONL_ARCHIVE_DIR_NAME = "jsonl_archive"
DEFAULT_MAX_JSONL_MB = 2
DEFAULT_JSONL_KEEP_LINES = 2000
DEFAULT_JSONL_MIN_AGE_SECONDS = 60
STATUS_FILE_NAME = "QuantGod_RuntimeLogMaintenanceStatus.json"
ARCHIVED_LOG_RE = re.compile(r"^.+\.\d{8}T\d{4}(?:\d{2})?[A-Z]{0,5}\.log(?:\.gz)?$")
ARCHIVED_JSONL_RE = re.compile(r"^.+\.\d{8}T\d{4}(?:\d{2})?[A-Z]{0,5}\.jsonl\.gz$")


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


def _is_archived_jsonl(path: Path) -> bool:
    return bool(ARCHIVED_JSONL_RE.match(path.name))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


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


def _unique_jsonl_archive_path(archive_dir: Path, stem: str, stamp: str) -> Path:
    candidate = archive_dir / f"{stem}.{stamp}.jsonl.gz"
    if not candidate.exists():
        return candidate
    for index in range(1, 1000):
        fallback = archive_dir / f"{stem}.{stamp}.{index}.jsonl.gz"
        if not fallback.exists():
            return fallback
    raise RuntimeError(f"could not find unique jsonl archive path for {stem}")


def _expired(path: Path, *, now: datetime, retention_days: int) -> bool:
    cutoff = now - timedelta(days=max(0, retention_days))
    return datetime.fromtimestamp(path.stat().st_mtime, tz=now.tzinfo) < cutoff


def _older_than(path: Path, *, now: datetime, min_age_seconds: int) -> bool:
    if min_age_seconds <= 0:
        return True
    age_seconds = max(0.0, now.timestamp() - path.stat().st_mtime)
    return age_seconds >= float(min_age_seconds)


def _safe_stem_for_runtime_path(path: Path, runtime_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(runtime_root.resolve())
    except ValueError:
        relative = Path(path.name)
    without_suffix = relative.with_suffix("")
    raw = "__".join(without_suffix.parts)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("._") or path.stem


def _read_jsonl_tail_bytes(path: Path, *, max_bytes: int, keep_lines: int) -> bytes:
    if max_bytes <= 0 or keep_lines <= 0:
        return b""
    lines: deque[bytes] = deque()
    total = 0
    with path.open("rb") as handle:
        for line in handle:
            lines.append(line)
            total += len(line)
            while lines and len(lines) > keep_lines:
                total -= len(lines.popleft())
            while len(lines) > 1 and total > max_bytes:
                total -= len(lines.popleft())
    return b"".join(lines)


def _prune_archive_size(
    archive_dir: Path,
    *,
    archived_matcher,
    max_bytes: int,
    reason: str,
) -> list[dict[str, Any]]:
    if max_bytes <= 0:
        return []
    candidates = sorted(
        (path for path in archive_dir.glob("*") if path.is_file() and archived_matcher(path)),
        key=lambda item: (item.stat().st_mtime, item.name),
    )
    total = sum(path.stat().st_size for path in candidates)
    deleted: list[dict[str, Any]] = []
    for path in candidates:
        if total <= max_bytes:
            break
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        total -= size
        deleted.append({"path": str(path), "sizeBytes": size, "reason": reason})
    return deleted


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def maintain_jsonl_ledgers(
    runtime_root: Path,
    *,
    archive_dir: Path | None = None,
    max_active_bytes: int = DEFAULT_MAX_JSONL_MB * 1024 * 1024,
    keep_lines: int = DEFAULT_JSONL_KEEP_LINES,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    min_age_seconds: int = DEFAULT_JSONL_MIN_AGE_SECONDS,
) -> dict[str, Any]:
    runtime_root = runtime_root.resolve()
    archive_dir = (archive_dir or (runtime_root / DEFAULT_JSONL_ARCHIVE_DIR_NAME)).resolve()
    archive_dir.mkdir(parents=True, exist_ok=True)

    now = _tokyo_now()
    stamp = _timestamp_stamp(now)
    compacted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []

    jsonl_files = sorted(
        path for path in runtime_root.rglob("*.jsonl")
        if path.is_file() and not _is_relative_to(path, archive_dir)
    )
    for path in jsonl_files:
        size = path.stat().st_size
        if size <= max_active_bytes:
            continue
        if not _older_than(path, now=now, min_age_seconds=min_age_seconds):
            skipped.append({"path": str(path), "sizeBytes": size, "reason": "recently_modified"})
            continue
        stem = _safe_stem_for_runtime_path(path, runtime_root)
        archive_path = _unique_jsonl_archive_path(archive_dir, stem, stamp)
        _stream_gzip_copy(path, archive_path)
        tail = _read_jsonl_tail_bytes(path, max_bytes=max_active_bytes, keep_lines=keep_lines)
        path.write_bytes(tail)
        compacted.append(
            {
                "source": str(path),
                "archive": str(archive_path),
                "sizeBytes": size,
                "retainedBytes": len(tail),
                "keepLines": int(keep_lines),
            }
        )

    archive_candidates = sorted(path for path in archive_dir.glob("*.jsonl.gz") if path.is_file() and _is_archived_jsonl(path))
    for path in archive_candidates:
        if not _expired(path, now=now, retention_days=retention_days):
            continue
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        deleted.append({"path": str(path), "sizeBytes": size, "reason": "expired_jsonl_archive"})

    archive_files = sorted(path for path in archive_dir.glob("*.jsonl.gz") if path.is_file())
    return {
        "archiveDir": str(archive_dir),
        "maxActiveBytes": int(max_active_bytes),
        "keepLines": int(keep_lines),
        "minAgeSeconds": int(min_age_seconds),
        "retentionDays": int(retention_days),
        "activeJsonlCount": len(jsonl_files),
        "archiveCount": len(archive_files),
        "compacted": compacted,
        "skipped": skipped,
        "deleted": deleted,
    }


def maintain_logs(
    runtime_root: Path,
    *,
    archive_dir: Path | None = None,
    max_active_bytes: int = DEFAULT_MAX_ACTIVE_MB * 1024 * 1024,
    archive_max_bytes: int = DEFAULT_ARCHIVE_MAX_MB * 1024 * 1024,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    jsonl_archive_dir: Path | None = None,
    jsonl_max_active_bytes: int = DEFAULT_MAX_JSONL_MB * 1024 * 1024,
    jsonl_keep_lines: int = DEFAULT_JSONL_KEEP_LINES,
    jsonl_min_age_seconds: int = DEFAULT_JSONL_MIN_AGE_SECONDS,
    maintain_jsonl: bool = True,
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

    deleted.extend(
        _prune_archive_size(
            archive_dir,
            archived_matcher=_is_archived_log,
            max_bytes=max(0, int(archive_max_bytes)),
            reason="archive_size_cap",
        )
    )

    archive_files = sorted(path for path in archive_dir.glob("*.log*") if path.is_file())
    jsonl_status = (
        maintain_jsonl_ledgers(
            runtime_root,
            archive_dir=jsonl_archive_dir,
            max_active_bytes=max(1, int(jsonl_max_active_bytes)),
            keep_lines=max(0, int(jsonl_keep_lines)),
            retention_days=max(0, int(retention_days)),
            min_age_seconds=max(0, int(jsonl_min_age_seconds)),
        )
        if maintain_jsonl
        else {"enabled": False}
    )
    status = {
        "schema": "quantgod.runtime_log_maintenance_status.v1",
        "generatedAtIso": _utc_now_iso(),
        "runtimeRoot": str(runtime_root),
        "archiveDir": str(archive_dir),
        "maxActiveBytes": int(max_active_bytes),
        "archiveMaxBytes": int(archive_max_bytes),
        "retentionDays": int(retention_days),
        "activeLogCount": len(active_logs),
        "archiveCount": len(archive_files),
        "rotated": rotated,
        "compressedLegacy": compressed_legacy,
        "deleted": deleted,
        "jsonl": jsonl_status,
    }
    _write_status(runtime_root / STATUS_FILE_NAME, status)
    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rotate/compress repo runtime logs and compact cold JSONL ledgers.")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--archive-dir", default="")
    parser.add_argument(
        "--max-active-mb",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_LOG_MAX_MB", DEFAULT_MAX_ACTIVE_MB)),
    )
    parser.add_argument(
        "--archive-max-mb",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_LOG_ARCHIVE_MAX_MB", DEFAULT_ARCHIVE_MAX_MB)),
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_LOG_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)),
    )
    parser.add_argument("--jsonl-archive-dir", default="")
    parser.add_argument(
        "--max-jsonl-mb",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_JSONL_MAX_MB", DEFAULT_MAX_JSONL_MB)),
    )
    parser.add_argument(
        "--jsonl-keep-lines",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_JSONL_KEEP_LINES", DEFAULT_JSONL_KEEP_LINES)),
    )
    parser.add_argument(
        "--jsonl-min-age-seconds",
        type=int,
        default=int(os.environ.get("QG_RUNTIME_JSONL_MIN_AGE_SECONDS", DEFAULT_JSONL_MIN_AGE_SECONDS)),
    )
    parser.add_argument("--no-jsonl-maintenance", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_root = Path(args.runtime_root)
    archive_dir = Path(args.archive_dir) if args.archive_dir else runtime_root / DEFAULT_ARCHIVE_DIR_NAME
    jsonl_archive_dir = Path(args.jsonl_archive_dir) if args.jsonl_archive_dir else runtime_root / DEFAULT_JSONL_ARCHIVE_DIR_NAME
    status = maintain_logs(
        runtime_root,
        archive_dir=archive_dir,
        max_active_bytes=max(1, int(args.max_active_mb)) * 1024 * 1024,
        archive_max_bytes=max(0, int(args.archive_max_mb)) * 1024 * 1024,
        retention_days=max(0, int(args.retention_days)),
        jsonl_archive_dir=jsonl_archive_dir,
        jsonl_max_active_bytes=max(1, int(args.max_jsonl_mb)) * 1024 * 1024,
        jsonl_keep_lines=max(0, int(args.jsonl_keep_lines)),
        jsonl_min_age_seconds=max(0, int(args.jsonl_min_age_seconds)),
        maintain_jsonl=not args.no_jsonl_maintenance,
    )
    jsonl_status = status.get("jsonl") if isinstance(status.get("jsonl"), dict) else {}
    print(
        json.dumps(
            {
                "runtimeRoot": status["runtimeRoot"],
                "archiveDir": status["archiveDir"],
                "rotatedCount": len(status["rotated"]),
                "compressedLegacyCount": len(status["compressedLegacy"]),
                "deletedCount": len(status["deleted"]),
                "archiveCount": status["archiveCount"],
                "jsonlCompactedCount": len(jsonl_status.get("compacted", [])),
                "jsonlDeletedCount": len(jsonl_status.get("deleted", [])),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
