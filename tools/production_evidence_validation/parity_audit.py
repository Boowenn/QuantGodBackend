from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_csv_rows, read_json, read_jsonl
from .schema import REQUIRED_STRATEGY_FAMILIES

try:
    from tools.usdjpy_evidence_os.io_utils import candidate_mt5_files_dirs
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.io_utils import candidate_mt5_files_dirs


BACKTEST_COVERAGE_SCHEMA = "quantgod.strategy_backtest_coverage_matrix.v1"
SHADOW_OBSERVE_STATUSES = {
    "SHADOW_OBSERVE",
    "SHADOW_WOULD_ENTER",
    "SHADOW_GUARD_BLOCKED",
    "SHADOW_WAIT_INDICATORS",
    "DIRECTION_SHADOW_ONLY_DEMOTED",
}


def _status_from_text(value: str) -> str:
    text = (value or "").upper()
    if "FAIL" in text or "BLOCK" in text or "REJECT" in text:
        return "FAIL"
    if "SHADOW_RESEARCH_ONLY" in text:
        return "SHADOW_RESEARCH_ONLY"
    if "WATCH" in text or "OBSERVE" in text:
        return "WATCH"
    if "WARN" in text or "MISS" in text or "NEED" in text:
        return "WARN"
    if "PASS" in text or "OK" in text or "READY" in text:
        return "PASS"
    return "UNKNOWN"


def audit_parity(runtime_dir: Path) -> dict[str, Any]:
    report_path = runtime_dir / "parity" / "QuantGod_StrategyParityReport.json"
    evidence_report_path = runtime_dir / "evidence_os" / "QuantGod_StrategyParityReport.json"
    ledger_path = runtime_dir / "parity" / "QuantGod_StrategyParityLedger.csv"
    report = read_json(report_path, {}) or read_json(evidence_report_path, {}) or {}
    ledger = read_csv_rows(ledger_path, 1000)
    coverage = _strategy_backtest_coverage(runtime_dir)
    shadow = _ea_shadow_adapter_coverage(runtime_dir)
    rows: list[dict[str, Any]] = []
    observed: dict[str, dict[str, Any]] = {}

    for item in report.get("families") or report.get("matrix") or []:
        if not isinstance(item, dict):
            continue
        family = item.get("strategyFamily") or item.get("strategy") or item.get("family")
        status = _status_from_text(str(item.get("status") or item.get("parityStatus") or ""))
        if family:
            _remember(observed, str(family), status, "strategy_parity_report", item)

    for row in ledger:
        family = row.get("strategyFamily") or row.get("strategy") or row.get("family")
        status = _status_from_text(row.get("status") or row.get("parityStatus") or "")
        if family:
            _remember(observed, str(family), status, "strategy_parity_ledger", row)

    for family in REQUIRED_STRATEGY_FAMILIES:
        explicit = observed.get(family) or {}
        backtest = coverage.get(family) or {}
        ea_shadow = shadow.get(family) or {}
        parity_status = _family_parity_status(family, explicit, backtest, ea_shadow)
        rows.append(
            {
                "strategyFamily": family,
                "parityStatus": parity_status,
                "strategyJsonBacktest": backtest.get("status", "MISSING"),
                "mql5EaShadowAdapter": ea_shadow.get("status", "MISSING"),
                "explicitParity": explicit.get("status", "MISSING"),
                "routeCount": backtest.get("routeCount", 0),
                "okRouteCount": backtest.get("okRouteCount", 0),
                "parityVectorRouteCount": backtest.get("parityVectorRouteCount", 0),
                "shadowRows": ea_shadow.get("rowCount", 0),
                "shadowWouldEnterCount": ea_shadow.get("shadowWouldEnterCount", 0),
                "latestShadowStatus": ea_shadow.get("latestStatus", ""),
                "source": _family_source(explicit, backtest, ea_shadow),
                "reasonZh": _family_reason_zh(parity_status, backtest, ea_shadow),
            }
        )

    fail_count = sum(1 for row in rows if row["parityStatus"] == "FAIL")
    missing_count = sum(1 for row in rows if row["parityStatus"] == "MISSING")
    pass_count = sum(1 for row in rows if row["parityStatus"] == "PASS")
    shadow_research_count = sum(1 for row in rows if row["parityStatus"] == "SHADOW_RESEARCH_ONLY")
    watch_count = sum(1 for row in rows if row["parityStatus"] == "WATCH")
    status = "FAIL" if fail_count else ("WARN" if missing_count else "PASS")
    return {
        "status": status,
        "reportPath": str(report_path) if report_path.exists() else "",
        "evidenceReportPath": str(evidence_report_path) if evidence_report_path.exists() else "",
        "ledgerPath": str(ledger_path) if ledger_path.exists() else "",
        "passCount": pass_count,
        "shadowResearchOnlyCount": shadow_research_count,
        "watchCount": watch_count,
        "missingCount": missing_count,
        "failCount": fail_count,
        "coveredCount": len(rows) - missing_count,
        "requiredFamilyCount": len(REQUIRED_STRATEGY_FAMILIES),
        "matrix": rows,
        "coverageSources": {
            "strategyJsonBacktestCoverage": coverage.get("_source", {}),
            "mql5EaShadowAdapter": shadow.get("_source", {}),
        },
        "recommendation": _recommendation(fail_count, missing_count, watch_count, shadow_research_count),
    }


