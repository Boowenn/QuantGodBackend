from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_csv_rows, read_json

try:
    from tools.ga_multi_generation_stability.stability import build_report as build_stability_report
except ModuleNotFoundError:  # pragma: no cover
    from ga_multi_generation_stability.stability import build_report as build_stability_report


def _count_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "candidates", "nodes", "edges", "elite", "elites", "graveyard", "strategies"):
            if isinstance(value.get(key), list):
                return len(value[key])
        return 0
    return 0


def audit_ga(runtime_dir: Path) -> dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    stability = build_stability_report(runtime_dir, write=True)
    factory_dir = runtime_dir / "ga_factory"
    state = read_json(factory_dir / "QuantGod_GAFactoryState.json", {}) or {}
    elite = read_json(factory_dir / "QuantGod_GAEliteArchive.json", {}) or {}
    graveyard = read_json(factory_dir / "QuantGod_GAStrategyGraveyard.json", {}) or {}
    lineage = read_json(factory_dir / "QuantGod_GALineageTree.json", {}) or {}
    ledger = read_csv_rows(factory_dir / "QuantGod_GAFactoryLedger.csv", 1000)

    generation = int(state.get("currentGeneration") or state.get("generation") or stability.get("currentGeneration") or 0)
    candidate_count = int(state.get("candidateCount") or _count_items(state.get("candidates")) or stability.get("candidateCount") or 0)
    elite_count = int(state.get("eliteCount") or _count_items(elite) or stability.get("eliteCount") or 0)
    graveyard_count = int(state.get("graveyardCount") or _count_items(graveyard) or stability.get("graveyardCount") or 0)
    lineage_nodes = int(
        state.get("lineageNodeCount")
        or _count_items(lineage.get("nodes") if isinstance(lineage, dict) else lineage)
        or stability.get("lineageNodeCount")
        or 0
    )

    status = "PASS" if stability.get("status") == "PASS" else "WARN"
    return {
        "status": status,
        "currentGeneration": generation,
        "candidateCount": candidate_count,
        "eliteCount": elite_count,
        "eliteGenerationCount": stability.get("eliteGenerationCount", 0),
        "eliteRepeatCount": stability.get("eliteRepeatCount", 0),
        "eliteRepeatEvidence": stability.get("eliteRepeatEvidence", []),
        "graveyardCount": graveyard_count,
        "lineageNodeCount": lineage_nodes,
        "ledgerRows": len(ledger),
        "stabilityGrade": stability.get("stabilityGrade"),
        "closureMode": stability.get("closureMode"),
        "promotionAllowed": bool(stability.get("promotionAllowed")),
        "evidenceUsability": stability.get("evidenceUsability"),
        "generationCount": stability.get("generationCount", 0),
        "lineageEdgeCount": stability.get("lineageEdgeCount", 0),
        "lineageDepth": stability.get("lineageDepth", 0),
        "fitnessSummary": stability.get("fitnessSummary", {}),
        "generationSummary": stability.get("generationSummary", []),
        "blockerCounts": stability.get("blockerCounts", {}),
        "recommendationsZh": stability.get("recommendationsZh", []),
        "recommendation": _recommendation(status, stability),
    }


def _recommendation(status: str, stability: dict[str, Any]) -> str:
    if status == "PASS":
        if stability.get("stabilityGrade") == "NEGATIVE_SELECTION_CLOSED":
            return "GA negative selection is closed; keep promotion blocked and expand the next search cycle."
        return "GA multi-generation stability evidence is usable for production observation."
    recommendations = stability.get("recommendationsZh") or []
    if recommendations:
        return str(recommendations[0])
    return "Run additional GA generations and confirm lineage/elite/graveyard stability."
