from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from .crossover import crossover_seed
from .mutation import mutate_seed
from .schema import CANDIDATE_RUNS_FILE, DEFAULT_ELITE_COUNT, DEFAULT_POPULATION_SIZE, ga_dir
from .seed_generator import (
    case_memory_seed_pool,
    exploration_seed_pool,
    initial_seed_pool,
    quality_repair_seed_pool,
)


def population_size() -> int:
    try:
        return max(4, min(64, int(os.environ.get("QG_GA_POPULATION_SIZE", DEFAULT_POPULATION_SIZE))))
    except Exception:
        return DEFAULT_POPULATION_SIZE


def elite_count() -> int:
    try:
        return max(1, min(8, int(os.environ.get("QG_GA_ELITE_COUNT", DEFAULT_ELITE_COUNT))))
    except Exception:
        return DEFAULT_ELITE_COUNT


def _recent_rejected_seeds(runtime_dir: Path | None, limit: int = 4) -> List[Dict[str, Any]]:
    if runtime_dir is None:
        return []
    candidate_file = ga_dir(runtime_dir) / CANDIDATE_RUNS_FILE
    if not candidate_file.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in candidate_file.read_text(encoding="utf-8").splitlines()[-256:]:
        try:
            row = json.loads(line)
        except Exception:
            continue
        seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
        if not seed:
            continue
        blocker = str(row.get("blockerCode") or "")
        if blocker in {"SAFETY_REJECTED", "DUPLICATE_STRATEGY", "HISTORY_PRODUCTION_NOT_READY"}:
            continue
        rows.append(row)
    rows.sort(key=lambda item: (int(item.get("rank") or 9999), -float(item.get("fitness") or -999)))
    seeds: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        seed = row.get("strategyJson")
        seed_id = str(seed.get("seedId") or "")
        if seed_id in seen:
            continue
        seen.add(seed_id)
        seeds.append(seed)
        if len(seeds) >= limit:
            break
    return seeds


def build_population(generation_number: int, previous_elites: List[Dict[str, Any]] | None = None, runtime_dir: Path | None = None) -> List[Dict[str, Any]]:
    size = population_size()
    case_seeds = case_memory_seed_pool(runtime_dir) if runtime_dir is not None else []
    if generation_number <= 1 or not previous_elites:
        if generation_number <= 1:
            return (case_seeds + initial_seed_pool(size))[:size]
        population: List[Dict[str, Any]] = []
        population.extend(case_seeds[: max(1, size // 4)])
        quality_seeds = (
            quality_repair_seed_pool(runtime_dir, generation_number, limit=max(2, size // 2))
            if runtime_dir is not None
            else []
        )
        population.extend(quality_seeds[: max(0, size - len(population))])
        offset = 1
        for parent in _recent_rejected_seeds(runtime_dir, limit=max(2, size // 4)):
            if len(population) >= size:
                break
            seed_id = f"GA-USDJPY-G{generation_number:04d}-RM{offset:04d}"
            mutated = mutate_seed(parent, seed_id, generation_number, offset)
            mutated["source"] = "EXPLORATION_MUTATION"
            mutated["explorationMode"] = "NO_ELITE_EXPAND_SEARCH"
            mutated["explorationReasonZh"] = "上一代没有 elite，基于最佳 rejected seed 做受控参数变异。"
            population.append(mutated)
            offset += 1
        population.extend(exploration_seed_pool(generation_number, max(0, size - len(population))))
        return population[:size]
    population: List[Dict[str, Any]] = []
    elites = [row.get("strategyJson") for row in previous_elites if isinstance(row.get("strategyJson"), dict)]
    population.extend(elites[: elite_count()])
    population.extend(case_seeds[: max(0, size - len(population))])
    offset = 1
    while len(population) < size and elites:
        parent = elites[(offset - 1) % len(elites)]
        seed_id = f"GA-USDJPY-G{generation_number:04d}-M{offset:04d}"
        population.append(mutate_seed(parent, seed_id, generation_number, offset))
        offset += 1
        if len(elites) > 1 and len(population) < size:
            left = elites[(offset - 2) % len(elites)]
            right = elites[(offset - 1) % len(elites)]
            crossed = crossover_seed(left, right, f"GA-USDJPY-G{generation_number:04d}-C{offset:04d}", generation_number, offset)
            if crossed:
                population.append(crossed)
            offset += 1
    if len(population) < size:
        population.extend(initial_seed_pool(size - len(population)))
    return population[:size]
