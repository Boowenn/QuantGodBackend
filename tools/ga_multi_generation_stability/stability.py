from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .io_utils import read_csv_rows, read_json, read_jsonl, write_csv_rows, write_json
from .schema import (
    AGENT_VERSION,
    MIN_CANDIDATES_STABLE,
    MIN_CANDIDATES_WATCH,
    MIN_ELITE_REPEAT_STABLE,
    MIN_ELITE_STABLE,
    MIN_GENERATIONS_PRODUCTION_READY,
    MIN_GENERATIONS_STABLE,
    MIN_GENERATIONS_WATCH,
    MIN_GRAVEYARD_CLOSED,
    MIN_LINEAGE_EDGES_STABLE,
    MIN_LINEAGE_NODES_STABLE,
    SAFETY,
    SCHEMA_STABILITY_REPORT,
    ledger_path,
    report_path,
    utc_now_iso,
)


def build_report(runtime_dir: Path, *, write: bool = True) -> dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    ga_dir = runtime_dir / "ga"
    factory_dir = runtime_dir / "ga_factory"

    status = read_json(ga_dir / "QuantGod_GAStatus.json", {}) or {}
    latest_generation = read_json(ga_dir / "QuantGod_GAGenerationLatest.json", {}) or {}
    generation_ledger = read_jsonl(ga_dir / "QuantGod_GAGenerationLedger.jsonl", limit=5000)
    candidate_runs = _candidate_runs(runtime_dir, ga_dir)
    elite_json = read_json(ga_dir / "QuantGod_GAEliteStrategies.json", {}) or {}
    lineage_json = read_json(ga_dir / "QuantGod_GALineage.json", {}) or {}
    blocker_json = read_json(ga_dir / "QuantGod_GABlockerSummary.json", {}) or {}
    fitness_cache = read_json(ga_dir / "QuantGod_GAFitnessCache.json", {}) or {}

    factory_state = read_json(factory_dir / "QuantGod_GAFactoryState.json", {}) or {}
    factory_elite = read_json(factory_dir / "QuantGod_GAEliteArchive.json", {}) or {}
    factory_graveyard = read_json(factory_dir / "QuantGod_GAStrategyGraveyard.json", {}) or {}
    factory_lineage = read_json(factory_dir / "QuantGod_GALineageTree.json", {}) or {}
    factory_ledger = read_csv_rows(factory_dir / "QuantGod_GAFactoryLedger.csv", limit=5000)

    candidate_lineage_edges = _candidate_lineage_edges(candidate_runs)
    candidate_lineage_nodes = _candidate_lineage_node_count(candidate_runs, candidate_lineage_edges)
    generation_numbers = _generation_numbers(status, latest_generation, generation_ledger, candidate_runs, factory_state)
    candidate_count = len(candidate_runs)
    elite_count = (
        _count_items(elite_json, "elites")
        or _count_items(factory_elite, "elites")
        or int(factory_state.get("eliteCount") or 0)
        or sum(
            1
            for row in candidate_runs
            if str(row.get("status") or "") == "ELITE_SELECTED"
        )
    )
    graveyard_count = _count_items(factory_graveyard, "strategies") or int(factory_state.get("graveyardCount") or 0)
    lineage_nodes = max(
        _count_items(lineage_json, "nodes"),
        _count_items(factory_lineage, "nodes"),
        int(factory_state.get("lineageNodeCount") or 0),
        candidate_lineage_nodes,
    )
    lineage_edges = max(
        _count_items(lineage_json, "edges"),
        _count_items(factory_lineage, "edges"),
        int(factory_state.get("lineageEdgeCount") or 0),
        len(candidate_lineage_edges),
    )

    blocker_counts = _blocker_counts(candidate_runs, blocker_json)
    status_counts = Counter(str(row.get("status") or "UNKNOWN") for row in candidate_runs)
    stage_counts = Counter(str(row.get("promotionStage") or "UNKNOWN") for row in candidate_runs)
    strategy_counts = Counter(str(row.get("strategyFamily") or row.get("strategy") or "UNKNOWN") for row in candidate_runs)
    fitness_summary = _fitness_summary(candidate_runs)
    generation_summary = _generation_summary(candidate_runs)
    lineage_depth = _lineage_depth(lineage_json, factory_lineage, candidate_runs)
    elite_repeat = _elite_repeat_summary(candidate_runs)

    grade, status_code, blockers, recommendations = _grade_report(
        generation_count=len(generation_numbers),
        candidate_count=candidate_count,
        elite_count=elite_count,
        elite_repeat_count=elite_repeat["eliteRepeatCount"],
        graveyard_count=graveyard_count,
        lineage_nodes=lineage_nodes,
        lineage_edges=lineage_edges,
        factory_ledger_rows=len(factory_ledger),
    )

    report: dict[str, Any] = {
        "ok": True,
        "schema": SCHEMA_STABILITY_REPORT,
        "agentVersion": AGENT_VERSION,
        "generatedAt": utc_now_iso(),
        "status": status_code,
        "stabilityGrade": grade,
        "evidenceUsability": _evidence_usability(grade),
        "closureMode": _closure_mode(grade),
        "promotionAllowed": grade in {"STABLE", "PRODUCTION_READY"},
        "generationCount": len(generation_numbers),
        "generations": generation_numbers,
        "currentGeneration": max(generation_numbers) if generation_numbers else int(factory_state.get("currentGeneration") or 0),
        "candidateCount": candidate_count,
        "eliteCount": elite_count,
        "eliteGenerationCount": elite_repeat["eliteGenerationCount"],
        "eliteRepeatCount": elite_repeat["eliteRepeatCount"],
        "eliteRepeatEvidence": elite_repeat["eliteRepeatEvidence"],
        "graveyardCount": graveyard_count,
        "lineageNodeCount": lineage_nodes,
        "lineageEdgeCount": lineage_edges,
        "lineageDepth": lineage_depth,
        "factoryLedgerRows": len(factory_ledger),
        "fitnessCacheCount": _count_fitness_cache(fitness_cache),
        "statusCounts": dict(status_counts),
        "promotionStageCounts": dict(stage_counts),
        "strategyFamilyCounts": dict(strategy_counts),
        "blockerCounts": dict(blocker_counts),
        "fitnessSummary": fitness_summary,
        "generationSummary": generation_summary,
        "blockers": blockers,
        "recommendationsZh": recommendations,
        "safety": dict(SAFETY),
    }

    if write:
        write_json(report_path(runtime_dir), report)
        _append_ledger(runtime_dir, report)
    return report


