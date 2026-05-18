from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .data_loader import fastlane_quality, focus_runtime_snapshot, runtime_fresh_limit_seconds
from .schema import FOCUS_SYMBOL, READ_ONLY_SAFETY, assert_no_secret_or_execution_flags, utc_now_iso


def build_risk_check(runtime_dir: Path) -> Dict[str, Any]:
    snapshot = focus_runtime_snapshot(runtime_dir) or {}
    quality = fastlane_quality(runtime_dir)
    blockers: List[str] = []
    if not snapshot:
        blockers.append("缺少 USDJPY 运行快照")
    elif snapshot.get("fallback"):
        blockers.append("运行快照处于 fallback")
    try:
        age = float(snapshot.get("runtimeAgeSeconds", 9999))
        if age > runtime_fresh_limit_seconds():
            blockers.append(f"运行快照过旧：{age:.0f}s")
    except Exception:
        blockers.append("运行快照年龄不可解析")
    if not quality.get("found"):
        blockers.append("缺少快通道质量")
    elif str(quality.get("quality") or "").upper() not in {"OK", "PASS", "PASSED", "GOOD", "HEALTHY", "FAST", "EA_DASHBOARD_OK"}:
        blockers.append(f"快通道质量未通过：{quality.get('quality')}")
    payload = {
        "schema": "quantgod.usdjpy_strategy_risk_check.v1",
        "generatedAt": utc_now_iso(),
        "symbol": FOCUS_SYMBOL,
        "status": "PASS" if not blockers else "BLOCKED",
        "blockers": blockers,
        "notes": [
            "风险检查只决定是否允许进入影子/干跑政策评估。",
            "不会下单、平仓、撤单或修改 live preset。",
        ],
        "safety": dict(READ_ONLY_SAFETY),
    }
    assert_no_secret_or_execution_flags(payload)
    return payload
