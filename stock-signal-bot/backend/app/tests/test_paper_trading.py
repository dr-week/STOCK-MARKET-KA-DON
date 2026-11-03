import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import routes_paper
from app.main import app
from app.paper_trading.engine import PaperTradingEngine


class TestPaperTrading(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "paper_trades.db"
        self.path_patch = patch("app.paper_trading.ledger_repository.DB_PATH", str(self.database_path))
        self.path_patch.start()
        self.engine = PaperTradingEngine()
        self.engine_patch = patch.object(routes_paper, "paper_engine", self.engine)
        self.engine_patch.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine_patch.stop()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_records_and_closes_a_paper_trade_in_sqlite(self):
        opened = self.client.post("/api/paper/order", json={
            "symbol": "reliance",
            "action": "BUY",
            "entry": 100,
            "stop_loss": 98,
            "target": 104,
            "qty": 5,
            "confluence_score": 7,
        })

        self.assertEqual(opened.status_code, 200)
        position = opened.json()["position"]
        self.assertEqual(position["symbol"], "RELIANCE")
        self.assertEqual(position["status"], "OPEN")
        self.assertTrue(position["opened_at"])
        self.assertEqual(len(self.engine.get_open_positions()), 1)

        closed = self.client.post(
            f"/api/paper/close/{position['id']}",
            json={"exit_price": 103},
        )
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.json()["position"]["status"], "CLOSED")
        self.assertEqual(closed.json()["position"]["pnl"], 15)
        self.assertTrue(closed.json()["position"]["closed_at"])
        self.assertEqual(self.engine.get_open_positions(), [])
        self.assertEqual(self.engine.get_closed_positions()[0]["id"], position["id"])

    def test_rejects_directionally_invalid_levels_and_fractional_quantity(self):
        invalid_levels = self.client.post("/api/paper/order", json={
            "symbol": "RELIANCE",
            "action": "BUY",
            "entry": 100,
            "stop_loss": 101,
            "target": 104,
            "qty": 5,
        })
        fractional_quantity = self.client.post("/api/paper/order", json={
            "symbol": "RELIANCE",
            "action": "BUY",
            "entry": 100,
            "stop_loss": 98,
            "target": 104,
            "qty": 1.5,
        })

        self.assertEqual(invalid_levels.status_code, 422)
        self.assertEqual(fractional_quantity.status_code, 422)
        self.assertEqual(self.engine.get_open_positions(), [])

    def test_refuses_to_close_a_position_twice(self):
        position = self.engine.place_order("RELIANCE", "BUY", 100, 98, 104, 1)
        first_close = self.client.post(
            f"/api/paper/close/{position['id']}",
            json={"exit_price": 101},
        )
        second_close = self.client.post(
            f"/api/paper/close/{position['id']}",
            json={"exit_price": 102},
        )

        self.assertEqual(first_close.status_code, 200)
        self.assertEqual(second_close.status_code, 400)
        self.assertEqual(self.engine.get_closed_positions()[0]["exit_price"], 101)

    def test_automatic_paper_trading_is_always_on(self):
        initial = self.client.get("/api/paper/automation")
        disabled = self.client.put("/api/paper/automation", json={"enabled": False})

        self.assertEqual(initial.status_code, 200)
        self.assertTrue(initial.json()["enabled"])
        self.assertEqual(initial.json()["mode"], "always_on_paper")
        self.assertFalse(initial.json()["broker_orders_placed"])
        self.assertFalse(initial.json()["real_money_used"])
        self.assertGreater(initial.json()["virtual_capital_inr"], 0)
        self.assertGreater(initial.json()["risk_per_trade_pct"], 0)
        self.assertEqual(disabled.status_code, 409)
        self.assertTrue(self.client.get("/api/paper/automation").json()["enabled"])

    def test_feedback_learning_status_is_research_only(self):
        response = self.client.get("/api/feedback/learning")

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["required_outcomes"], 0)
        self.assertFalse(response.json()["production_model_updated"])

    def test_pnl_reports_lifetime_automatic_results_separately(self):
        winner = self.engine.place_order("AAA", "BUY", 100, 95, 110, 2, source="AUTO")
        loser = self.engine.place_order("BBB", "SELL", 100, 105, 90, 1, source="AUTO")
        self.engine.place_order("CCC", "BUY", 50, 45, 55, 1, source="AUTO")
        self.engine.place_order("DDD", "BUY", 50, 45, 55, 1, source="MANUAL")
        self.engine.close_position(winner["id"], 110)
        self.engine.close_position(loser["id"], 105)

        response = self.client.get("/api/paper/pnl")

        self.assertEqual(response.status_code, 200)
        automatic = response.json()["automatic"]
        manual = response.json()["manual"]
        self.assertEqual(automatic["attempted_trades"], 3)
        self.assertEqual(automatic["closed_trades"], 2)
        self.assertEqual(automatic["open_trades"], 1)
        self.assertEqual(automatic["wins"], 1)
        self.assertEqual(automatic["losses"], 1)
        self.assertEqual(automatic["win_rate_pct"], 50.0)
        self.assertEqual(automatic["realized_pnl"], 15.0)
        self.assertEqual(automatic["return_on_entry_notional_pct"], 5.0)
        self.assertEqual(manual["attempted_trades"], 1)
        self.assertIsNone(manual["win_rate_pct"])


if __name__ == "__main__":
    unittest.main()
