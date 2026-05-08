from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from tools.strategy_json.fingerprint import strategy_fingerprint
    from tools.strategy_json.normalizer import normalize_strategy_json
    from tools.strategy_json.validator import validate_strategy_json
except ModuleNotFoundError:  # pragma: no cover
    from strategy_json.fingerprint import strategy_fingerprint
    from strategy_json.normalizer import normalize_strategy_json
    from strategy_json.validator import validate_strategy_json

from .blocker_explainer import explain_blocker
from .cache import cache_stats, evidence_signature, get_cached_score, put_cached_score
from .fitness import score_seed
from .frequency_limiter import check_run_allowed, record_run
from .lineage import build_lineage, read_lineage, write_lineage
from .population import build_population, elite_count, population_size
from .schema import (
    AGENT_VERSION,
    BLOCKER_FILE,
    ELITE_FILE,
    EVOLUTION_PATH_FILE,
    FITNESS_CACHE_FILE,
    LATEST_GENERATION_FILE,
    LINEAGE_FILE,
    RUN_LIMIT_FILE,
    SAFETY_BOUNDARY,
    STATUS_FILE,
    ga_dir,
    utc_now_iso,
)
from .trace_writer import write_trace


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _existing_elites(runtime_dir: Path) -> List[Dict[str, Any]]:
    data = _load_json(ga_dir(runtime_dir) / ELITE_FILE)
    rows = data.get("elites") if isinstance(data.get("elites"), list) else []
    return [row for row in rows if isinstance(row, dict)]


def _next_generation_number(runtime_dir: Path) -> int:
    latest = _load_json(ga_dir(runtime_dir) / LATEST_GENERATION_FILE)
    try:
        return int(latest.get("generation", 0)) + 1
    except Exception:
        return 1


def _candidate_status(rank: int, blocker: str | None, fitness: float) -> str:
    if blocker == "SAFETY_REJECTED":
        return "SAFETY_REJECTED"
    if blocker == "INSUFFICIENT_SAMPLES":
        return "NEEDS_MORE_DATA"
    if blocker:
        return "REJECTED"
    if rank <= elite_count():
        return "ELITE_SELECTED"
    if fitness > 0.5:
        return "PROMOTED_TO_SHADOW"
    return "NEEDS_MORE_DATA"


def _promotion_stage(status: str) -> str:
    if status == "ELITE_SELECTED":
        return "TESTER_ONLY"
    if status == "PROMOTED_TO_SHADOW":
        return "FAST_SHADOW"
    if status == "NEEDS_MORE_DATA":
        return "SHADOW"
    return "REJECTED"


def _read_status(runtime_dir: Path) -> Dict[str, Any]:
    status = _load_json(ga_dir(runtime_dir) / STATUS_FILE)
    if status:
        return status
    return {
        "schema": "quantgod.ga.status.v1",
        "agentVersion": AGENT_VERSION,
        "status": "WAITING_FIRST_GENERATION",
        "currentGeneration": 0,
        "populationSize": population_size(),
        "bestFitness": 0,
        "bestSeedId": None,
        "completedGenerations": 0,
        "blockedCandidates": 0,
        "eliteCount": 0,
        "nextAction": "运行第一代 Strategy JSON GA 评分",
        "singleSourceOfTruth": "USDJPY_STRATEGY_JSON_GA_TRACE",
        "safety": dict(SAFETY_BOUNDARY),
    }


def build_ga_status(runtime_dir: Path) -> Dict[str, Any]:
    root = ga_dir(runtime_dir)
    return {
        "ok": True,
        "status": _read_status(runtime_dir),
        "generation": _load_json(root / LATEST_GENERATION_FILE),
        "elites": _load_json(root / ELITE_FILE),
        "blockers": _load_json(root / BLOCKER_FILE),
        "evolutionPath": _load_json(root / EVOLUTION_PATH_FILE),
        "lineage": read_lineage(runtime_dir),
        "fitnessCache": _load_json(root / FITNESS_CACHE_FILE),
        "runLimiter": _load_json(root / RUN_LIMIT_FILE),
        "safety": dict(SAFETY_BOUNDARY),
    }


