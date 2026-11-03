from typing import List, Dict, Any
from app.indicators.technicals import (
    calculate_rsi, calculate_ema, calculate_vwap,
    calculate_atr, calculate_adx_di, calculate_rvol
)
from app.indicators.structure import (
    analyze_market_structure, detect_supply_demand_zones, detect_key_candle
)
from app.indicators.calculations import calculate_trade_risk_and_sizing
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
    bull_score = 0
    bear_score = 0
    bull_reasons = []
    bear_reasons = []

    # Rule A: Market Structure Aligned (+2 Points)
    if "BULLISH" in struct["trend"] or struct["bos"] and c_price > struct["last_swing_low"]:
        bull_score += 2
        bull_reasons.append(f"Market Structure (+2): {struct['description']}")
    elif "BEARISH" in struct["trend"] or struct["bos"] and c_price < struct["last_swing_high"]:
        bear_score += 2
        bear_reasons.append(f"Market Structure (+2): {struct['description']}")

    # Rule B: Supply & Demand Confirmation (+2 Points)
    if zones["at_demand"] or key_candle["is_bullish"] and zones["demand_zone"]:
        bull_score += 2
        bull_reasons.append(f"Supply/Demand (+2): Price respecting Demand Base ₹{zones['demand_zone']['bottom']}-₹{zones['demand_zone']['top']}")
    elif zones["at_supply"] or key_candle["is_bearish"] and zones["supply_zone"]:
        bear_score += 2
        bear_reasons.append(f"Supply/Demand (+2): Price rejecting Supply Base ₹{zones['supply_zone']['bottom']}-₹{zones['supply_zone']['top']}")

    # Rule C: VWAP Alignment (+2 Points)
    if c_price > vwap:
        bull_score += 2
        bull_reasons.append(f"VWAP Alignment (+2): Price (₹{c_price}) holds strictly above institutional VWAP (₹{vwap})")
    else:
        bear_score += 2
        bear_reasons.append(f"VWAP Alignment (+2): Price (₹{c_price}) rejected below institutional VWAP (₹{vwap})")

    # Rule D: EMA 9/21 Alignment (+1 Point)
    if ema_9 > ema_21 and c_price >= ema_9:
        bull_score += 1
        bull_reasons.append(f"EMA 9/21 (+1): 9-EMA (₹{ema_9}) bullish expansion above 21-EMA (₹{ema_21})")
    elif ema_9 < ema_21 and c_price <= ema_9:
        bear_score += 1
        bear_reasons.append(f"EMA 9/21 (+1): 9-EMA (₹{ema_9}) downward slope below 21-EMA (₹{ema_21})")

    # Rule E: Relative Volume (RVOL) Confirmation (+1 Point)
    if rvol >= 1.25:
        if c_price > closes[-2]:
            bull_score += 1
            bull_reasons.append(f"Volume Confirmation (+1): RVOL at {rvol}x average institutional turnover")
        else:
            bear_score += 1
            bear_reasons.append(f"Volume Confirmation (+1): High volume distribution at {rvol}x average")

    # Rule F: Momentum (RSI + ADX) Confirmation (+1 Point)
    if 52 <= rsi <= 68 and adx >= 20 and p_di > m_di:
        bull_score += 1
        bull_reasons.append(f"Momentum (+1): RSI ({rsi}) in healthy expansion with ADX trend strength ({adx})")
    elif 32 <= rsi <= 48 and adx >= 20 and m_di > p_di:
        bear_score += 1
        bear_reasons.append(f"Momentum (+1): RSI ({rsi}) bearish distribution with ADX ({adx})")

    # Rule G: Fibonacci Confluence (+1 Point)
    if fib_500 <= c_price <= fib_618 and c_price > vwap:
        bull_score += 1
        bull_reasons.append(f"Fibonacci (+1): Confluence bounce in Golden 0.50-0.618 Pocket (₹{round(fib_500,2)}-₹{round(fib_618,2)})")
    elif fib_382 <= c_price <= fib_500 and c_price < vwap:
        bear_score += 1
        bear_reasons.append(f"Fibonacci (+1): Resistance test at 0.382-0.50 Retracement")

    # 5. Determine Primary Signal & Calculate Dynamic Levels
    entry = round(c_price, 2)
    volatility_buffer = max(1.2 * atr, c_price * 0.005)

    if bull_score >= bear_score and bull_score >= MIN_CONFLUENCE_SCORE:
        signal_state = "BUY CANDIDATE"
        total_score = bull_score
        reasons = bull_reasons

        # Structure-based Stop Loss below demand / swing low
        structure_sl = zones["demand_zone"]["bottom"] if zones["demand_zone"] else struct["last_swing_low"]
        stop_loss = round(min(c_price - volatility_buffer, structure_sl - 0.5), 2)
        risk_dist = max(c_price - stop_loss, 1.0)
        target_1 = round(c_price + (risk_dist * 2.0), 2)  # Mandatory 1:2 R:R
        target_2 = round(c_price + (risk_dist * 3.0), 2)
    elif bear_score > bull_score and bear_score >= MIN_CONFLUENCE_SCORE:
        signal_state = "SELL CANDIDATE"
        total_score = bear_score
        reasons = bear_reasons

        # Structure-based Stop Loss above supply / swing high
        structure_sl = zones["supply_zone"]["top"] if zones["supply_zone"] else struct["last_swing_high"]
        stop_loss = round(max(c_price + volatility_buffer, structure_sl + 0.5), 2)
        risk_dist = max(stop_loss - c_price, 1.0)
        target_1 = round(c_price - (risk_dist * 2.0), 2)  # Mandatory 1:2 R:R
        target_2 = round(c_price - (risk_dist * 3.0), 2)
    else:
        signal_state = "WAIT"
        total_score = max(bull_score, bear_score)
        reasons = ["Confluence score below threshold (7/10 required). Awaiting clean setup alignment."]
        stop_loss = round(c_price - volatility_buffer, 2)
        target_1 = round(c_price + volatility_buffer * 2.0, 2)
        target_2 = round(c_price + volatility_buffer * 3.0, 2)

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
