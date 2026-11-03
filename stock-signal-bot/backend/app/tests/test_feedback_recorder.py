import tempfile
import unittest
from pathlib import Path

from app.feedback.recorder import SignalFeedbackRecorder


class TestFeedbackRecorder(unittest.TestCase):
    def test_records_outcomes_and_reports_accuracy_without_touching_app_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = SignalFeedbackRecorder(str(Path(temp_dir) / "feedback.sqlite"))
            signal = recorder.record_signal(
                symbol="reliance",
                signal_type="BUY CANDIDATE",
                confluence_score=8.5,
                entry=100.0,
                target=104.0,
                stop_loss=98.0,
                ai_score=0.73,
                feature_snapshot={"side": 1.0, "rsi": 55.0},
                provider_id="yahoo_finance",
                source_timestamp=1_800_000_000,
            )

            recorded = recorder.record_outcome(signal["id"], 104.0, "WIN")

            self.assertEqual(recorded["outcome"], "WIN")
            self.assertEqual(recorded["symbol"], "RELIANCE")
            self.assertIn('"rsi": 55.0', recorded["features_json"])
            self.assertEqual(recorded["provider_id"], "yahoo_finance")
            self.assertEqual(
                recorder.get_accuracy_stats(),
                {
                    "total_signals": 1,
                    "wins": 1,
                    "losses": 0,
                    "win_rate_pct": 100.0,
                    "avg_confluence_on_wins": 8.5,
                    "avg_confluence_on_losses": 0.0,
                },
            )
            self.assertEqual(
                recorder.get_signal_calibration()["BUY CANDIDATE"]["win_rate_pct"],
                100.0,
            )

    def test_rejects_invalid_outcome_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = SignalFeedbackRecorder(str(Path(temp_dir) / "feedback.sqlite"))
            signal = recorder.record_signal("RELIANCE", "BUY", 7.0, 100.0, 105.0, 98.0)

            with self.assertRaises(ValueError):
                recorder.record_outcome(signal["id"], 104.0, "UNKNOWN")

    def test_feature_snapshot_rejects_non_finite_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = SignalFeedbackRecorder(str(Path(temp_dir) / "feedback.sqlite"))
            with self.assertRaises(ValueError):
                recorder.record_signal(
                    "RELIANCE", "BUY", 7, 100, 105, 98,
                    feature_snapshot={"rsi": float("nan")},
                )


if __name__ == "__main__":
    unittest.main()
