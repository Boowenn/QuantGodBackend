from __future__ import annotations

FOCUS_SYMBOL = "USDJPYc"
REPORT_SCHEMA = "quantgod.production_evidence_validation.v1"
OUTPUT_DIR = "production_validation"
LATEST_REPORT = "QuantGod_ProductionEvidenceValidationReport.json"
STRATEGY_FAMILY_PARITY = "QuantGod_StrategyFamilyParityMatrix.json"
EXECUTION_FEEDBACK_COVERAGE = "QuantGod_LiveExecutionFeedbackCoverage.json"
GA_STABILITY_REPORT = "QuantGod_GAMultiGenerationStabilityReport.json"
PRODUCTION_BURN_IN_REPORT = "QuantGod_ProductionBurnInReport.json"
PRODUCTION_BURN_IN_LEDGER = "QuantGod_ProductionBurnInLedger.csv"
RSI_LINEAGE_CLOSURE_REPORT = "QuantGod_RSILineageClosureReport.json"
RSI_FROZEN_ELITE_LINEAGE = "QuantGod_RSIFrozenEliteLineage.json"

REQUIRED_STRATEGY_FAMILIES = [
    "RSI_Reversal",
    "MA_Cross",
    "BB_Triple",
    "MACD_Divergence",
    "SR_Breakout",
    "USDJPY_TOKYO_RANGE_BREAKOUT",
    "USDJPY_NIGHT_REVERSION_SAFE",
    "USDJPY_H4_TREND_PULLBACK",
]

PASS_STATES = {"PASS", "PASSED", "OK", "READY", "FAST", "EA_DASHBOARD_OK"}
WARN_STATES = {"WARN", "WARNING", "NEEDS_MORE_DATA", "NEEDS_SAMPLES", "PARTIAL"}
FAIL_STATES = {"FAIL", "FAILED", "PARITY_FAIL", "BLOCKED", "DEGRADED", "REJECTED"}

SAFETY = {
    "localOnly": True,
    "readOnlyDataPlane": True,
    "advisoryOnly": True,
    "productionEvidenceOnly": True,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "modifyAllowed": False,
    "livePresetMutationAllowed": False,
    "telegramCommandExecutionAllowed": False,
    "webhookReceiverAllowed": False,
    "polymarketRealMoneyAllowed": False,
    "walletIntegrationAllowed": False,
}
