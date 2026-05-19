from __future__ import annotations

from typing import Any, Dict, List, Tuple

try:
    from tools.strategy_json.normalizer import normalize_strategy_json
    from tools.strategy_json.validator import validate_strategy_json
except ModuleNotFoundError:  # pragma: no cover
    from strategy_json.normalizer import normalize_strategy_json
    from strategy_json.validator import validate_strategy_json

from .cost_model import BacktestCostModel, cost_model_from_strategy
from .historical_news import classify_historical_news
from .indicators import bollinger_bands, ema_values, macd_values, rsi_values
from .metrics import summarize_trades
from .sqlite_store import Bar


SUPPORTED_BACKTEST_FAMILIES = {
    "RSI_Reversal",
    "MA_Cross",
    "BB_Triple",
    "MACD_Divergence",
    "SR_Breakout",
    "USDJPY_TOKYO_RANGE_BREAKOUT",
    "USDJPY_NIGHT_REVERSION_SAFE",
    "USDJPY_H4_TREND_PULLBACK",
}


def run_strategy(
    seed: Dict[str, Any],
    bars: List[Bar] | Dict[str, List[Bar]],
    historical_news: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    validation = validate_strategy_json(seed)
    if not validation.get("valid"):
        return {
            "ok": False,
            "validation": validation,
            "trades": [],
            "equityCurve": [],
            "metrics": {},
            "reasonZh": "Strategy JSON 未通过安全校验，不能回测",
        }
    strategy = normalize_strategy_json(seed)
    bars_by_timeframe = _normalize_bars_input(bars)
    primary_timeframe = _primary_timeframe(strategy, bars_by_timeframe)
    primary_bars = bars_by_timeframe.get(primary_timeframe, [])
    if len(primary_bars) < 40:
        return {
            "ok": False,
            "validation": validation,
            "strategyJson": strategy,
            "trades": [],
            "equityCurve": [],
            "metrics": {},
            "reasonZh": "USDJPY H1 K线样本不足，无法生成高保真回测",
        }
    family = str(strategy.get("strategyFamily") or "")
    if family not in SUPPORTED_BACKTEST_FAMILIES:
        return _research_only_result(strategy, validation)

    cost_model = cost_model_from_strategy(strategy)
    signals = _entry_signals(strategy, primary_bars, bars_by_timeframe)
    trades, gate_stats = _run_entries(strategy, primary_bars, signals, cost_model, historical_news or {})
    equity_curve: List[float] = []
    running = 0.0
    for trade in trades:
        running += float(trade["profitR"])
        equity_curve.append(round(running, 4))
    return {
        "ok": True,
        "validation": validation,
        "strategyJson": strategy,
        "trades": trades,
        "equityCurve": equity_curve,
        "metrics": summarize_trades(trades, equity_curve),
        "reasonZh": "Strategy JSON 已按 USDJPY 多策略因果规则完成回测",
        "engine": {
            "schema": "quantgod.strategy_backtest_engine.v2",
            "coverage": "ALL_SUPPORTED_USDJPY_SHADOW_FAMILIES",
            "primaryTimeframe": primary_timeframe,
            "supportedFamilies": sorted(SUPPORTED_BACKTEST_FAMILIES),
            "signalCount": len(signals),
            "newsGateBacktest": gate_stats,
            "costModel": cost_model.to_payload(),
            "parityVector": _parity_vector(strategy, primary_bars, signals),
        },
    }


def _research_only_result(strategy: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "validation": validation,
        "strategyJson": strategy,
        "trades": [],
        "equityCurve": [],
        "metrics": summarize_trades([], []),
        "reasonZh": "该策略族暂未接入高保真 runner；保留为 shadow research",
    }


def _normalize_bars_input(bars: List[Bar] | Dict[str, List[Bar]]) -> Dict[str, List[Bar]]:
    if isinstance(bars, dict):
        return {str(key).upper(): value for key, value in bars.items() if isinstance(value, list)}
    return {"H1": bars}


def _primary_timeframe(strategy: Dict[str, Any], bars_by_timeframe: Dict[str, List[Bar]]) -> str:
    family = str(strategy.get("strategyFamily") or "")
    indicators = strategy.get("indicators") if isinstance(strategy.get("indicators"), dict) else {}
    cfg_key = {
        "RSI_Reversal": "rsi",
        "MA_Cross": "ma",
        "BB_Triple": "bollinger",
        "MACD_Divergence": "macd",
        "SR_Breakout": "supportResistance",
        "USDJPY_TOKYO_RANGE_BREAKOUT": "tokyoRange",
        "USDJPY_NIGHT_REVERSION_SAFE": "nightReversion",
        "USDJPY_H4_TREND_PULLBACK": "h4Pullback",
    }.get(family, "rsi")
    family_cfg = indicators.get(cfg_key) if isinstance(indicators.get(cfg_key), dict) else {}
    preferred = str(family_cfg.get("timeframe") or "H1").upper()
    if len(bars_by_timeframe.get(preferred, [])) >= 40:
        return preferred
    for candidate in ("H1", "M15", "M5", "M1", "H4", "D1"):
        if len(bars_by_timeframe.get(candidate, [])) >= 40:
            return candidate
    return preferred


def _entry_signals(strategy: Dict[str, Any], bars: List[Bar], bars_by_timeframe: Dict[str, List[Bar]]) -> List[Dict[str, Any]]:
    family = str(strategy.get("strategyFamily") or "")
    if family == "RSI_Reversal":
        return _rsi_signals(strategy, bars)
    if family == "MA_Cross":
        return _ma_cross_signals(strategy, bars)
    if family == "BB_Triple":
        return _bb_triple_signals(strategy, bars)
    if family == "MACD_Divergence":
        return _macd_signals(strategy, bars)
    if family == "SR_Breakout":
        return _sr_breakout_signals(strategy, bars)
    if family == "USDJPY_TOKYO_RANGE_BREAKOUT":
        return _tokyo_breakout_signals(strategy, bars)
    if family == "USDJPY_NIGHT_REVERSION_SAFE":
        return _night_reversion_signals(strategy, bars)
    if family == "USDJPY_H4_TREND_PULLBACK":
        return _h4_pullback_signals(strategy, bars, bars_by_timeframe)
    return []


def _rsi_signals(strategy: Dict[str, Any], bars: List[Bar]) -> List[Dict[str, Any]]:
    rsi_cfg = ((strategy.get("indicators") or {}).get("rsi") or {})
    exit_cfg = strategy.get("exit") if isinstance(strategy.get("exit"), dict) else {}
    period = int(float(rsi_cfg.get("period", 14)))
    buy_band = float(rsi_cfg.get("buyBand", 34))
    sell_band = float(rsi_cfg.get("sellBand", max(55.0, 100.0 - buy_band)))
    crossback_threshold = float(rsi_cfg.get("crossbackThreshold", 0.8))
    max_crossback_rsi = _float_param(rsi_cfg, "maxCrossbackRsi", 100.0, 20.0, 100.0)
    adverse_guard = _rsi_adverse_guard_cfg(strategy)

    closes = [item.close for item in bars]
    rsi_series = rsi_values(closes, period)
    regime_cfg = rsi_cfg.get("regimeFilter") if isinstance(rsi_cfg.get("regimeFilter"), dict) else {}
    fast_period = _int_param(regime_cfg, "emaFastPeriod", 20, 2, 120)
    slow_period = _int_param(regime_cfg, "emaSlowPeriod", 50, fast_period + 1, 240)
    fast_ema = ema_values(closes, fast_period) if _rsi_regime_filter_enabled(regime_cfg) else []
    slow_ema = ema_values(closes, slow_period) if _rsi_regime_filter_enabled(regime_cfg) else []
    signals: List[Dict[str, Any]] = []
    index = period + 1
    while index < len(bars) - 2:
        previous_rsi = rsi_series[index - 1]
        current_rsi = rsi_series[index]
        if previous_rsi is None or current_rsi is None:
            index += 1
            continue
        long_cross = previous_rsi <= buy_band and current_rsi >= buy_band + crossback_threshold
        short_cross = previous_rsi >= sell_band and current_rsi <= sell_band - crossback_threshold
        direction = str(strategy.get("direction") or "LONG").upper()
        if direction == "LONG" and long_cross and current_rsi > max_crossback_rsi:
            index += 1
            continue
        if (direction == "LONG" and long_cross) or (direction == "SHORT" and short_cross):
            regime = _rsi_regime_decision(bars, index, direction, regime_cfg, fast_ema, slow_ema)
            if not regime.get("allowed", True):
                index += 1
                continue
            volatility = _rsi_entry_volatility_decision(bars, index, adverse_guard)
            if not volatility.get("allowed", True):
                index += 1
                continue
            evidence = {"rsi": round(current_rsi, 4)}
            if regime.get("enabled"):
                evidence["regimeFilter"] = regime.get("mode")
                evidence["fastMinusSlowPips"] = regime.get("fastMinusSlowPips")
                evidence["distanceFromSlowPips"] = regime.get("distanceFromSlowPips")
                evidence["slowSlopePips"] = regime.get("slowSlopePips")
            if volatility.get("enabled"):
                evidence["adverseExcursionGuard"] = adverse_guard.get("mode")
                evidence["entryRangePips"] = volatility.get("entryRangePips")
            signals.append(_signal(index + 1, direction, "RSI_CROSSBACK", evidence))
            index += 3
        else:
            index += 1
    return signals


def _rsi_regime_filter_enabled(regime_cfg: Dict[str, Any]) -> bool:
    return bool(regime_cfg) and str(regime_cfg.get("mode") or "OFF").upper() not in {"", "OFF", "NONE"}


def _rsi_regime_decision(
    bars: List[Bar],
    index: int,
    direction: str,
    regime_cfg: Dict[str, Any],
    fast_ema: List[float | None],
    slow_ema: List[float | None],
) -> Dict[str, Any]:
    if not _rsi_regime_filter_enabled(regime_cfg):
        return {"enabled": False, "allowed": True}
    mode = str(regime_cfg.get("mode") or "").upper()
    allowed_hours = regime_cfg.get("allowedHoursUtc") if isinstance(regime_cfg.get("allowedHoursUtc"), list) else []
    hour = _hour_utc(bars[index].timestamp)
    if allowed_hours and hour not in _allowed_hours(allowed_hours):
        return {"enabled": True, "allowed": False, "mode": mode, "reason": "HOUR_FILTER"}
    if index >= len(fast_ema) or index >= len(slow_ema) or fast_ema[index] is None or slow_ema[index] is None:
        return {"enabled": True, "allowed": False, "mode": mode, "reason": "EMA_NOT_READY"}

    pip_size = 0.01
    lookback = _int_param(regime_cfg, "slopeLookbackBars", 3, 1, 24)
    lookback_index = max(0, index - lookback)
    slow_now = float(slow_ema[index] or 0.0)
    slow_then = slow_ema[lookback_index]
    if slow_then is None:
        return {"enabled": True, "allowed": False, "mode": mode, "reason": "SLOPE_NOT_READY"}

    close = float(bars[index].close)
    fast_minus_slow = (float(fast_ema[index] or 0.0) - slow_now) / pip_size
    distance_from_slow = (close - slow_now) / pip_size
    slow_slope = (slow_now - float(slow_then)) / pip_size
    min_fast_minus_slow = _float_param(regime_cfg, "minFastMinusSlowPips", -500.0, -1000.0, 1000.0)
    max_fast_minus_slow = _float_param(regime_cfg, "maxFastMinusSlowPips", 0.0, -1000.0, 1000.0)
    min_distance = _float_param(regime_cfg, "minDistanceFromSlowPips", -260.0, -1000.0, 1000.0)
    max_distance = _float_param(regime_cfg, "maxDistanceFromSlowPips", -50.0, -1000.0, 1000.0)
    min_slope = _float_param(regime_cfg, "minSlowSlopePips", -45.0, -1000.0, 1000.0)
    max_slope = _float_param(regime_cfg, "maxSlowSlopePips", -6.0, -1000.0, 1000.0)

    allowed = True
    reason = "PASS"
    if mode == "P4_10E_RSI_BEARISH_STRETCH":
        allowed = (
            direction == "LONG"
            and min_fast_minus_slow <= fast_minus_slow <= max_fast_minus_slow
            and min_distance <= distance_from_slow <= max_distance
            and min_slope <= slow_slope <= max_slope
        )
        if not allowed:
            reason = "BEARISH_STRETCH_FILTER"
    return {
        "enabled": True,
        "allowed": allowed,
        "mode": mode,
        "reason": reason,
        "fastMinusSlowPips": round(fast_minus_slow, 2),
        "distanceFromSlowPips": round(distance_from_slow, 2),
        "slowSlopePips": round(slow_slope, 2),
    }


def _allowed_hours(values: List[Any]) -> set[int]:
    hours: set[int] = set()
    for value in values:
        try:
            hour = int(float(value))
        except Exception:
            continue
        if 0 <= hour <= 23:
            hours.add(hour)
    return hours


def _ma_cross_signals(strategy: Dict[str, Any], bars: List[Bar]) -> List[Dict[str, Any]]:
    ma_cfg = _indicator_cfg(strategy, "ma")
    fast_period = _int_param(ma_cfg, "fastPeriod", 9, 2, 80)
    slow_period = _int_param(ma_cfg, "slowPeriod", 21, fast_period + 1, 240)
    closes = [item.close for item in bars]
    fast = ema_values(closes, fast_period)
    slow = ema_values(closes, slow_period)
    direction = str(strategy.get("direction") or "LONG").upper()
    signals: List[Dict[str, Any]] = []
    for index in range(slow_period + 1, len(bars) - 2):
        if None in (fast[index - 1], slow[index - 1], fast[index], slow[index]):
            continue
        long_cross = fast[index - 1] <= slow[index - 1] and fast[index] > slow[index]
        short_cross = fast[index - 1] >= slow[index - 1] and fast[index] < slow[index]
        if (direction == "LONG" and long_cross) or (direction == "SHORT" and short_cross):
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "EMA_CROSS",
                    {"fastEma": fast[index], "slowEma": slow[index], "fastPeriod": fast_period, "slowPeriod": slow_period},
                )
            )
    return signals


