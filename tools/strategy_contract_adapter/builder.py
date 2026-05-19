from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from strategy_ga.schema import CANDIDATE_RUNS_FILE, ELITE_FILE, ga_dir
    from strategy_json.fingerprint import strategy_fingerprint
    from strategy_json.normalizer import normalize_strategy_json
    from strategy_json.schema import ALLOWED_STRATEGY_FAMILIES, FOCUS_SYMBOL, base_strategy_seed
    from strategy_json.validator import validate_strategy_json
except ModuleNotFoundError:  # pragma: no cover - package import path for unittest
    from tools.strategy_ga.schema import CANDIDATE_RUNS_FILE, ELITE_FILE, ga_dir
    from tools.strategy_json.fingerprint import strategy_fingerprint
    from tools.strategy_json.normalizer import normalize_strategy_json
    from tools.strategy_json.schema import ALLOWED_STRATEGY_FAMILIES, FOCUS_SYMBOL, base_strategy_seed
    from tools.strategy_json.validator import validate_strategy_json

from .schema import (
    AGENT_VERSION,
    ALLOWED_CONTRACT_MODES,
    CONTRACT_EA_FILE,
    CONTRACT_JSON_FILE,
    CONTRACT_MODE,
    CONTRACT_SCHEMA,
    CONTRACT_STATUS_FILE,
    EA_STATUS_FILE,
    EA_SHADOW_EVALUATION_LEDGER_FILE,
    EA_SHADOW_EVALUATION_STATUS_FILE,
    FROZEN_RSI_LINEAGE_FILE,
    RSI_SHADOW_OBSERVATION_REPORT_FILE,
    SAFETY_BOUNDARY,
    contract_dir,
    utc_now_iso,
)

MT5_FILES_ENV_KEYS = (
    "QG_MT5_FILES_DIR",
    "QG_MT5_FILES",
    "QG_HFM_FILES_DIR",
    "QG_HFM_FILES",
)

