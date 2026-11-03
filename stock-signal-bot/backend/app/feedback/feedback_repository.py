import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR.mkdir(exist_ok=True)
DB_PATH = str(_DATA_DIR / "paper_trades.db")


@contextmanager
def connect(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path or DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def ensure_schema(db_path: Optional[str] = None) -> None:
    with connect(db_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS signal_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL, confluence_score REAL NOT NULL DEFAULT 0,
                entry REAL NOT NULL, target REAL NOT NULL, stop_loss REAL NOT NULL,
                ai_score REAL NOT NULL DEFAULT 0, actual_exit REAL, outcome TEXT,
                signal_at TEXT NOT NULL, outcome_at TEXT,
                features_json TEXT, provider_id TEXT, source_timestamp REAL,
                rule_version TEXT NOT NULL DEFAULT 'systemone_rules_v1'
            )
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(signal_outcomes)")}
        migrations = {
            "features_json": "TEXT",
            "provider_id": "TEXT",
            "source_timestamp": "REAL",
            "rule_version": "TEXT NOT NULL DEFAULT 'systemone_rules_v1'",
        }
        for column, definition in migrations.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE signal_outcomes ADD COLUMN {column} {definition}")
        connection.commit()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)