def _bb_triple_signals(strategy: Dict[str, Any], bars: List[Bar]) -> List[Dict[str, Any]]:
    bb_cfg = _indicator_cfg(strategy, "bollinger")
    period = _int_param(bb_cfg, "period", 20, 5, 120)
    deviations = _float_param(bb_cfg, "deviations", 2.0, 0.5, 4.0)
    reclaim_buffer_pips = _float_param(bb_cfg, "reclaimBufferPips", 0.0, 0.0, 30.0)
    reclaim_buffer = reclaim_buffer_pips * 0.01
    closes = [item.close for item in bars]
    bands = bollinger_bands(closes, period, deviations)
    direction = str(strategy.get("direction") or "LONG").upper()
    signals: List[Dict[str, Any]] = []
    for index in range(period + 1, len(bars) - 2):
        lower, mid, upper = bands[index]
        if lower is None or mid is None or upper is None:
            continue
        previous_close = closes[index - 1]
        current_close = closes[index]
        long_reclaim = previous_close < lower and current_close > lower + reclaim_buffer
        short_reclaim = previous_close > upper and current_close < upper - reclaim_buffer
        if (direction == "LONG" and long_reclaim) or (direction == "SHORT" and short_reclaim):
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "BOLLINGER_RECLAIM",
                    {"lower": lower, "mid": mid, "upper": upper, "period": period, "deviations": deviations},
                )
            )
    return signals


