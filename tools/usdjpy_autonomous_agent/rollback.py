from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.usdjpy_strategy_lab.data_loader import fastlane_quality, focus_runtime_snapshot, read_all_csv, to_float
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_strategy_lab.data_loader import fastlane_quality, focus_runtime_snapshot, read_all_csv, to_float

from .schema import FOCUS_SYMBOL, utc_now_iso


FAST_STATES = {"FAST", "EA_DASHBOARD_OK", "OK", "PASS", "PASSED", "GOOD", "HEALTHY"}


def _recent_losses(runtime_dir: Path) -> Dict[str, Any]:
    rows = read_all_csv(runtime_dir, "QuantGod_CloseHistory.csv", "QuantGod_CloseHistoryLedger.csv", "QuantGod_MT5CloseHistory.csv")
    usdjpy = [row for row in rows if "USDJPY" in " ".join(str(value) for value in row.values()).upper()]
    losses = 0
    daily_loss_r = 0.0
    for row in reversed(usdjpy[-20:]):
        profit_r = to_float(row.get("profitR") or row.get("rMultiple") or row.get("r") or row.get("signedR"), None)
        profit_usc = to_float(row.get("profitUSC") or row.get("profit") or row.get("pnl"), 0.0)
        value = profit_r if profit_r is not None else profit_usc
        if value < 0:
            losses += 1
        else:
            break
    for row in usdjpy[-50:]:
        profit_r = to_float(row.get("profitR") or row.get("rMultiple") or row.get("r") or row.get("signedR"), None)
        if profit_r is not None:
            daily_loss_r += min(0.0, profit_r)
    return {"consecutiveLosses": losses, "dailyLossR": round(daily_loss_r, 4), "closeRows": len(usdjpy)}


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _parity_execution_blockers(runtime_dir: Path) -> List[str]:
    evidence = _load_json(runtime_dir / "evidence_os" / "QuantGod_USDJPYEvidenceOSStatus.json")
    parity = evidence.get("parity") if isinstance(evidence.get("parity"), dict) else {}
    execution = evidence.get("executionFeedback") if isinstance(evidence.get("executionFeedback"), dict) else {}
    if not parity:
        parity = _load_json(runtime_dir / "parity" / "QuantGod_StrategyParityReport.json")
    if not execution:
        execution = _load_json(runtime_dir / "execution" / "QuantGod_LiveExecutionQualityReport.json")
    parity_gate = parity.get("promotionGate") if isinstance(parity.get("promotionGate"), dict) else {}
    execution_gate = execution.get("promotionGate") if isinstance(execution.get("promotionGate"), dict) else {}
    reasons: List[str] = []
    if str(parity.get("status") or "").upper() == "PARITY_FAIL" or parity_gate.get("status") == "BLOCKED":
        reasons.append("Strategy / Replay / EA parity 失败，禁止进入 SHADOW、GA elite 或 MICRO_LIVE")
    if execution_gate.get("status") == "BLOCKED":
        reasons.append("执行反馈质量阻断，禁止扩大 MICRO_LIVE")
    return reasons


def evaluate_hard_rollback(runtime_dir: Path) -> Dict[str, Any]:
    runtime_dir = Path(runtime_dir)
    reasons: List[str] = []
    snapshot = focus_runtime_snapshot(runtime_dir) or {}
    quality = fastlane_quality(runtime_dir)
    runtime = snapshot.get("runtime") if isinstance(snapshot.get("runtime"), dict) else {}
    age = snapshot.get("runtimeAgeSeconds", snapshot.get("_fileAgeSeconds"))
    if not snapshot:
        reasons.append("缺少 USDJPY 运行快照")
    if snapshot.get("fallback"):
        reasons.append("运行快照处于 fallback")
    try:
        if age is not None and float(age) > 120:
            reasons.append(f"runtime 陈旧：{round(float(age), 1)}s")
    except Exception:
        reasons.append("runtime 年龄无法解析")
    fast_state = str(quality.get("quality") or "MISSING").upper()
    if fast_state not in FAST_STATES:
        reasons.append(f"快通道非 FAST/EA_DASHBOARD_OK：{fast_state}")
    spread = to_float(runtime.get("spreadPoints") or snapshot.get("spreadPoints"), 0.0)
    if spread and spread > 120:
        reasons.append(f"点差异常：{spread}")
    if snapshot.get("newsBlocked") or runtime.get("newsBlocked"):
        reasons.append("新闻过滤阻断中")
    loss = _recent_losses(runtime_dir)
    if loss["consecutiveLosses"] >= 2:
        reasons.append(f"连续亏损 {loss['consecutiveLosses']} 笔")
    if loss["dailyLossR"] <= -1.0:
        reasons.append(f"当日亏损达到 {loss['dailyLossR']}R")
    reasons.extend(_parity_execution_blockers(runtime_dir))
    return {
        "ok": not reasons,
        "generatedAtIso": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "hardBlockers": reasons,
        "runtimeAgeSeconds": age,
        "fastlaneQuality": fast_state,
        "lossState": loss,
    }


def append_rollback(runtime_dir: Path, payload: Dict[str, Any]) -> None:
    path = Path(runtime_dir) / "agent" / "QuantGod_AutonomousRollbackLedger.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "generatedAtIso": payload.get("generatedAtIso", utc_now_iso()),
        "symbol": FOCUS_SYMBOL,
        "stage": payload.get("stage", ""),
        "reason": "；".join(payload.get("hardBlockers") or [])[:500],
    }
    is_new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if is_new:
            writer.writeheader()
        writer.writerow(row)
