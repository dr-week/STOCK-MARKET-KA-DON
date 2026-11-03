"""Paper Trading Engine — simulates trade execution against a SQLite store.

No external dependencies; pure Python + sqlite3 only.
"""

import math
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from . import ledger_repository
from .order_validation import validate_order
from .pnl_calculator import realized_pnl, unrealized_pnl
from .position_queries import get_by_id, get_closed, get_open
from .pnl_summary import summarize
from .unrealized_updates import update_for_symbol


class PaperTradingEngine:
    """Simulated order book backed by SQLite.

    Manages paper positions (BUY / SELL), tracks unrealised and
    realised P&L, and exposes simple query helpers for the API layer.
    """

    def __init__(self) -> None:
        """Initialise the engine and ensure the DB table exists."""
        self._create_table()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection and always close it after use."""
        with ledger_repository.connect() as conn:
            yield conn

    def _create_table(self) -> None:
        """Create the paper_positions table if it does not already exist."""
        ledger_repository.ensure_schema()

    @staticmethod
    def _now_iso() -> str:
        """Return the current UTC time as an ISO-8601 string."""
        return ledger_repository.now_iso()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a sqlite3.Row to a plain dict."""
        return ledger_repository.row_to_dict(row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place_order(
        self,
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
        """Open a new paper position and return the stored position dict.

        Args:
            symbol: Ticker symbol (e.g. 'RELIANCE').
            action: 'BUY' or 'SELL'.
            entry: Entry price.
            stop_loss: Stop-loss price level.
            target: Profit-target price level.
            qty: Number of units / lots.
            confluence_score: Experimental confluence score (0–10).

        Returns:
            Dict representing the newly created position row.
        """
        symbol, action = validate_order(
            symbol, action, entry, stop_loss, target, qty, confluence_score, source
        )

        opened_at = self._now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO paper_positions
                    (symbol, action, entry_price, stop_loss, target, qty,
                     confluence_score, status, opened_at, source, feedback_signal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
                """,
                (symbol.upper(), action, entry, stop_loss, target, qty,
                 confluence_score, opened_at, source, feedback_signal_id),
            )
            conn.commit()
            position_id = cur.lastrowid

        return self._get_position_by_id(position_id)

    def set_automation_enabled(self, enabled: bool) -> Dict[str, Any]:
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean")
        if not enabled:
            raise ValueError("Automatic paper trading is always on while the backend is running.")
        with self._connect() as conn:
            conn.execute(
                "UPDATE paper_automation_settings SET enabled=1, updated_at=? WHERE id=1",
                (self._now_iso(),),
            )
            conn.commit()
        return self.get_automation_settings()

    def get_automation_settings(self) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT enabled, updated_at FROM paper_automation_settings WHERE id=1"
            ).fetchone()
        return {"enabled": bool(row["enabled"]), "updated_at": row["updated_at"]}

    def close_position(self, position_id: int, exit_price: float) -> Dict[str, Any]:
        """Close an open position and compute realised P&L.

        Args:
            position_id: Primary-key id of the position to close.
            exit_price: The price at which the trade is exited.

        Returns:
            Updated position dict with pnl, status=CLOSED and closed_at set.

        Raises:
            ValueError: If position not found or already closed.
        """
        if not math.isfinite(exit_price) or exit_price <= 0:
            raise ValueError("exit price must be finite and greater than zero")
        closed_at = self._now_iso()

        with self._connect() as conn:
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
                (exit_price, pnl, closed_at, position_id),
            )
            if result.rowcount != 1:
                raise ValueError(f"Position {position_id} is already closed.")
            conn.commit()

        return self._get_position_by_id(position_id)

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Return all currently open positions."""
        with self._connect() as conn:
            return get_open(conn)

    def get_closed_positions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent closed trades.

        Args:
            limit: Maximum number of rows to return (default 20).
        """
        with self._connect() as conn:
            return get_closed(conn, limit)

    def get_pnl_summary(self) -> Dict[str, Any]:
        """Compute aggregate P&L statistics across all trades.

        Returns:
            Dict with keys: total_realized, total_unrealized, win_rate,
            trade_count, best_trade, worst_trade.
        """
        with self._connect() as conn:
            closed = conn.execute(
                "SELECT pnl, entry_price, qty, source FROM paper_positions WHERE status='CLOSED'"
            ).fetchall()
            open_rows = conn.execute(
                "SELECT unrealized_pnl, entry_price, qty, source FROM paper_positions WHERE status='OPEN'"
            ).fetchall()

        return summarize((dict(row) for row in closed), (dict(row) for row in open_rows))

    def update_unrealized(self, symbol: str, current_price: float) -> int:
        """Recalculate and store unrealised P&L for all open positions of a symbol.

        Args:
            symbol: Ticker symbol to update.
            current_price: Latest market price.

        Returns:
            Number of positions updated.
        """
        if not math.isfinite(current_price) or current_price <= 0:
            raise ValueError("current price must be finite and greater than zero")
        symbol = symbol.strip().upper()
        with self._connect() as conn:
            return update_for_symbol(conn, symbol, current_price)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_position_by_id(self, position_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single position row by primary key."""
        with self._connect() as conn:
            return get_by_id(conn, position_id)


# Module-level singleton — import and use directly.
paper_engine = PaperTradingEngine()