def _macd_signals(strategy: Dict[str, Any], bars: List[Bar]) -> List[Dict[str, Any]]:
    macd_cfg = _indicator_cfg(strategy, "macd")
    fast_period = _int_param(macd_cfg, "fastPeriod", 12, 2, 80)
    slow_period = _int_param(macd_cfg, "slowPeriod", 26, fast_period + 1, 160)
    signal_period = _int_param(macd_cfg, "signalPeriod", 9, 2, 80)
    min_histogram_abs = _float_param(macd_cfg, "minHistogramAbs", 0.0, 0.0, 1.0)
    closes = [item.close for item in bars]
    macd = macd_values(closes, fast_period, slow_period, signal_period)
    direction = str(strategy.get("direction") or "LONG").upper()
    signals: List[Dict[str, Any]] = []
    for index in range(slow_period + signal_period, len(bars) - 2):
        previous_hist = macd[index - 1][2]
        current_hist = macd[index][2]
        if previous_hist is None or current_hist is None:
            continue
        long_cross = previous_hist <= 0 < current_hist
        short_cross = previous_hist >= 0 > current_hist
        if abs(float(current_hist)) < min_histogram_abs:
            continue
        if (direction == "LONG" and long_cross) or (direction == "SHORT" and short_cross):
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "MACD_HISTOGRAM_CROSS",
                    {
                        "histogram": current_hist,
                        "fastPeriod": fast_period,
                        "slowPeriod": slow_period,
                        "signalPeriod": signal_period,
                    },
                )
            )
    return signals


