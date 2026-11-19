"""Paper Trading Engine — simulates trade execution against a SQLite store.

No external dependencies; pure Python + sqlite3 only.
"""

import math
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from . import ledger_repository
from .order_execution import close_paper_position, open_paper_order
from .order_validation import validate_order
from .pnl_calculator import realized_pnl, unrealized_pnl
from .position_queries import get_by_id, get_closed, get_open
from .pnl_summary import summarize
from .unrealized_updates import update_for_symbol


class PaperTradingEngine:
    """Simulated order book backed by SQLite."""

    def __init__(self) -> None:
        self._create_table()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with ledger_repository.connect() as conn:
            yield conn

    def _create_table(self) -> None:
        ledger_repository.ensure_schema()

    @staticmethod
    def _now_iso() -> str:
        return ledger_repository.now_iso()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return ledger_repository.row_to_dict(row)

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
        with self._connect() as conn:
            return open_paper_order(
                conn=conn,
                now_iso=self._now_iso(),
                symbol=symbol,
                action=action,
                entry=entry,
                stop_loss=stop_loss,
                target=target,
                qty=qty,
                confluence_score=confluence_score,
                source=source,
                feedback_signal_id=feedback_signal_id,
            )

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
        with self._connect() as conn:
            return close_paper_position(
                conn=conn,
                now_iso=self._now_iso(),
                position_id=position_id,
                exit_price=exit_price,
            )

    def get_open_positions(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            return get_open(conn)

    def get_closed_positions(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            return get_closed(conn, limit)

    def get_pnl_summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            closed = conn.execute(
                "SELECT pnl, entry_price, qty, source FROM paper_positions WHERE status='CLOSED'"
            ).fetchall()
            open_rows = conn.execute(
                "SELECT unrealized_pnl, entry_price, qty, source FROM paper_positions WHERE status='OPEN'"
            ).fetchall()
        return summarize((dict(row) for row in closed), (dict(row) for row in open_rows))

    def update_unrealized(self, symbol: str, current_price: float) -> int:
        if not math.isfinite(current_price) or current_price <= 0:
            raise ValueError("current price must be finite and greater than zero")
        symbol = symbol.strip().upper()
        with self._connect() as conn:
            return update_for_symbol(conn, symbol, current_price)

    def _get_position_by_id(self, position_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            return get_by_id(conn, position_id)


paper_engine = PaperTradingEngine()
