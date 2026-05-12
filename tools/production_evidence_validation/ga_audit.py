from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json, read_csv_rows


def _count_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "candidates", "nodes", "edges", "elite", "graveyard"):
            if isinstance(value.get(key), list):
                return len(value[key])
        return len(value)
    return 0


def audit_ga(runtime_dir: Path) -> dict[str, Any]:
    factory_dir = runtime_dir / "ga_factory"
    state = read_json(factory_dir / "QuantGod_GAFactoryState.json", {}) or {}
    elite = read_json(factory_dir / "QuantGod_GAEliteArchive.json", {}) or {}
    graveyard = read_json(factory_dir / "QuantGod_GAStrategyGraveyard.json", {}) or {}
    lineage = read_json(factory_dir / "QuantGod_GALineageTree.json", {}) or {}
    ledger = read_csv_rows(factory_dir / "QuantGod_GAFactoryLedger.csv", 1000)
    generation = int(state.get("currentGeneration") or state.get("generation") or 0)
    candidate_count = int(state.get("candidateCount") or _count_items(state.get("candidates")) or 0)
    elite_count = int(state.get("eliteCount") or _count_items(elite) or 0)
    graveyard_count = int(state.get("graveyardCount") or _count_items(graveyard) or 0)
    lineage_nodes = int(state.get("lineageNodeCount") or _count_items(lineage.get("nodes") if isinstance(lineage, dict) else lineage) or 0)
    status = "PASS" if generation >= 2 and candidate_count >= 5 and lineage_nodes >= 1 else "WARN"
    return {
        "status": status,
        "currentGeneration": generation,
        "candidateCount": candidate_count,
        "eliteCount": elite_count,
        "graveyardCount": graveyard_count,
        "lineageNodeCount": lineage_nodes,
        "ledgerRows": len(ledger),
        "recommendation": "GA factory has multi-generation evidence." if status == "PASS" else "Run additional GA factory generations and confirm lineage/elite/graveyard stability.",
    }
