from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .normalizer import normalize_strategy_json
from .safety import find_forbidden_tokens
from .schema import (
    ALLOWED_DIRECTIONS,
    ALLOWED_LANES,
    ALLOWED_STRATEGY_FAMILIES,
    ALLOWED_TIMEFRAMES,
    FOCUS_SYMBOL,
    LIVE_FORBIDDEN_STAGES,
    SCHEMA_VERSION,
)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _check_range(name: str, value: Any, low: float, high: float) -> Tuple[bool, str]:
    numeric = _num(value, low - 1)
    if numeric < low or numeric > high:
        return False, f"{name} 超出允许范围"
    return True, ""


def _check_timeframe(name: str, value: Any) -> Tuple[bool, str]:
    if str(value or "").upper() not in ALLOWED_TIMEFRAMES:
        return False, f"{name} 周期字段不合法"
    return True, ""


def _check_rsi_regime_filter(config: Dict[str, Any]) -> Tuple[bool, str]:
    mode = str(config.get("mode") or "OFF").upper()
    if mode not in {"OFF", "NONE", "P4_10E_RSI_BEARISH_STRETCH"}:
        return False, "RSI regimeFilter mode 不合法"
    if mode in {"OFF", "NONE"}:
        return True, ""
    hours = config.get("allowedHoursUtc") if isinstance(config.get("allowedHoursUtc"), list) else []
    if any(_num(hour, -1) < 0 or _num(hour, -1) > 23 for hour in hours):
        return False, "RSI regimeFilter allowedHoursUtc 不合法"
    checks = [
        _check_range("RSI regimeFilter emaFastPeriod", config.get("emaFastPeriod", 20), 2, 120),
        _check_range("RSI regimeFilter emaSlowPeriod", config.get("emaSlowPeriod", 50), 3, 240),
        _check_range("RSI regimeFilter slopeLookbackBars", config.get("slopeLookbackBars", 3), 1, 24),
        _check_range("RSI regimeFilter minFastMinusSlowPips", config.get("minFastMinusSlowPips", -500), -1000, 1000),
        _check_range("RSI regimeFilter maxFastMinusSlowPips", config.get("maxFastMinusSlowPips", 0), -1000, 1000),
        _check_range("RSI regimeFilter minDistanceFromSlowPips", config.get("minDistanceFromSlowPips", -260), -1000, 1000),
        _check_range("RSI regimeFilter maxDistanceFromSlowPips", config.get("maxDistanceFromSlowPips", -50), -1000, 1000),
        _check_range("RSI regimeFilter minSlowSlopePips", config.get("minSlowSlopePips", -45), -1000, 1000),
        _check_range("RSI regimeFilter maxSlowSlopePips", config.get("maxSlowSlopePips", -6), -1000, 1000),
    ]
    for ok, reason in checks:
        if not ok:
            return ok, reason
    if _num(config.get("emaFastPeriod"), 20) >= _num(config.get("emaSlowPeriod"), 50):
        return False, "RSI regimeFilter emaFastPeriod 必须小于 emaSlowPeriod"
    return True, ""


def _check_entry_event_filter(config: Dict[str, Any]) -> Tuple[bool, str]:
    mode = str(config.get("mode") or "OFF").upper()
    if mode not in {"OFF", "NONE", "P4_10E_RSI_AVOID_KNOWN_EVENT_RISK"}:
        return False, "entry eventFilter mode 不合法"
    levels = config.get("allowedRiskLevels") if isinstance(config.get("allowedRiskLevels"), list) else []
    allowed = {"NONE", "UNKNOWN", "SOFT", "HARD"}
    if any(str(item or "").upper() not in allowed for item in levels):
        return False, "entry eventFilter allowedRiskLevels 不合法"
    return True, ""


def _reject(seed: Dict[str, Any], code: str, reason: str, details: List[str] | None = None) -> Dict[str, Any]:
    return {
        "seedId": seed.get("seedId", "UNKNOWN"),
        "valid": False,
        "blockerCode": code,
        "reasonZh": reason,
        "details": details or [],
    }


