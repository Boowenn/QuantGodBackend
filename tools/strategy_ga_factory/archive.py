"""Small persistence helpers for GA Factory audit artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: Path, *, limit: int = 4096) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def latest_by_key(rows: Iterable[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "")
        if not value:
            continue
        index[value] = row
    return list(index.values())


def append_ledger_row(path: Path, row: Dict[str, Any], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fieldnames})