def _remember(
    observed: dict[str, dict[str, Any]],
    family: str,
    status: str,
    source: str,
    payload: dict[str, Any],
) -> None:
    current = observed.get(family)
    candidate = {"status": status, "source": source, "payload": payload}
    if current is None or _status_priority(status) > _status_priority(str(current.get("status") or "")):
        observed[family] = candidate


def _status_priority(status: str) -> int:
    status = (status or "").upper()
    if status == "FAIL":
        return 50
    if status == "PASS":
        return 40
    if status == "SHADOW_RESEARCH_ONLY":
        return 30
    if status == "WATCH":
        return 25
    if status == "WARN":
        return 20
    if status == "MISSING":
        return 10
    return 0


def _strategy_backtest_coverage(runtime_dir: Path) -> dict[str, Any]:
    path = runtime_dir / "backtest" / "QuantGod_StrategyBacktestReport.json"
    report = read_json(path, {}) or {}
    matrix = report.get("strategyCoverageMatrix") if isinstance(report.get("strategyCoverageMatrix"), dict) else {}
    rows = matrix.get("rows") if isinstance(matrix.get("rows"), list) else []
    coverage: dict[str, Any] = {
        "_source": {
            "path": str(path) if path.exists() else "",
            "schema": matrix.get("schema"),
            "status": matrix.get("status", "MISSING"),
            "rowCount": len(rows),
        }
    }
    by_family: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        family = str(item.get("strategyFamily") or "")
        if family:
            by_family.setdefault(family, []).append(item)
    for family, family_rows in by_family.items():
        route_count = len(family_rows)
        ok_count = sum(1 for row in family_rows if bool(row.get("ok")) or _status_from_text(str(row.get("status"))) == "PASS")
        vector_count = sum(1 for row in family_rows if bool(row.get("parityVectorPresent")))
        fail_count = sum(1 for row in family_rows if _status_from_text(str(row.get("status"))) == "FAIL")
        if matrix.get("schema") != BACKTEST_COVERAGE_SCHEMA:
            status = "MISSING"
        elif fail_count:
            status = "FAIL"
        elif route_count >= 2 and ok_count >= 2 and vector_count >= 2:
            status = "PASS"
        elif ok_count > 0 and vector_count > 0:
            status = "WATCH"
        else:
            status = "MISSING"
        coverage[family] = {
            "status": status,
            "routeCount": route_count,
            "okRouteCount": ok_count,
            "parityVectorRouteCount": vector_count,
            "tradeRouteCount": sum(1 for row in family_rows if int(float(row.get("tradeCount") or 0)) > 0),
            "rows": family_rows,
        }
    return coverage


def _ea_shadow_adapter_coverage(runtime_dir: Path) -> dict[str, Any]:
    rows = _ea_shadow_rows(runtime_dir)
    coverage: dict[str, Any] = {
        "_source": {
            "rowCount": len(rows),
            "files": _ea_shadow_files(runtime_dir),
        }
    }
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        family = str(row.get("strategyFamily") or "")
        if family:
            by_family.setdefault(family, []).append(row)
    case_summary = read_json(runtime_dir / "evidence_os" / "QuantGod_CaseMemorySummary.json", {}) or {}
    shadow_summary = (
        case_summary.get("strategyContractShadowEvaluation")
        if isinstance(case_summary.get("strategyContractShadowEvaluation"), dict)
        else {}
    )
    generic_summary = (
        shadow_summary.get("genericAdapterSummary")
        if isinstance(shadow_summary.get("genericAdapterSummary"), dict)
        else {}
    )
    for family, item in generic_summary.items():
        if isinstance(item, dict) and family not in by_family:
            by_family[str(family)] = [item]
    for family, family_rows in by_family.items():
        coverage[family] = _ea_shadow_family_status(family_rows)
    return coverage


def _ea_shadow_files(runtime_dir: Path) -> list[str]:
    files: list[str] = []
    for directory in _shadow_candidate_dirs(runtime_dir):
        for filename in (
            "QuantGod_StrategyJsonEAShadowEvaluationLedger.jsonl",
            "QuantGod_StrategyJsonEAShadowEvaluationStatus.json",
        ):
            path = directory / filename
            if path.exists():
                files.append(str(path))
    return files


