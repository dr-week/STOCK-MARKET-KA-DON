from typing import List, Dict, Any
from app.indicators.technicals import (
    calculate_rsi, calculate_ema, calculate_vwap,
    calculate_atr, calculate_adx_di, calculate_rvol
)
from app.indicators.structure import (
    analyze_market_structure, detect_supply_demand_zones, detect_key_candle
)
from app.indicators.calculations import calculate_trade_risk_and_sizing
from app.strategies.intraday_scoring import score_intraday_rules, determine_signal_levels
from app.core.config import MIN_CONFLUENCE_SCORE, ACCOUNT_CAPITAL

def evaluate_intraday_confluence(
    symbol: str,
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    capital: float = ACCOUNT_CAPITAL
) -> Dict[str, Any]:
    """
    Core Intraday Decision-Support Engine:
    - Analyzes every completed candle
    - Identifies Supply & Demand zones and Market Structure (HH/HL, BOS, CHoCH)
    - Confluence-weighted scoring model (Max 10 Points)
    - Validates setups via mandatory Risk Engine (1:2 R:R, ₹90 risk on ₹18k)
    - Produces explainable reasons for BUY / SELL / WAIT
    """
    if len(closes) < 28:
        return {
            "signal": "WAIT",
            "score": 0,
            "decision": "WAIT (Insufficient data)",
            "entry": None,
            "target_1": None,
            "target_2": None,
            "stop_loss": None,
            "reasons": ["Need at least 28 completed 5-minute candles for the 14-period Wilder ADX warm-up."],
            "risk_analysis": {}
        }


    c_price = closes[-1]

    # 1. Technical Indicators
    rsi = calculate_rsi(closes, 14)
    ema_9 = calculate_ema(closes, 9)
    ema_21 = calculate_ema(closes, 21)
    vwap = calculate_vwap(highs, lows, closes, volumes)
    atr = calculate_atr(highs, lows, closes, 14)
    adx, p_di, m_di = calculate_adx_di(highs, lows, closes, 14)
    rvol = calculate_rvol(volumes, 20)

    # 2. Market Structure & Key Candle
    struct = analyze_market_structure(highs, lows, closes)
    zones = detect_supply_demand_zones(highs, lows, closes, volumes)
    key_candle = detect_key_candle(opens, highs, lows, closes, volumes)

    # 3. Fibonacci Retracement Levels from Recent Swings
    swing_high = struct["last_swing_high"]
    swing_low = struct["last_swing_low"]
    fib_range = swing_high - swing_low or 1.0
    fib_382 = swing_low + 0.382 * fib_range
    fib_500 = swing_low + 0.500 * fib_range
    fib_618 = swing_low + 0.618 * fib_range

    # 4. Confluence Scoring Model (Max 10 Points)
    bull_score, bear_score, bull_reasons, bear_reasons = score_intraday_rules(
        c_price=c_price,
        closes=closes,
        vwap=vwap,
        ema_9=ema_9,
        ema_21=ema_21,
        rvol=rvol,
        rsi=rsi,
        adx=adx,
        p_di=p_di,
        m_di=m_di,
        struct=struct,
        zones=zones,
        key_candle=key_candle,
        fib_382=fib_382,
        fib_500=fib_500,
        fib_618=fib_618,
    )

    # 5. Determine Primary Signal & Calculate Dynamic Levels
    entry = round(c_price, 2)
    signal_state, total_score, reasons, stop_loss, target_1, target_2 = determine_signal_levels(
        bull_score=bull_score,
        bear_score=bear_score,
        bull_reasons=bull_reasons,
        bear_reasons=bear_reasons,
        c_price=c_price,
        atr=atr,
        zones=zones,
        struct=struct,
        min_score=MIN_CONFLUENCE_SCORE,
    )

    # 6. Trade Validation & Risk Sizing Engine
    risk_profile = calculate_trade_risk_and_sizing(
        entry_price=entry,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        capital=capital
    )

    # Hard Risk Filters Override: Disqualify if R:R is below 1:2 or entry too far
    if signal_state != "WAIT":
        if not risk_profile["passes_rr_filter"]:
            signal_state = "WAIT (Insufficient R:R)"
            reasons.append("Hard Risk Filter: Planned R:R did not satisfy mandatory 1:2 threshold.")

    # Confidence Percentage mapped from Score (7=70%, 8=80%, 9=90%, 10=95%)
    confidence = min(95, max(45, total_score * 10))

    # Sparkline series
    sparkline = [round(c, 2) for c in closes[-20:]] if closes else [c_price] * 10

    return {
        "signal": signal_state,
        "confluence_score": total_score,
        "max_score": 10,
        "confidence": confidence,
        "entry": entry,
        "target_1": target_1,
        "target_2": target_2,
        "stop_loss": stop_loss,
        "vwap": vwap,
        "rsi": rsi,
        "ema_9": ema_9,
        "ema_21": ema_21,
        "atr": atr,
        "adx": adx,
        "rvol": rvol,
        "sparkline": sparkline,
        "market_structure": struct,
        "supply_demand": zones,
        "key_candle": key_candle,
        "risk_sizing": risk_profile,
        "reasons": reasons
    }
