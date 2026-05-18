from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .schema import FITNESS_CACHE_FILE, ga_dir, utc_now_iso


EVIDENCE_FILES = (
    "replay/usdjpy/QuantGod_USDJPYBarReplayReport.json",
    "replay/usdjpy/QuantGod_USDJPYWalkForwardReport.json",
    "backtest/QuantGod_StrategyBacktestReport.json",
    "backtest/QuantGod_StrategyBacktestQualityReport.json",
    "backtest/QuantGod_USDJPYHistoryProductionStatus.json",
    "backtest/QuantGod_USDJPYHistorySyncReport.json",
    "evidence_os/QuantGod_StrategyParityReport.json",
    "evidence_os/QuantGod_LiveExecutionQualityReport.json",
    "evidence_os/QuantGod_CaseMemorySummary.json",
)


def evidence_signature(runtime_dir: Path) -> str:
    digest = hashlib.sha256()
    for rel in EVIDENCE_FILES:
        path = runtime_dir / rel
        digest.update(rel.encode("utf-8"))
        if path.exists():
            stat = path.stat()
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
            digest.update(str(stat.st_size).encode("ascii"))
        else:
            digest.update(b"MISSING")
    return digest.hexdigest()[:24]


def get_cached_score(runtime_dir: Path, fingerprint: str, signature: str) -> Dict[str, Any] | None:
    cache = _load_cache(runtime_dir)
    row = (cache.get("scores") or {}).get(fingerprint)
    if isinstance(row, dict) and row.get("evidenceSignature") == signature:
        score = row.get("score")
        return score if isinstance(score, dict) else None
    return None


def put_cached_score(runtime_dir: Path, fingerprint: str, signature: str, score: Dict[str, Any]) -> None:
    cache = _load_cache(runtime_dir)
    scores = cache.setdefault("scores", {})
    scores[fingerprint] = {
        "fingerprint": fingerprint,
        "evidenceSignature": signature,
        "updatedAt": utc_now_iso(),
        "score": score,
    }
    _prune(scores)
    _write_cache(runtime_dir, cache)


def cache_stats(runtime_dir: Path, fingerprints: Iterable[str], signature: str) -> Dict[str, Any]:
    cache = _load_cache(runtime_dir)
    scores = cache.get("scores") if isinstance(cache.get("scores"), dict) else {}
    keys = list(fingerprints)
    hits = sum(1 for key in keys if isinstance(scores.get(key), dict) and scores[key].get("evidenceSignature") == signature)
    return {
        "entries": len(scores),
        "checked": len(keys),
        "hits": hits,
        "misses": max(0, len(keys) - hits),
        "evidenceSignature": signature,
    }


def _load_cache(runtime_dir: Path) -> Dict[str, Any]:
    path = ga_dir(runtime_dir) / FITNESS_CACHE_FILE
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"scores": {}}
    except Exception:
        pass
    return {"schema": "quantgod.ga.fitness_cache.v1", "scores": {}}


def _write_cache(runtime_dir: Path, payload: Dict[str, Any]) -> None:
    path = ga_dir(runtime_dir) / FITNESS_CACHE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prune(scores: Dict[str, Any], limit: int = 512) -> None:
    if len(scores) <= limit:
        return
    ordered = sorted(scores.items(), key=lambda item: str((item[1] or {}).get("updatedAt") or ""))
    for key, _ in ordered[: max(0, len(scores) - limit)]:
        scores.pop(key, None)
