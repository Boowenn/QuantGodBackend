from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.usdjpy_strategy_lab.strategy_scoreboard import build_strategy_scoreboard
    from tools.usdjpy_strategy_lab.schema import DEFAULT_STRATEGIES, FOCUS_SYMBOL, utc_now_iso
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_strategy_lab.strategy_scoreboard import build_strategy_scoreboard
    from usdjpy_strategy_lab.schema import DEFAULT_STRATEGIES, FOCUS_SYMBOL, utc_now_iso

from .stage_machine import (
    STAGE_FAST_SHADOW,
    STAGE_PAUSED,
    STAGE_REJECTED,
    STAGE_SHADOW,
    STAGE_TESTER_ONLY,
    stage_label,
)


def _lane_stage(row: Dict[str, Any]) -> str:
    samples = int(row.get("sampleCount") or 0)
    win_rate = float(row.get("winRate") or 0.0)
    avg_r = float(row.get("avgR") or 0.0)
    profit_factor = float(row.get("profitFactor") or 0.0)
    loss_streak = int(row.get("lossStreak") or 0)
    status = str(row.get("status") or "").upper()
    if loss_streak >= 4 or avg_r < -0.25:
        return STAGE_PAUSED
    if samples >= 20 and win_rate >= 0.50 and avg_r > 0 and profit_factor > 1.02:
        return STAGE_TESTER_ONLY
    if samples >= 10 and avg_r > 0 and loss_streak <= 2:
        return STAGE_FAST_SHADOW
    if status in {"INSUFFICIENT_DATA", "REJECTED"} and samples <= 0:
        return STAGE_SHADOW
    if status == "PAUSED":
        return STAGE_PAUSED
    return STAGE_SHADOW if samples > 0 else STAGE_SHADOW


def _row_reason(row: Dict[str, Any], stage: str) -> str:
    reasons = row.get("reasons") if isinstance(row.get("reasons"), list) else []
    if reasons:
        return "；".join(str(item) for item in reasons[:2])
    if stage == STAGE_TESTER_ONLY:
        return "样本和收益质量达到测试器验证门槛。"
    if stage == STAGE_FAST_SHADOW:
        return "影子样本有正向表现，进入快速模拟强化。"
    if stage == STAGE_PAUSED:
        return "近期亏损或风险扩大，暂停该路线。"
    if stage == STAGE_REJECTED:
        return "证据不足或表现退化，暂不保留。"
    return "继续模拟观察，不进入实盘。"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _parity_gate(runtime_dir: Path) -> Dict[str, Any]:
    evidence = _load_json(runtime_dir / "evidence_os" / "QuantGod_USDJPYEvidenceOSStatus.json")
    parity = evidence.get("parity") if isinstance(evidence.get("parity"), dict) else {}
    if not parity:
        parity = _load_json(runtime_dir / "parity" / "QuantGod_StrategyParityReport.json")
    gate = parity.get("promotionGate") if isinstance(parity.get("promotionGate"), dict) else {}
    failed = str(parity.get("status") or "").upper() == "PARITY_FAIL" or gate.get("status") == "BLOCKED"
    return {
        "status": parity.get("status") or "MISSING",
        "promotionGateStatus": gate.get("status") or "MISSING",
        "parityFailBlocksShadow": failed,
        "reasonZh": parity.get("reasonZh") or gate.get("reasonZh") or "等待 Strategy / Replay / EA parity。",
    }


def _is_parity_scoped_route(row: Dict[str, Any]) -> bool:
    strategy = str(row.get("strategy") or "").upper()
    direction = str(row.get("direction") or "LONG").upper()
    return strategy == "RSI_REVERSAL" and direction == "LONG"


