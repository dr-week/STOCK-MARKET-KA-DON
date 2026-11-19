from typing import List, Dict, Any, Optional

def analyze_market_structure(highs: List[float], lows: List[float], closes: List[float]) -> Dict[str, Any]:
    """
    Detects Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL),
    Break of Structure (BOS), and Change of Character (CHoCH).
    """
    if len(closes) < 10:
        return {
            "trend": "NEUTRAL",
            "bos": False,
            "choch": False,
            "last_swing_high": highs[-1] if highs else 0.0,
            "last_swing_low": lows[-1] if lows else 0.0,
            "description": "Insufficient candle history"
        }

    # Find swing highs and lows (fractal 3-bar confirmation)
    swing_highs = []
    swing_lows = []

    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
            swing_highs.append({"index": i, "price": highs[i]})
        if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
            swing_lows.append({"index": i, "price": lows[i]})

    current_price = closes[-1]
    last_sh = swing_highs[-1]["price"] if swing_highs else max(highs[-10:])
    last_sl = swing_lows[-1]["price"] if swing_lows else min(lows[-10:])

    # Structure identification
    trend = "CONSOLIDATION"
    bos = False
    choch = False
    desc = "Consolidating within recent swing limits."

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        sh1, sh2 = swing_highs[-2]["price"], swing_highs[-1]["price"]
        sl1, sl2 = swing_lows[-2]["price"], swing_lows[-1]["price"]

        if sh2 > sh1 and sl2 > sl1:
            trend = "BULLISH_HH_HL"
            if current_price > sh2:
                bos = True
                desc = "Bullish BOS: Price broke above confirmed swing high."
            else:
                desc = "Bullish structure: Series of Higher Highs and Higher Lows."
        elif sh2 < sh1 and sl2 < sl1:
            trend = "BEARISH_LH_LL"
            if current_price < sl2:
                bos = True
                desc = "Bearish BOS: Price broke below confirmed swing low."
            else:
                desc = "Bearish structure: Series of Lower Highs and Lower Lows."
        elif sh2 > sh1 and sl2 < sl1:
            choch = True
            desc = "CHoCH detected: Market expanding with shifting character."
    else:
        if current_price > last_sh:
            trend = "BULLISH"
            bos = True
            desc = "Breakout above immediate resistance swing."
        elif current_price < last_sl:
            trend = "BEARISH"
            bos = True
            desc = "Breakdown below immediate support swing."

    return {
        "trend": trend,
        "bos": bos,
        "choch": choch,
        "last_swing_high": round(last_sh, 2),
        "last_swing_low": round(last_sl, 2),
        "description": desc
    }


# Re-export modular components for 100% backwards compatibility
from app.indicators.supply_demand import detect_supply_demand_zones
from app.indicators.key_candles import detect_key_candle

__all__ = [
    "analyze_market_structure",
    "detect_supply_demand_zones",
    "detect_key_candle",
]

