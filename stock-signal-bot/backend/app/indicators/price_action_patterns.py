from math import isfinite
from typing import Any, Dict, List, Optional


DISCLAIMER = (
    "Rule-based candle descriptions are heuristic and uncalibrated. "
    "They are not price forecasts or trade recommendations; wait for confirmation."
)


def _validate_series(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
) -> None:
    lengths = {len(opens), len(highs), len(lows), len(closes), len(volumes)}
    if len(lengths) != 1:
        raise ValueError("OHLCV series must have matching lengths")

    for index, (open_price, high, low, close, volume) in enumerate(
        zip(opens, highs, lows, closes, volumes)
    ):
        values = (open_price, high, low, close, volume)
        if not all(isfinite(value) for value in values):
            raise ValueError(f"OHLCV candle {index} contains a non-finite value")
        if low <= 0 or volume < 0 or high < max(open_price, close) or low > min(open_price, close) or high < low:
            raise ValueError(f"OHLCV candle {index} is inconsistent")


def _pattern(
    name: str,
    pattern_type: str,
    direction: str,
    explanation: str,
    confirmation_level: Optional[float],
    invalidation_level: Optional[float],
    status: str = "detected",
) -> Dict[str, Any]:
    return {
        "name": name,
        "type": pattern_type,
        "direction": direction,
        "status": status,
        "explanation": explanation,
        "confirmation_level": round(confirmation_level, 2) if confirmation_level is not None else None,
        "invalidation_level": round(invalidation_level, 2) if invalidation_level is not None else None,
    }


from app.indicators.flag_patterns import find_flag_pattern


def _find_flag(
    highs: List[float],
    lows: List[float],
    closes: List[float],
) -> Optional[Dict[str, Any]]:
    return find_flag_pattern(highs, lows, closes, _pattern)


def detect_price_action_patterns(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
) -> List[Dict[str, Any]]:
    """Describe selected patterns on completed candles without producing a trade signal."""
    _validate_series(opens, highs, lows, closes, volumes)
    if len(closes) < 3:
        return []

    patterns: List[Dict[str, Any]] = []
    candle_range = highs[-1] - lows[-1]
    if candle_range <= 0:
        return patterns

    body = abs(closes[-1] - opens[-1])
    upper_wick = highs[-1] - max(opens[-1], closes[-1])
    lower_wick = min(opens[-1], closes[-1]) - lows[-1]
    context = closes[-2] - closes[-min(6, len(closes))]
    recent_ranges = [highs[index] - lows[index] for index in range(max(0, len(highs) - 20), len(highs) - 1)]
    average_range = sum(recent_ranges) / len(recent_ranges) if recent_ranges else candle_range
    downtrend = context <= -0.8 * average_range
    uptrend = context >= 0.8 * average_range

    if body <= 0.1 * candle_range:
        patterns.append(_pattern(
            "Doji",
            "DOJI",
            "NEUTRAL",
            "Open and close are very close relative to this candle's range, suggesting indecision. A doji alone does not identify direction; watch for a completed close beyond its high or low.",
            highs[-1],
            lows[-1],
        ))

    if downtrend and body > 0 and lower_wick >= 2 * body and upper_wick <= max(0.5 * body, 0.08 * candle_range):
        patterns.append(_pattern(
            "Hammer",
            "HAMMER",
            "BULLISH",
            "After a short-term decline, the long lower wick and close away from the low can indicate rejection of lower prices. It is not confirmed until a later completed candle closes above the hammer high.",
            highs[-1],
            lows[-1],
        ))
    elif uptrend and body > 0 and upper_wick >= 2 * body and lower_wick <= max(0.5 * body, 0.08 * candle_range):
        patterns.append(_pattern(
            "Shooting star",
            "SHOOTING_STAR",
            "BEARISH",
            "After a short-term rise, the long upper wick and close away from the high can indicate rejection of higher prices. It is not confirmed until a later completed candle closes below the candle low.",
            lows[-1],
            highs[-1],
        ))

    if len(closes) >= 5:
        prior_context = closes[-3] - closes[-5]
        previous_bearish = closes[-2] < opens[-2]
        previous_bullish = closes[-2] > opens[-2]
        current_bullish = closes[-1] > opens[-1]
        current_bearish = closes[-1] < opens[-1]
        if downtrend and prior_context < 0 and previous_bearish and current_bullish and opens[-1] <= closes[-2] and closes[-1] >= opens[-2]:
            patterns.append(_pattern(
                "Bullish engulfing",
                "BULLISH_ENGULFING",
                "BULLISH",
                "The latest bullish real body covers the previous bearish real body after a decline. Confirmation requires follow-through above the pattern high; candle bodies, not full wicks, define this rule.",
                highs[-1],
                lows[-1],
            ))
        elif uptrend and prior_context > 0 and previous_bullish and current_bearish and opens[-1] >= closes[-2] and closes[-1] <= opens[-2]:
            patterns.append(_pattern(
                "Bearish engulfing",
                "BEARISH_ENGULFING",
                "BEARISH",
                "The latest bearish real body covers the previous bullish real body after a rise. Confirmation requires follow-through below the pattern low; candle bodies, not full wicks, define this rule.",
                lows[-1],
                highs[-1],
            ))

    flag = _find_flag(highs, lows, closes)
    if flag:
        patterns.append(flag)
    return patterns