def build_mt5_shadow_lane(runtime_dir: Path, *, write: bool = False) -> Dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    scoreboard = build_strategy_scoreboard(runtime_dir, min_samples=5)
    parity_gate = _parity_gate(runtime_dir)
    routes: List[Dict[str, Any]] = []
    for row in scoreboard.get("routes") or []:
        if not isinstance(row, dict):
            continue
        stage = _lane_stage(row)
        reason = _row_reason(row, stage)
        if parity_gate["parityFailBlocksShadow"] and _is_parity_scoped_route(row):
            stage = STAGE_REJECTED
            reason = "P4-2 parity 失败：该 RSI LONG 策略禁止进入 Shadow/GA elite/Micro-live。"
        routes.append({
            "symbol": FOCUS_SYMBOL,
            "strategy": row.get("strategy"),
            "direction": row.get("direction"),
            "regime": row.get("regime"),
            "timeframe": row.get("timeframe"),
            "sampleCount": row.get("sampleCount", 0),
            "winRate": row.get("winRate", 0),
            "avgR": row.get("avgR", 0),
            "profitFactor": row.get("profitFactor", 0),
            "maxAdverseR": row.get("maeP70", 0),
            "mfeCaptureRate": row.get("mfeCaptureRate", 0),
            "lossStreak": row.get("lossStreak", 0),
            "score": row.get("score", 0),
            "promotionStage": stage,
            "promotionStageZh": stage_label(stage),
            "reasonZh": reason,
        })
    for strategy in DEFAULT_STRATEGIES:
        if not any(route.get("strategy") == strategy for route in routes):
            stage = STAGE_SHADOW
            reason = "策略池保留，等待模拟样本。"
            if parity_gate["parityFailBlocksShadow"] and str(strategy).upper() == "RSI_REVERSAL":
                stage = STAGE_REJECTED
                reason = "P4-2 parity 失败：该 RSI LONG 策略禁止进入 Shadow/GA elite/Micro-live。"
            routes.append({
                "symbol": FOCUS_SYMBOL,
                "strategy": strategy,
                "direction": "LONG",
                "sampleCount": 0,
                "winRate": 0,
                "avgR": 0,
                "profitFactor": 0,
                "maxAdverseR": 0,
                "mfeCaptureRate": 0,
                "lossStreak": 0,
                "score": 0,
                "promotionStage": stage,
                "promotionStageZh": stage_label(stage),
                "reasonZh": reason,
            })
    routes.sort(key=lambda item: (
        {"TESTER_ONLY": 0, "FAST_SHADOW": 1, "SHADOW": 2, "PAUSED": 3, "REJECTED": 4}.get(str(item.get("promotionStage")), 9),
        -float(item.get("score") or 0),
        str(item.get("strategy") or ""),
    ))
    counts: Dict[str, int] = {}
    for route in routes:
        stage = str(route.get("promotionStage"))
        counts[stage] = counts.get(stage, 0) + 1
    payload = {
        "ok": True,
        "schema": "quantgod.mt5_shadow_strategy_lane.v1",
        "generatedAtIso": utc_now_iso(),
        "lane": "MT5_SHADOW",
        "laneZh": "MT5 多策略模拟车道",
        "symbol": FOCUS_SYMBOL,
        "strategyPool": list(DEFAULT_STRATEGIES),
        "routes": routes,
        "summary": {
            "routeCount": len(routes),
            "testerOnly": counts.get(STAGE_TESTER_ONLY, 0),
            "fastShadow": counts.get(STAGE_FAST_SHADOW, 0),
            "shadow": counts.get(STAGE_SHADOW, 0),
            "paused": counts.get(STAGE_PAUSED, 0),
            "rejected": counts.get(STAGE_REJECTED, 0),
            "topShadowStrategy": routes[0].get("strategy") if routes else "",
            "topShadowStage": routes[0].get("promotionStage") if routes else "",
        },
        "parityGate": parity_gate,
        "safety": {
            "shadowOnly": True,
            "liveEligible": False,
            "orderSendAllowed": False,
            "livePresetMutationAllowed": False,
            "noteZh": "MT5 Shadow 第一名不等于实盘第一名；实盘仍只允许 USDJPYc / RSI_Reversal / LONG。",
        },
    }
    if write:
        out = runtime_dir / "agent"
        out.mkdir(parents=True, exist_ok=True)
        (out / "QuantGod_MT5ShadowStrategyRanking.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        ledger = out / "QuantGod_MT5ShadowStrategyLedger.csv"
        with ledger.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "generatedAtIso", "symbol", "strategy", "direction", "regime", "timeframe",
                "promotionStage", "sampleCount", "winRate", "avgR", "profitFactor", "score", "reasonZh",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for route in routes:
                writer.writerow({key: route.get(key, "") for key in fieldnames} | {"generatedAtIso": payload["generatedAtIso"]})
    return payload
