from typing import Dict, List, Optional, Tuple

from app.ai.scoring_components import score_multi_timeframe, score_sector_regime


def score_intraday_factors(
    *,
    price: float,
    vwap: float,
    rsi: float,
    ema_9: float,
    ema_21: float,
    change_pct: float,
    news_sentiment: str,
    market_phase: str,
    adx: float,
    relative_volume: float,
    support: Optional[float],
    resistance: Optional[float],
    trend_strength: float,
    volume_confirmation: bool,
    structure_bias: str,
    market_regime: str,
    m15_trend: str,
    h1_trend: str,
    sector: str,
    sector_strengths: Dict[str, str],
) -> Tuple[float, List[str]]:
    score = 0.50
    rules_fired: List[str] = []

    vwap_delta_pct = ((price - vwap) / vwap) * 100 if vwap else 0.0
    if vwap_delta_pct > 0.15:
        score += 0.15
        rules_fired.append("Price is holding above VWAP with strong trend confirmation")
    elif vwap_delta_pct < -0.15:
        score -= 0.15
        rules_fired.append("Price rejected below VWAP and risks trend failure")

    ema_spread = ((ema_9 - ema_21) / ema_21) * 100 if ema_21 else 0.0
    if ema_spread > 0.1:
        score += 0.12
        rules_fired.append("Short-term EMA momentum is accelerating above the longer trend")
    elif ema_spread < -0.1:
        score -= 0.12
        rules_fired.append("Short-term EMA structure is slipping below the trend")

    if 55 <= rsi <= 68:
        score += 0.12
        rules_fired.append(f"RSI ({rsi}) remains in a healthy expansion zone")
    elif rsi > 74:
        score -= 0.18
        rules_fired.append(f"RSI ({rsi}) is stretched and vulnerable to mean reversion")
    elif 30 <= rsi <= 45:
        score -= 0.10
        rules_fired.append(f"RSI ({rsi}) is weak and still under distribution pressure")
    elif rsi < 25:
        score += 0.08
        rules_fired.append(f"RSI ({rsi}) is deeply oversold and improving")

    if news_sentiment == "BULLISH":
        score += 0.08
        rules_fired.append("Positive headlines are reinforcing the bullish tape")
    elif news_sentiment == "BEARISH":
        score -= 0.08
        rules_fired.append("Negative headlines are adding distribution pressure")

    if adx >= 25:
        score += 0.08 + min(0.12, max(0.0, float(trend_strength or 0.0) * 0.12))
        rules_fired.append(f"Trend strength is confirmed with ADX at {adx} and directional follow-through")
    elif adx < 18:
        score -= 0.06
        rules_fired.append("Trend is weak and the market is still rotation-driven")

    if relative_volume >= 1.4:
        score += 0.10
        rules_fired.append("Volume surge confirms participation")
    elif relative_volume <= 0.8:
        score -= 0.06
        rules_fired.append("Volume is thin and conviction remains weak")

    if volume_confirmation:
        score += 0.06
        rules_fired.append("Volume confirmation supports the move with stronger participation")
    if support and price >= support:
        score += 0.06
        rules_fired.append(f"Price is holding above support at ₹{support:.2f}")
    if resistance and price >= resistance * 0.995:
        score -= 0.04
        rules_fired.append(f"Price is close to resistance at ₹{resistance:.2f}, so continuation needs confirmation")

    structure = structure_bias.upper()
    if structure == "BULLISH":
        score += 0.07
        rules_fired.append("Structure bias is bullish and higher highs are intact")
    elif structure == "BEARISH":
        score -= 0.07
        rules_fired.append("Structure bias is bearish and lower lows are still in play")

    regime = market_regime.upper()
    if regime == "TRENDING":
        score += 0.04
        rules_fired.append("Market regime is trending and favors continuation trades")
    elif regime == "RANGE":
        score -= 0.04
        rules_fired.append("Market regime is range-bound and reduces breakout conviction")

    if market_phase == "OPENING_TRAP_ZONE":
        score = 0.50
        rules_fired.append("Session Rule: High-spread opening traps active; signals neutralized")

    if change_pct > 1.5:
        score += 0.05
        rules_fired.append("Momentum is accelerating with a healthy intraday move")
    elif change_pct < -1.5:
        score -= 0.08
        rules_fired.append("Momentum is fading and downside risk is increasing")

    timeframe_delta = score_multi_timeframe({"m15_trend": m15_trend, "h1_trend": h1_trend})
    if timeframe_delta > 0:
        score += timeframe_delta
        rules_fired.append(f"Multi-timeframe alignment is confluent: 15m={m15_trend}, H1={h1_trend}")
    elif timeframe_delta < 0:
        score += timeframe_delta
        rules_fired.append(f"Multi-timeframe conflict detected: 15m={m15_trend}, H1={h1_trend}; penalising signal")

    sector_delta = score_sector_regime(sector, sector_strengths)
    if sector_delta > 0:
        score += sector_delta
        rules_fired.append(f"Sector '{sector}' is showing strength; tailwind confirmed")
    elif sector_delta < 0:
        score += sector_delta
        rules_fired.append(f"Sector '{sector}' is under pressure; headwind factored in")

    return round(max(0.05, min(0.95, score)), 2), rules_fired
