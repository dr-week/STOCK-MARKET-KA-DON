"""Signal Feedback Recorder — logs signal outcomes to SQLite for calibration.

No external dependencies; pure Python + sqlite3 only.
"""

from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional
import sqlite3

from app.feedback import feedback_repository
from app.feedback.feedback_metrics import accuracy, calibration
from app.feedback.feedback_signal_actions import (
    delete_pending_signal,
    insert_signal_record,
    update_signal_outcome,
)


class SignalFeedbackRecorder:
    """Records emitted signals and their eventual WIN / LOSS / BREAKEVEN outcomes."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path
        self._create_table()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with feedback_repository.connect(self._db_path) as conn:
            yield conn

    def _create_table(self) -> None:
        feedback_repository.ensure_schema(self._db_path)

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return feedback_repository.row_to_dict(row)

    def record_signal(
        self,
        symbol: str,
        signal_type: str,
        confluence_score: float,
        entry: float,
        target: float,
        stop_loss: float,
        ai_score: float = 0.0,
        feature_snapshot: Optional[Dict[str, float]] = None,
        provider_id: Optional[str] = None,
        source_timestamp: Optional[float] = None,
        rule_version: str = "systemone_rules_v1",
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            return insert_signal_record(
                conn=conn,
                now_iso=self._now_iso(),
                symbol=symbol,
                signal_type=signal_type,
                confluence_score=confluence_score,
                entry=entry,
                target=target,
                stop_loss=stop_loss,
                ai_score=ai_score,
                feature_snapshot=feature_snapshot,
                provider_id=provider_id,
                source_timestamp=source_timestamp,
                rule_version=rule_version,
            )

    @property
    def database_path(self) -> str:
        return self._db_path or feedback_repository.DB_PATH

    def record_outcome(
        self,
        signal_id: int,
        actual_exit: float,
        outcome: str,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            return update_signal_outcome(
                conn=conn,
                now_iso=self._now_iso(),
                signal_id=signal_id,
                actual_exit=actual_exit,
                outcome=outcome,
            )

    def discard_pending_signal(self, signal_id: int) -> bool:
        with self._connect() as conn:
            return delete_pending_signal(conn, signal_id)

    def get_accuracy_stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT outcome, confluence_score FROM signal_outcomes WHERE outcome IS NOT NULL"
            ).fetchall()
            total_signals = conn.execute(
                "SELECT COUNT(*) FROM signal_outcomes"
            ).fetchone()[0]

        return accuracy([self._row_to_dict(row) for row in rows], total_signals)

    def get_signal_calibration(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT signal_type, outcome FROM signal_outcomes WHERE outcome IS NOT NULL"
            ).fetchall()

        return calibration([self._row_to_dict(row) for row in rows])

    def _get_signal_by_id(self, signal_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM signal_outcomes WHERE id=?", (signal_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None


feedback_recorder = SignalFeedbackRecorder()
