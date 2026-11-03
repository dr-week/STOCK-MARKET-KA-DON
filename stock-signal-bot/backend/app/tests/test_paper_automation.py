from contextlib import closing
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.feedback.recorder import SignalFeedbackRecorder
from app.paper_trading import engine as engine_module
from app.paper_trading.automation import PaperAutomationService


class TestPaperAutomation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "paper_trades.db")
        self.engine_path_patch = patch.object(engine_module.ledger_repository, "DB_PATH", self.database_path)
        self.engine_path_patch.start()
        self.engine = engine_module.PaperTradingEngine()
        self.feedback = SignalFeedbackRecorder(self.database_path)
        self.automation = PaperAutomationService(self.engine, self.feedback)
        self.learning_patch = patch(
            "app.paper_trading.automation.feedback_learning.schedule_after_outcome"
        )
        self.learning_mock = self.learning_patch.start()
        self.market_session_patch = patch(
            "app.paper_trading.automation.get_market_session_state",
            return_value={"can_trade_intraday": True},
        )
        self.market_session_patch.start()

    def tearDown(self):
        self.market_session_patch.stop()
        self.learning_patch.stop()
        self.engine_path_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def scan_result(price=100.0, signal="BUY CANDIDATE", fetched_at=None, candle_at=None):
        now = time.time()
        return {
            "symbol": "RELIANCE",
            "current_price": price,
            "market_data": {
                "data_quality": {
                    "status": "available",
                    "mode": "provider",
                    "provider": "yahoo_finance",
                    "fetched_at": fetched_at if fetched_at is not None else now,
                    "source_timestamp": now,
                    "last_complete_candle_timestamp": candle_at if candle_at is not None else now - 60,
                }
            },
            "signal_decision": {
                "signal": signal,
                "confluence_score": 8,
                "stop_loss": 98,
                "target_1": 104,
                "risk_sizing": {"shares_qty": 10},
            },
            "ai_decision": {"ai_score": 0.7},
            "technicals": {
                "rsi": 55.0,
                "adx": 28.0,
                "rvol": 1.5,
                "vwap": 99.0,
                "ema_9": 101.0,
                "ema_21": 100.0,
                "atr": 1.2,
            },
        }

    def test_auto_paper_runs_without_enabling_setting(self):
        result = self.automation.process_scan_results([self.scan_result()])

        self.assertEqual(result["enabled"], True)
        self.assertFalse(result["broker_orders_placed"])
        self.assertFalse(result["real_money_used"])
        self.assertEqual(result["opened"], 1)
        self.assertEqual(self.engine.get_open_positions()[0]["source"], "AUTO")

    def test_fresh_valid_signal_opens_and_target_exit_records_feedback(self):
        opened = self.automation.process_scan_results([self.scan_result()])

        self.assertEqual(opened["opened"], 1)
        position = self.engine.get_open_positions()[0]
        self.assertEqual(position["source"], "AUTO")
        self.assertEqual(position["qty"], 10)
        self.assertIsNotNone(position["feedback_signal_id"])

        closed = self.automation.process_scan_results([self.scan_result(price=104.5)])

        self.assertEqual(closed["closed"], 1)
        self.assertEqual(closed["opened"], 0)
        saved = self.engine.get_closed_positions()[0]
        self.assertEqual(saved["exit_price"], 104)
        self.assertEqual(saved["pnl"], 40)
        outcome = self.feedback._get_signal_by_id(position["feedback_signal_id"])
        self.assertEqual(outcome["outcome"], "WIN")
        self.assertEqual(outcome["actual_exit"], 104)
        self.assertEqual(outcome["provider_id"], "yahoo_finance")
        self.assertIn("vwap_distance_pct", outcome["features_json"])
        self.learning_mock.assert_called_once_with("yahoo_finance", self.database_path)
        self.assertEqual(self.feedback.get_accuracy_stats()["win_rate_pct"], 100.0)

    def test_stale_data_neither_opens_nor_marks_positions(self):
        self.engine.place_order("RELIANCE", "BUY", 100, 98, 104, 10, source="AUTO")
        stale = self.scan_result(
            fetched_at=time.time() - 16 * 60,
            candle_at=time.time() - 16 * 60,
        )

        result = self.automation.process_scan_results([stale])

        self.assertEqual(result["opened"], 0)
        self.assertEqual(len(self.engine.get_open_positions()), 1)

    def test_auto_target_exit_records_feedback(self):
        self.automation.process_scan_results([self.scan_result()])

        result = self.automation.process_scan_results([self.scan_result(price=97)])

        self.assertEqual(result["closed"], 1)
        saved = self.engine.get_closed_positions()[0]
        self.assertEqual(saved["exit_price"], 98)
        self.assertEqual(saved["pnl"], -20)
        outcome = self.feedback._get_signal_by_id(saved["feedback_signal_id"])
        self.assertEqual(outcome["outcome"], "LOSS")

    def test_manual_positions_are_not_managed_by_automation(self):
        self.engine.place_order("RELIANCE", "BUY", 100, 98, 104, 10)

        result = self.automation.process_scan_results([self.scan_result(price=105)])

        self.assertEqual(result["closed"], 0)
        self.assertEqual(result["opened"], 0)
        position = self.engine.get_open_positions()[0]
        self.assertEqual(position["source"], "MANUAL")
        self.assertIsNone(position["exit_price"])

    def test_auto_entries_stop_after_daily_loss_limit(self):
        losing_position = self.engine.place_order(
            "RELIANCE", "BUY", 100, 98, 104, 100, source="AUTO"
        )
        self.engine.close_position(losing_position["id"], 96)

        result = self.automation.process_scan_results([self.scan_result()])

        self.assertEqual(result["opened"], 0)
        self.assertEqual(self.engine.get_open_positions(), [])

    def test_existing_database_migrates_to_always_on_automation(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as connection, connection:
            connection.execute("""
                CREATE TABLE paper_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    target REAL NOT NULL,
                    qty REAL NOT NULL,
                    confluence_score REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    exit_price REAL,
                    pnl REAL DEFAULT 0,
                    unrealized_pnl REAL DEFAULT 0,
                    opened_at TEXT NOT NULL,
                    closed_at TEXT
                )
            """)
        with patch.object(engine_module.ledger_repository, "DB_PATH", str(legacy_path)):
            migrated_engine = engine_module.PaperTradingEngine()
            settings = migrated_engine.get_automation_settings()
            with closing(sqlite3.connect(legacy_path)) as connection:
                position_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(paper_positions)")
                }

        self.assertTrue(settings["enabled"])
        self.assertIn("source", position_columns)
        self.assertIn("feedback_signal_id", position_columns)


if __name__ == "__main__":
    unittest.main()
