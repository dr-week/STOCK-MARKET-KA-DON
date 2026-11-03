import unittest

from app.indicators.profitability import evaluate_intraday_profitability


class TestProfitabilityGate(unittest.TestCase):
    def test_low_adx_blocks_trade_even_when_target_is_positive(self):
        result = evaluate_intraday_profitability(
            {"break_even_move_per_share": 0.20, "expected_net_t1_inr": 10},
            adx=15, atr_5m=1.0, is_candidate=True,
        )
        self.assertFalse(result["profitability_eligible"])
        self.assertIn("DO NOT TRADE", result["viability_status"])

    def test_pass_requires_both_adx_and_range(self):
        result = evaluate_intraday_profitability(
            {"break_even_move_per_share": 0.50, "expected_net_t1_inr": 10},
            adx=25, atr_5m=0.60, is_candidate=True,
        )
        self.assertTrue(result["profitability_eligible"])


if __name__ == "__main__":
    unittest.main()
