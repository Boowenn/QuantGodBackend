from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict


METADATA_KEYS = {
    "seedId",
    "strategyId",
    "source",
    "parentSeedId",
    "parentSeedIds",
    "caseId",
    "mutationHint",
    "explorationMode",
    "explorationReasonZh",
    "parentFitness",
    "qualityProfile",
    "repairReasonZh",
    "repairTargetBlocker",
    "createdAt",
    "generation",
    "generationId",
}


def _canonical_strategy_json(seed: Dict[str, Any]) -> str:
    """Return a stable representation for dedupe and lineage tracing."""
    data = _strip_metadata(seed)
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_text(value: str) -> str:
    """Hash text with the repository-wide SHA-256 convention."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def strategy_fingerprint(seed: Dict[str, Any]) -> str:
    """Build the Strategy JSON fingerprint used by GA duplicate checks."""
    canonical = _canonical_strategy_json(seed)
    return _sha256_text(canonical)


def _strip_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_metadata(item)
            for key, item in deepcopy(value).items()
            if key not in METADATA_KEYS
        }
    if isinstance(value, list):
        return [_strip_metadata(item) for item in value]
    return value
