import unittest
from datetime import datetime
from unittest.mock import patch
from app.departments.market_data.candle_normalizer import extract_candles
from app.indicators.technicals import (
    calculate_rsi,
    calculate_ema,
    calculate_vwap,
    calculate_atr,
    calculate_adx_di,
    calculate_rvol
)
from app.market.sessions import IST, get_market_session_state
from app.departments.market_data.collector import MarketDataCollector, DataQualityStatus
from app.departments.signal_risk.service import SignalRiskDepartment
from app.departments.technical_analysis.service import TechnicalAnalysisDepartment

class TestMarketDataFreshnessAndIndicators(unittest.TestCase):
    """
    Phase 1 Core Audit:
    - Verifies mathematical correctness of technical indicators under edge cases.
    - Verifies market-data freshness and gap/spike detection.
    - Guarantees missing or insufficient data returns explicit None/safe fallback, never fabricated values.
    """

    def test_rsi_insufficient_warmup_returns_none(self):
        """RSI requires at least period + 1 candles; otherwise returns None."""
        prices = [100.0, 101.0, 102.0]
        self.assertIsNone(calculate_rsi(prices, period=14))

    def test_rsi_constant_prices_returns_100_or_bounded(self):
        """RSI with purely positive increments or zero loss returns 100.0."""
        prices = [100.0 + i for i in range(20)]
        rsi = calculate_rsi(prices, period=14)
        self.assertEqual(rsi, 100.0)

    def test_rsi_standard_oscillation_bounds(self):
        """RSI values must be strictly bounded between 0 and 100."""
        # Oscillating prices
        prices = [100.0 + (5.0 if i % 2 == 0 else -3.0) for i in range(30)]
        rsi = calculate_rsi(prices, period=14)
        self.assertIsNotNone(rsi)
        self.assertTrue(0.0 <= rsi <= 100.0)

    def test_ema_insufficient_warmup_returns_none(self):
        """EMA requires at least span candles; otherwise returns None."""
        prices = [100.0, 102.0, 104.0]
        self.assertIsNone(calculate_ema(prices, span=9))
        self.assertIsNone(calculate_ema(prices, span=21))

    def test_ema_deterministic_formula(self):
        """Verifies multiplier and smoothing against manual calculation."""
        # span 3: multiplier = 2 / (3 + 1) = 0.5
        # p0 = 10, p1 = 20 -> ema1 = (20-10)*0.5 + 10 = 15.0
        # p2 = 30 -> ema2 = (30-15)*0.5 + 15 = 22.5
        prices = [10.0, 20.0, 30.0]
        self.assertEqual(calculate_ema(prices, span=3), 22.5)

    def test_vwap_zero_volume_returns_last_close(self):
        """When total volume is zero, VWAP gracefully falls back to last close price."""
        highs = [105.0, 106.0]
        lows = [95.0, 96.0]
        closes = [100.0, 102.0]
        volumes = [0.0, 0.0]
        self.assertEqual(calculate_vwap(highs, lows, closes, volumes), 102.0)

    def test_atr_warmup_and_calculation(self):
        """ATR properly computes average true range with high/low/prev_close differences."""
        highs = [105.0, 110.0]
        lows = [95.0, 90.0]
        closes = [100.0, 105.0]
        # For candle 1: h=110, l=90, prev_c=100 -> TR = max(110-90=20, |110-100|=10, |90-100|=10) = 20.0
        atr = calculate_atr(highs, lows, closes, period=14)
        self.assertEqual(atr, 20.0)

    def test_adx_uses_wilder_smoothing_and_requires_full_warmup(self):
        closes = [100.0 + index for index in range(6)]
        highs = [close + 1 for close in closes]
        lows = [close - 1 for close in closes]

        self.assertEqual(calculate_adx_di(highs[:5], lows[:5], closes[:5], period=3), (None, None, None))
        adx, plus_di, minus_di = calculate_adx_di(highs, lows, closes, period=3)
        self.assertEqual(adx, 100.0)
        self.assertEqual(plus_di, 50.0)
        self.assertEqual(minus_di, 0.0)

    def test_adx_rejects_misaligned_price_series(self):
        with self.assertRaises(ValueError):
            calculate_adx_di([10.0, 11.0], [9.0], [9.5, 10.5], period=1)

    def test_adx_uses_first_period_true_range_seed(self):
        closes = [100 + index * 0.1 + ((index * 7) % 5) * 0.4 for index in range(32)]
        highs = [value + 0.4 + (index % 3) * 0.2 for index, value in enumerate(closes)]
        lows = [value - 0.3 - (index % 4) * 0.15 for index, value in enumerate(closes)]

        self.assertEqual(calculate_adx_di(highs, lows, closes), (13.26, 35.95, 27.36))

    def test_collector_flags_stale_feed_during_trading_hours(self):
        """Collector detects stale feed when no tick arrives past threshold."""
        collector = MarketDataCollector()
        collector.stale_threshold_seconds = 10.0
        # Feed not yet received
        is_healthy, msg = collector.check_feed_health("RELIANCE")
        self.assertFalse(is_healthy)
        self.assertEqual(msg, "NO_DATA_RECEIVED")

    def test_market_session_windows_are_exhaustive(self):
        """Market session evaluator always returns non-empty phase and boolean intraday status."""
        state = get_market_session_state()
        self.assertIn(state["phase"], [
            "PRE_MARKET / CLOSED",
            "OPENING_TRAP_ZONE",
            "PRIME_MOMENTUM_1",
            "MIDDAY_CONSOLIDATION",
            "PRIME_MOMENTUM_2",
            "SQUARE_OFF_PHASE",
            "MARKET_CLOSED",
            "WEEKEND / CLOSED"
        ])
        self.assertIsInstance(state["can_trade_intraday"], bool)

    def test_market_session_disables_entries_on_weekends(self):
        saturday = datetime(2026, 11, 7, 10, 0, tzinfo=IST)
        with patch("app.market.sessions.datetime") as clock:
            clock.now.return_value = saturday
            state = get_market_session_state()

        self.assertEqual(state["phase"], "WEEKEND / CLOSED")
        self.assertFalse(state["can_trade_intraday"])

