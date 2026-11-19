from typing import List, Dict, Any

def detect_key_candle(opens: List[float], highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> Dict[str, Any]:
    """
    Labels completed candles by their real market role:
    A. Bullish Engulfing
    B. Bearish Engulfing
    C. Rejection Wick (Demand Hammer / Supply Shooting Star)
    D. Breakout Candle
    """
    if len(closes) < 3:
        return {"type": "NORMAL", "role": "Standard Bar", "is_bullish": False, "is_bearish": False}

    c, o, h, l = closes[-1], opens[-1], highs[-1], lows[-1]
    prev_c, prev_o, prev_h, prev_l = closes[-2], opens[-2], highs[-2], lows[-2]

    body = abs(c - o)
    candle_range = h - l or 0.01
    upper_wick = h - max(c, o)
    lower_wick = min(c, o) - l

    # A. Bullish Engulfing
    if c > o and prev_c < prev_o and c >= prev_o and o <= prev_c:
        return {
            "type": "BULLISH_ENGULFING",
            "role": "Bullish Engulfing (Buyer takeover after pullback)",
            "is_bullish": True,
            "is_bearish": False,
            "signal_level": h
        }

    # B. Bearish Engulfing
    if c < o and prev_c > prev_o and c <= prev_o and o >= prev_c:
        return {
            "type": "BEARISH_ENGULFING",
            "role": "Bearish Engulfing (Seller takeover after rally)",
            "is_bullish": False,
            "is_bearish": True,
            "signal_level": l
        }

    # C. Rejection Candle (Wick > 55% of range)
    if lower_wick >= 0.55 * candle_range and c >= (l + 0.4 * candle_range):
        return {
            "type": "DEMAND_REJECTION",
            "role": "Demand Rejection Hammer (Aggressive absorption at lows)",
            "is_bullish": True,
            "is_bearish": False,
            "signal_level": h
        }
    elif upper_wick >= 0.55 * candle_range and c <= (h - 0.4 * candle_range):
        return {
            "type": "SUPPLY_REJECTION",
            "role": "Supply Rejection (Rejection wick at highs)",
            "is_bullish": False,
            "is_bearish": True,
            "signal_level": l
        }

    # D. Strong Breakout Candle
    if body >= 0.65 * candle_range and (c > prev_h or c < prev_l):
        is_bull = c > o
        return {
            "type": "BREAKOUT_CANDLE",
            "role": f"{'Bullish' if is_bull else 'Bearish'} Breakout Candle (High momentum expansion)",
            "is_bullish": is_bull,
            "is_bearish": not is_bull,
            "signal_level": h if is_bull else l
        }

    return {
        "type": "NORMAL",
        "role": "Consolidation Bar",
        "is_bullish": c > o,
        "is_bearish": c < o,
        "signal_level": c
    }