def _candidate_runs(runtime_dir: Path, ga_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_archived_candidate_runs(runtime_dir))
    rows.extend(read_jsonl(ga_dir / "QuantGod_GACandidateRuns.jsonl", limit=20000))
    deduped: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        key = "|".join(
            str(row.get(name) or "")
            for name in ("generation", "seedId", "candidateId", "strategyId", "fitness", "status")
        )
        if not key.replace("|", ""):
            key = f"row-{index}"
        deduped[key] = row
    return list(deduped.values())


def _archived_candidate_runs(runtime_dir: Path) -> list[dict[str, Any]]:
    archive_dir = Path(runtime_dir) / "jsonl_archive"
    rows: list[dict[str, Any]] = []
    for path in sorted(archive_dir.glob("ga__QuantGod_GACandidateRuns.*.jsonl.gz")):
        try:
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(payload, dict):
                        rows.append(payload)
        except Exception:
            continue
    return rows


def read_report(runtime_dir: Path) -> dict[str, Any]:
    payload = read_json(report_path(Path(runtime_dir)), {}) or {}
    if payload:
        return {"ok": True, **payload}
    return build_report(Path(runtime_dir), write=False)


def _generation_numbers(
    status: dict[str, Any],
    latest_generation: dict[str, Any],
    generation_ledger: list[dict[str, Any]],
    candidate_runs: list[dict[str, Any]],
    factory_state: dict[str, Any],
) -> list[int]:
    values: set[int] = set()
    for payload in (status, latest_generation, factory_state):
        for key in ("currentGeneration", "generation", "generationNumber"):
            number = _to_int(payload.get(key))
            if number > 0:
                values.add(number)
    for row in generation_ledger + candidate_runs:
        number = _to_int(row.get("generation") or row.get("currentGeneration") or row.get("generationNumber"))
        if number > 0:
            values.add(number)
    return sorted(values)


def _count_items(payload: Any, key: str) -> int:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            return len(value)
    if isinstance(payload, list):
        return len(payload)
    return 0


