import math
import sqlite3
from typing import Any, Dict, Optional

from .order_validation import validate_order
from .pnl_calculator import realized_pnl
from .position_queries import get_by_id


def open_paper_order(
    conn: sqlite3.Connection,
    now_iso: str,
    symbol: str,
    action: str,
    entry: float,
    stop_loss: float,
    target: float,
    qty: float,
    confluence_score: float = 0.0,
    source: str = "MANUAL",
    feedback_signal_id: Optional[int] = None,
) -> Dict[str, Any]:
    symbol, action = validate_order(
        symbol, action, entry, stop_loss, target, qty, confluence_score, source
    )
    cur = conn.execute(
        """
        INSERT INTO paper_positions
            (symbol, action, entry_price, stop_loss, target, qty,
             confluence_score, status, opened_at, source, feedback_signal_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
        """,
        (symbol.upper(), action, entry, stop_loss, target, qty,
         confluence_score, now_iso, source, feedback_signal_id),
    )
    conn.commit()
    position_id = cur.lastrowid
    return get_by_id(conn, position_id)


def close_paper_position(
    conn: sqlite3.Connection,
    now_iso: str,
    position_id: int,
    exit_price: float,
) -> Dict[str, Any]:
    if not math.isfinite(exit_price) or exit_price <= 0:
        raise ValueError("exit price must be finite and greater than zero")

    conn.execute("BEGIN IMMEDIATE")
    pos = conn.execute(
        "SELECT * FROM paper_positions WHERE id=?", (position_id,)
    ).fetchone()
    if pos is None:
        raise ValueError(f"Position {position_id} not found.")
    if pos["status"] != "OPEN":
        raise ValueError(f"Position {position_id} is already closed.")

    pnl = realized_pnl(pos["action"], pos["entry_price"], exit_price, pos["qty"])
    result = conn.execute(
        """
        UPDATE paper_positions
        SET status='CLOSED', exit_price=?, pnl=?,
            unrealized_pnl=0, closed_at=?
        WHERE id=? AND status='OPEN'
        """,
        (exit_price, pnl, now_iso, position_id),
    )
    if result.rowcount != 1:
        raise ValueError(f"Position {position_id} is already closed.")
    conn.commit()
    return get_by_id(conn, position_id)
