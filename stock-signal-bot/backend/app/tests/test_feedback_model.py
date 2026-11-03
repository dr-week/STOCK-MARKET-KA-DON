import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.feedback import feedback_repository
from app.feedback.feedback_features import FEATURE_NAMES
from app.feedback.feedback_model import readiness, train_candidate


class TestFeedbackModel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "feedback.sqlite")
        self.artifact_dir = Path(self.temp_dir.name) / "models"
        feedback_repository.ensure_schema(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_outcomes(self, count: int) -> None:
        start = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            for index in range(count):
                signal_at = start + timedelta(days=index // 3, minutes=(index % 3) * 5)
                outcome_at = signal_at + timedelta(minutes=30)
                outcome = "WIN" if index % 2 else "LOSS"
                features = {name: float((index % 10) + offset) for offset, name in enumerate(FEATURE_NAMES)}
                connection.execute(
                    """INSERT INTO signal_outcomes
                       (symbol, signal_type, confluence_score, entry, target, stop_loss,
                        signal_at, outcome_at, outcome, features_json, provider_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"SYM{index % 4}", "BUY CANDIDATE", 8, 100, 104, 98,
                        signal_at.isoformat(), outcome_at.isoformat(), outcome,
                        json.dumps(features), "yahoo_finance",
                    ),
                )

    def test_training_waits_for_minimum_realized_paper_outcomes(self):
        self.add_outcomes(20)

        report = train_candidate(self.db_path, "yahoo_finance", self.artifact_dir)

        self.assertEqual(report["status"], "NOT_READY")
        self.assertEqual(report["eligible_outcomes"], 20)
        self.assertFalse(report["ready"])
        self.assertFalse(self.artifact_dir.exists())

    def test_ready_provider_trains_candidate_but_never_promotes_it(self):
        self.add_outcomes(120)

        report = train_candidate(self.db_path, "yahoo_finance", self.artifact_dir)

        self.assertTrue(readiness(self.db_path, "yahoo_finance")["ready"])
        self.assertIn(report["status"], {"CANDIDATE_READY_FOR_REVIEW", "CANDIDATE_BELOW_BASELINE"})
        self.assertTrue(Path(report["artifact"]).is_file())
        self.assertEqual(report["promotion"], "manual only; candidate is never loaded by production signals")
        self.assertFalse(readiness(self.db_path, "groww_trade_api")["ready"])


if __name__ == "__main__":
    unittest.main()