def _ea_shadow_rows(runtime_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for directory in _shadow_candidate_dirs(runtime_dir):
        ledger = directory / "QuantGod_StrategyJsonEAShadowEvaluationLedger.jsonl"
        rows.extend(read_jsonl(ledger, 500))
        status = read_json(directory / "QuantGod_StrategyJsonEAShadowEvaluationStatus.json", {}) or {}
        if status:
            rows.append(status)
    return rows


def _shadow_candidate_dirs(runtime_dir: Path) -> list[Path]:
    candidates = [Path(runtime_dir), Path(runtime_dir) / "strategy_contract"]
    try:
        candidates.extend(candidate_mt5_files_dirs(Path(runtime_dir)))
    except Exception:
        pass
    seen: set[str] = set()
    result: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        key = str(resolved)
        if key in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(key)
        result.append(resolved)
    return result


def _ea_shadow_family_status(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    implemented_rows = 0
    adapter_gap_count = 0
    guard_blocked_count = 0
    shadow_would_enter_count = 0
    latest = rows[-1] if rows else {}
    for row in rows:
        status_value = str(row.get("status") or "UNKNOWN")
        blocker = str(row.get("blocker") or "")
        status_counts[status_value] = status_counts.get(status_value, 0) + 1
        generic_strategy = row.get("genericStrategy") if isinstance(row.get("genericStrategy"), dict) else {}
        if bool(row.get("contractFamilyImplemented")) or bool(generic_strategy.get("implemented")):
            implemented_rows += 1
        if blocker == "EA_CONTRACT_FAMILY_NOT_IMPLEMENTED":
            adapter_gap_count += 1
        if status_value == "SHADOW_GUARD_BLOCKED":
            guard_blocked_count += 1
        if status_value == "SHADOW_WOULD_ENTER":
            shadow_would_enter_count += 1
    if adapter_gap_count and adapter_gap_count >= len(rows):
        status = "MISSING"
    elif any(str(row.get("blocker") or "") in {"CONTRACT_SAFETY_REJECTED", "NON_USDJPY_CONTRACT"} for row in rows):
        status = "FAIL"
    elif implemented_rows or any(str(row.get("status") or "") in SHADOW_OBSERVE_STATUSES for row in rows):
        status = "PASS"
    elif rows:
        status = "WATCH"
    else:
        status = "MISSING"
    return {
        "status": status,
        "rowCount": len(rows),
        "implementedRows": implemented_rows,
        "adapterGapCount": adapter_gap_count,
        "guardBlockedCount": guard_blocked_count,
        "shadowWouldEnterCount": shadow_would_enter_count,
        "statusCounts": status_counts,
        "latestStatus": latest.get("status") or "",
        "latestBlocker": latest.get("blocker") or "",
    }


def _family_parity_status(
    family: str,
    explicit: dict[str, Any],
    backtest: dict[str, Any],
    ea_shadow: dict[str, Any],
) -> str:
    explicit_status = str(explicit.get("status") or "")
    backtest_status = str(backtest.get("status") or "")
    shadow_status = str(ea_shadow.get("status") or "")
    if "FAIL" in {explicit_status, backtest_status, shadow_status}:
        return "FAIL"
    if explicit_status == "PASS":
        return "PASS"
    if backtest_status == "PASS" and shadow_status == "PASS":
        return "PASS"
    if family == "RSI_Reversal" and backtest_status == "PASS":
        return "PASS"
    if backtest_status == "PASS":
        return "SHADOW_RESEARCH_ONLY"
    if backtest_status == "WATCH" or shadow_status in {"PASS", "WATCH"}:
        return "WATCH"
    return "MISSING"


def _family_source(explicit: dict[str, Any], backtest: dict[str, Any], ea_shadow: dict[str, Any]) -> str:
    sources = []
    if explicit:
        sources.append(str(explicit.get("source") or "strategy_parity"))
    if backtest:
        sources.append("strategy_json_backtest_coverage")
    if ea_shadow:
        sources.append("mql5_ea_shadow_adapter")
    return "+".join(sources) if sources else "missing"


def _family_reason_zh(status: str, backtest: dict[str, Any], ea_shadow: dict[str, Any]) -> str:
    if status == "PASS":
        return "Strategy JSON 回测覆盖和 EA/Parity 证据已覆盖该策略族。"
    if status == "SHADOW_RESEARCH_ONLY":
        return "Strategy JSON 回测覆盖已存在；该策略族保持 shadow research，不抢实盘路线。"
    if status == "WATCH":
        return "已有部分覆盖证据，但仍需更多 EA shadow rows 或 parityVector 样本。"
    if status == "FAIL":
        return "该策略族存在 parity 或 adapter 硬失败，禁止晋级。"
    if backtest.get("status") == "MISSING":
        return "缺少 Strategy JSON 多策略回测覆盖。"
    if ea_shadow.get("status") == "MISSING":
        return "缺少 EA shadow adapter 观测。"
    return "缺少该策略族的生产 parity 证据。"


def _recommendation(
    fail_count: int,
    missing_count: int,
    watch_count: int,
    shadow_research_count: int,
) -> str:
    if fail_count:
        return "Fix PARITY_FAIL or EA adapter hard failures before promotion."
    if missing_count:
        return "Run Strategy JSON coverage matrix and EA shadow contract rotation until missing families are covered."
    if watch_count:
        return "Collect more EA shadow rows for WATCH families; keep them out of live promotion."
    if shadow_research_count:
        return "All families are accounted for; shadow-only families remain research candidates until stronger parity evidence exists."
    return "Strategy family parity matrix is production-ready."
