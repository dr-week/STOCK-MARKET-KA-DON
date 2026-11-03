import unittest

from app.indicators.price_action_patterns import detect_price_action_patterns
from app.departments.technical_analysis.service import TechnicalAnalysisDepartment


def build_series(closes, opens=None, highs=None, lows=None):
    opens = opens or [closes[index - 1] if index else closes[index] for index in range(len(closes))]
    highs = highs or [max(opens[index], closes[index]) + 0.2 for index in range(len(closes))]
    lows = lows or [min(opens[index], closes[index]) - 0.2 for index in range(len(closes))]
    return opens, highs, lows, closes, [1000.0] * len(closes)


class PriceActionPatternTests(unittest.TestCase):
    def test_detects_doji_as_neutral_indecision(self):
        closes = [100.0, 100.5, 100.2, 100.4, 100.02]
        opens = [100.0, 100.0, 100.5, 100.2, 100.0]
        highs = [100.4, 100.8, 100.6, 100.7, 101.0]
        lows = [99.8, 99.9, 100.0, 100.0, 99.0]
        patterns = detect_price_action_patterns(*build_series(closes, opens, highs, lows))
        doji = next(pattern for pattern in patterns if pattern["type"] == "DOJI")
        self.assertEqual(doji["direction"], "NEUTRAL")
        self.assertIsNotNone(doji["confirmation_level"])

    def test_detects_hammer_only_after_decline(self):
        closes = [110.0, 108.0, 106.0, 104.0, 102.0, 100.2]
        opens = [111.0, 109.0, 107.0, 105.0, 103.0, 99.8]
        highs = [111.2, 109.2, 107.2, 105.2, 103.2, 100.3]
        lows = [109.8, 107.8, 105.8, 103.8, 101.8, 98.8]
        patterns = detect_price_action_patterns(*build_series(closes, opens, highs, lows))
        hammer = next(pattern for pattern in patterns if pattern["type"] == "HAMMER")
        self.assertEqual(hammer["direction"], "BULLISH")

    def test_detects_shooting_star_only_after_rise(self):
        closes = [100.0, 102.0, 104.0, 106.0, 108.0, 109.8]
        opens = [99.0, 101.0, 103.0, 105.0, 107.0, 110.2]
        highs = [100.2, 102.2, 104.2, 106.2, 108.2, 111.2]
        lows = [98.8, 100.8, 102.8, 104.8, 106.8, 109.7]
        patterns = detect_price_action_patterns(*build_series(closes, opens, highs, lows))
        star = next(pattern for pattern in patterns if pattern["type"] == "SHOOTING_STAR")
        self.assertEqual(star["direction"], "BEARISH")

    def test_detects_bullish_engulfing_after_decline(self):
        closes = [110.0, 108.0, 106.0, 104.0, 102.0, 104.5]
        opens = [111.0, 109.0, 107.0, 105.0, 104.0, 101.0]
        highs = [111.2, 109.2, 107.2, 105.2, 104.2, 104.7]
        lows = [109.8, 107.8, 105.8, 103.8, 101.8, 100.8]
        patterns = detect_price_action_patterns(*build_series(closes, opens, highs, lows))
        engulfing = next(pattern for pattern in patterns if pattern["type"] == "BULLISH_ENGULFING")
        self.assertEqual(engulfing["direction"], "BULLISH")

    def test_detects_bearish_engulfing_after_rise(self):
        closes = [100.0, 102.0, 104.0, 106.0, 108.0, 105.5]
        opens = [99.0, 101.0, 103.0, 105.0, 106.0, 109.0]
        highs = [100.2, 102.2, 104.2, 106.2, 108.2, 109.2]
        lows = [98.8, 100.8, 102.8, 104.8, 105.8, 105.0]
        patterns = detect_price_action_patterns(*build_series(closes, opens, highs, lows))
        engulfing = next(pattern for pattern in patterns if pattern["type"] == "BEARISH_ENGULFING")
        self.assertEqual(engulfing["direction"], "BEARISH")

    def test_detects_bull_flag_like_pullback_as_unconfirmed(self):
        closes = [100.0] * 20 + [101.0, 102.0, 103.0, 104.0, 103.5, 103.0, 102.5, 102.0]
        patterns = detect_price_action_patterns(*build_series(closes))
        flag = next(pattern for pattern in patterns if pattern["type"] == "BULL_FLAG")
        self.assertEqual(flag["direction"], "BULLISH")
        self.assertEqual(flag["status"], "forming")

    def test_detects_bear_flag_like_rally_as_unconfirmed(self):
        closes = [100.0] * 20 + [99.0, 98.0, 97.0, 96.0, 96.5, 97.0, 97.5, 98.0]
        patterns = detect_price_action_patterns(*build_series(closes))
        flag = next(pattern for pattern in patterns if pattern["type"] == "BEAR_FLAG")
        self.assertEqual(flag["direction"], "BEARISH")
        self.assertEqual(flag["status"], "forming")

    def test_rejects_misaligned_or_inconsistent_candles(self):
        with self.assertRaisesRegex(ValueError, "matching lengths"):
            detect_price_action_patterns([1.0], [], [], [], [])
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            detect_price_action_patterns([10.0], [9.0], [11.0], [10.0], [1.0])

    def test_technical_analysis_exposes_patterns_and_respects_warmup(self):
        closes = [110.0 - 0.5 * index for index in range(27)] + [97.0]
        opens = [close + 0.1 for close in closes[:-1]] + [97.0]
        highs = [max(open_price, close) + 0.2 for open_price, close in zip(opens, closes)]
        lows = [min(open_price, close) - 0.2 for open_price, close in zip(opens, closes)]
        highs[-1] = 97.5
        lows[-1] = 96.5
        department = TechnicalAnalysisDepartment()
        analysis = department.analyze({
            "current_price": closes[-1],
            "candles_5m": {
                "opens": opens,
                "highs": highs,
                "lows": lows,
                "closes": closes,
                "volumes": [1000.0] * len(closes),
            },
        })
        self.assertEqual(analysis["data_quality"]["status"], "available")
        self.assertEqual(analysis["price_action_patterns"][0]["type"], "DOJI")

        insufficient = department.analyze({
            "current_price": closes[-1],
            "candles_5m": {
                "opens": opens[:-1],
                "highs": highs[:-1],
                "lows": lows[:-1],
                "closes": closes[:-1],
                "volumes": [1000.0] * (len(closes) - 1),
            },
        })
        self.assertEqual(insufficient["price_action_patterns"], [])


if __name__ == "__main__":
    unittest.main()
