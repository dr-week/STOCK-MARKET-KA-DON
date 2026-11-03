"""Compatibility exports for task storage."""

from scripts.dev.departments.tasks.storage import DB_PATH, RUNTIME_DIR, get_connection, init_db

__all__ = ["DB_PATH", "RUNTIME_DIR", "get_connection", "init_db"]
