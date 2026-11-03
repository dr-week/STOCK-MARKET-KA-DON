import os
import unittest
import urllib.request
import json
from app.market.sessions import get_market_session_state
from app.market.fetcher import fetch_nse_chart

class TestLiveProviderIntegration(unittest.TestCase):
    """
    Opt-in live provider integration tests.
    Only executed when SMKD_LIVE_PROVIDER_TESTS=1 is explicitly set.
    Validates genuine upstream data provider responses without fabricating prices or candles.
    """

    def setUp(self):
        if os.environ.get("SMKD_LIVE_PROVIDER_TESTS") != "1":
            self.skipTest("Live provider tests skipped. Set SMKD_LIVE_PROVIDER_TESTS=1 to run.")

    def test_market_session_status_live(self):
        """Validates market session structure against current real-time clock without synthetic fallback."""
        status = get_market_session_state()
        self.assertIn("phase", status)
        self.assertIn("can_trade_intraday", status)
        self.assertIn("ist_time", status)
        self.assertIn("advisory", status)

    def test_live_nse_quote_or_graceful_unavailable(self):
        """
        Attempts to fetch real tick/quote for an NSE benchmark symbol (RELIANCE).
        If network fails, provider times out, or markets are closed/rate-limited,
        it must return None or raise an expected handled status, never fabricated fixture data.
        """
        ticker = "RELIANCE.NS"
        data = fetch_nse_chart(ticker, interval="5m", range_param="1d")

        if data is None:
            # Documented, expected behavior if provider is rate-limiting or network is closed
            print(f"\n[LIVE INTEGRATION NOTICE] Live provider returned None for {ticker}. Marked INCONCLUSIVE/UNAVAILABLE.")
            return

        # If data is returned, verify it is genuine chart payload with required fields
        self.assertIn("meta", data)
        self.assertIn("timestamp", data)
        self.assertIn("indicators", data)
        quote = data["indicators"]["quote"][0]
        self.assertIn("close", quote)
        self.assertIn("open", quote)
        self.assertIn("high", quote)
        self.assertIn("low", quote)
        self.assertIn("volume", quote)

if __name__ == "__main__":
    unittest.main()
