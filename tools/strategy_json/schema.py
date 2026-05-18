from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

FOCUS_SYMBOL = "USDJPYc"
SCHEMA_VERSION = "quantgod.strategy.v1"

ALLOWED_LANES = {"MT5_SHADOW", "TESTER_ONLY", "PAPER_LIVE_SIM", "SHADOW"}
ALLOWED_STRATEGY_FAMILIES = {
    "RSI_Reversal",
    "MA_Cross",
    "BB_Triple",
    "MACD_Divergence",
    "SR_Breakout",
    "USDJPY_TOKYO_RANGE_BREAKOUT",
    "USDJPY_NIGHT_REVERSION_SAFE",
    "USDJPY_H4_TREND_PULLBACK",
}
ALLOWED_DIRECTIONS = {"LONG", "SHORT"}
ALLOWED_TIMEFRAMES = {"M1", "M5", "M15", "H1", "H4", "D1"}
LIVE_FORBIDDEN_STAGES = {"MICRO_LIVE", "LIVE_LIMITED"}

SAFETY_BOUNDARY: Dict[str, Any] = {
    "usdJpyOnly": True,
    "strategyJsonOnly": True,
    "orderSendAllowed": False,
    "closeAllowed": False,
    "cancelAllowed": False,
    "livePresetMutationAllowed": False,
    "polymarketRealMoneyAllowed": False,
    "telegramCommandExecutionAllowed": False,
    "gaDirectLiveAllowed": False,
}

DEFAULT_RSI: Dict[str, Any] = {
    "period": 14,
    "timeframe": "H1",
    "buyBand": 34,
    "crossbackThreshold": 0.8,
    "maxCrossbackRsi": 100,
    "regimeFilter": {"mode": "OFF"},
}

DEFAULT_MA: Dict[str, Any] = {
    "timeframe": "H1",
    "fastPeriod": 9,
    "slowPeriod": 21,
}

DEFAULT_BOLLINGER: Dict[str, Any] = {
    "timeframe": "H1",
    "period": 20,
    "deviations": 2.0,
    "reclaimBufferPips": 0.0,
}

DEFAULT_MACD: Dict[str, Any] = {
    "timeframe": "H1",
    "fastPeriod": 12,
    "slowPeriod": 26,
    "signalPeriod": 9,
    "minHistogramAbs": 0.0,
}

DEFAULT_SUPPORT_RESISTANCE: Dict[str, Any] = {
    "timeframe": "H1",
    "lookbackBars": 24,
    "breakoutBufferPips": 0.0,
}

DEFAULT_TOKYO_RANGE: Dict[str, Any] = {
    "timeframe": "M15",
    "rangeStartHourUtc": 0,
    "rangeEndHourUtc": 2,
    "tradeStartHourUtc": 3,
    "tradeEndHourUtc": 6,
    "lookbackBars": 8,
    "bufferPips": 0.0,
}

DEFAULT_NIGHT_REVERSION: Dict[str, Any] = {
    "timeframe": "M15",
    "startHourUtc": 20,
    "endHourUtc": 2,
    "bollingerPeriod": 20,
    "deviations": 1.8,
    "entryBufferPips": 0.0,
}

DEFAULT_H4_PULLBACK: Dict[str, Any] = {
    "timeframe": "H4",
    "fastEmaPeriod": 20,
    "slowEmaPeriod": 50,
    "pullbackEmaPeriod": 20,
    "rsiPeriod": 14,
    "longRsiMin": 38,
    "shortRsiMax": 62,
}

DEFAULT_EXIT: Dict[str, Any] = {
    "breakevenDelayR": 1.0,
    "trailStartR": 1.5,
    "mfeGivebackPct": 0.6,
    "timeStopBars": {"M15": 6, "H1": 4},
}

DEFAULT_ENTRY_CONDITIONS: List[str] = [
    "runtimeFresh == true",
    "fastlane in ['FAST','EA_DASHBOARD_OK']",
    "spreadRisk != HARD",
    "newsRisk != HARD",
    "rsi.crossback == true",
]


def base_strategy_seed(seed_id: str, family: str = "RSI_Reversal", direction: str = "LONG") -> Dict[str, Any]:
    """Return a safe Strategy JSON seed in the MT5 shadow lane."""
    return {
        "schema": SCHEMA_VERSION,
        "seedId": seed_id,
        "strategyId": f"USDJPY_{family.upper()}_{direction}_SEED",
        "symbol": FOCUS_SYMBOL,
        "lane": "MT5_SHADOW",
        "strategyFamily": family,
        "direction": direction,
        "timeframes": ["M1", "M15", "H1", "H4"],
        "indicators": {
            "rsi": deepcopy(DEFAULT_RSI),
            "ma": deepcopy(DEFAULT_MA),
            "bollinger": deepcopy(DEFAULT_BOLLINGER),
            "macd": deepcopy(DEFAULT_MACD),
            "supportResistance": deepcopy(DEFAULT_SUPPORT_RESISTANCE),
            "tokyoRange": deepcopy(DEFAULT_TOKYO_RANGE),
            "nightReversion": deepcopy(DEFAULT_NIGHT_REVERSION),
            "h4Pullback": deepcopy(DEFAULT_H4_PULLBACK),
        },
        "entry": {
            "mode": "OPPORTUNITY_ENTRY",
            "conditions": list(DEFAULT_ENTRY_CONDITIONS),
        },
        "exit": deepcopy(DEFAULT_EXIT),
        "risk": {
            "maxLot": 2.0,
            "stage": "SHADOW",
            "opportunityLotMultiplier": 0.35,
        },
        "safety": dict(SAFETY_BOUNDARY),
    }
