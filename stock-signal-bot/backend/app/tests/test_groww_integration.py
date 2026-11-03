import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import routes_groww
from app.integrations.groww.service import GrowwIntegrationError, GrowwReadOnlyService
from app.main import app


class FakeGrowwClient:
    def __init__(self, token):
        self.token = token
        self.read_calls = []

    def get_holdings_for_user(self, **kwargs):
        self.read_calls.append(("holdings", kwargs))
        return {
            "holdings": [{
                "trading_symbol": "RELIANCE",
                "quantity": 3,
                "average_price": 2500,
                "isin": "INE002A01018",
                "t1_quantity": 0,
            }]
        }

    def get_positions_for_user(self, segment, **kwargs):
        self.read_calls.append(("positions", segment, kwargs))
        return {"positions": [{
            "trading_symbol": "RELIANCE",
            "segment": segment,
            "quantity": 2 if segment == "CASH" else 0,
            "net_price": 2500,
            "realised_pnl": 0,
        }]}

    def get_order_list(self, segment, **kwargs):
        self.read_calls.append(("orders", segment, kwargs))
        return {"orders": [{
            "groww_order_id": f"order-{segment}",
            "trading_symbol": "RELIANCE",
            "transaction_type": "BUY",
            "order_status": "EXECUTED",
            "segment": segment,
            "created_at": "2026-11-02T10:01:00+05:30",
        }]}

    def get_trade_list_for_order(self, groww_order_id, segment, **kwargs):
        self.read_calls.append(("trades", groww_order_id, segment, kwargs))
        return {"trades": [{
            "groww_order_id": groww_order_id,
            "groww_trade_id": f"trade-{segment}",
            "trading_symbol": "RELIANCE",
            "transaction_type": "BUY",
            "segment": segment,
            "exchange": "NSE",
            "quantity": 2,
            "price": 2501.5,
            "trade_status": "EXECUTED",
            "trade_date_time": "2026-11-02T10:01:02+05:30",
        }]}

    def get_historical_candles(self, **kwargs):
        self.read_calls.append(("historical_candles", kwargs))
        return {"candles": [["2024-01-02 09:15:00", 100, 103, 99, 102, 5000, 0]]}


class TestGrowwReadOnlyIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, client=("127.0.0.1", 50000))
        self.service = GrowwReadOnlyService()
        self.service_patch = patch.object(routes_groww, "groww_read_only", self.service)
        self.service_patch.start()
        self.client_patch = patch("app.integrations.groww.service.GrowwAPI")
        self.groww_api = self.client_patch.start()
        self.fake_client = FakeGrowwClient("ephemeral-access-token")
        self.groww_api.get_access_token.return_value = "ephemeral-access-token"
        self.groww_api.return_value = self.fake_client

    def tearDown(self):
        self.service.disconnect()
        self.client_patch.stop()
        self.service_patch.stop()
        self.client.close()

    def test_account_snapshot_contains_validated_positions_and_exact_execution_times(self):
        connected = self.client.post("/api/groww/connect", json={
            "api_key": "local-test-key",
            "secret": "local-test-secret",
        })
        snapshot = self.client.get("/api/groww/account")

        self.assertEqual(connected.status_code, 200)
        self.assertEqual(connected.json(), {"connected": True})
        self.assertEqual(snapshot.status_code, 200)
        body = snapshot.json()
        self.assertEqual(body["holdings"][0]["symbol"], "RELIANCE")
        self.assertEqual(body["positions"][0]["quantity"], 2)
        self.assertEqual(body["executions"][0]["price"], 2501.5)
        self.assertEqual(body["executions"][0]["executed_at"], "2026-11-02T10:01:02+05:30")
        self.assertEqual(body["orders"][0]["created_at"], "2026-11-02T10:01:00+05:30")
        self.assertNotIn("local-test-secret", snapshot.text)
        self.assertNotIn("ephemeral-access-token", snapshot.text)
        self.assertEqual(self.groww_api.get_access_token.call_args.kwargs["secret"], "local-test-secret")
        self.assertTrue(all(call[0] != "place_order" for call in self.fake_client.read_calls))

    def test_disconnect_clears_the_in_memory_session(self):
        self.service.connect("local-test-key", "local-test-secret")

        response = self.client.post("/api/groww/disconnect")
        account = self.client.get("/api/groww/account")

        self.assertEqual(response.json(), {"connected": False})
        self.assertEqual(account.status_code, 502)
        self.assertNotIn("local-test-secret", account.text)

    def test_invalid_provider_payload_is_not_reported_as_empty_success(self):
        self.service.connect("local-test-key", "local-test-secret")
        self.fake_client.get_holdings_for_user = lambda **kwargs: {"unexpected": []}

        with self.assertRaises(GrowwIntegrationError):
            self.service.snapshot()

    def test_authentication_error_does_not_echo_credentials(self):
        self.groww_api.get_access_token.side_effect = RuntimeError("credential rejected")

        response = self.client.post("/api/groww/connect", json={
            "api_key": "private-key",
            "secret": "private-secret",
        })

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private-key", response.text)
        self.assertNotIn("private-secret", response.text)
        self.assertFalse(self.service.is_connected())

    def test_account_endpoints_reject_non_loopback_clients(self):
        remote_client = TestClient(app, client=("192.0.2.10", 50000))

        response = remote_client.get("/api/groww/status")

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("connected", response.json())
        remote_client.close()

    def test_historical_candles_are_validated_and_archived_separately(self):
        self.service.connect("local-test-key", "local-test-secret")
        with patch.object(routes_groww.market_history_store, "save_candles", return_value=1) as archive:
            response = self.client.get("/api/groww/history/RELIANCE?interval=5m&days=30&end_date=2024-01-02")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["provider"], "groww_trade_api")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["archived_count"], 1)
        self.assertEqual(body["candles"][0]["close"], 102)
        self.assertEqual(archive.call_args.args[0:4], ("RELIANCE", "NSE-RELIANCE", "5m", "groww_trade_api"))
        request = next(call[1] for call in self.fake_client.read_calls if call[0] == "historical_candles")
        self.assertEqual(request["groww_symbol"], "NSE-RELIANCE")
        self.assertEqual(request["candle_interval"], "5minute")

    def test_one_and_three_minute_history_are_supported(self):
        self.service.connect("local-test-key", "local-test-secret")
        for interval, expected_provider_interval in (("1m", "1minute"), ("3m", "3minute")):
            with self.subTest(interval=interval), patch.object(
                routes_groww.market_history_store, "save_candles", return_value=0
            ):
                response = self.client.get(
                    f"/api/groww/history/RELIANCE?interval={interval}&days=30&end_date=2024-01-02"
                )
                request = next(
                    call[1] for call in self.fake_client.read_calls
                    if call[0] == "historical_candles" and call[1]["candle_interval"] == expected_provider_interval
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["interval"], interval)
                self.assertEqual(request["candle_interval"], expected_provider_interval)

    def test_history_endpoint_rejects_non_loopback_clients(self):
        remote_client = TestClient(app, client=("192.0.2.10", 50000))
        response = remote_client.get("/api/groww/history/RELIANCE")
        self.assertEqual(response.status_code, 403)
        remote_client.close()


if __name__ == "__main__":
    unittest.main()