def _blocker_counts(candidate_runs: list[dict[str, Any]], blocker_json: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in candidate_runs:
        code = str(row.get("blockerCode") or row.get("blocker") or "")
        if code:
            counts[code] += 1
    for key in ("blockers", "items", "counts"):
        value = blocker_json.get(key) if isinstance(blocker_json, dict) else None
        if isinstance(value, dict):
            for code, count in value.items():
                counts[str(code)] += _to_int(count)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    code = str(item.get("blockerCode") or item.get("code") or "UNKNOWN")
                    counts[code] += _to_int(item.get("count") or 1)
    return counts


def _fitness_summary(candidate_runs: list[dict[str, Any]]) -> dict[str, Any]:
    values = [_to_float(row.get("fitness"), None) for row in candidate_runs]
    values = [value for value in values if value is not None]
    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None, "best": None}
    best = max(candidate_runs, key=lambda row: _to_float(row.get("fitness"), -10**9) or -10**9)
    return {
        "count": len(values),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "avg": round(sum(values) / len(values), 6),
        "best": {
            "seedId": best.get("seedId"),
            "strategyId": best.get("strategyId"),
            "strategyFamily": best.get("strategyFamily"),
            "fitness": best.get("fitness"),
            "status": best.get("status"),
            "promotionStage": best.get("promotionStage"),
        },
    }


