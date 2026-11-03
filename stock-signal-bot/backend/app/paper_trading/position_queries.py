import sqlite3
from typing import Any, Dict, List, Optional

from . import ledger_repository


def get_by_id(connection: sqlite3.Connection, position_id: int) -> Optional[Dict[str, Any]]:
    row = connection.execute("SELECT * FROM paper_positions WHERE id=?", (position_id,)).fetchone()
    return ledger_repository.row_to_dict(row) if row else None


def get_open(connection: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM paper_positions WHERE status='OPEN' ORDER BY id DESC"
    ).fetchall()
    return [ledger_repository.row_to_dict(row) for row in rows]


def get_closed(connection: sqlite3.Connection, limit: int) -> List[Dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM paper_positions WHERE status='CLOSED' ORDER BY closed_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [ledger_repository.row_to_dict(row) for row in rows]
