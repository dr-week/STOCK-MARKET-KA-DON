import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.db import database


class TestAnalysisTreePersistence(unittest.TestCase):
    def test_missing_ai_decision_does_not_block_scan_snapshot(self):
        stock = {
            "symbol": "RELIANCE",
            "name": "Reliance Industries",
            "sector": "Energy",
            "current_price": 100.0,
            "change_pct": 0.5,
            "intraday": {"signal": "WAIT"},
            "ai_decision": None,
            "news": [],
        }

        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "signals_tree.db")
            with patch.object(database, "DB_PATH", database_path):
                scan_id = database.record_analysis_tree("OPEN", "10:00", [stock])
                connection = sqlite3.connect(database_path)
                try:
                    row = connection.execute(
                        "SELECT ai_score, ai_verdict FROM signal_nodes WHERE scan_run_id = ?",
                        (scan_id,),
                    ).fetchone()
                finally:
                    connection.close()

        self.assertEqual(row, (0.5, "NEUTRAL"))


if __name__ == "__main__":
    unittest.main()
