from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .execution_feedback_audit import audit_execution_feedback
from .ga_audit import audit_ga
from .history_audit import audit_history
from .io_utils import ensure_dir, write_json
from .parity_audit import audit_parity
from .schema import (
    EXECUTION_FEEDBACK_COVERAGE,
    GA_STABILITY_REPORT,
    LATEST_REPORT,
    OUTPUT_DIR,
    REPORT_SCHEMA,
    SAFETY,
    STRATEGY_FAMILY_PARITY,
)


def _overall_status(sections: list[dict[str, Any]]) -> str:
    states = {str(section.get("status") or "UNKNOWN").upper() for section in sections}
    if "FAIL" in states:
        return "FAIL"
    if "WARN" in states or "UNKNOWN" in states:
        return "WARN"
    return "PASS"


def build_report(runtime_dir: Path) -> dict[str, Any]:
    history = audit_history(runtime_dir)
    parity = audit_parity(runtime_dir)
    execution_feedback = audit_execution_feedback(runtime_dir)
    ga = audit_ga(runtime_dir)
    sections = [history, parity, execution_feedback, ga]
    status = _overall_status(sections)
    blockers = []
    if parity.get("failCount"):
        blockers.append("存在 PARITY_FAIL，相关策略不得晋级")
    if execution_feedback.get("sampleCount", 0) < 5:
        blockers.append("真实/影子执行反馈样本不足")
    if history.get("status") != "PASS":
        blockers.append("USDJPY 历史数据深度或表覆盖不足")
    if ga.get("status") != "PASS":
        blockers.append("GA 多代稳定性证据不足")
    return {
        "schema": REPORT_SCHEMA,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summaryZh": "生产证据可用" if status == "PASS" else "生产证据仍需补强",
        "blockersZh": blockers,
        "historyProduction": history,
        "strategyFamilyParity": parity,
        "liveExecutionFeedbackCoverage": execution_feedback,
        "gaMultiGenerationStability": ga,
        "safety": SAFETY,
        "nextActionsZh": [
            "优先补齐 PARITY_FAIL / 缺失 strategy family",
            "持续收集 live/shadow execution feedback",
            "连续观察 GA 多代 elite / graveyard / lineage 稳定性",
            "确认 USDJPY 历史数据同步长期 PASS",
        ],
    }


def write_reports(runtime_dir: Path, report: dict[str, Any]) -> dict[str, str]:
    out_dir = ensure_dir(runtime_dir / OUTPUT_DIR)
    paths = {
        "latest": str(out_dir / LATEST_REPORT),
        "parityMatrix": str(out_dir / STRATEGY_FAMILY_PARITY),
        "executionFeedbackCoverage": str(out_dir / EXECUTION_FEEDBACK_COVERAGE),
        "gaStability": str(out_dir / GA_STABILITY_REPORT),
    }
    write_json(Path(paths["latest"]), report)
    write_json(Path(paths["parityMatrix"]), report.get("strategyFamilyParity") or {})
    write_json(Path(paths["executionFeedbackCoverage"]), report.get("liveExecutionFeedbackCoverage") or {})
    write_json(Path(paths["gaStability"]), report.get("gaMultiGenerationStability") or {})
    return paths


def load_latest(runtime_dir: Path) -> dict[str, Any] | None:
    from .io_utils import read_json
    return read_json(runtime_dir / OUTPUT_DIR / LATEST_REPORT, None)