class TestAlignedCandles(unittest.TestCase):
    def setUp(self):
        self.chart = {
            "timestamp": [1000, 1300, 1600],
            "indicators": {
                "quote": [{
                    "open": [10.0, None, 10.5],
                    "high": [11.0, 12.0, 11.5],
                    "low": [9.0, 8.0, 10.0],
                    "close": [10.5, None, 11.0],
                    "volume": [100.0, None, 120.0],
                }]
            },
        }

    def test_invalid_row_is_removed_without_misaligning_fields(self):
        candles = extract_candles(
            self.chart, interval_seconds=300, now=2000, exclude_incomplete=False
        )
        self.assertEqual(candles["timestamps"], [1000, 1600])
        self.assertEqual(candles["opens"], [10.0, 10.5])
        self.assertEqual(candles["closes"], [10.5, 11.0])
        self.assertEqual(candles["volumes"], [100.0, 120.0])
        self.assertEqual(candles["invalid_count"], 1)

    def test_incomplete_live_candle_is_excluded(self):
        chart = {
            "timestamp": [1000, 1300],
            "indicators": {
                "quote": [{
                    "open": [10.0, 10.5],
                    "high": [11.0, 11.5],
                    "low": [9.0, 10.0],
                    "close": [10.5, 11.0],
                    "volume": [100.0, 120.0],
                }]
            },
        }
        candles = extract_candles(
            chart, interval_seconds=300, now=1500, exclude_incomplete=True
        )
        self.assertEqual(candles["timestamps"], [1000])
        self.assertEqual(candles["incomplete_count"], 1)

    def test_inconsistent_ohlc_row_is_rejected(self):
        chart = {
            "timestamp": [1000],
            "indicators": {
                "quote": [{
                    "open": [10.0],
                    "high": [10.4],
                    "low": [9.0],
                    "close": [10.5],
                    "volume": [100.0],
                }]
            },
        }
        candles = extract_candles(
            chart, interval_seconds=300, now=2000, exclude_incomplete=False
        )
        self.assertEqual(candles["timestamps"], [])
        self.assertEqual(candles["invalid_count"], 1)

