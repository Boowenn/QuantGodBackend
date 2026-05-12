from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.strategy_ga.seed_generator import case_memory_seed_pool
    from tools.strategy_json.normalizer import normalize_strategy_json
    from tools.strategy_json.validator import validate_strategy_json
except ModuleNotFoundError:  # pragma: no cover
    from strategy_ga.seed_generator import case_memory_seed_pool
    from strategy_json.normalizer import normalize_strategy_json
    from strategy_json.validator import validate_strategy_json

from .io_utils import load_json, utc_now_iso
from .schema import FOCUS_SYMBOL, SAFETY, SCHEMA_CANDIDATE


def build_strategy_candidates(runtime_dir: Path, *, limit: int = 8) -> Dict[str, Any]:
    parity_gate = _parity_gate(runtime_dir)
    if parity_gate["blocked"]:
        return {
            "status": "BLOCKED_BY_PARITY",
            "candidates": [],
            "gaSeeds": [],
            "parityGate": parity_gate,
            "reasonZh": "PARITY_FAIL 阻断 Strategy JSON candidate 生成；先修一致性再进入 GA。",
        }

    seeds = case_memory_seed_pool(Path(runtime_dir), limit=limit)
    candidates: List[Dict[str, Any]] = []
    ga_seeds: List[Dict[str, Any]] = []
    for index, seed in enumerate(seeds, start=1):
        candidate = _candidate_from_seed(index, seed)
        candidates.append(candidate)
        if candidate["validation"].get("valid"):
            ga_seeds.append(candidate["strategyJson"])
    return {
        "status": "READY" if candidates else "WAITING_CASE_MEMORY",
        "candidates": candidates,
        "gaSeeds": ga_seeds,
        "parityGate": parity_gate,
        "reasonZh": (
            f"已把 {len(ga_seeds)} 条 Case Memory 转成 shadow Strategy JSON candidate。"
            if candidates
            else "等待 Case Memory 产生 queued GA seed hint。"
        ),
    }


def _candidate_from_seed(index: int, seed: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_strategy_json(seed)
    validation = validate_strategy_json(normalized)
    case_id = str(seed.get("caseId") or "")
    mutation_hint = str(seed.get("mutationHint") or "case_memory_observe")
    digest = hashlib.sha256(
        f"{case_id}|{mutation_hint}|{normalized.get('strategyId')}".encode("utf-8", errors="ignore")
    ).hexdigest()[:16]
    return {
        "schema": SCHEMA_CANDIDATE,
        "candidateId": f"USDJPY-CASE-CANDIDATE-{index:03d}-{digest}",
        "createdAt": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "caseId": case_id,
        "caseType": seed.get("caseType"),
        "priority": seed.get("casePriority") or "MEDIUM",
        "rootCause": seed.get("caseReasonZh") or "Case Memory generated a strategy mutation.",
        "proposedMutation": mutation_hint,
        "recommendedLane": "MT5_SHADOW",
        "status": "SHADOW_STRATEGY_JSON_CANDIDATE" if validation.get("valid") else "REJECTED",
        "validation": validation,
        "strategyJson": validation.get("normalized") if validation.get("valid") else normalized,
        "gaSeed": validation.get("valid"),
        "safety": dict(SAFETY),
    }


def _parity_gate(runtime_dir: Path) -> Dict[str, Any]:
    evidence = load_json(Path(runtime_dir) / "evidence_os" / "QuantGod_USDJPYEvidenceOSStatus.json")
    parity = evidence.get("parity") if isinstance(evidence.get("parity"), dict) else {}
    if not parity:
        parity = load_json(Path(runtime_dir) / "parity" / "QuantGod_StrategyParityReport.json")
    gate = parity.get("promotionGate") if isinstance(parity.get("promotionGate"), dict) else {}
    status = str(parity.get("status") or "MISSING").upper()
    gate_status = str(gate.get("status") or "MISSING").upper()
    blocked = status == "PARITY_FAIL" or gate_status == "BLOCKED"
    return {
        "status": status,
        "promotionGateStatus": gate_status,
        "blocked": blocked,
        "reasonZh": parity.get("reasonZh") or gate.get("reasonZh") or "等待 P4-2 parity 证据。",
    }
