from __future__ import annotations

import gzip
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import read_json, read_jsonl, write_json
from .schema import (
    OUTPUT_DIR,
    RSI_FROZEN_ELITE_LINEAGE,
    RSI_LINEAGE_CLOSURE_REPORT,
    SAFETY,
)

try:
    from tools.strategy_ga.schema import CANDIDATE_RUNS_FILE, ga_dir
except ModuleNotFoundError:  # pragma: no cover
    from strategy_ga.schema import CANDIDATE_RUNS_FILE, ga_dir


SCHEMA = "quantgod.rsi_lineage_closure.v1"
FOCUS_FAMILY = "RSI_Reversal"
FOCUS_DIRECTION = "LONG"
FOCUS_PROFILE = "RSI_REVERSAL_GUARDED_SAMPLE_RECOVERY"
GUARDED_PROFILES = {
    FOCUS_PROFILE,
    "RSI_REVERSAL_GUARDED_20_TRADE_BALANCER",
    "RSI_REVERSAL_GUARDED_MEDIUM_GUARD",
}
BLOCKING_CODES = {
    "RSI_MIN_TRADE_GATE",
    "OVERFIT_RISK",
    "WALK_FORWARD_UNSTABLE",
    "MAX_ADVERSE_TOO_HIGH",
}
MIN_SAMPLE_COUNT = 20
MIN_TRADE_COUNT = 20
MIN_RECENT_PROFILE_REPEAT = 3
MAX_ADVERSE_FLOOR_R = -1.15


def build_rsi_lineage_closure(
    runtime_dir: Path,
    *,
    production_sections: dict[str, Any] | None = None,
    write: bool = False,
) -> dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    rows = _candidate_runs(runtime_dir)
    selected = _select_candidate(rows)
    generated_at = _utc_now()
    production = _production_alignment(runtime_dir, production_sections)
    replay = _replay_alignment(runtime_dir, selected)
    repeat = _repeat_evidence(rows, selected)
    lineage_path = _lineage_path(rows, selected)
    criteria = _criteria_snapshot(selected)
    blockers = _blockers(criteria, repeat, production, replay, selected)
    status = "PASS" if not blockers else "WARN"
    shadow_promotion = _shadow_promotion(status, selected, production, replay)
    frozen = _frozen_lineage(generated_at, selected, lineage_path, criteria, production, replay)
    report = {
        "ok": True,
        "schema": SCHEMA,
        "generatedAt": generated_at,
        "status": status,
        "closureStage": (
            "P4_10I_RSI_STABILITY_LINEAGE_CLOSED"
            if status == "PASS"
            else "P4_10I_RSI_STABILITY_LINEAGE_WATCH"
        ),
        "selectedSeedId": selected.get("seedId") if selected else None,
        "selectedGeneration": selected.get("generation") if selected else None,
        "selectedFingerprint": selected.get("fingerprint") if selected else None,
        "selectedProfile": _quality_profile(selected),
        "criteria": criteria,
        "eliteRepeat": repeat,
        "lineagePath": lineage_path,
        "replayAlignment": replay,
        "productionEvidenceAlignment": production,
        "shadowPromotion": shadow_promotion,
        "blockers": blockers,
        "recommendationsZh": _recommendations(status, shadow_promotion, blockers),
        "frozenLineage": frozen,
        "safety": dict(SAFETY),
    }
    if write:
        write_rsi_lineage_closure(runtime_dir, report)
    return report


def load_latest_rsi_lineage_closure(runtime_dir: Path) -> dict[str, Any] | None:
    return read_json(Path(runtime_dir) / OUTPUT_DIR / RSI_LINEAGE_CLOSURE_REPORT, None)


def write_rsi_lineage_closure(runtime_dir: Path, report: dict[str, Any]) -> dict[str, str]:
    runtime_dir = Path(runtime_dir)
    paths = {
        "rsiLineageClosure": str(runtime_dir / OUTPUT_DIR / RSI_LINEAGE_CLOSURE_REPORT),
    }
    write_json(Path(paths["rsiLineageClosure"]), report)
    frozen = report.get("frozenLineage") if isinstance(report.get("frozenLineage"), dict) else {}
    if report.get("status") == "PASS" and frozen:
        latest = ga_dir(runtime_dir) / RSI_FROZEN_ELITE_LINEAGE
        write_json(latest, frozen)
        paths["rsiFrozenEliteLineage"] = str(latest)
    return paths


