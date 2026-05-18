from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

try:
    from tools.usdjpy_strategy_lab.data_loader import focus_runtime_snapshot, runtime_fresh_limit_seconds
    from tools.usdjpy_strategy_lab.dry_run_bridge import build_dry_run_decision
    from tools.usdjpy_strategy_lab.policy_builder import build_usdjpy_policy
except ModuleNotFoundError:  # CLI execution from tools/
    from usdjpy_strategy_lab.data_loader import focus_runtime_snapshot, runtime_fresh_limit_seconds
    from usdjpy_strategy_lab.dry_run_bridge import build_dry_run_decision
    from usdjpy_strategy_lab.policy_builder import build_usdjpy_policy

from .preset import load_live_preset
from .schema import (
    FOCUS_SYMBOL,
    SAFE_EVIDENCE_BOUNDARY,
    SCHEMA_DAILY,
    SCHEMA_INTENT,
    SCHEMA_STATUS,
    STATE_EVIDENCE_MISSING,
    STATE_POLICY_BLOCKED,
    STATE_POLICY_READY_PRESET_BLOCKED,
    STATE_READY,
    STATE_ZH,
    direction_zh,
    entry_mode_zh,
    utc_now_iso,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_ledger(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    top = payload.get("topLiveEligiblePolicy") or payload.get("topPolicy") or {}
    row = {
        "generatedAt": payload.get("generatedAt", ""),
        "state": payload.get("state", ""),
        "stateZh": payload.get("stateZh", ""),
        "topStrategy": top.get("strategy", ""),
        "topDirection": top.get("direction", ""),
        "entryMode": top.get("entryMode", ""),
        "recommendedLot": top.get("recommendedLot", ""),
        "presetReady": str(bool((payload.get("preset") or {}).get("ready"))).lower(),
        "runtimeReady": str(bool((payload.get("runtime") or {}).get("ready"))).lower(),
        "whyNoEntry": "；".join(payload.get("whyNoEntry") or [])[:500],
    }
    fields = list(row)
    is_new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def _runtime_status(runtime_dir: Path) -> dict[str, Any]:
    snapshot = focus_runtime_snapshot(runtime_dir)
    if not snapshot:
        return {
            "found": False,
            "ready": False,
            "reasons": ["缺少 USDJPY 运行快照，无法确认 EA 现场状态"],
        }
    runtime = snapshot.get("runtime") if isinstance(snapshot.get("runtime"), dict) else {}
    age = snapshot.get("runtimeAgeSeconds", snapshot.get("_fileAgeSeconds"))
    ready = bool(snapshot) and not bool(snapshot.get("fallback")) and snapshot.get("runtimeFresh") is not False
    try:
        if age is not None and float(age) > runtime_fresh_limit_seconds():
            ready = False
    except Exception:
        pass
    reasons: list[str] = []
    if snapshot.get("fallback"):
        reasons.append("运行快照处于 fallback")
    if snapshot.get("runtimeFresh") is False:
        reasons.append("运行快照标记为不新鲜")
    if not reasons:
        reasons.append("USDJPY 运行快照可用")
    return {
        "found": True,
        "ready": ready,
        "ageSeconds": age,
        "tradeStatus": runtime.get("tradeStatus") or snapshot.get("tradeStatus"),
        "executionEnabled": runtime.get("executionEnabled", snapshot.get("executionEnabled")),
        "readOnlyMode": runtime.get("readOnlyMode", snapshot.get("readOnlyMode")),
        "openPositions": runtime.get("positions", snapshot.get("openPositions")),
        "tickAgeSeconds": runtime.get("tickAgeSeconds"),
        "reasons": reasons,
        "source": snapshot.get("_filePath"),
    }


def _policy_ready(policy: dict[str, Any]) -> tuple[bool, list[str]]:
    top = policy.get("topLiveEligiblePolicy") or {}
    if not top:
        fallback = policy.get("liveRecoveryCandidate") or {}
        fallback_reasons = list(fallback.get("reasons") or [])
        return False, ["没有可进入实盘复核的 RSI_Reversal 买入政策", *fallback_reasons[:3]]
    reasons = list(top.get("reasons") or [])
    strategy = str(top.get("strategy") or "")
    direction = str(top.get("direction") or "").upper()
    entry_mode = str(top.get("entryMode") or "")
    if strategy != "RSI_Reversal" or direction != "LONG":
        return False, [f"当前优先策略不是 RSI 买入路线：{strategy} {direction}", *reasons[:3]]
    if entry_mode not in {"STANDARD_ENTRY", "OPPORTUNITY_ENTRY"}:
        return False, [f"当前策略状态为{entry_mode_zh(entry_mode)}", *reasons[:3]]
    return True, ["USDJPY RSI 买入路线政策已就绪", *reasons[:3]]


def _build_next_actions(state: str, policy: dict[str, Any], preset: dict[str, Any], runtime: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if not runtime.get("ready"):
        actions.append("先恢复 USDJPY 运行快照和快通道证据，避免基于旧数据判断。")
    if not preset.get("ready"):
        actions.append("检查 HFM live preset：必须只恢复 RSI 买入路线，非 RSI 继续模拟。")
    if state == STATE_POLICY_BLOCKED:
        actions.append("继续自动 retune/backtest：重点分析阻断原因是否来自样本不足、触发缺失或动态止盈止损缺失。")
    if state == STATE_READY:
        actions.append("保持 EA 风控接管真实入场；人工仓位不计入 EA 自动仓位上限。")
    if not actions:
        actions.append("保持 USDJPY-only 自动链路每小时刷新，并在 Telegram 推送中文复盘。")
    return actions


def build_live_loop(repo_root: Path, runtime_dir: Path, *, write: bool = False, min_samples: int = 5) -> dict[str, Any]:
    policy = build_usdjpy_policy(runtime_dir, write=write, min_samples=min_samples)
    dry_run = build_dry_run_decision(runtime_dir, write=write)
    preset = load_live_preset(repo_root)
    runtime = _runtime_status(runtime_dir)
    policy_ok, policy_reasons = _policy_ready(policy)
    why_no_entry: list[str] = []
    if not runtime.get("ready"):
        why_no_entry.extend(runtime.get("reasons") or [])
    if not policy_ok:
        why_no_entry.extend(policy_reasons)
    if not preset.get("ready"):
        why_no_entry.extend(preset.get("reasons") or [])
    if not runtime.get("ready"):
        state = STATE_EVIDENCE_MISSING
    elif not policy_ok:
        state = STATE_POLICY_BLOCKED
    elif not preset.get("ready"):
        state = STATE_POLICY_READY_PRESET_BLOCKED
    else:
        state = STATE_READY
    top = policy.get("topLiveEligiblePolicy") or policy.get("liveRecoveryCandidate") or policy.get("topPolicy") or {}
    intent = {
        "schema": SCHEMA_INTENT,
        "generatedAt": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "state": state,
        "stateZh": STATE_ZH.get(state, state),
        "existingEaOwnsExecution": True,
        "toolDoesNotTrade": True,
        "allowedLiveRoute": "RSI_Reversal BUY",
        "manualPositionsIgnoredByPolicy": True,
        "maxEaPositions": preset.get("maxEaPositions", 2),
        "topPolicy": top,
        "topLiveEligiblePolicy": policy.get("topLiveEligiblePolicy"),
        "topShadowPolicy": policy.get("topShadowPolicy"),
        "recommendedLot": top.get("recommendedLot", 0.0),
        "entryMode": top.get("entryMode", "BLOCKED"),
        "strategy": top.get("strategy", "UNKNOWN"),
        "direction": top.get("direction", "UNKNOWN"),
        "whyNoEntry": list(dict.fromkeys(str(item) for item in why_no_entry if item)),
        "nextActions": _build_next_actions(state, policy, preset, runtime),
        "safety": dict(SAFE_EVIDENCE_BOUNDARY),
    }
    payload = {
        "schema": SCHEMA_STATUS,
        "generatedAt": intent["generatedAt"],
        "symbol": FOCUS_SYMBOL,
        "state": state,
        "stateZh": intent["stateZh"],
        "liveRouteZh": "仅 RSI_Reversal 买入路线允许由现有 EA 评估；SELL 和非 RSI 继续模拟。",
        "policyReady": policy_ok,
        "presetReady": bool(preset.get("ready")),
        "runtimeReady": bool(runtime.get("ready")),
        "manualPositionsIgnoredByPolicy": True,
        "maxEaPositions": preset.get("maxEaPositions", 2),
        "topPolicy": top,
        "topLiveEligiblePolicy": policy.get("topLiveEligiblePolicy"),
        "topShadowPolicy": policy.get("topShadowPolicy"),
        "policy": policy,
        "dryRun": dry_run,
        "preset": preset,
        "runtime": runtime,
        "intent": intent,
        "whyNoEntry": intent["whyNoEntry"],
        "nextActions": intent["nextActions"],
        "safety": dict(SAFE_EVIDENCE_BOUNDARY),
    }
    if write:
        live_dir = runtime_dir / "live"
        _write_json(live_dir / "QuantGod_USDJPYLiveLoopStatus.json", payload)
        _write_json(live_dir / "QuantGod_USDJPYLiveIntent.json", intent)
        daily = {
            "schema": SCHEMA_DAILY,
            "generatedAt": payload["generatedAt"],
            "summaryZh": payload["stateZh"],
            "state": state,
            "allowedLiveRoute": intent["allowedLiveRoute"],
            "topStrategy": top.get("strategy"),
            "topDirectionZh": direction_zh(top.get("direction")),
            "entryModeZh": entry_mode_zh(top.get("entryMode")),
            "whyNoEntry": intent["whyNoEntry"],
            "nextActions": intent["nextActions"],
            "safety": dict(SAFE_EVIDENCE_BOUNDARY),
        }
        _write_json(live_dir / "QuantGod_USDJPYDailyAutopilot.json", daily)
        _append_ledger(live_dir / "QuantGod_USDJPYLiveLoopLedger.csv", payload)
    return payload
