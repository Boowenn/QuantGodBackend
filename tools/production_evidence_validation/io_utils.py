from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
        except Exception:
            continue
    return rows


def read_csv_rows(path: Path, limit: int = 500) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return rows[-limit:]
    except Exception:
        return []


def sqlite_table_summary(db_path: Path, table_names: list[str]) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    summaries: list[dict[str, Any]] = []
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            for table in table_names:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                    time_col = next((c for c in ["time", "timestamp", "openTime", "timeIso", "datetime"] if c in columns), None)
                    min_time = max_time = None
                    if time_col:
                        row = conn.execute(f"SELECT MIN({time_col}), MAX({time_col}) FROM {table}").fetchone()
                        min_time, max_time = row[0], row[1]
                    summaries.append({"table": table, "rows": int(count), "minTime": min_time, "maxTime": max_time})
                except Exception as exc:
                    summaries.append({"table": table, "rows": 0, "error": str(exc)})
        finally:
            conn.close()
    except Exception as exc:
        return [{"database": str(db_path), "error": str(exc)}]
    return summaries


def existing_candidates(runtime_dir: Path, relative_paths: list[str]) -> list[Path]:
    paths = []
    for rel in relative_paths:
        path = runtime_dir / rel
        if path.exists():
            paths.append(path)
    return paths
