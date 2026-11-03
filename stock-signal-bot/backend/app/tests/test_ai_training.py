import math
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.ai.training.data import load_candles
from app.ai.training.features import FEATURE_NAMES, build_samples
from app.ai.training.trainer import train_time_split


_IST = ZoneInfo("Asia/Kolkata")


def _session_candles(days=4, bars_per_day=40):
    candles = []
    start = datetime(2026, 1, 5, 9, 15, tzinfo=_IST)
    for day in range(days):
        for index in range(bars_per_day):
            close = 100 + day * 0.2 + index * 0.05 + 2 * math.sin(index * 0.35)
            candles.append({
                "symbol": "TEST",
                "timestamp": int((start + timedelta(days=day, minutes=5 * index)).timestamp()),
                "open": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 100 + index,
            })
    return candles


class TestAiTraining(unittest.TestCase):
    def test_features_use_past_bars_and_labels_end_within_session(self):
        samples = build_samples(_session_candles(), horizon_bars=3, cost_bps=1)

        self.assertTrue(samples)
        self.assertEqual(len(samples[0]["features"]), len(FEATURE_NAMES))
        self.assertEqual(samples[0]["session_date"], samples[0]["label_end_date"])
        self.assertTrue(all(math.isfinite(value) for value in samples[0]["features"]))

    def test_time_split_keeps_latest_sessions_out_of_training(self):
        samples = []
        for day in range(10):
            day_id = f"2026-02-{day + 1:02d}"
            for index in range(20):
                label = 1 if index % 2 else -1
                samples.append({
                    "session_date": day_id,
                    "label_end_date": day_id,
                    "features": [label * (index + 1), index / 20, 0, 0, 1],
                    "label": label,
                    "forward_return": label * 0.002,
                })

        _, metrics = train_time_split(samples, cost_bps=10)

        self.assertEqual(metrics["train_sessions"], 8)
        self.assertEqual(metrics["test_sessions"], 2)
        self.assertEqual(metrics["non_neutral_predictions"], metrics["test_samples"])
        self.assertIn("majority_baseline_balanced_accuracy", metrics)

    def test_provider_selection_keeps_different_sources_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite"
            connection = sqlite3.connect(path)
            connection.execute("""
                CREATE TABLE market_candles (
                    symbol TEXT, interval TEXT, timestamp INTEGER, open REAL, high REAL,
                    low REAL, close REAL, volume REAL, provider TEXT
                )
            """)
            values = ("TEST", "5m", 100, 10, 11, 9, 10.5, 100, "yahoo_finance")
            connection.execute("INSERT INTO market_candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            connection.execute(
                "INSERT INTO market_candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (*values[:-1], "yahoo_finance_public_unofficial"),
            )
            connection.commit()
            connection.close()

            candles = load_candles(str(path), "5m", "yahoo_finance_public_unofficial")
            self.assertEqual(len(candles), 1)
            self.assertEqual(candles[0]["close"], 10.5)

            connection = sqlite3.connect(path)
            connection.execute(
                "UPDATE market_candles SET close=10.6 WHERE provider='yahoo_finance_public_unofficial'"
            )
            connection.commit()
            connection.close()

            newer = load_candles(str(path), "5m", "yahoo_finance_public_unofficial")
            older = load_candles(str(path), "5m", "yahoo_finance")
            self.assertEqual(newer[0]["close"], 10.6)
            self.assertEqual(older[0]["close"], 10.5)


if __name__ == "__main__":
    unittest.main()
