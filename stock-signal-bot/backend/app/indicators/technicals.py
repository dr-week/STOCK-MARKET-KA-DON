import math
from typing import List, Optional, Tuple

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Computes Relative Strength Index on confirmed closes"""
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(delta if delta >= 0 else 0.0)
        losses.append(abs(delta) if delta < 0 else 0.0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)

def calculate_ema(prices: List[float], span: int) -> float:
    """Computes Exponential Moving Average"""
    if not prices:
        return None
    if len(prices) < span:
        return None
    multiplier = 2.0 / (span + 1.0)
    ema = prices[0]
    for p in prices[1:]:
        ema = (p - ema) * multiplier + ema
    return round(ema, 2)

def calculate_vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> float:
    """Computes Volume Weighted Average Price (VWAP)"""
    cum_pv, cum_vol = 0.0, 0.0
    for h, l, c, v in zip(highs, lows, closes, volumes):
        if v and h and l and c:
            cum_pv += ((h + l + c) / 3.0) * v
            cum_vol += v
    if cum_vol == 0:
        return closes[-1] if closes else 0.0
    return round(cum_pv / cum_vol, 2)

def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Computes Average True Range for dynamic volatility stop-loss"""
    if len(closes) < 2:
        return None
    tr_list = []
    for i in range(1, len(closes)):
        h, l, prev_c = highs[i], lows[i], closes[i - 1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        tr_list.append(tr)
    recent_tr = tr_list[-period:] if len(tr_list) >= period else tr_list
    return round(sum(recent_tr) / len(recent_tr), 2) if recent_tr else 1.0

def calculate_adx_di(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Compute Wilder-smoothed (ADX, +DI, -DI).

    Requires 2 * period completed candles for the initial ADX. Returns
    (None, None, None) before that warm-up instead of fabricating a neutral value.
    """
    if period <= 0 or len(closes) < 2 * period:
        return (None, None, None)
    if len(highs) != len(lows) or len(highs) != len(closes):
        raise ValueError("High, low, and close series must have matching lengths")

    tr_list, plus_dm, minus_dm = [], [], []
    for i in range(1, len(closes)):
        h, l, prev_c = highs[i], lows[i], closes[i - 1]
        prev_h, prev_l = highs[i - 1], lows[i - 1]

        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        up_move = h - prev_h
        down_move = prev_l - l

        p_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        m_dm = down_move if down_move > up_move and down_move > 0 else 0.0

        tr_list.append(tr)
        plus_dm.append(p_dm)
        minus_dm.append(m_dm)

    smooth_tr = sum(tr_list[:period])
    smooth_p_dm = sum(plus_dm[:period])
    smooth_m_dm = sum(minus_dm[:period])
    dx_values = []

    for index in range(period - 1, len(tr_list)):
        if index >= period:
            smooth_tr = smooth_tr - (smooth_tr / period) + tr_list[index]
            smooth_p_dm = smooth_p_dm - (smooth_p_dm / period) + plus_dm[index]
            smooth_m_dm = smooth_m_dm - (smooth_m_dm / period) + minus_dm[index]
        if smooth_tr <= 0:
            dx_values.append(0.0)
            continue
        plus_di_value = (smooth_p_dm / smooth_tr) * 100
        minus_di_value = (smooth_m_dm / smooth_tr) * 100
        di_sum = plus_di_value + minus_di_value
        dx_values.append(
            abs(plus_di_value - minus_di_value) / di_sum * 100 if di_sum > 0 else 0.0
        )

    if len(dx_values) < period:
        return (None, None, None)

    adx_value = sum(dx_values[:period]) / period
    for dx in dx_values[period:]:
        adx_value = ((adx_value * (period - 1)) + dx) / period

    plus_di = (smooth_p_dm / smooth_tr) * 100 if smooth_tr > 0 else 0.0
    minus_di = (smooth_m_dm / smooth_tr) * 100 if smooth_tr > 0 else 0.0
    return (round(adx_value, 2), round(plus_di, 2), round(minus_di, 2))

def calculate_rvol(volumes: List[float], lookback: int = 20) -> float:
    """Relative Volume (RVOL) = current bar volume / average volume"""
    if not volumes or len(volumes) < 2:
        return 1.0
    avg_vol = sum(volumes[-lookback-1:-1]) / min(lookback, len(volumes) - 1)
    if avg_vol <= 0:
        return 1.0
    return round(volumes[-1] / avg_vol, 2)
