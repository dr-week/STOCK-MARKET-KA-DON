import unittest
import time
from app.indicators.calculations import compute_intraday_levels, calculate_trade_risk_and_sizing
from app.departments.market_data.collector import collector_service, DataQualityStatus
from app.departments.signal_risk.service import signal_risk_dep
from app.db.backup import backup_service

class TestTradingCorrectnessAndReliability(unittest.TestCase):
    
    def test_short_selling_levels_directionality(self):
        """
        P0 Test: For short positions:
        - Entry must be the confirmed sell trigger price.
        - Stop-loss MUST be strictly ABOVE entry.
        - Targets (T1, T2) MUST be strictly BELOW entry.
        - Enforces minimum 1:2 Risk-to-Reward ratio.
        """
        entry_price = 1190.00
        atr = 5.0
        entry, t1, t2, sl = compute_intraday_levels(entry_price, atr, signal_type="SELL CANDIDATE")
        
        self.assertEqual(entry, 1190.00)
        self.assertGreater(sl, entry, f"Short Stop Loss ({sl}) must be strictly ABOVE entry ({entry})")
        self.assertLess(t1, entry, f"Short Target 1 ({t1}) must be strictly BELOW entry ({entry})")
        self.assertLess(t2, t1, f"Short Target 2 ({t2}) must be strictly BELOW Target 1 ({t1})")

        risk_dist = sl - entry
        reward_dist = entry - t1
        rr_ratio = reward_dist / risk_dist
        self.assertGreaterEqual(rr_ratio, 2.0, f"Risk-Reward ({rr_ratio}) must be >= 1:2")

    def test_risk_sizing_and_inr_capital_cap(self):
        """
        P0 Test: Strict capital risk constraints:
        - 0.5% risk per trade on ₹18,000 = ₹90.00 max allowable loss.
        - Position size keeps gross stop loss plus estimated charges within the risk budget.
        """
        capital = 18000.0
        entry = 1190.0
        sl = 1194.0  # ₹4.0 risk per share
        t1 = 1182.0  # ₹8.0 reward per share (1:2 R:R)
        t2 = 1178.0

        sizing = calculate_trade_risk_and_sizing(entry, sl, t1, t2, capital)
        self.assertLess(sizing["shares_qty"], 22, "Estimated round-trip charges reduce risk-budget size")
        self.assertLessEqual(sizing["actual_risk_inr"], 90.0)
        self.assertLessEqual(sizing["estimated_loss_at_stop_inr"], sizing["allowable_risk_inr"])
        self.assertGreater(sizing["estimated_friction_inr"], 0.0)

    def test_market_data_gap_and_spike_detection(self):
        """
        Data Integrity Test:
        - Rejects corrupted OHLC (e.g. low > high).
        - Detects sequence gaps (> 5m interval silence).
        - Stamps every record with exchange and received timestamps.
        """
        # Corrupt candle
        corrupt = collector_service.inspect_and_normalize_candle(
            "TEST", "NSE", 1729774800, open_p=100.0, high_p=90.0, low_p=110.0, close_p=95.0, volume=1000
        )
        self.assertEqual(corrupt["data_quality_status"], DataQualityStatus.SUSPECT_SPIKE)

        # Normal candle
        now = time.time()
        c1 = collector_service.inspect_and_normalize_candle(
            "RELIANCE", "NSE", now, open_p=1190.0, high_p=1192.0, low_p=1188.0, close_p=1189.5, volume=50000
        )
        self.assertEqual(c1["data_quality_status"], DataQualityStatus.VALID)
        self.assertEqual(c1["data_source"], "GROWW_API")

        # Gap simulation: jump 15 minutes ahead
        c2 = collector_service.inspect_and_normalize_candle(
            "RELIANCE", "NSE", now + 900, open_p=1189.5, high_p=1191.0, low_p=1187.0, close_p=1188.0, volume=30000
        )
        self.assertEqual(c2["data_quality_status"], DataQualityStatus.GAP_DETECTED)

    def test_database_backup_integrity(self):
        """
        Reliability Test:
        - Automated snapshot backup runs atomically with gzip compression.
        - Verifies PRAGMA integrity_check.
        """
        res = backup_service.create_snapshot_backup()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["backup_filename"].endswith(".db.gz"))

if __name__ == "__main__":
    unittest.main()
