from typing import List
from app.indicators.technicals import calculate_ema


def compute_trend_direction(closes: List[float]) -> str:
    """
    Determine trend direction for a given candle series using EMA alignment.

    Rules:
    - ``BULLISH``  if EMA-9 > EMA-21 **and** last close > EMA-9
    - ``BEARISH``  if EMA-9 < EMA-21 **and** last close < EMA-9
    - ``NEUTRAL``  otherwise (cross-over zone, insufficient bars, or flat)
    """
    if len(closes) < 22:
        return "NEUTRAL"

    ema_9 = calculate_ema(closes, 9)
    ema_21 = calculate_ema(closes, 21)

    if ema_9 is None or ema_21 is None:
        return "NEUTRAL"

    last_close = closes[-1]

    if ema_9 > ema_21 and last_close > ema_9:
        return "BULLISH"
    elif ema_9 < ema_21 and last_close < ema_9:
        return "BEARISH"

    return "NEUTRAL"