def _sr_breakout_signals(strategy: Dict[str, Any], bars: List[Bar]) -> List[Dict[str, Any]]:
    sr_cfg = _indicator_cfg(strategy, "supportResistance")
    direction = str(strategy.get("direction") or "LONG").upper()
    lookback = _int_param(sr_cfg, "lookbackBars", 24, 4, 240)
    buffer_pips = _float_param(sr_cfg, "breakoutBufferPips", 0.0, 0.0, 50.0)
    buffer_price = buffer_pips * 0.01
    signals: List[Dict[str, Any]] = []
    for index in range(lookback, len(bars) - 2):
        window = bars[index - lookback : index]
        resistance = max(item.high for item in window)
        support = min(item.low for item in window)
        long_break = bars[index].close > resistance + buffer_price
        short_break = bars[index].close < support - buffer_price
        if (direction == "LONG" and long_break) or (direction == "SHORT" and short_break):
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "SR_BREAKOUT",
                    {"support": support, "resistance": resistance, "lookbackBars": lookback, "bufferPips": buffer_pips},
                )
            )
    return signals


def _tokyo_breakout_signals(strategy: Dict[str, Any], bars: List[Bar]) -> List[Dict[str, Any]]:
    tokyo_cfg = _indicator_cfg(strategy, "tokyoRange")
    range_hours = _hour_window(
        _int_param(tokyo_cfg, "rangeStartHourUtc", 0, 0, 23),
        _int_param(tokyo_cfg, "rangeEndHourUtc", 2, 0, 23),
    )
    trade_hours = _hour_window(
        _int_param(tokyo_cfg, "tradeStartHourUtc", 3, 0, 23),
        _int_param(tokyo_cfg, "tradeEndHourUtc", 6, 0, 23),
    )
    lookback = _int_param(tokyo_cfg, "lookbackBars", 8, 2, 96)
    buffer_pips = _float_param(tokyo_cfg, "bufferPips", 0.0, 0.0, 50.0)
    buffer_price = buffer_pips * 0.01
    direction = str(strategy.get("direction") or "LONG").upper()
    signals: List[Dict[str, Any]] = []
    for index in range(max(lookback + 1, 12), len(bars) - 2):
        hour = _hour_utc(bars[index].timestamp)
        if hour not in trade_hours:
            continue
        asian_window = [item for item in bars[max(0, index - lookback) : index] if _hour_utc(item.timestamp) in range_hours]
        if len(asian_window) < 2:
            continue
        high = max(item.high for item in asian_window)
        low = min(item.low for item in asian_window)
        if direction == "LONG" and bars[index].close > high + buffer_price:
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "TOKYO_RANGE_BREAKOUT",
                    {"rangeHigh": high, "rangeLow": low, "bufferPips": buffer_pips},
                )
            )
        if direction == "SHORT" and bars[index].close < low - buffer_price:
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "TOKYO_RANGE_BREAKOUT",
                    {"rangeHigh": high, "rangeLow": low, "bufferPips": buffer_pips},
                )
            )
    return signals


