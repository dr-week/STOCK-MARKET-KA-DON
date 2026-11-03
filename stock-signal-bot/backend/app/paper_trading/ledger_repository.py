import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from app.storage_paths import DATA_DIR

DB_PATH = str(DATA_DIR / "paper_trades.db")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def ensure_schema() -> None:
    with connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL,
                action TEXT NOT NULL, entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL, target REAL NOT NULL, qty REAL NOT NULL,
                confluence_score REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'OPEN',
                exit_price REAL, pnl REAL DEFAULT 0, unrealized_pnl REAL DEFAULT 0,
                opened_at TEXT NOT NULL, closed_at TEXT,
                source TEXT NOT NULL DEFAULT 'MANUAL', feedback_signal_id INTEGER
            )
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(paper_positions)")}
        if "source" not in columns:
            connection.execute("ALTER TABLE paper_positions ADD COLUMN source TEXT NOT NULL DEFAULT 'MANUAL'")
        if "feedback_signal_id" not in columns:
            connection.execute("ALTER TABLE paper_positions ADD COLUMN feedback_signal_id INTEGER")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS paper_automation_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1), enabled INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        connection.execute(
            "INSERT OR IGNORE INTO paper_automation_settings (id, enabled, updated_at) VALUES (1, 1, ?)",
            (now_iso(),),
        )
        connection.execute("UPDATE paper_automation_settings SET enabled=1 WHERE id=1")
        connection.commit()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)
