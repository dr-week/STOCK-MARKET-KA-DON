import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api import routes_market_history, routes_scan
from app.departments.market_data.history_store import MarketHistoryStore
from app.departments.market_data.yahoo_history import (
    YahooFinanceHistoryProvider,
    YahooHistoryUnavailable,
)
from app.integrations.groww.history_provider import GrowwHistoryError, GrowwHistoryProvider
from app.main import app


class FakeHistoryClient:
    def __init__(self, candles):
        self.candles = candles
        self.request = None

    def get_historical_candles(self, **kwargs):
        self.request = kwargs
        return {"candles": self.candles}


class TestMarketHistoryStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "market_history.db")
        self.path_patch = patch("app.departments.market_data.history_store._DB_PATH", self.db_path)
        self.path_patch.start()
        self.store = MarketHistoryStore()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_saves_validated_candles_and_reads_them_in_time_order(self):
        candles = [
            {"timestamp": 1700000000, "open": 100, "high": 105, "low": 99, "close": 104, "volume": 500},
            {"timestamp": 1700000300, "open": 104, "high": 106, "low": 103, "close": 105, "volume": 600},
        ]

        saved = self.store.save_candles("reliance", "NSE-RELIANCE", "5m", "groww_trade_api", candles)
        rows = self.store.get_candles("RELIANCE", "5m")

        self.assertEqual(saved, 2)
        self.assertEqual([row["timestamp"] for row in rows], [1700000000, 1700000300])
        self.assertEqual(rows[0]["provider"], "groww_trade_api")
        self.assertEqual(self.store.save_candles("RELIANCE", "NSE-RELIANCE", "5m", "groww_trade_api", candles), 2)
        self.assertEqual(len(self.store.get_candles("RELIANCE", "5m")), 2)

    def test_rejects_inconsistent_or_unordered_candles(self):
        invalid_candles = [
            [{"timestamp": 1700000000, "open": 100, "high": 99, "low": 98, "close": 100, "volume": 1}],
            [
                {"timestamp": 1700000300, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
                {"timestamp": 1700000000, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
            ],
        ]
        for candles in invalid_candles:
            with self.subTest(candles=candles), self.assertRaises(ValueError):
                self.store.save_candles("RELIANCE", "NSE-RELIANCE", "5m", "test", candles)


class TestGrowwHistoryProvider(unittest.TestCase):
    def test_uses_bounded_documented_request_and_normalizes_ist_timestamps(self):
        client = FakeHistoryClient([
            ["2024-01-02 09:15:00", 100, 103, 99, 102, 5000, 0],
        ])

        result = GrowwHistoryProvider.fetch(client, "reliance", "5m", 30, date(2024, 1, 2))

        self.assertEqual(client.request["exchange"], "NSE")
        self.assertEqual(client.request["segment"], "CASH")
        self.assertEqual(client.request["groww_symbol"], "NSE-RELIANCE")
        self.assertEqual(client.request["candle_interval"], "5minute")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["candles"][0]["close"], 102)
        self.assertEqual(result["timestamp_basis"], "Provider timestamps without an offset are interpreted as Asia/Kolkata.")

    def test_rejects_request_beyond_provider_window(self):
        with self.assertRaisesRegex(ValueError, "1 to 30 days"):
            GrowwHistoryProvider.fetch(FakeHistoryClient([]), "RELIANCE", "5m", 31)

    def test_supports_a_bounded_historical_window_ending_on_a_selected_date(self):
        client = FakeHistoryClient([])

        GrowwHistoryProvider.fetch(client, "RELIANCE", "5m", 30, date(2024, 1, 2))

        self.assertEqual(client.request["end_time"], "2024-01-02 23:59:59")
        self.assertEqual(client.request["start_time"], "2023-12-03 23:59:59")

    def test_rejects_invalid_ohlcv_in_provider_response(self):
        client = FakeHistoryClient([
            ["2024-01-02 09:15:00", 100, 98, 99, 102, 5000, 0],
        ])
        with self.assertRaises(GrowwHistoryError):
            GrowwHistoryProvider.fetch(client, "RELIANCE", "5m", 30)


class TestYahooFinanceHistoryProvider(unittest.TestCase):
    def test_fetches_and_validates_bounded_public_history(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"""
        {
          "chart": {
            "result": [{
              "meta": {"symbol": "RELIANCE.NS"},
              "timestamp": [1700000000, 1700000300, 1700000600],
              "indicators": {
                "quote": [{
                  "open": [100, 101, 102],
                  "high": [102, 103, 104],
                  "low": [99, 100, 101],
                  "close": [101, 102, 103],
                  "volume": [1000, 1100, 1200]
                }]
              }
            }]
          }
        }
        """

        with patch("app.departments.market_data.yahoo_history.urllib.request.urlopen", return_value=response) as request:
            history = YahooFinanceHistoryProvider.fetch("RELIANCE", "5m", now=1700001500)

        self.assertEqual(history["provider"], "yahoo_finance_public_unofficial")
        self.assertEqual(history["count"], 3)
        self.assertEqual(history["candles"][-1]["close"], 103)
        self.assertIn("interval=5m&range=60d", request.call_args.args[0].full_url)

    def test_rejects_wrong_instrument_and_unsupported_intervals(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"""
        {"chart":{"result":[{"meta":{"symbol":"OTHER.NS"},"timestamp":[1700000000],
        "indicators":{"quote":[{"open":[100],"high":[101],"low":[99],"close":[100],"volume":[1]}]}}]}}
        """
        with patch("app.departments.market_data.yahoo_history.urllib.request.urlopen", return_value=response):
            with self.assertRaises(YahooHistoryUnavailable):
                YahooFinanceHistoryProvider.fetch("RELIANCE", "5m", now=1700001500)
        with self.assertRaisesRegex(ValueError, "does not support"):
            YahooFinanceHistoryProvider.fetch("RELIANCE", "3m")


class TestMarketHistoryRoute(unittest.TestCase):
    def test_returns_local_candles_and_restricts_non_loopback_clients(self):
        candle = {
            "symbol": "RELIANCE",
            "ticker": "NSE-RELIANCE",
            "interval": "15m",
            "timestamp": 1700000000,
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 500.0,
            "provider": "groww_trade_api",
            "observed_at": "2026-11-02T00:00:00+00:00",
        }
        with (
            patch.object(routes_market_history.yahoo_finance_history, "fetch", return_value={
                "provider": "yahoo_finance_public_unofficial",
                "candles": [{
                    "timestamp": candle["timestamp"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                }],
            }),
            patch.object(routes_market_history.market_history_store, "save_candles", return_value=1),
            patch.object(routes_market_history.market_history_store, "get_candles", return_value=[candle]),
        ):
            local = TestClient(app, client=("127.0.0.1", 50000))
            response = local.get("/api/market-history/RELIANCE?interval=15m")
            local.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candles"][0]["timestamp"], 1700000000)
        self.assertEqual(response.json()["provider"], "yahoo_finance_public_unofficial")
        remote = TestClient(app, client=("192.0.2.10", 50000))
        denied = remote.get("/api/market-history/RELIANCE")
        remote.close()
        self.assertEqual(denied.status_code, 403)


class TestSingleStockSymbolLookup(unittest.TestCase):
    def test_supports_valid_untracked_symbols_and_rejects_invalid_input(self):
        client = TestClient(app, client=("127.0.0.1", 50000))
        with patch.object(routes_scan.market_intelligence_dep, "get_intelligence", return_value={}):
            with patch.object(routes_scan, "process_unified_stock", return_value={"symbol": "M&M"}) as process:
                response = client.get("/api/stock/M%26M")
            invalid = client.get("/api/stock/%20")
        client.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(process.call_args.args[0]["symbol"], "M&M")
        self.assertEqual(process.call_args.args[0]["groww"], "m&m")
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
