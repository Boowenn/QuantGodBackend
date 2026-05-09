from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from strategy_ga.schema import CANDIDATE_RUNS_FILE, ELITE_FILE, ga_dir
    from strategy_json.fingerprint import strategy_fingerprint
    from strategy_json.normalizer import normalize_strategy_json
    from strategy_json.schema import FOCUS_SYMBOL, base_strategy_seed
    from strategy_json.validator import validate_strategy_json
except ModuleNotFoundError:  # pragma: no cover - package import path for unittest
    from tools.strategy_ga.schema import CANDIDATE_RUNS_FILE, ELITE_FILE, ga_dir
    from tools.strategy_json.fingerprint import strategy_fingerprint
    from tools.strategy_json.normalizer import normalize_strategy_json
    from tools.strategy_json.schema import FOCUS_SYMBOL, base_strategy_seed
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
    SAFETY_BOUNDARY,
    contract_dir,
    utc_now_iso,
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


def select_strategy_candidate(runtime_dir: Path) -> Dict[str, Any]:
    for row, validation in _valid_candidate_rows(runtime_dir):
        return {
            "source": "GA_CANDIDATE",
            "reasonZh": "选择最新 GA elite / shadow 候选作为 EA 只读评估契约。",
            "row": row,
            "validation": validation,
            "strategyJson": validation.get("normalized") or normalize_strategy_json(row.get("strategyJson") or {}),
        }
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
    rsi = ((strategy_json.get("indicators") or {}).get("rsi") or {})
    exit_plan = strategy_json.get("exit") if isinstance(strategy_json.get("exit"), dict) else {}
    risk = strategy_json.get("risk") if isinstance(strategy_json.get("risk"), dict) else {}
    entry = strategy_json.get("entry") if isinstance(strategy_json.get("entry"), dict) else {}
    return {
        "seedId": strategy_json.get("seedId"),
        "strategyId": strategy_json.get("strategyId"),
        "symbol": strategy_json.get("symbol"),
        "lane": strategy_json.get("lane"),
        "strategyFamily": strategy_json.get("strategyFamily"),
        "direction": strategy_json.get("direction"),
        "timeframes": strategy_json.get("timeframes") if isinstance(strategy_json.get("timeframes"), list) else [],
        "entryMode": entry.get("mode") or "OPPORTUNITY_ENTRY",
        "entryConditions": entry.get("conditions") if isinstance(entry.get("conditions"), list) else [],
        "rsi": {
            "period": int(float(rsi.get("period", 14))),
            "timeframe": rsi.get("timeframe") or "H1",
            "buyBand": float(rsi.get("buyBand", 34)),
            "crossbackThreshold": float(rsi.get("crossbackThreshold", 0.8)),
        },
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
        "lane": strategy.get("lane"),
        "entryMode": strategy.get("entryMode"),
        "timeframes": strategy.get("timeframes"),
        "rsiPeriod": rsi.get("period"),
        "rsiTimeframe": rsi.get("timeframe"),
        "rsiBuyBand": rsi.get("buyBand"),
        "rsiCrossbackThreshold": rsi.get("crossbackThreshold"),
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
    root_status = _load_json(runtime_dir / EA_STATUS_FILE)
    contract_status = _load_json(contract_dir(runtime_dir) / EA_STATUS_FILE)
    return root_status or contract_status


def build_strategy_contract(runtime_dir: Path, write: bool = True) -> Dict[str, Any]:
    selection = select_strategy_candidate(runtime_dir)
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


def read_strategy_contract_status(runtime_dir: Path) -> Dict[str, Any]:
    status = _load_json(runtime_dir / CONTRACT_STATUS_FILE) or _load_json(contract_dir(runtime_dir) / CONTRACT_STATUS_FILE)
    contract = _load_json(runtime_dir / CONTRACT_JSON_FILE) or _load_json(contract_dir(runtime_dir) / CONTRACT_JSON_FILE)
    ea_status = _read_ea_status(runtime_dir)
    if not status:
        return {
            "ok": True,
            "schema": "quantgod.strategy_json_ea_contract_status.v1",
            "agentVersion": AGENT_VERSION,
            "updatedAt": utc_now_iso(),
            "status": "WAITING_CONTRACT_BUILD",
            "contract": contract,
            "eaStatus": ea_status,
            "reasonZh": "等待 Agent 生成 Strategy JSON → EA 只读评估契约。",
            "safety": dict(SAFETY_BOUNDARY),
        }
    status = dict(status)
    status["contract"] = status.get("contract") or contract
    status["eaStatus"] = ea_status
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