def _night_reversion_signals(strategy: Dict[str, Any], bars: List[Bar]) -> List[Dict[str, Any]]:
    night_cfg = _indicator_cfg(strategy, "nightReversion")
    active_hours = _hour_window(
        _int_param(night_cfg, "startHourUtc", 20, 0, 23),
        _int_param(night_cfg, "endHourUtc", 2, 0, 23),
    )
    period = _int_param(night_cfg, "bollingerPeriod", 20, 5, 120)
    deviations = _float_param(night_cfg, "deviations", 1.8, 0.5, 4.0)
    entry_buffer_pips = _float_param(night_cfg, "entryBufferPips", 0.0, 0.0, 30.0)
    entry_buffer = entry_buffer_pips * 0.01
    closes = [item.close for item in bars]
    bands = bollinger_bands(closes, period, deviations)
    direction = str(strategy.get("direction") or "LONG").upper()
    signals: List[Dict[str, Any]] = []
    for index in range(period + 1, len(bars) - 2):
        hour = _hour_utc(bars[index].timestamp)
        if hour not in active_hours:
            continue
        lower, _, upper = bands[index]
        if lower is None or upper is None:
            continue
        if direction == "LONG" and closes[index] <= lower - entry_buffer:
            signals.append(_signal(index + 1, direction, "NIGHT_REVERSION_LOWER_BAND", {"lower": lower, "deviations": deviations}))
        if direction == "SHORT" and closes[index] >= upper + entry_buffer:
            signals.append(_signal(index + 1, direction, "NIGHT_REVERSION_UPPER_BAND", {"upper": upper, "deviations": deviations}))
    return signals


def _h4_pullback_signals(strategy: Dict[str, Any], bars: List[Bar], bars_by_timeframe: Dict[str, List[Bar]]) -> List[Dict[str, Any]]:
    h4_cfg = _indicator_cfg(strategy, "h4Pullback")
    fast_period = _int_param(h4_cfg, "fastEmaPeriod", 20, 2, 120)
    slow_period = _int_param(h4_cfg, "slowEmaPeriod", 50, fast_period + 1, 240)
    pullback_period = _int_param(h4_cfg, "pullbackEmaPeriod", fast_period, 2, 120)
    rsi_period = _int_param(h4_cfg, "rsiPeriod", 14, 2, 50)
    long_rsi_min = _float_param(h4_cfg, "longRsiMin", 38.0, 5.0, 65.0)
    short_rsi_max = _float_param(h4_cfg, "shortRsiMax", 62.0, 35.0, 95.0)
    closes = [item.close for item in bars]
    fast_ema = ema_values(closes, fast_period)
    slow_ema = ema_values(closes, slow_period)
    pullback_ema = ema_values(closes, pullback_period)
    rsi_series = rsi_values(closes, rsi_period)
    direction = str(strategy.get("direction") or "LONG").upper()
    signals: List[Dict[str, Any]] = []
    start_index = max(slow_period, pullback_period, rsi_period) + 1
    for index in range(start_index, len(bars) - 2):
        if fast_ema[index] is None or slow_ema[index] is None or pullback_ema[index] is None or rsi_series[index] is None:
            continue
        trend_long = fast_ema[index] > slow_ema[index]
        trend_short = fast_ema[index] < slow_ema[index]
        pullback_long = bars[index].low <= pullback_ema[index] <= bars[index].close
        pullback_short = bars[index].high >= pullback_ema[index] >= bars[index].close
        if direction == "LONG" and trend_long and pullback_long and rsi_series[index] >= long_rsi_min:
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "H4_TREND_PULLBACK",
                    {"fastEma": fast_ema[index], "slowEma": slow_ema[index], "pullbackEma": pullback_ema[index], "rsi": rsi_series[index]},
                )
            )
        if direction == "SHORT" and trend_short and pullback_short and rsi_series[index] <= short_rsi_max:
            signals.append(
                _signal(
                    index + 1,
                    direction,
                    "H4_TREND_PULLBACK",
                    {"fastEma": fast_ema[index], "slowEma": slow_ema[index], "pullbackEma": pullback_ema[index], "rsi": rsi_series[index]},
                )
            )
    return signals


def _indicator_cfg(strategy: Dict[str, Any], key: str) -> Dict[str, Any]:
    indicators = strategy.get("indicators") if isinstance(strategy.get("indicators"), dict) else {}
    return indicators.get(key) if isinstance(indicators.get(key), dict) else {}


