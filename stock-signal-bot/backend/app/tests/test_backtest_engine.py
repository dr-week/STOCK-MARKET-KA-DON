import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.routes import process_unified_stock
from app.api import scan_orchestrator
from app.backtesting import backtest_engine
from app.backtesting import simulation, simulation_loop
from app.core.config import MIN_CONFLUENCE_SCORE
from app.departments.fundamental_analysis.service import fundamental_dep
from app.departments.market_data.service import market_data_dep
from app.departments.signal_risk.service import signal_risk_dep
from app.departments.technical_analysis.service import technical_dep
from app.main import app


IST = timezone(timedelta(hours=5, minutes=30))


def make_two_session_bars(bars_per_session=32):
    start = datetime(2026, 10, 26, 9, 15, tzinfo=IST)
    bars = []
    for session in range(2):
        session_start = start + timedelta(days=session)
        for index in range(bars_per_session):
            timestamp = int((session_start + timedelta(minutes=5 * index)).timestamp())
            bars.append({
                "time": timestamp,
                "open": 100.0,
                "high": 101.0,
                "low": 99.5,
                "close": 100.0,
                "volume": 1000.0,
            })
    return bars


class TestBacktestEngine(unittest.TestCase):
    def test_app_exposes_health_and_root_endpoints(self):
        client = TestClient(app)

        root_response = client.get("/")
        self.assertEqual(root_response.status_code, 200)
        self.assertIn("SMKD", root_response.json()["app"])

        health_response = client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json()["status"], "ok")

    def test_build_signal_uses_production_technical_and_risk_services(self):
        bars = make_two_session_bars()[:32]
        decision = simulation.build_signal(
            bars,
            index=31,
            threshold=7,
            intelligence={"session": {}, "nifty_50": {"trend": "SIDEWAYS"}},
        )

        self.assertIsNotNone(decision)
        self.assertIn(decision["signal"], ("BUY CANDIDATE", "SELL CANDIDATE", "SCANNING", "WATCHING"))
        self.assertIn("confluence_score", decision)
        self.assertIn("risk_sizing", decision)

    def test_process_unified_stock_includes_lightweight_ai_decision(self):
        with patch.object(market_data_dep, "get_stock_data", return_value={
            "current_price": 248.5,
            "change_pct": 1.8,
            "day_high": 251.0,
            "day_low": 245.0,
            "volume_today": 220000,
            "timestamp": 1700000000,
            "candles_5m": {
                "opens": [246.0] * 20,
                "highs": [249.0] * 20,
                "lows": [244.5] * 20,
                "closes": [246.8, 247.5, 248.0, 248.4, 249.2, 249.8, 249.1, 248.6, 248.9, 249.5,
                           250.0, 249.7, 249.1, 249.8, 250.5, 250.6, 250.2, 250.8, 251.2, 251.5],
                "volumes": [1000] * 20,
            },
            "candles_daily": {"closes": [240.0, 242.0, 246.0, 248.0]},
        }), \
            patch.object(technical_dep, "analyze", return_value={
                "vwap": 247.0,
                "rsi": 62.0,
                "ema_9": 249.2,
                "ema_21": 247.5,
                "atr": 2.4,
                "adx": 28.0,
                "market_structure": {"trend": "BULLISH", "description": "Bullish continuation", "bos": True, "last_swing_low": 245.0},
                "supply_demand": {"demand_zone": {"bottom": 246.0, "top": 248.0}, "at_demand": True},
                "key_candle": {"is_bullish": True},
                "sparkline": [246.4, 247.1, 247.7, 248.5, 249.2, 249.8, 249.1, 249.7, 250.3, 250.8],
                "rvol": 1.4,
            }), \
            patch.object(fundamental_dep, "analyze", return_value={
                "quality_filter_passed": True,
                "news": [{"sentiment": "BULLISH"}, {"sentiment": "NEUTRAL"}],
                "news_summary": {"overall_sentiment": "BULLISH"},
            }), \
            patch.object(signal_risk_dep, "synthesize_decision", return_value={
                "signal": "BUY CANDIDATE",
                "confluence_score": 8,
                "confidence": 88,
                "entry": 248.5,
                "target_1": 253.2,
                "target_2": 255.6,
                "stop_loss": 245.8,
                "reasons": ["Trend confirmation"],
                "risk_sizing": {
                    "shares_qty": 10,
                    "allowable_risk_inr": 90.0,
                    "estimated_friction_inr": 4.0,
                    "estimated_brokerage_inr": 3.0,
                    "estimated_statutory_charges_inr": 1.0,
                    "expected_net_t1_inr": 43.0,
                    "estimated_loss_at_stop_inr": 31.0,
                    "break_even_move_per_share": 0.4,
                    "minimum_profitable_qty_at_t1": 1,
                },
            }):
            result = process_unified_stock({
                "symbol": "RELIANCE",
                "name": "Reliance Industries",
                "sector": "Energy",
                "groww": "reliance-industries",
                "ticker": "RELIANCE.NS",
            }, {
                "session": {"phase": "MORNING_SESSION", "ist_time": "10:30"},
                "nifty_50": {"trend": "BULLISH"},
            })
            passed_signal = result["signal_decision"]["signal"]
            with patch.object(scan_orchestrator, "evaluate_intraday_profitability", return_value={
                "profitability_eligible": False,
                "viability_status": "WAIT — ADX is unavailable (warm-up incomplete)",
            }):
                blocked = process_unified_stock({
                    "symbol": "RELIANCE",
                    "name": "Reliance Industries",
                    "sector": "Energy",
                    "groww": "reliance-industries",
                    "ticker": "RELIANCE.NS",
                }, {
                    "session": {"phase": "MORNING_SESSION", "ist_time": "10:30"},
                    "nifty_50": {"trend": "BULLISH"},
                })

        self.assertIn("ai_decision", result)
        self.assertIn("probable_move_pct", result["ai_decision"])
        self.assertGreaterEqual(result["ai_decision"]["ai_score"], 0.5)
        self.assertIn("ai_verdict", result["ai_decision"])
        self.assertTrue(result["intraday"]["risk_sizing"]["trend_strength_passed"])
        self.assertTrue(result["intraday"]["risk_sizing"]["movement_covers_costs"])
        self.assertEqual(
            result["intraday"]["risk_sizing"]["viability_status"],
            "TRADE FILTER PASSED — modeled edge covers costs",
        )
        self.assertIn("CANDIDATE", passed_signal)

        self.assertEqual(blocked["signal_decision"]["signal"], "WAIT")
        self.assertEqual(blocked["signal_decision"]["setup_signal"], "BUY CANDIDATE")
        self.assertEqual(blocked["intraday"]["signal"], "WAIT")
        self.assertEqual(blocked["intraday"]["setup_signal"], "BUY CANDIDATE")
        self.assertFalse(blocked["intraday"]["risk_sizing"]["profitability_eligible"])
        self.assertTrue(any("ADX is unavailable" in reason for reason in blocked["intraday"]["reasons"]))

    def test_simulation_resets_warmup_and_closes_within_session(self):
        bars = make_two_session_bars()
        candidate = {
            "signal": "BUY CANDIDATE",
            "confluence_score": 7,
            "entry": 100.0,
            "stop_loss": 98.0,
            "target_1": 104.0,
        }
        with patch.object(simulation_loop, "build_signal", return_value=candidate):
            result = simulation_loop.simulate_threshold(
                bars,
                threshold=7,
                intelligence={"session": {}, "nifty_50": {"trend": "SIDEWAYS"}},
                holding_bars=15,
                cost_bps_per_side=5.0,
            )

        self.assertEqual(result["total_signals"], 2)
        for trade in result["trades"]:
            signal_day = simulation_loop._session_key(trade["signal_time"])
            entry_day = simulation_loop._session_key(trade["entry_time"])
            exit_index = next(i for i, bar in enumerate(bars) if bar["time"] == trade["entry_time"])
            exit_day = simulation_loop._session_key(bars[exit_index + trade["bars_held"] - 1]["time"])
            self.assertEqual(signal_day, entry_day)
            self.assertEqual(entry_day, exit_day)
            self.assertEqual(trade["outcome"], "TIME_EXPIRED")
            self.assertGreater(trade["estimated_round_trip_cost_pct"], 0)

    def test_threshold_comparison_does_not_change_live_configuration(self):
        original_threshold = MIN_CONFLUENCE_SCORE
        bars = make_two_session_bars()
        with patch.object(backtest_engine, "load_bars", return_value=bars), patch.object(
            simulation_loop, "build_signal", return_value={"signal": "SCANNING"}
        ):
            result = backtest_engine.run_historical_backtest("RELIANCE", days=2, optimize=True)

        self.assertEqual(MIN_CONFLUENCE_SCORE, original_threshold)
        self.assertEqual([item["threshold"] for item in result["threshold_comparison"]], [6, 7, 8, 9])
        self.assertNotIn("suggested_threshold", result)
        self.assertIn("written to production", result["optimization_notice"])

    def test_both_stop_and_target_touched_uses_conservative_stop(self):
        bars = make_two_session_bars()
        bars[31]["high"] = 105.0
        bars[31]["low"] = 97.0
        candidate = {
            "signal": "BUY CANDIDATE",
            "confluence_score": 7,
            "entry": 100.0,
            "stop_loss": 98.0,
            "target_1": 104.0,
        }
        with patch.object(simulation_loop, "build_signal", return_value=candidate):
            result = simulation_loop.simulate_threshold(
                bars,
                threshold=7,
                intelligence={"session": {}, "nifty_50": {"trend": "SIDEWAYS"}},
                holding_bars=3,
                cost_bps_per_side=5.0,
            )

        self.assertEqual(result["trades"][0]["outcome"], "STOP_LOSS_HIT")
        self.assertEqual(result["trades"][0]["exit"], 98.0)

    def test_adverse_gap_after_entry_uses_open_fill(self):
        bars = make_two_session_bars(bars_per_session=34)
        bars[32]["open"] = 97.0
        bars[32]["high"] = 98.0
        bars[32]["low"] = 96.0
        bars[32]["close"] = 97.0
        candidate = {
            "signal": "BUY CANDIDATE",
            "confluence_score": 7,
            "entry": 100.0,
            "stop_loss": 98.0,
            "target_1": 104.0,
        }
        with patch.object(simulation_loop, "build_signal", return_value=candidate):
            result = simulation_loop.simulate_threshold(
                bars,
                threshold=7,
                intelligence={"session": {}, "nifty_50": {"trend": "SIDEWAYS"}},
                holding_bars=3,
                cost_bps_per_side=5.0,
            )

        trade = result["trades"][0]
        self.assertEqual(trade["outcome"], "STOP_LOSS_GAP")
        self.assertEqual(trade["entry"], 100.0)
        self.assertEqual(trade["exit"], 97.0)


if __name__ == "__main__":
    unittest.main()
