import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.research.forecast_benchmark import evaluate_forecaster
from app.research.market_history import load_close_series


class TestForecastBenchmark(unittest.TestCase):
    def test_holdout_forecasts_beat_naive_baseline_on_linear_series(self):
        closes = [100.0 + index for index in range(500)]
        observed_contexts = []

        def forecast(contexts, horizon):
            observed_contexts.extend(contexts)
            return [context[-1] + horizon for context in contexts]

        result = evaluate_forecaster(closes, forecast, context_length=20, horizon=3, max_windows=10)

        self.assertEqual(result["status"], "beats_naive_mae")
        self.assertEqual(result["windows"], 10)
        self.assertEqual(result["naive_mae"], 3.0)
        self.assertEqual(result["model_mae"], 0.0)
        self.assertTrue(all(len(context) == 20 for context in observed_contexts))
        self.assertTrue(all(context[-1] < closes[-1] for context in observed_contexts))

    def test_insufficient_holdout_history_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "insufficient history"):
            evaluate_forecaster([100.0 + index for index in range(23)], lambda _x, _h: [], 20, 3, 5)

    def test_forecast_shape_and_values_are_validated(self):
        closes = [100.0 + index for index in range(100)]
        with self.assertRaisesRegex(ValueError, "one terminal price"):
            evaluate_forecaster(closes, lambda _x, _h: [], 10, 1, 5)
        with self.assertRaisesRegex(ValueError, "non-finite"):
            evaluate_forecaster(closes, lambda contexts, _h: [float("nan")] * len(contexts), 10, 1, 5)

    def test_history_loader_keeps_provider_series_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market_history.db"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute("""CREATE TABLE market_candles (
                    symbol TEXT, interval TEXT, timestamp INTEGER, close REAL, provider TEXT
                )""")
                connection.executemany(
                    "INSERT INTO market_candles VALUES (?, ?, ?, ?, ?)",
                    [
                        ("RELIANCE", "5m", 100, 10.0, "source_a"),
                        ("RELIANCE", "5m", 200, 11.0, "source_a"),
                        ("RELIANCE", "5m", 100, 100.0, "source_b"),
                    ],
                )
                connection.commit()
            timestamps, closes = load_close_series("reliance", "5m", "source_a", path)
        self.assertEqual(timestamps, [100, 200])
        self.assertEqual(closes, [10.0, 11.0])


if __name__ == "__main__":
    unittest.main()