def _int_param(config: Dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    try:
        value = int(float(config.get(key, default)))
    except Exception:
        value = default
    return max(low, min(high, value))


def _float_param(config: Dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    try:
        value = float(config.get(key, default))
    except Exception:
        value = default
    return max(low, min(high, value))


def _hour_window(start_hour: int, end_hour: int) -> set[int]:
    start = int(start_hour) % 24
    end = int(end_hour) % 24
    if start <= end:
        return set(range(start, end + 1))
    return set(range(start, 24)) | set(range(0, end + 1))


def _signal(index: int, direction: str, reason: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "entryIndex": index,
        "direction": direction,
        "reason": reason,
        "evidence": {key: round(value, 5) if isinstance(value, float) else value for key, value in evidence.items()},
    }


def _run_entries(
    strategy: Dict[str, Any],
    bars: List[Bar],
    signals: List[Dict[str, Any]],
    cost_model: BacktestCostModel,
    historical_news: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    exit_cfg = strategy.get("exit") if isinstance(strategy.get("exit"), dict) else {}
    hold_bars = int(((exit_cfg.get("timeStopBars") or {}).get("H1") or 4))
    giveback_pct = float(exit_cfg.get("mfeGivebackPct", 0.6))
    trail_start_r = float(exit_cfg.get("trailStartR", 1.5))
    risk_pips = float(((strategy.get("risk") or {}).get("riskPips") or 10.0))
    trades: List[Dict[str, Any]] = []
    gate_stats = {
        "schema": "quantgod.strategy_backtest_news_gate_stats.v1",
        "sourceAvailable": bool(historical_news.get("sourceAvailable")),
        "eventCount": int(historical_news.get("eventCount") or 0),
        "evaluatedSignals": 0,
        "hardBlockedSignals": 0,
        "eventFilteredSignals": 0,
        "softAdjustedTrades": 0,
        "unknownSignals": 0,
        "lotMultiplierSum": 0.0,
        "reasonZh": historical_news.get("reasonZh") or "历史新闻门禁未接入。",
    }
    event_filter = _event_filter_cfg(strategy)
    next_available_index = 0
    for signal in signals:
        entry_index = int(signal["entryIndex"])
        if entry_index < next_available_index or entry_index >= len(bars) - 1:
            continue
        news_decision = classify_historical_news(bars[entry_index].timestamp, historical_news)
        gate_stats["evaluatedSignals"] += 1
        if news_decision.get("riskLevel") == "UNKNOWN":
            gate_stats["unknownSignals"] += 1
        if news_decision.get("hardBlock"):
            gate_stats["hardBlockedSignals"] += 1
            continue
        if _event_filter_blocks(news_decision, event_filter):
            gate_stats["eventFilteredSignals"] += 1
            continue
        lot_multiplier = float(news_decision.get("lotMultiplier") or 1.0)
        gate_stats["lotMultiplierSum"] += lot_multiplier
        if lot_multiplier < 1.0 or news_decision.get("stageDowngrade"):
            gate_stats["softAdjustedTrades"] += 1
        trade, exit_index = _simulate_exit(
            strategy,
            bars,
            entry_index=entry_index,
            direction=signal["direction"],
            hold_bars=hold_bars,
            risk_pips=risk_pips,
            trail_start_r=trail_start_r,
            giveback_pct=giveback_pct,
            trade_no=len(trades) + 1,
            signal=signal,
            cost_model=cost_model,
            news_decision=news_decision,
        )
        trades.append(trade)
        next_available_index = exit_index + 1
    if trades:
        gate_stats["avgLotMultiplier"] = round(gate_stats["lotMultiplierSum"] / len(trades), 4)
    else:
        gate_stats["avgLotMultiplier"] = 0.0
    gate_stats.pop("lotMultiplierSum", None)
    return trades, gate_stats


def _event_filter_cfg(strategy: Dict[str, Any]) -> Dict[str, Any]:
    entry = strategy.get("entry") if isinstance(strategy.get("entry"), dict) else {}
    config = entry.get("eventFilter") if isinstance(entry.get("eventFilter"), dict) else {}
    mode = str(config.get("mode") or "OFF").upper()
    if mode in {"", "OFF", "NONE"}:
        return {}
    return config


def _event_filter_blocks(news_decision: Dict[str, Any], event_filter: Dict[str, Any]) -> bool:
    if not event_filter:
        return False
    risk_level = str(news_decision.get("riskLevel") or "UNKNOWN").upper()
    if risk_level == "UNKNOWN" and bool(event_filter.get("allowUnknownRisk", True)):
        return False
    allowed_levels = {
        str(item or "").upper()
        for item in event_filter.get("allowedRiskLevels", [])
        if str(item or "").strip()
    }
    if allowed_levels and risk_level not in allowed_levels:
        return True
    if risk_level == "SOFT" and bool(event_filter.get("blockSoftRisk", False)):
        return True
    return False


def _rsi_adverse_guard_cfg(strategy: Dict[str, Any]) -> Dict[str, Any]:
    if str(strategy.get("strategyFamily") or "") != "RSI_Reversal":
        return {}
    rsi = ((strategy.get("indicators") or {}).get("rsi") or {})
    config = rsi.get("adverseExcursionGuard") if isinstance(rsi.get("adverseExcursionGuard"), dict) else {}
    mode = str(config.get("mode") or "OFF").upper()
    if mode in {"", "OFF", "NONE"}:
        return {}
    return config


def _rsi_entry_volatility_decision(bars: List[Bar], index: int, guard_cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not guard_cfg:
        return {"enabled": False, "allowed": True}
    lookback = _int_param(guard_cfg, "rangeLookbackBars", 4, 1, 24)
    max_range_pips = _float_param(guard_cfg, "maxEntryRangePips", 60.0, 1.0, 240.0)
    entry_range_pips = _recent_average_range_pips(bars, index, lookback)
    return {
        "enabled": True,
        "allowed": entry_range_pips <= max_range_pips,
        "entryRangePips": round(entry_range_pips, 2),
        "maxEntryRangePips": round(max_range_pips, 2),
    }


def _recent_average_range_pips(bars: List[Bar], index: int, lookback: int) -> float:
    pip_size = 0.01
    start = max(0, index - max(1, lookback) + 1)
    window = bars[start : index + 1]
    if not window:
        return 0.0
    return sum(max(0.0, float(item.high) - float(item.low)) / pip_size for item in window) / len(window)


def _simulate_exit(
    strategy: Dict[str, Any],
    bars: List[Bar],
    entry_index: int,
    direction: str,
    hold_bars: int,
    risk_pips: float,
    trail_start_r: float,
    giveback_pct: float,
    trade_no: int,
    signal: Dict[str, Any],
    cost_model: BacktestCostModel,
    news_decision: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    entry = bars[entry_index]
    entry_price = entry.open
    pip_size = 0.01
    risk_price = risk_pips * pip_size
    signed = 1.0 if direction == "LONG" else -1.0
    stop_price = entry_price - (signed * risk_price)
    max_profit_pips = 0.0
    max_loss_pips = 0.0
    exit_bar = entry
    exit_price = entry.close
    exit_reason = "TIME_STOP"
    adverse_guard = _rsi_adverse_guard_cfg(strategy)
    last_index = min(len(bars) - 1, entry_index + max(1, hold_bars))
    for index in range(entry_index, last_index + 1):
        bar = bars[index]
        elapsed_bars = index - entry_index
        high_profit = signed * (bar.high - entry_price) / pip_size
        low_profit = signed * (bar.low - entry_price) / pip_size
        if direction == "SHORT":
            high_profit, low_profit = low_profit, high_profit
        max_profit_pips = max(max_profit_pips, high_profit)
        max_loss_pips = min(max_loss_pips, low_profit)
        if adverse_guard and elapsed_bars <= _int_param(adverse_guard, "lookaheadBars", 2, 1, 8):
            adverse_limit_r = _float_param(adverse_guard, "maxEarlyAdverseR", 0.8, 0.2, 2.0)
            guard_price = entry_price - signed * (adverse_limit_r * risk_price)
            guard_hit = bar.low <= guard_price if direction == "LONG" else bar.high >= guard_price
            if guard_hit:
                exit_bar = bar
                exit_price = guard_price
                exit_reason = "RSI_EARLY_ADVERSE_KILL"
                max_loss_pips = max(max_loss_pips, -adverse_limit_r * risk_pips)
                last_index = index
                break
        stop_hit = bar.low <= stop_price if direction == "LONG" else bar.high >= stop_price
        if stop_hit:
            exit_bar = bar
            exit_price = stop_price
            exit_reason = "STOP_LOSS"
            last_index = index
            break
        if adverse_guard and elapsed_bars >= _int_param(adverse_guard, "confirmationBars", 2, 1, 8):
            min_confirm_r = _float_param(adverse_guard, "minConfirmR", 0.05, -0.5, 1.5)
            current_profit_pips = signed * (bar.close - entry_price) / pip_size
            if max_profit_pips / risk_pips < min_confirm_r and current_profit_pips <= 0:
                exit_bar = bar
                exit_price = bar.close
                exit_reason = "RSI_CONFIRMATION_TIMEOUT"
                last_index = index
                break
        if max_profit_pips / risk_pips >= trail_start_r:
            giveback_stop = entry_price + signed * (max_profit_pips * (1.0 - giveback_pct) * pip_size)
            giveback_hit = bar.low <= giveback_stop if direction == "LONG" else bar.high >= giveback_stop
            if giveback_hit:
                exit_bar = bar
                exit_price = giveback_stop
                exit_reason = "MFE_GIVEBACK"
                last_index = index
                break
        exit_bar = bar
        exit_price = bar.close
    gross_profit_pips = signed * (exit_price - entry_price) / pip_size
    cost_pips = cost_model.round_turn_pips_for_bar(entry)
    profit_pips = gross_profit_pips - cost_pips
    raw_profit_r = profit_pips / risk_pips
    lot_multiplier = max(0.0, min(1.0, float(news_decision.get("lotMultiplier") or 1.0)))
    profit_r = raw_profit_r * lot_multiplier
    return {
        "tradeId": f"BT-{trade_no:04d}",
        "symbol": "USDJPYc",
        "strategyFamily": strategy.get("strategyFamily"),
        "direction": direction,
        "signalReason": signal.get("reason"),
        "signalEvidence": signal.get("evidence", {}),
        "entryTime": entry.timestamp,
        "exitTime": exit_bar.timestamp,
        "entryPrice": round(entry_price, 5),
        "exitPrice": round(exit_price, 5),
        "exitReason": exit_reason,
        "riskPips": round(risk_pips, 3),
        "spreadPoints": round(float(getattr(entry, "spread", 0.0) or 0.0), 3),
        "spreadPips": round(cost_model.spread_pips_for_bar(entry), 3),
        "grossProfitPips": round(gross_profit_pips, 3),
        "costPips": round(cost_pips, 3),
        "profitPips": round(profit_pips, 3),
        "rawProfitR": round(raw_profit_r, 4),
        "profitR": round(profit_r, 4),
        "mfeR": round(max_profit_pips / risk_pips, 4),
        "maeR": round(max_loss_pips / risk_pips, 4),
        "newsRiskLevel": news_decision.get("riskLevel") or "NONE",
        "newsLotMultiplier": round(lot_multiplier, 4),
        "newsReasonZh": news_decision.get("reasonZh") or "",
    }, last_index


def _parity_vector(strategy: Dict[str, Any], bars: List[Bar], signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    last_signal = signals[-1] if signals else {}
    last_signal_index = int(last_signal["entryIndex"]) if last_signal else -1
    rsi_cfg = ((strategy.get("indicators") or {}).get("rsi") or {})
    entry_cfg = strategy.get("entry") if isinstance(strategy.get("entry"), dict) else {}
    exit_cfg = strategy.get("exit") if isinstance(strategy.get("exit"), dict) else {}
    risk_cfg = strategy.get("risk") if isinstance(strategy.get("risk"), dict) else {}
    indicators = strategy.get("indicators") if isinstance(strategy.get("indicators"), dict) else {}
    return {
        "schema": "quantgod.strategy_parity_vector.v1",
        "strategyId": strategy.get("strategyId"),
        "seedId": strategy.get("seedId"),
        "symbol": strategy.get("symbol"),
        "strategyFamily": strategy.get("strategyFamily"),
        "direction": strategy.get("direction"),
        "entryMode": entry_cfg.get("mode"),
        "entryConditions": entry_cfg.get("conditions") if isinstance(entry_cfg.get("conditions"), list) else [],
        "entryEventFilter": entry_cfg.get("eventFilter") if isinstance(entry_cfg.get("eventFilter"), dict) else {},
        "rsi": {
            "period": rsi_cfg.get("period"),
            "timeframe": rsi_cfg.get("timeframe"),
            "buyBand": rsi_cfg.get("buyBand"),
            "sellBand": rsi_cfg.get("sellBand"),
            "crossbackThreshold": rsi_cfg.get("crossbackThreshold"),
            "maxCrossbackRsi": rsi_cfg.get("maxCrossbackRsi"),
            "regimeFilter": rsi_cfg.get("regimeFilter") if isinstance(rsi_cfg.get("regimeFilter"), dict) else {},
            "adverseExcursionGuard": (
                rsi_cfg.get("adverseExcursionGuard") if isinstance(rsi_cfg.get("adverseExcursionGuard"), dict) else {}
            ),
        },
        "familyParameters": {
            "ma": indicators.get("ma") if isinstance(indicators.get("ma"), dict) else {},
            "bollinger": indicators.get("bollinger") if isinstance(indicators.get("bollinger"), dict) else {},
            "macd": indicators.get("macd") if isinstance(indicators.get("macd"), dict) else {},
            "supportResistance": indicators.get("supportResistance") if isinstance(indicators.get("supportResistance"), dict) else {},
            "tokyoRange": indicators.get("tokyoRange") if isinstance(indicators.get("tokyoRange"), dict) else {},
            "nightReversion": indicators.get("nightReversion") if isinstance(indicators.get("nightReversion"), dict) else {},
            "h4Pullback": indicators.get("h4Pullback") if isinstance(indicators.get("h4Pullback"), dict) else {},
        },
        "exit": {
            "breakevenDelayR": exit_cfg.get("breakevenDelayR"),
            "trailStartR": exit_cfg.get("trailStartR"),
            "mfeGivebackPct": exit_cfg.get("mfeGivebackPct"),
            "timeStopBars": exit_cfg.get("timeStopBars") if isinstance(exit_cfg.get("timeStopBars"), dict) else {},
        },
        "risk": {
            "maxLot": risk_cfg.get("maxLot"),
            "stage": risk_cfg.get("stage"),
            "opportunityLotMultiplier": risk_cfg.get("opportunityLotMultiplier"),
        },
        "barCount": len(bars),
        "lastSignalTime": bars[last_signal_index].timestamp if 0 <= last_signal_index < len(bars) else None,
        "lastSignalReason": last_signal.get("reason"),
        "lastSignalDirection": last_signal.get("direction"),
        "signalCount": len(signals),
    }


def _hour_utc(timestamp: str) -> int:
    try:
        return int(timestamp.split("T", 1)[1].split(":", 1)[0])
    except Exception:
        return -1