DEFAULT_MT5_FILES_PATH = (
    Path.home()
    / "Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5/MQL5/Files"
)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path, limit: int = 512) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    except Exception:
        return rows
    for line in lines:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _candidate_runtime_dirs(runtime_dir: Path) -> List[Path]:
    candidates: List[Path] = [runtime_dir, contract_dir(runtime_dir)]
    for key in MT5_FILES_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            candidates.append(Path(value).expanduser())
    candidates.append(DEFAULT_MT5_FILES_PATH)
    seen: set[str] = set()
    dirs: List[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        key = str(resolved)
        if key in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(key)
        dirs.append(resolved)
    return dirs


def _safe_str(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else fallback)
    return text.replace("\r", " ").replace("\n", " ").strip()


def _flatten_contract_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "|".join(_safe_str(item).replace(" ", "_") for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace(" ", "_")
    return _safe_str(value).replace(" ", "_")


def _candidate_priority(row: Dict[str, Any]) -> Tuple[int, float, str]:
    status = str(row.get("status") or "")
    stage = str(row.get("promotionStage") or "")
    source = str(row.get("source") or "")
    fitness = float(row.get("fitness") or 0.0)
    if status == "ELITE_SELECTED":
        bucket = 0
    elif stage in {"TESTER_ONLY", "PAPER_LIVE_SIM", "FAST_SHADOW"}:
        bucket = 1
    elif status in {"PROMOTED_TO_SHADOW", "NEEDS_MORE_DATA"}:
        bucket = 2
    elif source in {"MUTATION", "CROSSOVER", "CASE_MEMORY"}:
        bucket = 3
    else:
        bucket = 4
    return (bucket, -fitness, str(row.get("seedId") or ""))


def _candidate_strategy(row: Dict[str, Any]) -> Dict[str, Any] | None:
    seed = row.get("strategyJson")
    return seed if isinstance(seed, dict) else None


def _load_frozen_rsi_lineage(runtime_dir: Path) -> Dict[str, Any]:
    return _load_json(ga_dir(runtime_dir) / FROZEN_RSI_LINEAGE_FILE)


def _frozen_lineage_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    criteria = payload.get("criteria") if isinstance(payload.get("criteria"), dict) else {}
    lineage = payload.get("lineagePath") if isinstance(payload.get("lineagePath"), dict) else {}
    production = (
        payload.get("productionEvidenceAlignment")
        if isinstance(payload.get("productionEvidenceAlignment"), dict)
        else {}
    )
    replay = payload.get("replayAlignment") if isinstance(payload.get("replayAlignment"), dict) else {}
    return {
        "sourceFile": FROZEN_RSI_LINEAGE_FILE,
        "frozenAt": payload.get("frozenAt"),
        "selectedGeneration": payload.get("selectedGeneration"),
        "selectedProfile": payload.get("selectedProfile"),
        "selectedFingerprint": payload.get("selectedFingerprint"),
        "lineageDepth": lineage.get("lineageDepth"),
        "criteria": {
            "allPass": bool(criteria.get("allPass")),
            "sampleCount": criteria.get("sampleCount"),
            "tradeCount": criteria.get("tradeCount"),
            "netR": criteria.get("netR"),
            "validationNetR": criteria.get("validationNetR"),
            "forwardNetR": criteria.get("forwardNetR"),
            "maxAdverseR": criteria.get("maxAdverseR"),
            "walkForwardStatus": criteria.get("walkForwardStatus"),
        },
        "productionEvidenceAllPass": bool(production.get("allPass")),
        "replayAllPass": bool(replay.get("allPass")),
    }


def _frozen_rsi_selection(runtime_dir: Path) -> Dict[str, Any] | None:
    frozen = _load_frozen_rsi_lineage(runtime_dir)
    seed = frozen.get("strategyJson") if isinstance(frozen.get("strategyJson"), dict) else {}
    if not seed:
        return None
    validation = validate_strategy_json(seed)
    if not validation.get("valid"):
        return None
    criteria = frozen.get("criteria") if isinstance(frozen.get("criteria"), dict) else {}
    production = (
        frozen.get("productionEvidenceAlignment")
        if isinstance(frozen.get("productionEvidenceAlignment"), dict)
        else {}
    )
    replay = frozen.get("replayAlignment") if isinstance(frozen.get("replayAlignment"), dict) else {}
    normalized = validation.get("normalized") or normalize_strategy_json(seed)
    if (
        normalized.get("strategyFamily") != "RSI_Reversal"
        or normalized.get("direction") != "LONG"
        or not criteria.get("allPass")
        or not production.get("allPass")
        or not replay.get("allPass")
    ):
        return None
    row = {
        "seedId": normalized.get("seedId"),
        "strategyId": normalized.get("strategyId"),
        "strategyFamily": normalized.get("strategyFamily"),
        "direction": normalized.get("direction"),
        "source": "P4_10I_FROZEN_RSI_LINEAGE",
        "fingerprint": frozen.get("selectedFingerprint") or strategy_fingerprint(normalized),
        "status": "ELITE_SELECTED",
        "promotionStage": "TESTER_ONLY",
        "fitness": criteria.get("fitness"),
        "rank": criteria.get("rank"),
        "strategyJson": normalized,
    }
    selection = _selection_from_row(
        row,
        validation,
        source="P4_10J_FROZEN_RSI_SEED",
        reason_zh="按 P4-10I 冻结的 guarded RSI elite lineage 强制轮换到 EA 只读 shadow contract。",
    )
    selection["frozenLineage"] = _frozen_lineage_summary(frozen)
    return selection


def _valid_candidate_rows(runtime_dir: Path) -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    elites = _load_json(ga_dir(runtime_dir) / ELITE_FILE).get("elites")
    rows: List[Dict[str, Any]] = [row for row in elites if isinstance(row, dict)] if isinstance(elites, list) else []
    rows.extend(_read_jsonl(ga_dir(runtime_dir) / CANDIDATE_RUNS_FILE))
    rows = sorted(rows, key=_candidate_priority)
    seen: set[str] = set()
    for row in rows:
        seed_id = str(row.get("seedId") or "")
        if seed_id in seen:
            continue
        seen.add(seed_id)
        seed = _candidate_strategy(row)
        if not seed:
            continue
        validation = validate_strategy_json(seed)
        if validation.get("valid"):
            yield row, validation


def _selection_from_row(
    row: Dict[str, Any],
    validation: Dict[str, Any],
    *,
    source: str,
    reason_zh: str,
) -> Dict[str, Any]:
    return {
        "source": source,
        "reasonZh": reason_zh,
        "row": row,
        "validation": validation,
        "strategyJson": validation.get("normalized") or normalize_strategy_json(row.get("strategyJson") or {}),
    }


def select_strategy_candidate(
    runtime_dir: Path,
    *,
    forced_seed_id: str | None = None,
    forced_family: str | None = None,
    force_frozen_rsi: bool = False,
) -> Dict[str, Any]:
    forced_seed_id = _safe_str(forced_seed_id)
    forced_family = _safe_str(forced_family)
    candidates = list(_valid_candidate_rows(runtime_dir))
    if forced_seed_id:
        for row, validation in candidates:
            strategy_json = validation.get("normalized") or normalize_strategy_json(row.get("strategyJson") or {})
            if str(strategy_json.get("seedId") or row.get("seedId") or "") == forced_seed_id:
                return _selection_from_row(
                    row,
                    validation,
                    source="GA_CANDIDATE_FORCED_SEED",
                    reason_zh="按 seedId 轮换 Strategy JSON → EA 只读影子评估契约；不代表晋级或实盘授权。",
                )
        raise ValueError(f"Strategy JSON seed not found or invalid for shadow contract rotation: {forced_seed_id}")
    if force_frozen_rsi:
        selection = _frozen_rsi_selection(runtime_dir)
        if selection:
            return selection
        raise ValueError("Frozen RSI lineage is missing, invalid, or not closed for shadow contract rotation")
    if forced_family:
        if forced_family not in ALLOWED_STRATEGY_FAMILIES:
            raise ValueError(f"Strategy JSON family is not allowed for shadow contract rotation: {forced_family}")
        for row, validation in candidates:
            strategy_json = validation.get("normalized") or normalize_strategy_json(row.get("strategyJson") or {})
            if str(strategy_json.get("strategyFamily") or "") == forced_family:
                return _selection_from_row(
                    row,
                    validation,
                    source="GA_CANDIDATE_FORCED_FAMILY",
                    reason_zh=f"按策略族 {forced_family} 轮换 Strategy JSON → EA 只读影子评估契约；不代表晋级或实盘授权。",
                )
        raise ValueError(f"Strategy JSON family has no valid GA candidate for shadow contract rotation: {forced_family}")
    for row, validation in candidates:
        return _selection_from_row(
            row,
            validation,
            source="GA_CANDIDATE",
            reason_zh="选择最新 GA elite / shadow 候选作为 EA 只读评估契约。",
        )
    seed = base_strategy_seed("SAFE_BASE_USDJPY_RSI_LONG")
    validation = validate_strategy_json(seed)
    return {
        "source": "SAFE_BASE_SEED",
        "reasonZh": "未找到可用 GA 候选，生成安全 USDJPY RSI_Reversal LONG shadow 基准契约。",
        "row": {"seedId": seed.get("seedId"), "status": "SAFE_BASE_SEED", "promotionStage": "SHADOW"},
        "validation": validation,
        "strategyJson": validation.get("normalized") or normalize_strategy_json(seed),
    }


def _strategy_summary(strategy_json: Dict[str, Any]) -> Dict[str, Any]:
    indicators = strategy_json.get("indicators") if isinstance(strategy_json.get("indicators"), dict) else {}
    rsi = indicators.get("rsi") if isinstance(indicators.get("rsi"), dict) else {}
    exit_plan = strategy_json.get("exit") if isinstance(strategy_json.get("exit"), dict) else {}
    risk = strategy_json.get("risk") if isinstance(strategy_json.get("risk"), dict) else {}
    entry = strategy_json.get("entry") if isinstance(strategy_json.get("entry"), dict) else {}
    family_parameters = {
        "ma": indicators.get("ma") if isinstance(indicators.get("ma"), dict) else {},
        "bollinger": indicators.get("bollinger") if isinstance(indicators.get("bollinger"), dict) else {},
        "macd": indicators.get("macd") if isinstance(indicators.get("macd"), dict) else {},
        "supportResistance": indicators.get("supportResistance") if isinstance(indicators.get("supportResistance"), dict) else {},
        "tokyoRange": indicators.get("tokyoRange") if isinstance(indicators.get("tokyoRange"), dict) else {},
        "nightReversion": indicators.get("nightReversion") if isinstance(indicators.get("nightReversion"), dict) else {},
        "h4Pullback": indicators.get("h4Pullback") if isinstance(indicators.get("h4Pullback"), dict) else {},
    }
    return {
        "seedId": strategy_json.get("seedId"),
        "strategyId": strategy_json.get("strategyId"),
        "symbol": strategy_json.get("symbol"),
        "lane": strategy_json.get("lane"),
        "strategyFamily": strategy_json.get("strategyFamily"),
        "direction": strategy_json.get("direction"),
        "qualityProfile": strategy_json.get("qualityProfile"),
        "timeframes": strategy_json.get("timeframes") if isinstance(strategy_json.get("timeframes"), list) else [],
        "entryMode": entry.get("mode") or "OPPORTUNITY_ENTRY",
        "entryConditions": entry.get("conditions") if isinstance(entry.get("conditions"), list) else [],
        "rsi": {
            "period": int(float(rsi.get("period", 14))),
            "timeframe": rsi.get("timeframe") or "H1",
            "buyBand": float(rsi.get("buyBand", 34)),
            "crossbackThreshold": float(rsi.get("crossbackThreshold", 0.8)),
            "adverseExcursionGuard": (
                rsi.get("adverseExcursionGuard")
                if isinstance(rsi.get("adverseExcursionGuard"), dict)
                else {}
            ),
        },
        "familyParameters": family_parameters,
        "exit": {
            "breakevenDelayR": float(exit_plan.get("breakevenDelayR", 1.0)),
            "trailStartR": float(exit_plan.get("trailStartR", 1.5)),
            "mfeGivebackPct": float(exit_plan.get("mfeGivebackPct", 0.6)),
            "timeStopBars": exit_plan.get("timeStopBars") if isinstance(exit_plan.get("timeStopBars"), dict) else {},
        },
        "risk": {
            "stage": risk.get("stage") or "SHADOW",
            "maxLot": float(risk.get("maxLot", 2.0)),
            "opportunityLotMultiplier": float(risk.get("opportunityLotMultiplier", 0.35)),
        },
    }


def _build_ea_text(contract: Dict[str, Any]) -> str:
    strategy = contract["strategy"]
    rsi = strategy["rsi"]
    adverse_guard = rsi.get("adverseExcursionGuard") if isinstance(rsi.get("adverseExcursionGuard"), dict) else {}
    family_params = strategy.get("familyParameters") if isinstance(strategy.get("familyParameters"), dict) else {}
    ma = family_params.get("ma") if isinstance(family_params.get("ma"), dict) else {}
    bollinger = family_params.get("bollinger") if isinstance(family_params.get("bollinger"), dict) else {}
    macd = family_params.get("macd") if isinstance(family_params.get("macd"), dict) else {}
    support_resistance = (
        family_params.get("supportResistance") if isinstance(family_params.get("supportResistance"), dict) else {}
    )
    tokyo_range = family_params.get("tokyoRange") if isinstance(family_params.get("tokyoRange"), dict) else {}
    night_reversion = family_params.get("nightReversion") if isinstance(family_params.get("nightReversion"), dict) else {}
    h4_pullback = family_params.get("h4Pullback") if isinstance(family_params.get("h4Pullback"), dict) else {}
    exit_plan = strategy["exit"]
    risk = strategy["risk"]
    values = {
        "schema": contract["schema"],
        "agentVersion": contract["agentVersion"],
        "generatedAt": contract["generatedAt"],
        "contractMode": contract["contractMode"],
        "focusSymbol": contract["focusSymbol"],
        "fingerprint": contract["fingerprint"],
        "selectedSeedId": contract["selectedSeedId"],
        "strategyId": strategy.get("strategyId"),
        "strategyFamily": strategy.get("strategyFamily"),
        "direction": strategy.get("direction"),
        "qualityProfile": strategy.get("qualityProfile"),
        "lane": strategy.get("lane"),
        "entryMode": strategy.get("entryMode"),
        "timeframes": strategy.get("timeframes"),
        "rsiPeriod": rsi.get("period"),
        "rsiTimeframe": rsi.get("timeframe"),
        "rsiBuyBand": rsi.get("buyBand"),
        "rsiCrossbackThreshold": rsi.get("crossbackThreshold"),
        "rsiAdverseGuardMode": adverse_guard.get("mode"),
        "rsiAdverseGuardMaxEarlyAdverseR": adverse_guard.get("maxEarlyAdverseR"),
        "rsiAdverseGuardMaxEntryRangePips": adverse_guard.get("maxEntryRangePips"),
        "rsiAdverseGuardConfirmationBars": adverse_guard.get("confirmationBars"),
        "rsiAdverseGuardLookaheadBars": adverse_guard.get("lookaheadBars"),
        "rsiAdverseGuardMinConfirmR": adverse_guard.get("minConfirmR"),
        "rsiAdverseGuardRangeLookbackBars": adverse_guard.get("rangeLookbackBars"),
        "familyParameters": family_params,
        "maTimeframe": ma.get("timeframe"),
        "maFastPeriod": ma.get("fastPeriod"),
        "maSlowPeriod": ma.get("slowPeriod"),
        "bbTimeframe": bollinger.get("timeframe"),
        "bbPeriod": bollinger.get("period"),
        "bbDeviations": bollinger.get("deviations"),
        "bbReclaimBufferPips": bollinger.get("reclaimBufferPips"),
        "macdTimeframe": macd.get("timeframe"),
        "macdFastPeriod": macd.get("fastPeriod"),
        "macdSlowPeriod": macd.get("slowPeriod"),
        "macdSignalPeriod": macd.get("signalPeriod"),
        "macdMinHistogramAbs": macd.get("minHistogramAbs"),
        "srTimeframe": support_resistance.get("timeframe"),
        "srLookbackBars": support_resistance.get("lookbackBars"),
        "srBreakoutBufferPips": support_resistance.get("breakoutBufferPips"),
        "tokyoTimeframe": tokyo_range.get("timeframe"),
        "tokyoRangeStartHourUtc": tokyo_range.get("rangeStartHourUtc"),
        "tokyoRangeEndHourUtc": tokyo_range.get("rangeEndHourUtc"),
        "tokyoTradeStartHourUtc": tokyo_range.get("tradeStartHourUtc"),
        "tokyoTradeEndHourUtc": tokyo_range.get("tradeEndHourUtc"),
        "tokyoLookbackBars": tokyo_range.get("lookbackBars"),
        "tokyoBufferPips": tokyo_range.get("bufferPips"),
        "nightTimeframe": night_reversion.get("timeframe"),
        "nightStartHourUtc": night_reversion.get("startHourUtc"),
        "nightEndHourUtc": night_reversion.get("endHourUtc"),
        "nightBollingerPeriod": night_reversion.get("bollingerPeriod"),
        "nightDeviations": night_reversion.get("deviations"),
        "nightEntryBufferPips": night_reversion.get("entryBufferPips"),
        "h4Timeframe": h4_pullback.get("timeframe"),
        "h4FastEmaPeriod": h4_pullback.get("fastEmaPeriod"),
        "h4SlowEmaPeriod": h4_pullback.get("slowEmaPeriod"),
        "h4PullbackEmaPeriod": h4_pullback.get("pullbackEmaPeriod"),
        "h4RsiPeriod": h4_pullback.get("rsiPeriod"),
        "h4LongRsiMin": h4_pullback.get("longRsiMin"),
        "h4ShortRsiMax": h4_pullback.get("shortRsiMax"),
        "breakevenDelayR": exit_plan.get("breakevenDelayR"),
        "trailStartR": exit_plan.get("trailStartR"),
        "mfeGivebackPct": exit_plan.get("mfeGivebackPct"),
        "riskStage": risk.get("stage"),
        "maxLot": risk.get("maxLot"),
        "opportunityLotMultiplier": risk.get("opportunityLotMultiplier"),
        "orderSendAllowed": False,
        "livePresetMutationAllowed": False,
        "gaDirectLiveAllowed": False,
        "shadowOnly": True,
        "wouldAffectLive": False,
    }
    return "".join(f"{key}={_flatten_contract_value(value)}\n" for key, value in values.items())


def _read_ea_status(runtime_dir: Path) -> Dict[str, Any]:
    for directory in _candidate_runtime_dirs(runtime_dir):
        payload = _load_json(directory / EA_STATUS_FILE)
        if payload:
            return {**payload, "sourcePath": str(directory / EA_STATUS_FILE)}
    return {}


def _read_shadow_evaluation_status(runtime_dir: Path) -> Dict[str, Any]:
    primary_paths = [
        runtime_dir / EA_SHADOW_EVALUATION_STATUS_FILE,
        contract_dir(runtime_dir) / EA_SHADOW_EVALUATION_STATUS_FILE,
    ]
    for path in primary_paths:
        payload = _load_json(path)
        if payload:
            return {**payload, "sourcePath": str(path)}
    for directory in _candidate_runtime_dirs(runtime_dir):
        payload = _load_json(directory / EA_SHADOW_EVALUATION_STATUS_FILE)
        if payload:
            return {**payload, "sourcePath": str(directory / EA_SHADOW_EVALUATION_STATUS_FILE)}
    return {}


def _read_shadow_evaluation_ledger(runtime_dir: Path, limit: int = 20) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    primary_dirs = [runtime_dir, contract_dir(runtime_dir)]
    for directory in primary_dirs:
        path = directory / EA_SHADOW_EVALUATION_LEDGER_FILE
        for row in _read_jsonl(path, limit=limit):
            rows.append({**row, "sourcePath": str(path)})
    if rows:
        rows.sort(key=lambda item: str(item.get("generatedAtServer") or item.get("generatedAtLocal") or ""))
        return rows[-limit:]
    for directory in _candidate_runtime_dirs(runtime_dir):
        path = directory / EA_SHADOW_EVALUATION_LEDGER_FILE
        for row in _read_jsonl(path, limit=limit):
            rows.append({**row, "sourcePath": str(path)})
    rows.sort(key=lambda item: str(item.get("generatedAtServer") or item.get("generatedAtLocal") or ""))
    return rows[-limit:]


def build_strategy_contract(
    runtime_dir: Path,
    write: bool = True,
    *,
    forced_seed_id: str | None = None,
    forced_family: str | None = None,
    force_frozen_rsi: bool = False,
) -> Dict[str, Any]:
    selection = select_strategy_candidate(
        runtime_dir,
        forced_seed_id=forced_seed_id,
        forced_family=forced_family,
        force_frozen_rsi=force_frozen_rsi,
    )
    strategy_json = selection["strategyJson"]
    strategy = _strategy_summary(strategy_json)
    fingerprint = strategy_fingerprint(strategy_json)
    now = utc_now_iso()
    contract = {
        "ok": True,
        "schema": CONTRACT_SCHEMA,
        "agentVersion": AGENT_VERSION,
        "generatedAt": now,
        "singleSourceOfTruth": "STRATEGY_JSON_EA_CONTRACT_ADAPTER",
        "contractMode": CONTRACT_MODE,
        "allowedContractModes": sorted(ALLOWED_CONTRACT_MODES),
        "focusSymbol": FOCUS_SYMBOL,
        "selectedSeedId": strategy_json.get("seedId"),
        "selectionSource": selection["source"],
        "selectionReasonZh": selection["reasonZh"],
        "forcedSeedId": forced_seed_id or None,
        "forcedFamily": forced_family or None,
        "forceFrozenRsi": bool(force_frozen_rsi),
        "frozenRsiLineage": selection.get("frozenLineage") or {},
        "fingerprint": fingerprint,
        "strategy": strategy,
        "strategyJson": strategy_json,
        "validation": selection["validation"],
        "safety": dict(SAFETY_BOUNDARY),
        "ea": {
            "inputFile": CONTRACT_EA_FILE,
            "statusFile": EA_STATUS_FILE,
            "readOnlyAdapter": True,
            "shadowOnly": True,
            "reasonZh": "EA 只读 Strategy JSON contract，用于 shadow/tester/paper lane 评估；不会影响实盘下单权限。",
        },
    }
    status = {
        "ok": True,
        "schema": "quantgod.strategy_json_ea_contract_status.v1",
        "agentVersion": AGENT_VERSION,
        "updatedAt": now,
        "status": "CONTRACT_WRITTEN" if write else "CONTRACT_PREVIEW",
        "contract": contract,
        "eaStatus": _read_ea_status(runtime_dir),
        "eaShadowEvaluation": _read_shadow_evaluation_status(runtime_dir),
        "eaShadowEvaluationRecent": _read_shadow_evaluation_ledger(runtime_dir, limit=20),
        "safety": dict(SAFETY_BOUNDARY),
    }
    if write:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        contract_dir(runtime_dir).mkdir(parents=True, exist_ok=True)
        ea_text = _build_ea_text(contract)
        for base in (runtime_dir, contract_dir(runtime_dir)):
            _write_json(base / CONTRACT_JSON_FILE, contract)
            _write_json(base / CONTRACT_STATUS_FILE, status)
            (base / CONTRACT_EA_FILE).write_text(ea_text, encoding="utf-8")
    return status


def build_rsi_shadow_contract_observation(runtime_dir: Path, *, write: bool = True) -> Dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    frozen = _load_frozen_rsi_lineage(runtime_dir)
    frozen_seed_id = str(frozen.get("selectedSeedId") or "")
    frozen_fingerprint = str(frozen.get("selectedFingerprint") or "")
    contract_status = _load_json(runtime_dir / CONTRACT_STATUS_FILE) or _load_json(
        contract_dir(runtime_dir) / CONTRACT_STATUS_FILE
    )
    contract = contract_status.get("contract") if isinstance(contract_status.get("contract"), dict) else {}
    if not contract:
        contract = _load_json(runtime_dir / CONTRACT_JSON_FILE) or _load_json(contract_dir(runtime_dir) / CONTRACT_JSON_FILE)
    shadow_status = _read_shadow_evaluation_status(runtime_dir)
    rows = _read_shadow_evaluation_ledger(runtime_dir, limit=512)
    if shadow_status:
        rows.append(shadow_status)
    matching = [
        row
        for row in rows
        if _row_matches_frozen_seed(row, frozen_seed_id, frozen_fingerprint)
    ]
    latest = _latest_shadow_row(matching)
    contract_rotated = bool(frozen_seed_id) and str(contract.get("selectedSeedId") or "") == frozen_seed_id
    entry_quality = _entry_quality_summary(matching)
    adverse = _adverse_quality_summary(matching, frozen)
    blockers: List[Dict[str, Any]] = []
    if not frozen_seed_id:
        blockers.append({"code": "NO_FROZEN_RSI_LINEAGE", "reasonZh": "缺少 P4-10I frozen RSI lineage。"})
    if not contract_rotated:
        blockers.append({"code": "FROZEN_RSI_CONTRACT_NOT_ROTATED", "reasonZh": "EA contract 尚未轮换到 frozen RSI seed。"})
    if not matching:
        blockers.append({"code": "WAITING_FROZEN_RSI_SHADOW_LEDGER", "reasonZh": "等待 EA 写入 frozen RSI seed 的 shadow evaluation ledger。"})
    if entry_quality.get("status") == "FAIL":
        blockers.append({"code": "RSI_SHADOW_ENTRY_QUALITY_FAIL", "reasonZh": entry_quality.get("reasonZh")})
    if adverse.get("status") == "FAIL":
        blockers.append({"code": "RSI_SHADOW_ADVERSE_DEGRADED", "reasonZh": adverse.get("reasonZh")})
    status = "PASS"
    if blockers:
        hard_blockers = {"NO_FROZEN_RSI_LINEAGE", "FROZEN_RSI_CONTRACT_NOT_ROTATED", "RSI_SHADOW_ADVERSE_DEGRADED"}
        status = "WARN"
        if any(blocker.get("code") in hard_blockers for blocker in blockers):
            status = "WARN"
    elif entry_quality.get("status") == "WATCH" or adverse.get("status") == "WATCH":
        status = "WATCH"
    report = {
        "ok": True,
        "schema": "quantgod.rsi_shadow_contract_observation.v1",
        "generatedAt": utc_now_iso(),
        "status": status,
        "phase": "P4_10J_RSI_SHADOW_CONTRACT_OBSERVATION",
        "frozenSeedId": frozen_seed_id or None,
        "frozenFingerprint": frozen_fingerprint or None,
        "contractRotation": {
            "selectedSeedId": contract.get("selectedSeedId"),
            "selectionSource": contract.get("selectionSource"),
            "forceFrozenRsi": bool(contract.get("forceFrozenRsi")),
            "matchesFrozenSeed": contract_rotated,
            "contractMode": contract.get("contractMode"),
        },
        "shadowEvaluation": {
            "matchingRowCount": len(matching),
            "latest": _shadow_row_summary(latest),
            "statusCounts": dict(_status_counts(matching)),
            "sourceRowsInspected": len(rows),
        },
        "entryQuality": entry_quality,
        "adverseExcursion": adverse,
        "blockers": blockers,
        "recommendationsZh": _rsi_shadow_observation_recommendations(status, blockers),
        "safety": dict(SAFETY_BOUNDARY),
    }
    if write:
        _write_json(contract_dir(runtime_dir) / RSI_SHADOW_OBSERVATION_REPORT_FILE, report)
    return report


def _row_matches_frozen_seed(row: Dict[str, Any], seed_id: str, fingerprint: str) -> bool:
    if not isinstance(row, dict):
        return False
    if seed_id and str(row.get("selectedSeedId") or "") == seed_id:
        return True
    return bool(fingerprint and str(row.get("fingerprint") or "") == fingerprint)


def _latest_shadow_row(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    return sorted(rows, key=lambda item: str(item.get("generatedAtServer") or item.get("generatedAtLocal") or ""))[-1]


def _status_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _shadow_row_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    if not row:
        return {}
    adverse_guard = row.get("rsiAdverseGuard") if isinstance(row.get("rsiAdverseGuard"), dict) else {}
    return {
        "evaluationId": row.get("evaluationId"),
        "generatedAtLocal": row.get("generatedAtLocal"),
        "generatedAtServer": row.get("generatedAtServer"),
        "status": row.get("status"),
        "blocker": row.get("blocker"),
        "selectedSeedId": row.get("selectedSeedId"),
        "strategyFamily": row.get("strategyFamily"),
        "direction": row.get("direction"),
        "wouldEnter": bool(row.get("wouldEnter")),
        "hardGuardsPass": bool(row.get("hardGuardsPass")),
        "indicatorReady": bool(row.get("indicatorReady")),
        "rsiLongSignal": bool(row.get("rsiLongSignal")),
        "spreadPips": row.get("spreadPips"),
        "rsiClosed1": row.get("rsiClosed1"),
        "rsiClosed2": row.get("rsiClosed2"),
        "rsiAdverseGuard": adverse_guard,
        "reasonZh": row.get("reasonZh"),
    }


def _entry_quality_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"status": "WATCH", "reasonZh": "等待 frozen RSI seed 的 EA shadow evaluation 样本。"}
    would_enter = [row for row in rows if bool(row.get("wouldEnter")) or row.get("status") == "SHADOW_WOULD_ENTER"]
    hard_pass = sum(1 for row in rows if bool(row.get("hardGuardsPass")))
    indicator_ready = sum(1 for row in rows if bool(row.get("indicatorReady")))
    guard_blocked = sum(1 for row in rows if str(row.get("status") or "") == "SHADOW_GUARD_BLOCKED")
    if any(str(row.get("status") or "") in {"SAFETY_REJECTED", "MODE_REJECTED", "SYMBOL_REJECTED"} for row in rows):
        status = "FAIL"
        reason = "EA shadow evaluation 拒绝了 contract 安全边界。"
    elif would_enter and all(bool(row.get("hardGuardsPass")) for row in would_enter):
        status = "PASS"
        reason = "frozen RSI seed 已在 EA shadow ledger 里复现 would-enter，且硬守门通过。"
    elif guard_blocked:
        status = "WATCH"
        reason = "EA 已读取 frozen RSI seed，但当前 tick/spread/session/news 守门阻断。"
    else:
        status = "WATCH"
        reason = "EA 已读取 frozen RSI seed，当前 RSI 入场条件尚未触发；继续观察。"
    return {
        "status": status,
        "rowCount": len(rows),
        "wouldEnterCount": len(would_enter),
        "hardGuardsPassCount": hard_pass,
        "indicatorReadyCount": indicator_ready,
        "guardBlockedCount": guard_blocked,
        "reasonZh": reason,
    }


def _adverse_quality_summary(rows: List[Dict[str, Any]], frozen: Dict[str, Any]) -> Dict[str, Any]:
    criteria = frozen.get("criteria") if isinstance(frozen.get("criteria"), dict) else {}
    baseline_max_adverse = _safe_float(criteria.get("maxAdverseR"), None)
    observed_values = [_adverse_value(row) for row in rows]
    observed_values = [value for value in observed_values if value is not None]
    guard_loaded_count = sum(1 for row in rows if _rsi_adverse_guard_loaded(row))
    if observed_values:
        worst = min(observed_values)
        status = "PASS" if worst >= -1.15 else "FAIL"
        reason = "EA shadow adverse 样本仍在 P4-10H/P4-10I 低回撤阈值内。" if status == "PASS" else "EA shadow adverse 样本重新劣化。"
    elif rows and guard_loaded_count:
        worst = None
        status = "WATCH"
        reason = "EA 已加载 RSI adverse guard；等待 post-entry adverse/MAE 样本。"
    elif rows:
        worst = None
        status = "WATCH"
        reason = "EA 已写入 frozen seed ledger，但当前 EA build 尚未输出 adverse guard 字段。"
    else:
        worst = None
        status = "WATCH"
        reason = "等待 frozen RSI seed 的 shadow ledger 后再判断 adverse excursion。"
    return {
        "status": status,
        "baselineMaxAdverseR": baseline_max_adverse,
        "observedAdverseSampleCount": len(observed_values),
        "worstObservedAdverseR": worst,
        "guardLoadedCount": guard_loaded_count,
        "reasonZh": reason,
    }


def _adverse_value(row: Dict[str, Any]) -> float | None:
    for key in ("maxAdverseR", "maeR", "adverseR", "earlyAdverseR", "rsiAdverseR"):
        value = _safe_float(row.get(key), None)
        if value is not None:
            return value
    return None


def _rsi_adverse_guard_loaded(row: Dict[str, Any]) -> bool:
    guard = row.get("rsiAdverseGuard") if isinstance(row.get("rsiAdverseGuard"), dict) else {}
    return bool(guard.get("mode") or row.get("rsiAdverseGuardMode"))


def _safe_float(value: Any, fallback: float | None = 0.0) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _rsi_shadow_observation_recommendations(status: str, blockers: List[Dict[str, Any]]) -> List[str]:
    if status == "PASS":
        return ["继续让 EA shadow contract 收集 frozen RSI 入场/结果样本，暂不扩大 live scope。"]
    if blockers:
        return [str(blocker.get("reasonZh") or blocker.get("code")) for blocker in blockers]
    return ["继续观察 frozen RSI seed 的 EA shadow ledger。"]


def read_strategy_contract_status(runtime_dir: Path) -> Dict[str, Any]:
    status = _load_json(runtime_dir / CONTRACT_STATUS_FILE) or _load_json(contract_dir(runtime_dir) / CONTRACT_STATUS_FILE)
    contract = _load_json(runtime_dir / CONTRACT_JSON_FILE) or _load_json(contract_dir(runtime_dir) / CONTRACT_JSON_FILE)
    ea_status = _read_ea_status(runtime_dir)
    shadow_evaluation = _read_shadow_evaluation_status(runtime_dir)
    shadow_evaluation_recent = _read_shadow_evaluation_ledger(runtime_dir, limit=20)
    if not status:
        return {
            "ok": True,
            "schema": "quantgod.strategy_json_ea_contract_status.v1",
            "agentVersion": AGENT_VERSION,
            "updatedAt": utc_now_iso(),
            "status": "WAITING_CONTRACT_BUILD",
            "contract": contract,
            "eaStatus": ea_status,
            "eaShadowEvaluation": shadow_evaluation,
            "eaShadowEvaluationRecent": shadow_evaluation_recent,
            "reasonZh": "等待 Agent 生成 Strategy JSON → EA 只读评估契约。",
            "safety": dict(SAFETY_BOUNDARY),
        }
    status = dict(status)
    status["contract"] = status.get("contract") or contract
    status["eaStatus"] = ea_status
    status["eaShadowEvaluation"] = shadow_evaluation
    status["eaShadowEvaluationRecent"] = shadow_evaluation_recent
    status["safety"] = dict(SAFETY_BOUNDARY)
    if ea_status:
        status["eaAck"] = {
            "status": ea_status.get("status"),
            "loaded": ea_status.get("loaded"),
            "selectedSeedId": ea_status.get("selectedSeedId"),
            "fingerprint": ea_status.get("fingerprint"),
            "reasonZh": ea_status.get("reasonZh"),
        }
    return status