def validate_strategy_json(seed: Dict[str, Any]) -> Dict[str, Any]:
    if seed.get("symbol") not in (None, FOCUS_SYMBOL):
        return _reject(seed, "NON_USDJPY_REJECTED", "GA 只允许 USDJPYc 策略种子")
    data = normalize_strategy_json(seed)
    if data.get("schema") != SCHEMA_VERSION:
        return _reject(data, "SCHEMA_INVALID", "Strategy JSON schema 不匹配")
    if data.get("symbol") != FOCUS_SYMBOL:
        return _reject(data, "NON_USDJPY_REJECTED", "GA 只允许 USDJPYc 策略种子")
    if data.get("lane") not in ALLOWED_LANES:
        return _reject(data, "LANE_INVALID", "策略种子只能进入 MT5 Shadow / Tester / Paper-live-sim")
    if data.get("strategyFamily") not in ALLOWED_STRATEGY_FAMILIES:
        return _reject(data, "STRATEGY_FAMILY_INVALID", "策略族不在允许的 USDJPY 模拟池内")
    if data.get("direction") not in ALLOWED_DIRECTIONS:
        return _reject(data, "DIRECTION_INVALID", "方向字段不合法")

    stage = str((data.get("risk") or {}).get("stage") or "SHADOW").upper()
    if stage in LIVE_FORBIDDEN_STAGES:
        return _reject(data, "LIVE_STAGE_REJECTED", "GA 种子不能直接进入 MICRO_LIVE 或 LIVE_LIMITED")
    if _num((data.get("risk") or {}).get("maxLot"), 0) > 2.0:
        return _reject(data, "MAX_LOT_TOO_HIGH", "最大仓位超过 2.0 上限")

    bad_tokens = find_forbidden_tokens(data)
    if bad_tokens:
        return _reject(data, "SAFETY_REJECTED", "Strategy JSON 含有代码、密钥或交易执行原语", bad_tokens[:6])

    timeframes = data.get("timeframes") if isinstance(data.get("timeframes"), list) else []
    if not timeframes or any(item not in ALLOWED_TIMEFRAMES for item in timeframes):
        return _reject(data, "TIMEFRAME_INVALID", "周期字段不合法")

    rsi = ((data.get("indicators") or {}).get("rsi") or {})
    entry = data.get("entry") if isinstance(data.get("entry"), dict) else {}
    indicators = data.get("indicators") if isinstance(data.get("indicators"), dict) else {}
    ma = indicators.get("ma") if isinstance(indicators.get("ma"), dict) else {}
    bollinger = indicators.get("bollinger") if isinstance(indicators.get("bollinger"), dict) else {}
    macd = indicators.get("macd") if isinstance(indicators.get("macd"), dict) else {}
    support_resistance = indicators.get("supportResistance") if isinstance(indicators.get("supportResistance"), dict) else {}
    tokyo_range = indicators.get("tokyoRange") if isinstance(indicators.get("tokyoRange"), dict) else {}
    night_reversion = indicators.get("nightReversion") if isinstance(indicators.get("nightReversion"), dict) else {}
    h4_pullback = indicators.get("h4Pullback") if isinstance(indicators.get("h4Pullback"), dict) else {}
    checks = [
        _check_timeframe("RSI", rsi.get("timeframe")),
        _check_range("RSI period", rsi.get("period"), 2, 50),
        _check_range("RSI buyBand", rsi.get("buyBand"), 5, 45),
        _check_range("RSI crossbackThreshold", rsi.get("crossbackThreshold"), 0, 3),
        _check_range("RSI maxCrossbackRsi", rsi.get("maxCrossbackRsi", 100), 20, 100),
        _check_rsi_regime_filter(rsi.get("regimeFilter") if isinstance(rsi.get("regimeFilter"), dict) else {}),
        _check_entry_event_filter(entry.get("eventFilter") if isinstance(entry.get("eventFilter"), dict) else {}),
        _check_timeframe("MA", ma.get("timeframe")),
        _check_range("MA fastPeriod", ma.get("fastPeriod"), 2, 80),
        _check_range("MA slowPeriod", ma.get("slowPeriod"), 3, 240),
        _check_timeframe("Bollinger", bollinger.get("timeframe")),
        _check_range("Bollinger period", bollinger.get("period"), 5, 120),
        _check_range("Bollinger deviations", bollinger.get("deviations"), 0.5, 4.0),
        _check_range("Bollinger reclaimBufferPips", bollinger.get("reclaimBufferPips"), 0, 30),
        _check_timeframe("MACD", macd.get("timeframe")),
        _check_range("MACD fastPeriod", macd.get("fastPeriod"), 2, 80),
        _check_range("MACD slowPeriod", macd.get("slowPeriod"), 3, 160),
        _check_range("MACD signalPeriod", macd.get("signalPeriod"), 2, 80),
        _check_range("MACD minHistogramAbs", macd.get("minHistogramAbs"), 0, 1.0),
        _check_timeframe("Support/Resistance", support_resistance.get("timeframe")),
        _check_range("Support/Resistance lookbackBars", support_resistance.get("lookbackBars"), 4, 240),
        _check_range("Support/Resistance breakoutBufferPips", support_resistance.get("breakoutBufferPips"), 0, 50),
        _check_timeframe("Tokyo range", tokyo_range.get("timeframe")),
        _check_range("Tokyo rangeStartHourUtc", tokyo_range.get("rangeStartHourUtc"), 0, 23),
        _check_range("Tokyo rangeEndHourUtc", tokyo_range.get("rangeEndHourUtc"), 0, 23),
        _check_range("Tokyo tradeStartHourUtc", tokyo_range.get("tradeStartHourUtc"), 0, 23),
        _check_range("Tokyo tradeEndHourUtc", tokyo_range.get("tradeEndHourUtc"), 0, 23),
        _check_range("Tokyo lookbackBars", tokyo_range.get("lookbackBars"), 2, 96),
        _check_range("Tokyo bufferPips", tokyo_range.get("bufferPips"), 0, 50),
        _check_timeframe("Night reversion", night_reversion.get("timeframe")),
        _check_range("Night startHourUtc", night_reversion.get("startHourUtc"), 0, 23),
        _check_range("Night endHourUtc", night_reversion.get("endHourUtc"), 0, 23),
        _check_range("Night bollingerPeriod", night_reversion.get("bollingerPeriod"), 5, 120),
        _check_range("Night deviations", night_reversion.get("deviations"), 0.5, 4.0),
        _check_range("Night entryBufferPips", night_reversion.get("entryBufferPips"), 0, 30),
        _check_timeframe("H4 pullback", h4_pullback.get("timeframe")),
        _check_range("H4 fastEmaPeriod", h4_pullback.get("fastEmaPeriod"), 2, 120),
        _check_range("H4 slowEmaPeriod", h4_pullback.get("slowEmaPeriod"), 3, 240),
        _check_range("H4 pullbackEmaPeriod", h4_pullback.get("pullbackEmaPeriod"), 2, 120),
        _check_range("H4 rsiPeriod", h4_pullback.get("rsiPeriod"), 2, 50),
        _check_range("H4 longRsiMin", h4_pullback.get("longRsiMin"), 5, 65),
        _check_range("H4 shortRsiMax", h4_pullback.get("shortRsiMax"), 35, 95),
        _check_range("breakevenDelayR", (data.get("exit") or {}).get("breakevenDelayR"), 0, 3),
        _check_range("trailStartR", (data.get("exit") or {}).get("trailStartR"), 0, 5),
        _check_range("mfeGivebackPct", (data.get("exit") or {}).get("mfeGivebackPct"), 0.1, 0.9),
    ]
    for ok, reason in checks:
        if not ok:
            return _reject(data, "PARAM_RANGE_INVALID", reason)
    if _num(ma.get("fastPeriod"), 9) >= _num(ma.get("slowPeriod"), 21):
        return _reject(data, "PARAM_RANGE_INVALID", "MA fastPeriod 必须小于 slowPeriod")
    if _num(macd.get("fastPeriod"), 12) >= _num(macd.get("slowPeriod"), 26):
        return _reject(data, "PARAM_RANGE_INVALID", "MACD fastPeriod 必须小于 slowPeriod")
    if _num(h4_pullback.get("fastEmaPeriod"), 20) >= _num(h4_pullback.get("slowEmaPeriod"), 50):
        return _reject(data, "PARAM_RANGE_INVALID", "H4 fastEmaPeriod 必须小于 slowEmaPeriod")

    return {
        "seedId": data.get("seedId"),
        "valid": True,
        "blockerCode": None,
        "reasonZh": "Strategy JSON 合法；可进入 GA replay / walk-forward 评分",
        "normalized": data,
    }
