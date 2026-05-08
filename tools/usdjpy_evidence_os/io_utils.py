from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


MT5_FILES_ENV_KEYS = (
    "QG_MT5_FILES_DIR",
    "QG_MT5_FILES",
    "QG_HFM_FILES_DIR",
    "QG_HFM_FILES",
)

DEFAULT_MT5_FILES_PATH = (
    Path.home()
    / "Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/MQL5/Files"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path


def unique_existing_dirs(candidates: Iterable[Path]) -> List[Path]:
    seen = set()
    dirs: List[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        key = str(resolved)
        if key in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(key)
        dirs.append(resolved)
    return dirs


def candidate_mt5_files_dirs(runtime_dir: Path) -> List[Path]:
    """Return runtime plus configured live MT5/HFM MQL5/Files directories.

    Evidence OS can be run from a repository runtime directory while the real EA
    writes into the broker terminal's MQL5/Files folder. Keep the discovery logic
    shared so parity, execution feedback, and future evidence readers agree on the
    same real source of truth.
    """
    candidates: List[Path] = [Path(runtime_dir)]
    explicit_candidates: List[Path] = []
    for key in MT5_FILES_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            explicit_candidates.append(resolve_path(value))
    candidates.extend(explicit_candidates)
    if not explicit_candidates and os.environ.get("QG_ENABLE_DEFAULT_MT5_FEEDBACK_DISCOVERY") == "1":
        candidates.append(DEFAULT_MT5_FILES_PATH)
    return unique_existing_dirs(candidates)


def append_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def append_jsonl_unique(path: Path, rows: Iterable[Dict[str, Any]], key: str) -> int:
    existing = {str(row.get(key)) for row in read_jsonl_tail(path, 2000) if row.get(key)}
    to_write: List[Dict[str, Any]] = []
    for row in rows:
        value = str(row.get(key) or "")
        if not value or value in existing:
            continue
        existing.add(value)
        to_write.append(row)
    append_jsonl(path, to_write)
    return len(to_write)


def read_jsonl_tail(path: Path, limit: int = 200) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                rows.append(data)
        except Exception:
            continue
    return rows