class TestInsufficientTechnicalHistory(unittest.TestCase):
    def test_analysis_readiness_at_candle_boundaries(self):
        for count in (20, 21, 27, 28):
            with self.subTest(count=count):
                closes = [100.0 + index * 0.1 for index in range(count)]
                market_data = {
                    "current_price": closes[-1],
                    "candles_5m": {
                        "opens": closes,
                        "highs": [close + 0.2 for close in closes],
                        "lows": [close - 0.2 for close in closes],
                        "closes": closes,
                        "volumes": [1000.0 + index for index in range(count)],
                    },
                }
                technicals = TechnicalAnalysisDepartment().analyze(market_data)
                decision = SignalRiskDepartment().synthesize_decision(
                    market_data=market_data,
                    technicals=technicals,
                    fundamentals={},
                    intelligence={},
                )

                if count < 21:
                    self.assertEqual(technicals["data_quality"]["status"], "insufficient")
                    self.assertEqual(decision["signal"], "WAIT")
                    self.assertNotIn("max_score", decision)
                elif count < 28:
                    self.assertEqual(technicals["data_quality"]["status"], "available")
                    self.assertIsNone(technicals["adx"])
                    self.assertEqual(decision["max_score"], 9)
                else:
                    self.assertEqual(technicals["data_quality"]["status"], "available")
                    self.assertIsNotNone(technicals["adx"])
                    self.assertEqual(decision["max_score"], 10)

    def test_short_history_does_not_create_neutral_indicator_values_or_candidate(self):
        market_data = {
            "current_price": 100.0,
            "candles_5m": {
                "opens": [99.0, 100.0],
                "highs": [101.0, 102.0],
                "lows": [98.0, 99.0],
                "closes": [100.0, 101.0],
                "volumes": [1000.0, 1200.0],
            },
        }
        technicals = TechnicalAnalysisDepartment().analyze(market_data)
        decision = SignalRiskDepartment().synthesize_decision(
            market_data=market_data,
            technicals=technicals,
            fundamentals={},
            intelligence={},
        )

        self.assertEqual(technicals["data_quality"]["status"], "insufficient")
        self.assertIsNone(technicals["vwap"])
        self.assertEqual(technicals["sparkline"], [])
        self.assertEqual(decision["signal"], "WAIT")
        self.assertEqual(decision["confluence_score"], 0)
        self.assertIsNone(decision["confidence"])
        self.assertNotIn("max_score", decision)
        self.assertIsNone(decision["risk_sizing"])

    def test_partial_history_scores_available_indicators_without_fabricating_adx(self):
        closes = [100.0 + index * 0.1 for index in range(24)]
        market_data = {
            "current_price": closes[-1],
            "candles_5m": {
                "opens": closes,
                "highs": [close + 0.2 for close in closes],
                "lows": [close - 0.2 for close in closes],
                "closes": closes,
                "volumes": [1000.0 + index for index in range(len(closes))],
            },
        }

        technicals = TechnicalAnalysisDepartment().analyze(market_data)
        decision = SignalRiskDepartment().synthesize_decision(
            market_data=market_data,
            technicals=technicals,
            fundamentals={},
            intelligence={},
        )

        self.assertEqual(technicals["data_quality"]["status"], "available")
        self.assertEqual(technicals["data_quality"]["minimum_5m_bars"], 21)
        self.assertEqual(technicals["data_quality"]["available_5m_bars"], 24)
        self.assertEqual(technicals["data_quality"]["adx_minimum_5m_bars"], 28)
        self.assertEqual(technicals["data_quality"]["indicators_pending"], ["ADX", "15m trend"])
        self.assertIsNone(technicals["adx"])
        self.assertIsNotNone(technicals["rsi"])
        self.assertEqual(decision["max_score"], 9)
        self.assertNotEqual(decision["signal"], "WAIT")
        self.assertTrue(any("ADX is still warming up" in reason for reason in decision["reasons"]))

    def test_long_candidate_waits_when_quote_and_completed_close_are_below_both_emas(self):
        decision = SignalRiskDepartment().synthesize_decision(
            market_data={"current_price": 101.2, "candles_5m": {"closes": [100.0]}},
            technicals={
                "market_structure": {"trend": "BULLISH", "description": "Higher highs"},
                "supply_demand": {"at_demand": True, "demand_zone": {"bottom": 94.0, "top": 96.0}},
                "key_candle": {},
                "vwap": 90.0,
                "ema_9": 102.0,
                "ema_21": 101.0,
                "rsi": 60.0,
                "adx": 30.0,
                "plus_di": 25.0,
                "minus_di": 10.0,
                "rvol": 1.0,
                "atr": 1.0,
                "m15_trend": "BULLISH",
                "data_quality": {"m15_trend_available": True},
            },
            fundamentals={},
            intelligence={"nifty_50": {"trend": "BULLISH"}},
        )

        self.assertEqual(decision["signal"], "WATCHING")
        self.assertGreaterEqual(decision["confluence_score"], 7)
        self.assertTrue(any("BUY trigger withheld" in reason for reason in decision["reasons"]))
        self.assertIsNone(decision["risk_sizing"])
        self.assertEqual(decision["target_1"], 101.2)

    def test_bullish_candle_outside_demand_zone_does_not_award_zone_points(self):
        decision = SignalRiskDepartment().synthesize_decision(
            market_data={"current_price": 100.0},
            technicals={
                "market_structure": {"trend": "NEUTRAL"},
                "supply_demand": {
                    "at_demand": False,
                    "at_supply": False,
                    "demand_zone": {"bottom": 90.0, "top": 92.0},
                    "supply_zone": {"bottom": 108.0, "top": 110.0},
                },
                "key_candle": {"is_bullish": True, "is_bearish": False},
                "vwap": 99.0,
                "ema_9": 100.0,
                "ema_21": 100.0,
                "rsi": 50.0,
                "adx": None,
                "rvol": 1.0,
                "atr": 1.0,
                "data_quality": {},
            },
            fundamentals={},
            intelligence={},
        )

        self.assertFalse(any("Supply/Demand (+2)" in reason for reason in decision["reasons"]))

    def test_short_candidate_waits_when_quote_and_completed_close_are_above_both_emas(self):
        decision = SignalRiskDepartment().synthesize_decision(
            market_data={"current_price": 105.0, "candles_5m": {"closes": [104.0]}},
            technicals={
                "market_structure": {"trend": "BEARISH", "description": "Lower highs"},
                "supply_demand": {"at_supply": True, "supply_zone": {"bottom": 104.0, "top": 106.0}},
                "key_candle": {},
                "vwap": 110.0,
                "ema_9": 98.0,
                "ema_21": 99.0,
                "rsi": 40.0,
                "adx": 30.0,
                "plus_di": 10.0,
                "minus_di": 25.0,
                "rvol": 1.0,
                "atr": 1.0,
                "m15_trend": "BEARISH",
                "data_quality": {"m15_trend_available": True},
            },
            fundamentals={},
            intelligence={"nifty_50": {"trend": "BEARISH"}},
        )

        self.assertEqual(decision["signal"], "WATCHING")
        self.assertGreaterEqual(decision["confluence_score"], 7)
        self.assertTrue(any("SHORT trigger withheld" in reason for reason in decision["reasons"]))

    def test_tied_confluence_does_not_issue_directional_candidate(self):
        decision = SignalRiskDepartment().synthesize_decision(
            market_data={"current_price": 100.0},
            technicals={
                "market_structure": {"trend": "BULLISH", "description": "Higher highs"},
                "supply_demand": {},
                "key_candle": {},
                "vwap": 100.0,
                "ema_9": 100.0,
                "ema_21": 100.0,
                "rsi": 50.0,
                "adx": None,
                "rvol": 1.0,
                "atr": 1.0,
                "data_quality": {},
            },
            fundamentals={},
            intelligence={},
        )

        self.assertIn(decision["signal"], {"WATCHING", "SCANNING"})
        self.assertIsNone(decision["risk_sizing"])
        self.assertIsNone(decision["confidence"])
        self.assertEqual(decision["stop_loss"], 100.0)
        self.assertEqual(decision["target_1"], 100.0)

    def test_available_15m_trend_adds_one_confluence_point(self):
        market_data = {"current_price": 100.0}
        base_technicals = {
            "market_structure": {"trend": "NEUTRAL"},
            "supply_demand": {},
            "key_candle": {},
            "vwap": 90.0,
            "ema_9": 100.0,
            "ema_21": 100.0,
            "rsi": 50.0,
            "adx": None,
            "rvol": 1.0,
            "atr": 1.0,
            "data_quality": {"m15_trend_available": True},
        }

        neutral = SignalRiskDepartment().synthesize_decision(
            market_data, {**base_technicals, "m15_trend": "NEUTRAL"}, {}, {}
        )
        aligned = SignalRiskDepartment().synthesize_decision(
            market_data, {**base_technicals, "m15_trend": "BULLISH"}, {}, {}
        )
        conflicting = SignalRiskDepartment().synthesize_decision(
            market_data, {**base_technicals, "m15_trend": "BEARISH"}, {}, {}
        )

        self.assertEqual(neutral["max_score"], 10)
        self.assertEqual(aligned["max_score"], 10)
        self.assertEqual(aligned["confluence_score"], neutral["confluence_score"] + 1)
        self.assertTrue(any("15m Trend Alignment (+1)" in reason for reason in aligned["reasons"]))
        self.assertEqual(conflicting["confluence_score"], neutral["confluence_score"])
        self.assertTrue(any("conflicts with the intraday confluence" in reason for reason in conflicting["reasons"]))

    def test_15m_alignment_is_only_available_after_ema_warmup(self):
        closes = [100.0 + index for index in range(21)]
        market_data = {
            "current_price": 120.0,
            "candles_5m": {
                "opens": closes,
                "highs": [value + 1 for value in closes],
                "lows": [value - 1 for value in closes],
                "closes": closes,
                "volumes": [1000.0] * len(closes),
            },
            "candles_15m": {"closes": closes.copy()},
        }

        one_short = TechnicalAnalysisDepartment().analyze(market_data)
        market_data["candles_15m"]["closes"].append(121.0)
        ready = TechnicalAnalysisDepartment().analyze(market_data)

        self.assertFalse(one_short["data_quality"]["m15_trend_available"])
        self.assertTrue(ready["data_quality"]["m15_trend_available"])
        self.assertEqual(ready["m15_trend"], "BULLISH")

if __name__ == "__main__":
    unittest.main()
