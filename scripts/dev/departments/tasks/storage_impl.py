import os
import sqlite3
import json
from typing import Dict, Any, List, Optional

RUNTIME_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".runtime"))
DB_PATH = os.path.join(RUNTIME_DIR, "dev-control.sqlite")

def get_connection() -> sqlite3.Connection:
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT DEFAULT 'MEDIUM',
            scope_json TEXT DEFAULT '[]',
            acceptance_json TEXT DEFAULT '[]',
            next_action TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS task_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details_json TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        );

        CREATE TABLE IF NOT EXISTS command_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            command TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            duration_ms INTEGER,
            output_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            fingerprint TEXT NOT NULL,
            category TEXT NOT NULL,
            attempt_count INTEGER DEFAULT 1,
            status TEXT DEFAULT 'OPEN',
            diagnostic_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS doc_jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            target_path TEXT NOT NULL,
            status TEXT NOT NULL,
            validation_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        );
        """)
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Initialized database at: {DB_PATH}")