def _candidate_runs(runtime_dir: Path) -> list[dict[str, Any]]:
    rows = _archived_candidate_runs(runtime_dir)
    rows.extend(read_jsonl(ga_dir(runtime_dir) / CANDIDATE_RUNS_FILE, limit=30000))
    return [row for row in rows if isinstance(row, dict)]


def _archived_candidate_runs(runtime_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    archive_dir = Path(runtime_dir) / "jsonl_archive"
    for path in sorted(archive_dir.glob("ga__QuantGod_GACandidateRuns.*.jsonl.gz")):
        try:
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        import json

                        payload = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(payload, dict):
                        rows.append(payload)
        except Exception:
            continue
    return rows


def _select_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    qualified = [row for row in rows if _is_guarded_rsi_elite(row) and _criteria_snapshot(row)["allPass"]]
    if not qualified:
        candidates = [row for row in rows if _is_guarded_rsi_elite(row)]
        return sorted(candidates, key=_candidate_sort_key)[0] if candidates else None
    return sorted(qualified, key=_candidate_sort_key)[0]


def _candidate_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    generation = _to_int(row.get("generation"))
    rank = _to_int(row.get("rank")) or 9999
    fitness = _to_float(row.get("fitness"))
    profile_score = 0 if _quality_profile(row) == FOCUS_PROFILE else 1
    return (-generation, profile_score, rank, -fitness, str(row.get("seedId") or ""))


def _is_guarded_rsi_elite(row: dict[str, Any]) -> bool:
    return (
        str(row.get("strategyFamily") or "") == FOCUS_FAMILY
        and str(row.get("direction") or "") == FOCUS_DIRECTION
        and str(row.get("status") or "") == "ELITE_SELECTED"
        and _quality_profile(row) in GUARDED_PROFILES
    )


def _quality_profile(row: dict[str, Any] | None) -> str | None:
    if not isinstance(row, dict):
        return None
    seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
    return str(seed.get("qualityProfile") or "") or None


def _criteria_snapshot(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {
            "allPass": False,
            "reasonZh": "没有可冻结的 guarded RSI elite。",
        }
    fitness = row.get("fitnessBreakdown") if isinstance(row.get("fitnessBreakdown"), dict) else {}
    backtest = fitness.get("strategyBacktest") if isinstance(fitness.get("strategyBacktest"), dict) else {}
    walk_forward = fitness.get("walkForward") if isinstance(fitness.get("walkForward"), dict) else {}
    wf_summary = walk_forward.get("summary") if isinstance(walk_forward.get("summary"), dict) else {}
    blocker = str(row.get("blockerCode") or "")
    sample_count = _to_int(fitness.get("sampleCount"))
    trade_count = _to_int(backtest.get("tradeCount"))
    net_r = _to_float(fitness.get("netR"))
    validation_net_r = _to_float(wf_summary.get("validationNetR"))
    forward_net_r = _to_float(wf_summary.get("forwardNetR"))
    max_adverse_r = _to_float(fitness.get("maxAdverseR"))
    checks = {
        "profileGuarded": _quality_profile(row) in GUARDED_PROFILES,
        "sampleCountPass": sample_count >= MIN_SAMPLE_COUNT,
        "tradeCountPass": trade_count >= MIN_TRADE_COUNT,
        "netRPositive": net_r > 0,
        "walkForwardPass": str(wf_summary.get("promotionGateStatus") or "") == "PASS",
        "validationNetRPositive": validation_net_r > 0,
        "forwardNetRPositive": forward_net_r > 0,
        "maxAdverseControlled": max_adverse_r >= MAX_ADVERSE_FLOOR_R,
        "blockersClear": not blocker or blocker not in BLOCKING_CODES,
    }
    return {
        "allPass": all(checks.values()),
        "checks": checks,
        "seedId": row.get("seedId"),
        "generation": row.get("generation"),
        "rank": row.get("rank"),
        "fitness": row.get("fitness"),
        "profile": _quality_profile(row),
        "sampleCount": sample_count,
        "tradeCount": trade_count,
        "netR": round(net_r, 4),
        "validationNetR": round(validation_net_r, 4),
        "forwardNetR": round(forward_net_r, 4),
        "maxAdverseR": round(max_adverse_r, 4),
        "walkForwardStatus": wf_summary.get("promotionGateStatus"),
        "blockerCode": row.get("blockerCode"),
        "reasonZh": (
            "guarded RSI elite 满足 P4-10I 冻结门槛。"
            if all(checks.values())
            else "guarded RSI elite 仍未满足 P4-10I 全部门槛。"
        ),
    }


def _repeat_evidence(rows: list[dict[str, Any]], selected: dict[str, Any] | None) -> dict[str, Any]:
    latest_generation = max((_to_int(row.get("generation")) for row in rows), default=0)
    recent_floor = max(1, latest_generation - 4)
    profile_generations: set[int] = set()
    seed_generations: set[int] = set()
    fingerprint_generations: set[int] = set()
    profile_counts: Counter[str] = Counter()
    selected_seed_id = str(selected.get("seedId") or "") if selected else ""
    selected_fingerprint = str(selected.get("fingerprint") or "") if selected else ""
    for row in rows:
        if not _is_guarded_rsi_elite(row):
            continue
        generation = _to_int(row.get("generation"))
        if generation <= 0:
            continue
        profile = _quality_profile(row) or "UNKNOWN"
        profile_counts[profile] += 1
        if generation >= recent_floor:
            profile_generations.add(generation)
        if selected_seed_id and str(row.get("seedId") or "") == selected_seed_id:
            seed_generations.add(generation)
        if selected_fingerprint and str(row.get("fingerprint") or "") == selected_fingerprint:
            fingerprint_generations.add(generation)
    recent_profile_generations = sorted(profile_generations)
    return {
        "latestGeneration": latest_generation,
        "recentWindowFrom": recent_floor,
        "profile": _quality_profile(selected),
        "profileRepeatGenerations": recent_profile_generations,
        "profileRepeatCount": len(recent_profile_generations),
        "seedRepeatGenerations": sorted(seed_generations),
        "seedRepeatCount": len(seed_generations),
        "fingerprintRepeatGenerations": sorted(fingerprint_generations),
        "fingerprintRepeatCount": len(fingerprint_generations),
        "profileCounts": dict(profile_counts),
        "repeatPass": len(recent_profile_generations) >= MIN_RECENT_PROFILE_REPEAT,
        "reasonZh": (
            "同类 guarded RSI elite 已跨多个近期 generation 重复出现。"
            if len(recent_profile_generations) >= MIN_RECENT_PROFILE_REPEAT
            else "guarded RSI elite 重复代数不足，继续观察 lineage 稳定性。"
        ),
    }


def _lineage_path(rows: list[dict[str, Any]], selected: dict[str, Any] | None) -> dict[str, Any]:
    if not selected:
        return {"nodes": [], "edgeCount": 0, "nodeCount": 0, "reasonZh": "没有 selected seed。"}
    by_id = _rows_by_seed_id(rows)
    path_ids = [str(selected.get("seedId") or "")]
    visited = set(path_ids)
    current = selected
    edges: list[dict[str, Any]] = []
    for _ in range(12):
        parent_id, edge_type = _preferred_parent(current, by_id)
        if not parent_id or parent_id in visited:
            break
        edges.append({"from": parent_id, "to": str(current.get("seedId") or ""), "type": edge_type})
        path_ids.append(parent_id)
        visited.add(parent_id)
        current = by_id.get(parent_id, {})
    ordered_ids = list(reversed([seed_id for seed_id in path_ids if seed_id]))
    ordered_edges = list(reversed(edges))
    nodes = [_lineage_node_summary(by_id.get(seed_id, {}), seed_id, index + 1) for index, seed_id in enumerate(ordered_ids)]
    return {
        "schema": "quantgod.rsi_lineage_closure.path.v1",
        "seedId": selected.get("seedId"),
        "nodes": nodes,
        "edges": ordered_edges,
        "nodeCount": len(nodes),
        "edgeCount": len(ordered_edges),
        "lineageDepth": len(nodes),
        "generationSpan": {
            "from": min((node.get("generation") for node in nodes if node.get("generation")), default=None),
            "to": max((node.get("generation") for node in nodes if node.get("generation")), default=None),
        },
        "reasonZh": f"已冻结 guarded RSI 主 lineage，共 {len(nodes)} 个节点。",
    }


def _rows_by_seed_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        seed_id = str(row.get("seedId") or "")
        if not seed_id:
            continue
        current = result.get(seed_id)
        if current is None or _candidate_sort_key(row) < _candidate_sort_key(current):
            result[seed_id] = row
    return result


def _preferred_parent(row: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> tuple[str | None, str | None]:
    seed = row.get("strategyJson") if isinstance(row.get("strategyJson"), dict) else {}
    parent_ids: list[tuple[str, str]] = []
    if seed.get("parentSeedId"):
        parent_ids.append((str(seed.get("parentSeedId")), "MUTATION"))
    if isinstance(seed.get("parentSeedIds"), list):
        parent_ids.extend((str(item), "CROSSOVER") for item in seed.get("parentSeedIds") if item)
    if not parent_ids:
        return None, None
    parent_ids = sorted(parent_ids, key=lambda item: _parent_sort_key(by_id.get(item[0], {}), item[0]))
    return parent_ids[0]


def _parent_sort_key(row: dict[str, Any], seed_id: str) -> tuple[Any, ...]:
    status_score = 0 if str(row.get("status") or "") == "ELITE_SELECTED" else 1
    profile_score = 0 if _quality_profile(row) == FOCUS_PROFILE else 1
    rank = _to_int(row.get("rank")) or 9999
    fitness = _to_float(row.get("fitness"))
    return (status_score, profile_score, rank, -fitness, seed_id)


def _lineage_node_summary(row: dict[str, Any], seed_id: str, order: int) -> dict[str, Any]:
    criteria = _criteria_snapshot(row) if row else {}
    return {
        "order": order,
        "seedId": seed_id,
        "generation": row.get("generation"),
        "generationId": row.get("generationId"),
        "strategyId": row.get("strategyId"),
        "strategyFamily": row.get("strategyFamily"),
        "direction": row.get("direction"),
        "source": row.get("source"),
        "rank": row.get("rank"),
        "status": row.get("status"),
        "promotionStage": row.get("promotionStage"),
        "fitness": row.get("fitness"),
        "profile": _quality_profile(row),
        "sampleCount": criteria.get("sampleCount"),
        "tradeCount": criteria.get("tradeCount"),
        "netR": criteria.get("netR"),
        "validationNetR": criteria.get("validationNetR"),
        "forwardNetR": criteria.get("forwardNetR"),
        "maxAdverseR": criteria.get("maxAdverseR"),
        "blockerCode": row.get("blockerCode"),
    }


def _production_alignment(runtime_dir: Path, sections: dict[str, Any] | None) -> dict[str, Any]:
    if sections is None:
        latest = read_json(Path(runtime_dir) / OUTPUT_DIR / "QuantGod_ProductionEvidenceValidationReport.json", {}) or {}
        sections = {
            "overall": latest,
            "history": latest.get("historyProduction") if isinstance(latest, dict) else {},
            "parity": latest.get("strategyFamilyParity") if isinstance(latest, dict) else {},
            "executionFeedback": latest.get("liveExecutionFeedbackCoverage") if isinstance(latest, dict) else {},
            "ga": latest.get("gaMultiGenerationStability") if isinstance(latest, dict) else {},
        }
    statuses = {
        "overall": _status_of(sections.get("overall")),
        "history": _status_of(sections.get("history")),
        "parity": _status_of(sections.get("parity")),
        "executionFeedback": _status_of(sections.get("executionFeedback")),
        "ga": _status_of(sections.get("ga")),
    }
    all_pass = all(value == "PASS" for value in statuses.values() if value != "UNKNOWN")
    return {
        "statuses": statuses,
        "allPass": all_pass and "UNKNOWN" not in statuses.values(),
        "gaStabilityGrade": _safe_get(sections.get("ga"), "stabilityGrade"),
        "gaClosureMode": _safe_get(sections.get("ga"), "closureMode"),
        "productionEvidenceOnly": True,
        "reasonZh": "production evidence 全部 PASS，可支撑 shadow/tester 晋级评估。" if all_pass else "production evidence 尚未完全对齐。",
    }


def _replay_alignment(runtime_dir: Path, selected: dict[str, Any] | None) -> dict[str, Any]:
    bar_replay = read_json(Path(runtime_dir) / "replay/usdjpy/QuantGod_USDJPYBarReplayReport.json", {}) or {}
    summary = bar_replay.get("summary") if isinstance(bar_replay.get("summary"), dict) else {}
    causal = bar_replay.get("causalReplay") if isinstance(bar_replay.get("causalReplay"), dict) else {}
    criteria = _criteria_snapshot(selected)
    causal_pass = causal.get("posteriorMayAffectTrigger") is False
    bar_status = str(bar_replay.get("status") or "MISSING")
    wf_pass = criteria.get("walkForwardStatus") == "PASS"
    return {
        "barReplayStatus": bar_status,
        "barReplaySampleCount": summary.get("sampleCount"),
        "barReplayCurrentEntryCount": summary.get("currentEntryCount"),
        "causalInputsOnly": causal_pass,
        "posteriorUsedForScoringOnly": causal.get("posteriorUsedForScoringOnly"),
        "seedWalkForwardStatus": criteria.get("walkForwardStatus"),
        "validationNetR": criteria.get("validationNetR"),
        "forwardNetR": criteria.get("forwardNetR"),
        "allPass": causal_pass and wf_pass and criteria.get("validationNetR", 0) > 0 and criteria.get("forwardNetR", 0) > 0,
        "reasonZh": "bar replay 因果边界和 per-seed walk-forward 均可对齐。" if causal_pass and wf_pass else "replay 证据仍需补齐或复核。",
    }


def _blockers(
    criteria: dict[str, Any],
    repeat: dict[str, Any],
    production: dict[str, Any],
    replay: dict[str, Any],
    selected: dict[str, Any] | None,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if not selected:
        blockers.append({"code": "NO_GUARDED_RSI_ELITE", "reasonZh": "没有可冻结的 guarded RSI elite。"})
        return blockers
    if not criteria.get("allPass"):
        blockers.append({"code": "RSI_CRITERIA_NOT_CLOSED", "reasonZh": criteria.get("reasonZh", "")})
    if not repeat.get("repeatPass"):
        blockers.append({"code": "RSI_ELITE_REPEAT_INSUFFICIENT", "reasonZh": repeat.get("reasonZh", "")})
    if not replay.get("allPass"):
        blockers.append({"code": "RSI_REPLAY_ALIGNMENT_INCOMPLETE", "reasonZh": replay.get("reasonZh", "")})
    if not production.get("allPass"):
        blockers.append({"code": "PRODUCTION_EVIDENCE_NOT_ALIGNED", "reasonZh": production.get("reasonZh", "")})
    return blockers


def _shadow_promotion(
    status: str,
    selected: dict[str, Any] | None,
    production: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    allowed = status == "PASS" and bool(selected) and production.get("allPass") and replay.get("allPass")
    return {
        "decision": "READY_FOR_TESTER_ONLY_SHADOW_PROMOTION" if allowed else "KEEP_SHADOW_OBSERVATION",
        "promotionAllowed": allowed,
        "allowedStage": "TESTER_ONLY" if allowed else "SHADOW_OBSERVE",
        "selectedSeedId": selected.get("seedId") if selected else None,
        "directLiveAllowed": False,
        "orderSendAllowed": False,
        "livePresetMutationAllowed": False,
        "reasonZh": (
            "可进入 tester-only / MT5 shadow contract 轮换；仍不允许直接 live 或改实盘 preset。"
            if allowed
            else "先保持 shadow 观察，等待 P4-10I blockers 清零。"
        ),
    }


def _frozen_lineage(
    generated_at: str,
    selected: dict[str, Any] | None,
    lineage_path: dict[str, Any],
    criteria: dict[str, Any],
    production: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    if not selected:
        return {}
    seed = selected.get("strategyJson") if isinstance(selected.get("strategyJson"), dict) else {}
    return {
        "schema": "quantgod.rsi_frozen_elite_lineage.v1",
        "frozenAt": generated_at,
        "freezeReason": "P4-10I guarded RSI elite lineage closure",
        "selectedSeedId": selected.get("seedId"),
        "selectedGeneration": selected.get("generation"),
        "selectedFingerprint": selected.get("fingerprint"),
        "selectedProfile": _quality_profile(selected),
        "strategyJson": seed,
        "criteria": criteria,
        "lineagePath": lineage_path,
        "productionEvidenceAlignment": production,
        "replayAlignment": replay,
        "safety": dict(SAFETY),
    }


def _recommendations(status: str, shadow_promotion: dict[str, Any], blockers: list[dict[str, str]]) -> list[str]:
    if status == "PASS" and shadow_promotion.get("promotionAllowed"):
        return [
            "冻结该 guarded RSI elite lineage，并把 seed 作为 tester-only / MT5 shadow contract 候选复核。",
            "下一轮不要扩大搜索，重点观察 shadow contract 是否复现同类入场和低 adverse excursion。",
        ]
    if blockers:
        return [str(blocker.get("reasonZh") or blocker.get("code")) for blocker in blockers]
    return ["继续观察 P4-10I lineage closure。"]


def _status_of(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("status") or "UNKNOWN").upper()
    return "UNKNOWN"


def _safe_get(payload: Any, key: str) -> Any:
    return payload.get(key) if isinstance(payload, dict) else None


def _to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
