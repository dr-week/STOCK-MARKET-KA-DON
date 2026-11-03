from typing import Dict, Any, List
from app.indicators.technicals import (
    calculate_rsi, calculate_ema, calculate_vwap,
    calculate_atr, calculate_adx_di, calculate_rvol
)
from app.indicators.structure import (
    analyze_market_structure, detect_supply_demand_zones, detect_key_candle
)
from app.indicators.price_action_patterns import detect_price_action_patterns

ADX_PERIOD = 14
ADX_MINIMUM_BARS = 2 * ADX_PERIOD


class TechnicalAnalysisDepartment:
    """
    DEPARTMENT 2: TECHNICAL ANALYSIS
    Responsibility: Evaluates purely mathematical and price-action structures:
    VWAP, EMA, RSI, ADX, Fibonacci, Key Candles, Supply/Demand zones, and
    multi-timeframe trend direction (15m and daily-proxy H1).
    """

    def _compute_trend_direction(self, closes: List[float]) -> str:
        """
        Determine trend direction for a given candle series using EMA alignment.

        Rules:
        - ``BULLISH``  if EMA-9 > EMA-21 **and** last close > EMA-9
        - ``BEARISH``  if EMA-9 < EMA-21 **and** last close < EMA-9
        - ``NEUTRAL``  otherwise (cross-over zone, insufficient bars, or flat)

        Requires at least 22 bars (EMA-21 warm-up). Returns ``NEUTRAL`` for
        shorter series rather than raising.

        Parameters
        ----------
        closes : list of float
            Chronologically ordered closing prices.

        Returns
        -------
        str
            One of: ``"BULLISH"``, ``"BEARISH"``, ``"NEUTRAL"``.
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

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        c_5m = market_data.get("candles_5m", {})
        opens = c_5m.get("opens", [])
        highs = c_5m.get("highs", [])
        lows = c_5m.get("lows", [])
        closes = c_5m.get("closes", [])
        volumes = c_5m.get("volumes", [])

        c_price = market_data["current_price"]

        minimum_bars = 21
        if len(closes) < minimum_bars:
            reason = f"Need at least {minimum_bars} complete 5-minute bars; received {len(closes)}."
            return {
                "rsi": None, "ema_9": None, "ema_21": None, "vwap": None,
                "atr": None, "adx": None, "rvol": None,
                "market_structure": {"trend": "UNAVAILABLE", "description": reason},
                "supply_demand": {"description": reason},
                "key_candle": {"role": "Normal Bar", "is_bullish": False, "is_bearish": False},
                "price_action_patterns": [],
                "sparkline": [],
                "data_quality": {
                    "status": "insufficient",
                    "minimum_5m_bars": minimum_bars,
                    "available_5m_bars": len(closes),
                    "adx_minimum_5m_bars": ADX_MINIMUM_BARS,
                    "indicators_pending": ["ADX"],
                    "reason": reason,
                    "m15_trend_available": False,
                },
                "m15_trend": "NEUTRAL",
                "h1_trend": "NEUTRAL",
            }

        rsi = calculate_rsi(closes, 14)
        ema_9 = calculate_ema(closes, 9)
        ema_21 = calculate_ema(closes, 21)
        vwap = calculate_vwap(highs, lows, closes, volumes)
        atr = calculate_atr(highs, lows, closes, 14)
        adx, p_di, m_di = calculate_adx_di(highs, lows, closes, ADX_PERIOD)
        rvol = calculate_rvol(volumes, 20)

        struct = analyze_market_structure(highs, lows, closes)
        zones = detect_supply_demand_zones(highs, lows, closes, volumes)
        key_candle = detect_key_candle(opens, highs, lows, closes, volumes)
        price_action_patterns = detect_price_action_patterns(opens, highs, lows, closes, volumes)

        sh = struct["last_swing_high"]
        sl = struct["last_swing_low"]
        fib_range = sh - sl or 1.0
        fib_pocket_min = round(sl + 0.500 * fib_range, 2)
        fib_pocket_max = round(sl + 0.618 * fib_range, 2)

        sparkline = [round(c, 2) for c in closes[-20:]]

        # --- Multi-timeframe trend direction ---
        # 15m trend: derived from the 15-minute candle closes
        closes_15m = market_data.get("candles_15m", {}).get("closes", [])
        m15_trend_available = len(closes_15m) >= 22
        m15_trend = self._compute_trend_direction(closes_15m)

        # H1/Daily proxy trend: derived from daily closing EMA alignment.
        # Using daily candles as a structural proxy for the higher timeframe
        # bias avoids an extra H1 fetch while providing adequate signal.
        closes_daily = market_data.get("candles_daily", {}).get("closes", [])
        h1_trend = self._compute_trend_direction(closes_daily)

        return {
            "rsi": rsi,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "vwap": vwap,
            "atr": atr,
            "adx": adx,
            "plus_di": p_di,
            "minus_di": m_di,
            "rvol": rvol,
            "market_structure": struct,
            "supply_demand": zones,
            "key_candle": key_candle,
            "price_action_patterns": price_action_patterns,
            "sparkline": sparkline,
            "fibonacci": {
                "swing_high": sh,
                "swing_low": sl,
                "golden_pocket": f"₹{fib_pocket_min} - ₹{fib_pocket_max}"
            },
            "m15_trend": m15_trend,
            "h1_trend": h1_trend,
            "data_quality": {
                "status": "available",
                "minimum_5m_bars": minimum_bars,
                "available_5m_bars": len(closes),
                "adx_minimum_5m_bars": ADX_MINIMUM_BARS,
                "m15_trend_available": m15_trend_available,
                "indicators_pending": [
                    *([] if adx is not None else ["ADX"]),
                    *([] if m15_trend_available else ["15m trend"]),
                ],
            },
        }


technical_dep = TechnicalAnalysisDepartment()