def _score_candidates(runtime_dir: Path, generation_number: int, generation_id: str, seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    runs: List[Dict[str, Any]] = []
    signature = evidence_signature(runtime_dir)
    for seed in seeds:
        normalized = normalize_strategy_json(seed)
        fingerprint = strategy_fingerprint(normalized)
        validation = validate_strategy_json(normalized)
        cache_hit = False
        blocker = None
        score = {
            "fitness": -99,
            "netR": 0,
            "maxAdverseR": 0,
            "profitCaptureRatio": 0,
            "missedOpportunityReduction": 0,
            "sampleCount": 0,
            "overfitPenalty": 0,
            "evidenceQuality": "LOW",
        }
        if fingerprint in seen:
            blocker = "DUPLICATE_STRATEGY"
        elif not validation.get("valid"):
            blocker = str(validation.get("blockerCode") or "SAFETY_REJECTED")
        else:
            cached = get_cached_score(runtime_dir, fingerprint, signature)
            if cached:
                score = cached
                cache_hit = True
            else:
                score = score_seed(normalized, runtime_dir)
                put_cached_score(runtime_dir, fingerprint, signature, score)
            blocker = score.get("blockerCode")
        seen.add(fingerprint)
        runs.append({
            "schema": "quantgod.ga.candidate_run.v1",
            "generation": generation_number,
            "generationId": generation_id,
            "seedId": normalized.get("seedId"),
            "strategyId": normalized.get("strategyId"),
            "strategyFamily": normalized.get("strategyFamily"),
            "direction": normalized.get("direction"),
            "source": normalized.get("source", "LLM_SEED"),
            "fingerprint": fingerprint,
            "strategyJson": normalized,
            "validation": validation,
            "fitnessBreakdown": score,
            "fitness": score["fitness"],
            "cacheHit": cache_hit,
            "evidenceSignature": signature,
            "blockerCode": blocker,
            "blockerZh": explain_blocker(blocker),
            "safety": dict(SAFETY_BOUNDARY),
        })
    ranked = sorted(runs, key=lambda row: float(row.get("fitness", -99)), reverse=True)
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        row["status"] = _candidate_status(index, row.get("blockerCode"), float(row.get("fitness", -99)))
        row["promotionStage"] = _promotion_stage(row["status"])
    return ranked


def _generation_cache_stats(runtime_dir: Path, candidates: List[Dict[str, Any]], signature: str) -> Dict[str, Any]:
    stats = cache_stats(runtime_dir, [str(row.get("fingerprint") or "") for row in candidates], signature)
    hits = sum(1 for row in candidates if row.get("cacheHit"))
    stats["hits"] = hits
    stats["misses"] = max(0, len(candidates) - hits)
    return stats


def _backtest_stats(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [
        row.get("fitnessBreakdown", {}).get("strategyBacktest")
        for row in candidates
        if isinstance(row.get("fitnessBreakdown"), dict)
    ]
    backtests = [row for row in rows if isinstance(row, dict)]
    scored = [row for row in backtests if row.get("present")]
    passed = [row for row in scored if row.get("ok")]
    trade_counts = [int(row.get("tradeCount") or 0) for row in scored]
    net_values = [float(row.get("netR") or 0.0) for row in scored]
    max_drawdowns = [float(row.get("maxDrawdownR") or 0.0) for row in scored]
    return {
        "required": True,
        "candidateCount": len(candidates),
        "scoredCount": len(scored),
        "passedCount": len(passed),
        "failedCount": max(0, len(candidates) - len(passed)),
        "avgTradeCount": round(sum(trade_counts) / max(1, len(trade_counts)), 2),
        "avgNetR": round(sum(net_values) / max(1, len(net_values)), 4),
        "maxDrawdownR": round(max(max_drawdowns, default=0.0), 4),
        "reasonZh": "每个 GA 候选必须先跑 USDJPY SQLite Strategy JSON 回测，结果进入 fitness。",
    }


def run_generation(runtime_dir: Path, write: bool = True, force: bool = False) -> Dict[str, Any]:
    limiter = check_run_allowed(runtime_dir, force=force)
    if not limiter.get("allowed"):
        status = build_ga_status(runtime_dir)
        status["ok"] = False
        status["skipped"] = True
        status["runLimiter"] = limiter
        return status
    generation_number = _next_generation_number(runtime_dir)
    generation_id = f"GA-USDJPY-GEN-{generation_number:04d}"
    seeds = build_population(generation_number, _existing_elites(runtime_dir), runtime_dir=runtime_dir)
    candidates = _score_candidates(runtime_dir, generation_number, generation_id, seeds)
    signature = evidence_signature(runtime_dir)
    backtest_stats = _backtest_stats(candidates)
    elites = [row for row in candidates if row.get("status") == "ELITE_SELECTED"][: elite_count()]
    blocker_counts = Counter(str(row.get("blockerCode") or "PASSED") for row in candidates)
    best = candidates[0] if candidates else {}
    generation = {
        "schema": "quantgod.ga.generation.v1",
        "agentVersion": AGENT_VERSION,
        "generation": generation_number,
        "generationId": generation_id,
        "parentGenerationId": f"GA-USDJPY-GEN-{generation_number - 1:04d}" if generation_number > 1 else None,
        "createdAt": utc_now_iso(),
        "populationSize": len(candidates),
        "eliteCount": len(elites),
        "mutationRate": 0.18,
        "crossoverRate": 0.35,
        "status": "COMPLETED_BY_AGENT",
        "bestFitness": best.get("fitness", 0),
        "bestSeedId": best.get("seedId"),
        "bestStrategy": best.get("strategyId"),
        "avgFitness": round(sum(float(row.get("fitness", 0)) for row in candidates) / max(1, len(candidates)), 4),
        "blockedCount": sum(1 for row in candidates if row.get("blockerCode")),
        "mutationCount": sum(1 for row in candidates if row.get("source") == "MUTATION"),
        "crossoverCount": sum(1 for row in candidates if row.get("source") == "CROSSOVER"),
        "caseMemorySeedCount": sum(1 for row in candidates if row.get("source") == "CASE_MEMORY"),
        "strategyBacktest": backtest_stats,
        "cache": _generation_cache_stats(runtime_dir, candidates, signature),
        "runLimiter": limiter,
        "safety": dict(SAFETY_BOUNDARY),
    }
    path = _load_json(ga_dir(runtime_dir) / EVOLUTION_PATH_FILE)
    generations = path.get("generations") if isinstance(path.get("generations"), list) else []
    generations.append({
        "generation": generation_number,
        "generationId": generation_id,
        "bestFitness": best.get("fitness", 0),
        "avgFitness": generation["avgFitness"],
        "bestStrategy": best.get("strategyId"),
        "blockedCount": generation["blockedCount"],
        "eliteCount": generation["eliteCount"],
    })
    evolution_path = {
        "schema": "quantgod.ga.evolution_path.v1",
        "agentVersion": AGENT_VERSION,
        "generations": generations[-50:],
        "safety": dict(SAFETY_BOUNDARY),
    }
    blockers = {
        "schema": "quantgod.ga.blockers.v1",
        "agentVersion": AGENT_VERSION,
        "summary": [{"blockerCode": code, "reasonZh": explain_blocker(code), "count": count} for code, count in blocker_counts.items()],
        "safety": dict(SAFETY_BOUNDARY),
    }
    status = {
        "schema": "quantgod.ga.status.v1",
        "agentVersion": AGENT_VERSION,
        "status": "COMPLETED_BY_AGENT",
        "currentGeneration": generation_number,
        "populationSize": len(candidates),
        "bestFitness": best.get("fitness", 0),
        "bestSeedId": best.get("seedId"),
        "completedGenerations": generation_number,
        "blockedCandidates": generation["blockedCount"],
        "eliteCount": len(elites),
        "nextAction": f"基于 {len(elites)} 个 elite 生成第 {generation_number + 1} 代候选",
        "singleSourceOfTruth": "USDJPY_STRATEGY_JSON_GA_TRACE",
        "strategyBacktestRequired": True,
        "safety": dict(SAFETY_BOUNDARY),
    }
    lineage = build_lineage(candidates)
    payload = {
        "ok": True,
        "status": status,
        "generation": generation,
        "candidates": candidates,
        "elites": {
            "schema": "quantgod.ga.elites.v1",
            "agentVersion": AGENT_VERSION,
            "elites": elites,
            "safety": dict(SAFETY_BOUNDARY),
        },
        "blockers": blockers,
        "evolutionPath": evolution_path,
        "lineage": lineage,
        "safety": dict(SAFETY_BOUNDARY),
    }
    if write:
        write_trace(runtime_dir, payload)
        write_lineage(runtime_dir, lineage)
        record_run(runtime_dir, generation_id)
    return payload


def read_generations(runtime_dir: Path) -> Dict[str, Any]:
    return _load_json(ga_dir(runtime_dir) / EVOLUTION_PATH_FILE) or {"ok": True, "generations": []}


def read_candidates(runtime_dir: Path) -> Dict[str, Any]:
    latest = _load_json(ga_dir(runtime_dir) / LATEST_GENERATION_FILE)
    candidate_file = ga_dir(runtime_dir) / "QuantGod_GACandidateRuns.jsonl"
    rows: List[Dict[str, Any]] = []
    if candidate_file.exists():
        for line in candidate_file.read_text(encoding="utf-8").splitlines()[-256:]:
            try:
                row = json.loads(line)
                if row.get("generation") == latest.get("generation"):
                    rows.append(row)
            except Exception:
                continue
    return {"ok": True, "candidates": rows, "generation": latest.get("generation"), "safety": dict(SAFETY_BOUNDARY)}


def read_candidate(runtime_dir: Path, seed_id: str) -> Dict[str, Any]:
    rows = read_candidates(runtime_dir).get("candidates", [])
    match = next((row for row in rows if str(row.get("seedId") or "") == seed_id), None)
    if not match:
        return {
            "ok": False,
            "candidate": None,
            "seedId": seed_id,
            "reasonZh": "没有找到该 GA seed；请先运行 GA 一代或刷新候选列表。",
            "safety": dict(SAFETY_BOUNDARY),
        }
    enriched = dict(match)
    lineage = _lineage_audit(runtime_dir, seed_id)
    lineage_tree = _lineage_tree_audit(runtime_dir, seed_id)
    enriched["audit"] = {
        "schema": "quantgod.ga.candidate_audit.v1",
        "agentVersion": AGENT_VERSION,
        "seedId": seed_id,
        "lineage": lineage,
        "lineageTree": lineage_tree,
        "lineagePath": _lineage_path_audit(seed_id, lineage_tree),
        "sourceTrace": _source_trace(match),
        "backtest": _candidate_backtest_audit(runtime_dir, match),
        "evidenceChain": _candidate_evidence_chain(match),
        "safety": dict(SAFETY_BOUNDARY),
    }
    return {"ok": True, "candidate": enriched, "safety": dict(SAFETY_BOUNDARY)}


def _candidate_rows_by_id(runtime_dir: Path) -> Dict[str, Dict[str, Any]]:
    candidate_file = ga_dir(runtime_dir) / "QuantGod_GACandidateRuns.jsonl"
    rows_by_id: Dict[str, Dict[str, Any]] = {}
    if not candidate_file.exists():
        return rows_by_id
    for line in candidate_file.read_text(encoding="utf-8").splitlines()[-4096:]:
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        seed_id = str(row.get("seedId") or "")
        if seed_id:
            if seed_id not in rows_by_id:
                rows_by_id[seed_id] = row
            else:
                rows_by_id[seed_id]["latestGeneration"] = row.get("generation")
                rows_by_id[seed_id]["latestGenerationId"] = row.get("generationId")
                rows_by_id[seed_id]["latestStatus"] = row.get("status")
                rows_by_id[seed_id]["latestPromotionStage"] = row.get("promotionStage")
                rows_by_id[seed_id]["latestFitness"] = row.get("fitness")
    return rows_by_id


def _lineage_audit(runtime_dir: Path, seed_id: str) -> Dict[str, Any]:
    lineage = read_lineage(runtime_dir)
    nodes = lineage.get("nodes") if isinstance(lineage.get("nodes"), list) else []
    edges = lineage.get("edges") if isinstance(lineage.get("edges"), list) else []
    nodes_by_id = {str(node.get("seedId")): node for node in nodes if isinstance(node, dict)}
    parent_edges = [edge for edge in edges if isinstance(edge, dict) and str(edge.get("to")) == seed_id]
    child_edges = [edge for edge in edges if isinstance(edge, dict) and str(edge.get("from")) == seed_id]
    parents = [_lineage_endpoint(edge, nodes_by_id, "from") for edge in parent_edges]
    children = [_lineage_endpoint(edge, nodes_by_id, "to") for edge in child_edges]
    return {
        "node": nodes_by_id.get(seed_id, {}),
        "parents": parents,
        "children": children,
        "parentCount": len(parents),
        "childCount": len(children),
        "reasonZh": _lineage_reason(parents),
    }


def _lineage_endpoint(edge: Dict[str, Any], nodes_by_id: Dict[str, Dict[str, Any]], key: str) -> Dict[str, Any]:
    endpoint = str(edge.get(key) or "")
    return {
        "seedId": endpoint,
        "type": edge.get("type"),
        "node": nodes_by_id.get(endpoint, {}),
    }


def _lineage_reason(parents: List[Dict[str, Any]]) -> str:
    if not parents:
        return "初始种子或归档导入，没有父代。"
    types = {str(item.get("type") or "") for item in parents}
    if "CROSSOVER" in types:
        return "该 seed 来自同策略族父代交叉。"
    if "MUTATION" in types:
        return "该 seed 来自父代参数变异。"
    if "CASE_MEMORY" in types:
        return "该 seed 来自 Case Memory 经验线索。"
    return "该 seed 存在父代 lineage 记录。"


def _lineage_tree_audit(runtime_dir: Path, seed_id: str) -> Dict[str, Any]:
    rows_by_id = _candidate_rows_by_id(runtime_dir)
    lineage = read_lineage(runtime_dir)
    latest_nodes = lineage.get("nodes") if isinstance(lineage.get("nodes"), list) else []
    latest_edges = lineage.get("edges") if isinstance(lineage.get("edges"), list) else []
    node_index = _lineage_node_index(rows_by_id, latest_nodes)
    edges = _lineage_edges(rows_by_id, latest_edges)
    parent_map: Dict[str, List[Dict[str, Any]]] = {}
    child_map: Dict[str, List[Dict[str, Any]]] = {}
    for edge in edges:
        parent_map.setdefault(str(edge.get("to") or ""), []).append(edge)
        child_map.setdefault(str(edge.get("from") or ""), []).append(edge)
    relative_depths: Dict[str, int] = {seed_id: 0}
    _collect_relative_lineage(seed_id, parent_map, relative_depths, -1, max_depth=6)
    _collect_relative_lineage(seed_id, child_map, relative_depths, 1, max_depth=4)
    elite_path_seed_ids = _elite_path_seed_ids(seed_id, parent_map, node_index, max_depth=8)
    for index, current_id in enumerate(elite_path_seed_ids):
        relative_depths.setdefault(current_id, index - (len(elite_path_seed_ids) - 1))
    visible_ids = set(relative_depths)
    visible_edges = [
        edge
        for edge in edges
        if str(edge.get("from") or "") in visible_ids and str(edge.get("to") or "") in visible_ids
    ]
    elite_path_edge_ids = {
        (parent, child)
        for parent, child in zip(elite_path_seed_ids, elite_path_seed_ids[1:])
    }
    for edge in visible_edges:
        edge["onElitePath"] = (str(edge.get("from") or ""), str(edge.get("to") or "")) in elite_path_edge_ids
    for edge in visible_edges:
        for endpoint in (str(edge.get("from") or ""), str(edge.get("to") or "")):
            if endpoint and endpoint not in node_index:
                node_index[endpoint] = _external_lineage_node(endpoint)
    visible_nodes = []
    for current_id in sorted(visible_ids, key=lambda item: (relative_depths.get(item, 0), item)):
        node = dict(node_index.get(current_id) or _external_lineage_node(current_id))
        node["relativeDepth"] = relative_depths.get(current_id, 0)
        node["selected"] = current_id == seed_id
        node["eliteSelected"] = str(node.get("status") or "").upper() == "ELITE_SELECTED"
        node["onElitePath"] = current_id in elite_path_seed_ids
        node["foldedByDefault"] = _lineage_folded_by_default(node)
        node["lineageRole"] = _lineage_role(node)
        visible_nodes.append(node)
    mutation_count = sum(1 for edge in visible_edges if edge.get("type") == "MUTATION")
    crossover_count = sum(1 for edge in visible_edges if edge.get("type") == "CROSSOVER")
    generations = [
        int(node.get("generation"))
        for node in visible_nodes
        if isinstance(node.get("generation"), int)
    ]
    return {
        "schema": "quantgod.ga.lineage_tree.v1",
        "agentVersion": AGENT_VERSION,
        "seedId": seed_id,
        "nodes": visible_nodes,
        "edges": visible_edges,
        "nodeCount": len(visible_nodes),
        "edgeCount": len(visible_edges),
        "ancestorCount": sum(1 for value in relative_depths.values() if value < 0),
        "descendantCount": sum(1 for value in relative_depths.values() if value > 0),
        "mutationCount": mutation_count,
        "crossoverCount": crossover_count,
        "elitePathSeedIds": elite_path_seed_ids,
        "elitePathCount": len(elite_path_seed_ids),
        "fold": {
            "mode": "COLLAPSE_REMOTE_BRANCHES",
            "defaultVisibleDepth": 2,
            "foldedNodeCount": sum(1 for node in visible_nodes if node.get("foldedByDefault")),
            "canExpand": any(node.get("foldedByDefault") for node in visible_nodes),
            "reasonZh": "默认折叠远端旁支；当前 seed 与 elite path 始终高亮显示。",
        },
        "generationSpan": {
            "from": min(generations) if generations else None,
            "to": max(generations) if generations else None,
        },
        "reasonZh": _lineage_tree_reason(visible_nodes, visible_edges),
    }


def _lineage_path_audit(seed_id: str, lineage_tree: Dict[str, Any]) -> Dict[str, Any]:
    nodes = lineage_tree.get("nodes") if isinstance(lineage_tree.get("nodes"), list) else []
    edges = lineage_tree.get("edges") if isinstance(lineage_tree.get("edges"), list) else []
    node_by_id = {
        str(node.get("seedId") or ""): node
        for node in nodes
        if isinstance(node, dict) and node.get("seedId")
    }
    path_ids = [
        str(item)
        for item in lineage_tree.get("elitePathSeedIds", [])
        if str(item or "")
    ]
    if not path_ids and seed_id:
        path_ids = [seed_id]
    edge_by_pair = {
        (str(edge.get("from") or ""), str(edge.get("to") or "")): edge
        for edge in edges
        if isinstance(edge, dict)
    }
    path_nodes: List[Dict[str, Any]] = []
    previous_fitness: Optional[float] = None
    previous_id: Optional[str] = None
    for index, current_id in enumerate(path_ids, start=1):
        node = node_by_id.get(current_id) or _external_lineage_node(current_id)
        fitness = _safe_float(node.get("fitness"))
        edge = edge_by_pair.get((previous_id or "", current_id), {}) if previous_id else {}
        path_node = {
            "order": index,
            "seedId": current_id,
            "generation": node.get("generation"),
            "generationId": node.get("generationId"),
            "strategyId": node.get("strategyId"),
            "strategyFamily": node.get("strategyFamily"),
            "source": node.get("source"),
            "status": node.get("status"),
            "promotionStage": node.get("promotionStage"),
            "fitness": fitness,
            "selected": current_id == seed_id,
            "onElitePath": True,
            "lineageEdgeType": edge.get("type") if edge else None,
            "lineageEdgeReasonZh": edge.get("reasonZh") if edge else None,
            "fitnessDeltaFromPrevious": (
                round(fitness - previous_fitness, 4)
                if fitness is not None and previous_fitness is not None
                else None
            ),
        }
        path_nodes.append(path_node)
        previous_id = current_id
        if fitness is not None:
            previous_fitness = fitness
    fitness_values = [
        node.get("fitness")
        for node in path_nodes
        if isinstance(node.get("fitness"), (int, float))
    ]
    generations = [
        int(node.get("generation"))
        for node in path_nodes
        if isinstance(node.get("generation"), int)
    ]
    start_fitness = fitness_values[0] if fitness_values else None
    end_fitness = fitness_values[-1] if fitness_values else None
    return {
        "schema": "quantgod.ga.lineage_path.v1",
        "agentVersion": AGENT_VERSION,
        "seedId": seed_id,
        "nodes": path_nodes,
        "nodeCount": len(path_nodes),
        "edgeCount": max(0, len(path_nodes) - 1),
        "generationCount": len(set(generations)),
        "generationSpan": {
            "from": min(generations) if generations else None,
            "to": max(generations) if generations else None,
        },
        "bestFitnessStart": start_fitness,
        "bestFitnessEnd": end_fitness,
        "fitnessDelta": (
            round(end_fitness - start_fitness, 4)
            if start_fitness is not None and end_fitness is not None
            else None
        ),
        "reasonZh": _lineage_path_reason(path_nodes),
    }


def _lineage_path_reason(path_nodes: List[Dict[str, Any]]) -> str:
    if len(path_nodes) <= 1:
        return "当前 seed 暂无跨代主血统；通常是第一代 seed、归档导入或尚未产生 mutation/crossover。"
    mutation_count = sum(1 for node in path_nodes if node.get("lineageEdgeType") == "MUTATION")
    crossover_count = sum(1 for node in path_nodes if node.get("lineageEdgeType") == "CROSSOVER")
    return f"已串联 {len(path_nodes)} 个主血统节点；mutation {mutation_count} 次，crossover {crossover_count} 次。"


def _lineage_node_index(rows_by_id: Dict[str, Dict[str, Any]], latest_nodes: List[Any]) -> Dict[str, Dict[str, Any]]:
    nodes: Dict[str, Dict[str, Any]] = {}
    for seed_id, row in rows_by_id.items():
        nodes[seed_id] = _lineage_node_from_candidate(seed_id, row)
    for node in latest_nodes:
        if not isinstance(node, dict):
            continue
        seed_id = str(node.get("seedId") or "")
        if not seed_id:
            continue
        merged = dict(nodes.get(seed_id) or {})
        merged.update(node)
        merged.setdefault("seedId", seed_id)
        merged.setdefault("external", False)
        nodes[seed_id] = merged
    return nodes


def _lineage_node_from_candidate(seed_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "seedId": seed_id,
        "strategyId": row.get("strategyId"),
        "strategyFamily": row.get("strategyFamily"),
        "direction": row.get("direction"),
        "source": row.get("source"),
        "generation": row.get("generation"),
        "generationId": row.get("generationId"),
        "fitness": row.get("fitness"),
        "rank": row.get("rank"),
        "status": row.get("status"),
        "promotionStage": row.get("promotionStage"),
        "latestGeneration": row.get("latestGeneration"),
        "latestGenerationId": row.get("latestGenerationId"),
        "latestStatus": row.get("latestStatus"),
        "latestPromotionStage": row.get("latestPromotionStage"),
        "latestFitness": row.get("latestFitness"),
        "blockerCode": row.get("blockerCode"),
        "blockerZh": row.get("blockerZh"),
        "external": False,
    }


def _external_lineage_node(seed_id: str) -> Dict[str, Any]:
    return {
        "seedId": seed_id,
        "strategyId": seed_id,
        "strategyFamily": "EXTERNAL",
        "source": "EXTERNAL",
        "status": "EXTERNAL_REFERENCE",
        "promotionStage": "REFERENCE",
        "external": True,
    }


def _elite_path_seed_ids(
    seed_id: str,
    parent_map: Dict[str, List[Dict[str, Any]]],
    node_index: Dict[str, Dict[str, Any]],
    max_depth: int,
) -> List[str]:
    """Return the preferred ancestor path ending at seed_id.

    The path prefers elite parents, then stronger ranked/fitness parents. It is
    deliberately deterministic so the frontend can highlight a stable main
    bloodline while still letting the user expand side branches.
    """
    path = [seed_id]
    current_id = seed_id
    visited = {seed_id}
    for _ in range(max_depth):
        candidates = [
            edge
            for edge in parent_map.get(current_id, [])
            if str(edge.get("from") or "") and str(edge.get("from") or "") not in visited
        ]
        if not candidates:
            break
        selected_edge = sorted(
            candidates,
            key=lambda edge: _elite_parent_sort_key(str(edge.get("from") or ""), node_index),
        )[0]
        parent_id = str(selected_edge.get("from") or "")
        if not parent_id:
            break
        path.append(parent_id)
        visited.add(parent_id)
        current_id = parent_id
    return list(reversed(path))


def _elite_parent_sort_key(seed_id: str, node_index: Dict[str, Dict[str, Any]]) -> tuple[Any, ...]:
    node = node_index.get(seed_id) or {}
    status = str(node.get("status") or "").upper()
    promotion_stage = str(node.get("promotionStage") or "").upper()
    elite_score = 0 if status == "ELITE_SELECTED" else 1
    stage_score = 0 if promotion_stage in {"FAST_SHADOW", "TESTER_ONLY", "PAPER_LIVE_SIM"} else 1
    rank = node.get("rank")
    rank_score = int(rank) if isinstance(rank, int) else 9999
    fitness = _safe_float(node.get("fitness"))
    fitness_score = -fitness if fitness is not None else 9999.0
    return (elite_score, stage_score, rank_score, fitness_score, seed_id)


def _safe_float(value: Any) -> Optional[float]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _lineage_folded_by_default(node: Dict[str, Any]) -> bool:
    if node.get("selected") or node.get("onElitePath") or node.get("eliteSelected"):
        return False
    try:
        depth = abs(int(node.get("relativeDepth") or 0))
    except (TypeError, ValueError):
        depth = 0
    return depth > 2


def _lineage_role(node: Dict[str, Any]) -> str:
    if node.get("selected"):
        return "SELECTED"
    if node.get("onElitePath"):
        return "ELITE_PATH"
    if node.get("eliteSelected"):
        return "ELITE"
    if node.get("external"):
        return "EXTERNAL"
    depth = int(node.get("relativeDepth") or 0)
    if depth < 0:
        return "ANCESTOR"
    if depth > 0:
        return "DESCENDANT"
    return "SIDE_BRANCH"


def _lineage_edges(rows_by_id: Dict[str, Dict[str, Any]], latest_edges: List[Any]) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    for row in rows_by_id.values():
        seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
        seed_id = str(row.get("seedId") or seed.get("seedId") or "")
        if not seed_id:
            continue
        parent = seed.get("parentSeedId")
        if parent:
            edges.append(_lineage_edge(str(parent), seed_id, "MUTATION", row))
        parent_ids = seed.get("parentSeedIds") if isinstance(seed.get("parentSeedIds"), list) else []
        for parent_id in parent_ids:
            if parent_id:
                edges.append(_lineage_edge(str(parent_id), seed_id, "CROSSOVER", row))
        case_id = seed.get("caseId")
        if case_id:
            edges.append(_lineage_edge(str(case_id), seed_id, "CASE_MEMORY", row))
    for edge in latest_edges:
        if isinstance(edge, dict) and edge.get("from") and edge.get("to"):
            edges.append({
                "from": str(edge.get("from")),
                "to": str(edge.get("to")),
                "type": edge.get("type") or "LINK",
                "reasonZh": _edge_reason(edge.get("type")),
            })
    deduped: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in edges:
        key = (str(edge.get("from")), str(edge.get("to")), str(edge.get("type")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    return deduped


def _lineage_edge(parent: str, child: str, edge_type: str, row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "from": parent,
        "to": child,
        "type": edge_type,
        "generation": row.get("generation"),
        "generationId": row.get("generationId"),
        "reasonZh": _edge_reason(edge_type),
    }


def _edge_reason(edge_type: Any) -> str:
    edge_text = str(edge_type or "LINK")
    if edge_text == "MUTATION":
        return "父代参数变异生成子代。"
    if edge_text == "CROSSOVER":
        return "同策略族父代交叉生成子代。"
    if edge_text == "CASE_MEMORY":
        return "Case Memory 经验线索生成候选。"
    return "GA lineage 关联。"


def _collect_relative_lineage(
    seed_id: str,
    edge_map: Dict[str, List[Dict[str, Any]]],
    relative_depths: Dict[str, int],
    direction: int,
    max_depth: int,
) -> None:
    frontier = [(seed_id, 0)]
    while frontier:
        current, depth = frontier.pop(0)
        if abs(depth) >= max_depth:
            continue
        for edge in edge_map.get(current, []):
            next_value = edge.get("from") if direction < 0 else edge.get("to")
            next_id = str(next_value or "")
            if not next_id:
                continue
            next_depth = depth + direction
            existing = relative_depths.get(next_id)
            if existing is not None and abs(existing) <= abs(next_depth):
                continue
            relative_depths[next_id] = next_depth
            frontier.append((next_id, next_depth))


def _lineage_tree_reason(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    if len(nodes) <= 1:
        return "该 seed 暂无可视化父子 lineage；通常是第一代 seed 或归档导入。"
    mutation_count = sum(1 for edge in edges if edge.get("type") == "MUTATION")
    crossover_count = sum(1 for edge in edges if edge.get("type") == "CROSSOVER")
    return f"已串联 {len(nodes)} 个 lineage 节点；mutation {mutation_count} 条，crossover {crossover_count} 条。"


def _source_trace(row: Dict[str, Any]) -> Dict[str, Any]:
    seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
    parent_ids = seed.get("parentSeedIds") if isinstance(seed.get("parentSeedIds"), list) else []
    if seed.get("parentSeedId"):
        parent_ids = [seed.get("parentSeedId"), *parent_ids]
    return {
        "source": row.get("source"),
        "parentSeedIds": [item for item in parent_ids if item],
        "caseId": seed.get("caseId"),
        "mutationHint": seed.get("mutationHint"),
        "strategyFamily": row.get("strategyFamily"),
        "direction": row.get("direction"),
        "reasonZh": _source_reason(row.get("source"), seed),
    }


def _source_reason(source: Any, seed: Dict[str, Any]) -> str:
    source_text = str(source or "LLM_SEED")
    if source_text == "MUTATION":
        return f"来自父代 {seed.get('parentSeedId') or 'unknown'} 的参数变异。"
    if source_text == "CROSSOVER":
        parents = ", ".join(str(item) for item in seed.get("parentSeedIds", []) if item)
        return f"来自同策略族父代交叉：{parents or 'unknown'}。"
    if source_text == "CASE_MEMORY":
        return f"来自 Case Memory：{seed.get('caseId') or 'unknown'}。"
    return "来自初始 Strategy JSON seed pool。"


def _candidate_backtest_audit(runtime_dir: Path, row: Dict[str, Any]) -> Dict[str, Any]:
    seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else None
    if not seed:
        return {"present": False, "ok": False, "reasonZh": "候选缺少 Strategy JSON，无法回测。"}
    try:
        try:
            from tools.usdjpy_strategy_backtest.report import run_backtest
        except ModuleNotFoundError:  # pragma: no cover
            from usdjpy_strategy_backtest.report import run_backtest

        report = run_backtest(runtime_dir, seed, write=False)
    except Exception as exc:  # pragma: no cover - defensive audit path
        return {"present": False, "ok": False, "reasonZh": f"候选回测审计生成失败：{exc}"}
    equity = report.get("equityCurve") if isinstance(report.get("equityCurve"), list) else []
    trades = report.get("trades") if isinstance(report.get("trades"), list) else []
    return {
        "present": True,
        "ok": bool(report.get("ok")),
        "runId": report.get("runId"),
        "strategyId": report.get("strategyId"),
        "seedId": report.get("seedId"),
        "metrics": report.get("metrics") if isinstance(report.get("metrics"), dict) else {},
        "evidenceQuality": report.get("evidenceQuality"),
        "equityCurve": _sample_equity_curve(equity),
        "equityPointCount": len(equity),
        "trades": trades[-20:],
        "tradeCount": len(trades),
        "engine": report.get("engine") if isinstance(report.get("engine"), dict) else {},
        "reasonZh": report.get("reasonZh") or "Strategy JSON 已生成候选专属回测审计。",
    }


def _sample_equity_curve(values: List[Any], limit: int = 160) -> List[Dict[str, Any]]:
    if not values:
        return []
    if len(values) <= limit:
        indexes = list(range(len(values)))
    else:
        step = (len(values) - 1) / max(1, limit - 1)
        indexes = sorted({round(index * step) for index in range(limit)})
    points: List[Dict[str, Any]] = []
    for index in indexes:
        try:
            value = float(values[index])
        except Exception:
            continue
        points.append({"index": index + 1, "equityR": round(value, 4)})
    return points


def _candidate_evidence_chain(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    validation = row.get("validation") if isinstance(row.get("validation"), dict) else {}
    fitness = row.get("fitnessBreakdown") if isinstance(row.get("fitnessBreakdown"), dict) else {}
    backtest = fitness.get("strategyBacktest") if isinstance(fitness.get("strategyBacktest"), dict) else {}
    parity = fitness.get("parity") if isinstance(fitness.get("parity"), dict) else {}
    execution = fitness.get("executionFeedback") if isinstance(fitness.get("executionFeedback"), dict) else {}
    blocker = row.get("blockerCode")
    return [
        {
            "step": "Strategy JSON 校验",
            "status": "PASS" if validation.get("valid") else "FAIL",
            "reasonZh": validation.get("reasonZh") or ("Strategy JSON 合法" if validation.get("valid") else "Strategy JSON 未通过校验"),
        },
        {
            "step": "USDJPY SQLite 回测",
            "status": "PASS" if backtest.get("ok") else "FAIL",
            "reasonZh": backtest.get("reasonZh") or ("回测已进入 fitness" if backtest.get("present") else "缺少回测证据"),
        },
        {
            "step": "三方 Parity",
            "status": parity.get("promotionGateStatus") or parity.get("status") or "WAITING",
            "reasonZh": parity.get("reasonZh") or "等待 Strategy JSON / Python Replay / MQL5 EA 三方一致性证据。",
        },
        {
            "step": "执行反馈",
            "status": execution.get("promotionGateStatus") or execution.get("fieldCompletenessStatus") or "WAITING",
            "reasonZh": execution.get("reasonZh") or "等待 LiveExecutionFeedback 字段契约和执行质量证据。",
        },
        {
            "step": "Fitness / 晋级",
            "status": row.get("status") or "UNKNOWN",
            "reasonZh": row.get("blockerZh") or explain_blocker(blocker) or "通过 fitness 排名，进入候选晋级路径。",
        },
    ]
