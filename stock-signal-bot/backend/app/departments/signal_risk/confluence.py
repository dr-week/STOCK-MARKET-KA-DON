from typing import Dict, Any, Tuple, List

class ConfluenceResult:
    def __init__(
        self,
        bull_score: int,
        bear_score: int,
        max_score: int,
        bull_reasons: List[str],
        bear_reasons: List[str],
        adx_available: bool,
        m15_alignment_reason: str | None,
        m15_conflicts: bool,
    ):
        self.bull_score = bull_score
        self.bear_score = bear_score
        self.max_score = max_score
        self.bull_reasons = bull_reasons
        self.bear_reasons = bear_reasons
        self.adx_available = adx_available
        self.m15_alignment_reason = m15_alignment_reason
        self.m15_conflicts = m15_conflicts


def evaluate_confluence_rules(
    c_price: float,
    technicals: Dict[str, Any],
    quality: Dict[str, Any],
    fundamentals: Dict[str, Any],
    intelligence: Dict[str, Any],
) -> ConfluenceResult:
    struct = technicals.get("market_structure", {})
    zones = technicals.get("supply_demand", {})
    vwap = technicals.get("vwap", c_price)
    ema_9 = technicals.get("ema_9", c_price)
    ema_21 = technicals.get("ema_21", c_price)
    rsi = technicals.get("rsi", 50.0)
    adx = technicals.get("adx") or 0.0
    adx_available = technicals.get("adx") is not None
    m15_trend = technicals.get("m15_trend", "NEUTRAL")
    m15_trend_available = quality.get("m15_trend_available") is True
    max_score = 9 + int(adx_available) + int(m15_trend_available)
    p_di = technicals.get("plus_di") or 0.0
    m_di = technicals.get("minus_di") or 0.0
    rvol = technicals.get("rvol", 1.0)

    bull_score = 0
    bear_score = 0
    bull_reasons = []
    bear_reasons = []

    # 1. Market Structure (+2)
    if "BULLISH" in struct.get("trend", "") or struct.get("bos") and c_price > struct.get("last_swing_low", 0):
        bull_score += 2
        bull_reasons.append(f"Market Structure (+2): {struct.get('description')}")
    elif "BEARISH" in struct.get("trend", "") or struct.get("bos") and c_price < struct.get("last_swing_high", 0):
        bear_score += 2
        bear_reasons.append(f"Market Structure (+2): {struct.get('description')}")

    # 2. Supply / Demand Zone (+2)
    if zones.get("at_demand"):
        bull_score += 2
        bull_reasons.append(f"Supply/Demand (+2): Price respecting Demand Base ₹{zones['demand_zone']['bottom']}-₹{zones['demand_zone']['top']}")
    elif zones.get("at_supply"):
        bear_score += 2
        bear_reasons.append(f"Supply/Demand (+2): Price rejecting Supply Base ₹{zones['supply_zone']['bottom']}-₹{zones['supply_zone']['top']}")

    # 3. VWAP Alignment (+2)
    if c_price > vwap:
        bull_score += 2
        bull_reasons.append(f"VWAP Alignment (+2): Price (₹{c_price}) holds strictly above institutional VWAP (₹{vwap})")
    else:
        bear_score += 2
        bear_reasons.append(f"VWAP Alignment (+2): Price (₹{c_price}) rejected below institutional VWAP (₹{vwap})")

    # 4. EMA 9/21 (+1)
    if ema_9 > ema_21 and c_price >= ema_9:
        bull_score += 1
        bull_reasons.append(f"EMA 9/21 (+1): 9-EMA (₹{ema_9}) expansion above 21-EMA (₹{ema_21})")
    elif ema_9 < ema_21 and c_price <= ema_9:
        bear_score += 1
        bear_reasons.append(f"EMA 9/21 (+1): 9-EMA (₹{ema_9}) downward slope under 21-EMA (₹{ema_21})")

    # 5. Relative Volume (+1)
    if rvol >= 1.25:
        if c_price >= ema_9:
            bull_score += 1
            bull_reasons.append(f"Volume (+1): RVOL at {rvol}x average institutional turnover")
        else:
            bear_score += 1
            bear_reasons.append(f"Volume (+1): RVOL distribution at {rvol}x average")

    # 6. Momentum RSI + ADX (+1)
    if adx_available and 52 <= rsi <= 68 and adx >= 20 and p_di > m_di:
        bull_score += 1
        bull_reasons.append(f"Momentum (+1): RSI ({rsi}) in expansion zone with ADX trend ({adx})")
    elif adx_available and 32 <= rsi <= 48 and adx >= 20 and m_di > p_di:
        bear_score += 1
        bear_reasons.append(f"Momentum (+1): RSI ({rsi}) bearish pressure with ADX ({adx})")

    # 7. Market Intelligence Sector / Macro (+1)
    nifty_trend = intelligence.get("nifty_50", {}).get("trend", "SIDEWAYS")
    if nifty_trend == "BULLISH":
        bull_score += 1
        bull_reasons.append("Market Intelligence (+1): Nifty 50 macro trend is positive")
    elif nifty_trend == "BEARISH":
        bear_score += 1
        bear_reasons.append("Market Intelligence (+1): Nifty 50 macro trend is negative")

    # 8. 15-minute trend alignment (+1)
    m15_conflicts = False
    m15_alignment_reason = None
    if m15_trend_available and m15_trend == "BULLISH" and bull_score >= bear_score:
        bull_score += 1
        m15_alignment_reason = "15m Trend Alignment (+1): Higher-timeframe trend is bullish"
        bull_reasons.append(m15_alignment_reason)
    elif m15_trend_available and m15_trend == "BEARISH" and bear_score >= bull_score:
        bear_score += 1
        m15_alignment_reason = "15m Trend Alignment (+1): Higher-timeframe trend is bearish"
        bear_reasons.append(m15_alignment_reason)
    elif m15_trend_available and m15_trend in ("BULLISH", "BEARISH"):
        m15_conflicts = True

    # Fundamental Risk Filter
    if not fundamentals.get("quality_filter_passed", True):
        bull_score = min(bull_score, 4)
        bull_reasons.append("Fundamental Filter Warning: High balance sheet debt detected; longs capped")

    return ConfluenceResult(
        bull_score, bear_score, max_score,
        bull_reasons, bear_reasons,
        adx_available, m15_alignment_reason, m15_conflicts
    )
