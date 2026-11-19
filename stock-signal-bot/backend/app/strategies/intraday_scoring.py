from typing import Dict, Any, List, Tuple

def score_intraday_rules(
    c_price: float,
    closes: List[float],
    vwap: float,
    ema_9: float,
    ema_21: float,
    rvol: float,
    rsi: float,
    adx: float,
    p_di: float,
    m_di: float,
    struct: Dict[str, Any],
    zones: Dict[str, Any],
    key_candle: Dict[str, Any],
    fib_382: float,
    fib_500: float,
    fib_618: float,
) -> Tuple[int, int, List[str], List[str]]:
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
        bear_reasons.append("Fibonacci (+1): Resistance test at 0.382-0.50 Retracement")

    return bull_score, bear_score, bull_reasons, bear_reasons

def determine_signal_levels(
    bull_score: int,
    bear_score: int,
    bull_reasons: List[str],
    bear_reasons: List[str],
    c_price: float,
    atr: float,
    zones: Dict[str, Any],
    struct: Dict[str, Any],
    min_score: int
) -> Tuple[str, int, List[str], float, float, float]:
    volatility_buffer = max(1.2 * atr, c_price * 0.005)

    if bull_score >= bear_score and bull_score >= min_score:
        signal_state = "BUY CANDIDATE"
        total_score = bull_score
        reasons = bull_reasons
        structure_sl = zones["demand_zone"]["bottom"] if zones["demand_zone"] else struct["last_swing_low"]
        stop_loss = round(min(c_price - volatility_buffer, structure_sl - 0.5), 2)
        risk_dist = max(c_price - stop_loss, 1.0)
        target_1 = round(c_price + (risk_dist * 2.0), 2)
        target_2 = round(c_price + (risk_dist * 3.0), 2)
    elif bear_score > bull_score and bear_score >= min_score:
        signal_state = "SELL CANDIDATE"
        total_score = bear_score
        reasons = bear_reasons
        structure_sl = zones["supply_zone"]["top"] if zones["supply_zone"] else struct["last_swing_high"]
        stop_loss = round(max(c_price + volatility_buffer, structure_sl + 0.5), 2)
        risk_dist = max(stop_loss - c_price, 1.0)
        target_1 = round(c_price - (risk_dist * 2.0), 2)
        target_2 = round(c_price - (risk_dist * 3.0), 2)
    else:
        signal_state = "WAIT"
        total_score = max(bull_score, bear_score)
        reasons = [f"Confluence score below threshold ({min_score}/10 required). Awaiting clean setup alignment."]
        stop_loss = round(c_price - volatility_buffer, 2)
        target_1 = round(c_price + volatility_buffer * 2.0, 2)
        target_2 = round(c_price + volatility_buffer * 3.0, 2)

    return signal_state, total_score, reasons, stop_loss, target_1, target_2