def _generation_summary(candidate_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_runs:
        generation = _to_int(row.get("generation"))
        if generation > 0:
            grouped[generation].append(row)
    rows: list[dict[str, Any]] = []
    for generation in sorted(grouped):
        candidates = grouped[generation]
        fitness_values = [_to_float(row.get("fitness"), None) for row in candidates]
        fitness_values = [value for value in fitness_values if value is not None]
        rows.append(
            {
                "generation": generation,
                "candidateCount": len(candidates),
                "eliteCount": sum(1 for row in candidates if str(row.get("status")) == "ELITE_SELECTED"),
                "rejectedCount": sum(1 for row in candidates if str(row.get("status")) in {"REJECTED", "SAFETY_REJECTED"}),
                "bestFitness": round(max(fitness_values), 6) if fitness_values else None,
                "avgFitness": round(sum(fitness_values) / len(fitness_values), 6) if fitness_values else None,
            }
        )
    return rows[-20:]


def _lineage_depth(lineage_json: dict[str, Any], factory_lineage: dict[str, Any], candidate_runs: list[dict[str, Any]]) -> int:
    edges = []
    for payload in (lineage_json, factory_lineage):
        if isinstance(payload.get("edges"), list):
            edges.extend(edge for edge in payload.get("edges", []) if isinstance(edge, dict))
    edges.extend(_candidate_lineage_edges(candidate_runs))
    if not edges:
        return 1 if candidate_runs else 0
    parents: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for edge in edges:
        source = str(edge.get("source") or edge.get("parent") or edge.get("from") or "")
        target = str(edge.get("target") or edge.get("child") or edge.get("to") or "")
        if source and target:
            parents[target].append(source)
            nodes.add(source)
            nodes.add(target)

    memo: dict[str, int] = {}

    def depth(node: str) -> int:
        if node in memo:
            return memo[node]
        if not parents.get(node):
            memo[node] = 1
        else:
            memo[node] = 1 + max(depth(parent) for parent in parents[node])
        return memo[node]

    return max((depth(node) for node in nodes), default=0)


def _candidate_lineage_edges(candidate_runs: list[dict[str, Any]]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for row in candidate_runs:
        seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
        seed_id = str(row.get("seedId") or seed.get("seedId") or "")
        if not seed_id:
            continue
        parent = str(seed.get("parentSeedId") or "")
        if parent:
            edges.append({"from": parent, "to": seed_id, "type": "MUTATION"})
        parent_ids = seed.get("parentSeedIds") if isinstance(seed.get("parentSeedIds"), list) else []
        for parent_id in parent_ids:
            parent_text = str(parent_id or "")
            if parent_text:
                edges.append({"from": parent_text, "to": seed_id, "type": "CROSSOVER"})
        case_id = str(seed.get("caseId") or "")
        if case_id:
            edges.append({"from": case_id, "to": seed_id, "type": "CASE_MEMORY"})
    return edges


def _candidate_lineage_node_count(candidate_runs: list[dict[str, Any]], edges: list[dict[str, str]]) -> int:
    nodes: set[str] = set()
    for row in candidate_runs:
        seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
        seed_id = str(row.get("seedId") or seed.get("seedId") or "")
        if seed_id:
            nodes.add(seed_id)
    for edge in edges:
        for key in ("from", "to"):
            value = str(edge.get(key) or "")
            if value:
                nodes.add(value)
    return len(nodes)


def _elite_repeat_summary(candidate_runs: list[dict[str, Any]]) -> dict[str, Any]:
    generations_by_key: dict[str, set[int]] = defaultdict(set)
    examples: dict[str, dict[str, Any]] = {}
    elite_generations: set[int] = set()
    for row in candidate_runs:
        if str(row.get("status") or "") != "ELITE_SELECTED":
            continue
        generation = _to_int(row.get("generation"))
        key = str(row.get("fingerprint") or row.get("strategyId") or row.get("seedId") or "")
        if not key or generation <= 0:
            continue
        generations_by_key[key].add(generation)
        elite_generations.add(generation)
        examples.setdefault(
            key,
            {
                "seedId": row.get("seedId"),
                "strategyId": row.get("strategyId"),
                "strategyFamily": row.get("strategyFamily"),
                "fingerprint": row.get("fingerprint"),
            },
        )
    repeat_rows = [
        {
            **examples.get(key, {}),
            "generations": sorted(generations),
            "repeatCount": len(generations),
        }
        for key, generations in generations_by_key.items()
        if len(generations) >= 2
    ]
    repeat_rows.sort(key=lambda row: (-int(row.get("repeatCount") or 0), str(row.get("strategyId") or "")))
    return {
        "eliteGenerationCount": len(elite_generations),
        "eliteRepeatCount": len(repeat_rows),
        "eliteRepeatEvidence": repeat_rows[:12],
    }


def _grade_report(
    *,
    generation_count: int,
    candidate_count: int,
    elite_count: int,
    elite_repeat_count: int,
    graveyard_count: int,
    lineage_nodes: int,
    lineage_edges: int,
    factory_ledger_rows: int,
) -> tuple[str, str, list[str], list[str]]:
    blockers: list[str] = []
    recommendations: list[str] = []

    if generation_count < 1:
        blockers.append("NO_GENERATION_EVIDENCE")
        recommendations.append("先运行 Strategy JSON GA generation，再构建 GA Factory 稳定性报告。")
        return "NO_GENERATIONS", "WARN", blockers, recommendations

    if generation_count < MIN_GENERATIONS_WATCH:
        blockers.append("SINGLE_GENERATION_ONLY")
        recommendations.append("至少运行 2 代 GA，确认候选、精英、墓园和 lineage 能跨代延续。")
        return "SINGLE_GENERATION", "WARN", blockers, recommendations

    if candidate_count < MIN_CANDIDATES_WATCH:
        blockers.append("INSUFFICIENT_CANDIDATES")
        recommendations.append("扩大 population 或吸收 Case Memory seed，至少产生 8 个候选。")
        return "INSUFFICIENT_CANDIDATES", "WARN", blockers, recommendations

    if generation_count < MIN_GENERATIONS_STABLE or candidate_count < MIN_CANDIDATES_STABLE:
        recommendations.append("已有多代证据，但仍需更多候选和代际记录，继续观察。")
        return "STABILITY_WATCH", "WARN", blockers, recommendations

    if elite_count < MIN_ELITE_STABLE:
        if (
            generation_count >= MIN_GENERATIONS_PRODUCTION_READY
            and candidate_count >= MIN_CANDIDATES_STABLE
            and graveyard_count >= MIN_GRAVEYARD_CLOSED
            and lineage_nodes >= MIN_LINEAGE_NODES_STABLE
            and lineage_edges >= MIN_LINEAGE_EDGES_STABLE
        ):
            recommendations.append(
                "GA 已完成多代负筛选闭环：当前没有可晋级 elite，保持禁止晋级并扩大下一轮搜索。"
            )
            return "NEGATIVE_SELECTION_CLOSED", "PASS", blockers, recommendations
        blockers.append("NO_ELITE_STABILITY")
        recommendations.append("暂无稳定 elite，继续扩大搜索并检查 fitness / blocker 分布。")
        return "NO_ELITE", "WARN", blockers, recommendations

    if elite_repeat_count < MIN_ELITE_REPEAT_STABLE:
        blockers.append("ELITE_REPEAT_INSUFFICIENT")
        recommendations.append("elite 尚未跨代重复出现，继续运行到 mutation / crossover 能复现强候选。")
        return "ELITE_REPEAT_WATCH", "WARN", blockers, recommendations

    if lineage_nodes < MIN_LINEAGE_NODES_STABLE or lineage_edges < MIN_LINEAGE_EDGES_STABLE:
        blockers.append("LINEAGE_INCOMPLETE")
        recommendations.append("lineage 节点或父子边不足，确认 mutation / crossover lineage 正常写入。")
        return "LINEAGE_WEAK", "WARN", blockers, recommendations

    if factory_ledger_rows < 2:
        recommendations.append("GA Factory 已具备稳定证据，但 ledger 行数较少，继续保留 24-72 小时观察。")
        return "STABLE", "PASS", blockers, recommendations

    if generation_count >= MIN_GENERATIONS_PRODUCTION_READY:
        recommendations.append("GA 多代稳定性已达到生产观察门槛，可进入 Case Memory / GA 深化。")
        return "PRODUCTION_READY", "PASS", blockers, recommendations

    recommendations.append("GA 多代稳定性已通过基础门槛，继续运行到 5 代以上以观察 alpha drift。")
    return "STABLE", "PASS", blockers, recommendations


def _evidence_usability(grade: str) -> str:
    if grade in {"STABLE", "PRODUCTION_READY"}:
        return "USABLE_FOR_GA_FACTORY_OBSERVATION"
    if grade == "NEGATIVE_SELECTION_CLOSED":
        return "USABLE_FOR_GA_NEGATIVE_SELECTION"
    if grade in {"STABILITY_WATCH", "NO_ELITE", "ELITE_REPEAT_WATCH", "LINEAGE_WEAK"}:
        return "WATCH_ONLY"
    return "NOT_USABLE"


def _closure_mode(grade: str) -> str:
    if grade == "NEGATIVE_SELECTION_CLOSED":
        return "NO_ELITE_NEGATIVE_SELECTION"
    if grade in {"STABLE", "PRODUCTION_READY"}:
        return "ELITE_STABILITY"
    return "WATCH"


def _append_ledger(runtime_dir: Path, report: dict[str, Any]) -> None:
    path = ledger_path(runtime_dir)
    existing = []
    if path.exists():
        existing = []
        try:
            import csv

            with path.open("r", encoding="utf-8", newline="") as handle:
                existing = [dict(row) for row in csv.DictReader(handle)]
        except Exception:
            existing = []
    row = {
        "generatedAt": report.get("generatedAt"),
        "status": report.get("status"),
        "stabilityGrade": report.get("stabilityGrade"),
        "closureMode": report.get("closureMode"),
        "promotionAllowed": report.get("promotionAllowed"),
        "generationCount": report.get("generationCount"),
        "candidateCount": report.get("candidateCount"),
        "eliteCount": report.get("eliteCount"),
        "eliteGenerationCount": report.get("eliteGenerationCount"),
        "eliteRepeatCount": report.get("eliteRepeatCount"),
        "graveyardCount": report.get("graveyardCount"),
        "lineageNodeCount": report.get("lineageNodeCount"),
        "lineageEdgeCount": report.get("lineageEdgeCount"),
        "lineageDepth": report.get("lineageDepth"),
    }
    rows = existing[-999:] + [row]
    write_csv_rows(
        path,
        rows,
        [
            "generatedAt",
            "status",
            "stabilityGrade",
            "closureMode",
            "promotionAllowed",
            "generationCount",
            "candidateCount",
            "eliteCount",
            "eliteGenerationCount",
            "eliteRepeatCount",
            "graveyardCount",
            "lineageNodeCount",
            "lineageEdgeCount",
            "lineageDepth",
        ],
    )


def _count_fitness_cache(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in ("items", "cache", "entries"):
            value = payload.get(key)
            if isinstance(value, dict):
                return len(value)
            if isinstance(value, list):
                return len(value)
        return len(payload)
    if isinstance(payload, list):
        return len(payload)
    return 0


def _to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any, fallback: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback
