"""Signal Feedback Recorder — logs signal outcomes to SQLite for calibration.

No external dependencies; pure Python + sqlite3 only.
"""

from contextlib import contextmanager
import json
import math
from typing import Any, Dict, Iterator, List, Optional

import sqlite3
from app.feedback import feedback_repository
from app.feedback.feedback_validation import normalize_outcome, validate_exit
from app.feedback.feedback_metrics import accuracy, calibration


class SignalFeedbackRecorder:
    """Records emitted signals and their eventual WIN / LOSS / BREAKEVEN outcomes.

    Useful for tracking live signal accuracy and calibrating confluence
    thresholds over time without any ML dependencies.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialise the recorder and ensure the DB table exists."""
        self._db_path = db_path
        self._create_table()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection and always close it after use."""
        with feedback_repository.connect(self._db_path) as conn:
            yield conn

    def _create_table(self) -> None:
        """Create the signal_outcomes table if it does not already exist."""
        feedback_repository.ensure_schema(self._db_path)

    @staticmethod
    def _now_iso() -> str:
        """Return the current UTC time as an ISO-8601 string."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a sqlite3.Row to a plain dict."""
        return feedback_repository.row_to_dict(row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        """Persist a newly generated signal to the outcomes table.

        Args:
            symbol: Ticker symbol.
            signal_type: e.g. 'BUY_BREAKOUT', 'SELL_REVERSAL'.
            confluence_score: Aggregated confidence (0–100).
            entry: Suggested entry price.
            target: Profit-target price.
            stop_loss: Stop-loss price.
            ai_score: AI model score attached to the signal (0–1).

        Returns:
            Dict of the newly inserted signal row.
        """
        signal_at = self._now_iso()
        features_json = None
        if feature_snapshot is not None:
            if any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in feature_snapshot.values()
            ):
                raise ValueError("Feature snapshot values must be finite numbers.")
            features_json = json.dumps(feature_snapshot, sort_keys=True, allow_nan=False)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO signal_outcomes
                    (symbol, signal_type, confluence_score, entry,
                     target, stop_loss, ai_score, signal_at, features_json,
                     provider_id, source_timestamp, rule_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (symbol.upper(), signal_type, confluence_score, entry,
                 target, stop_loss, ai_score, signal_at, features_json,
                 provider_id, source_timestamp, rule_version),
            )
            conn.commit()
            signal_id = cur.lastrowid

        return self._get_signal_by_id(signal_id)

    @property
    def database_path(self) -> str:
        return self._db_path or feedback_repository.DB_PATH

    def record_outcome(
        self,
        signal_id: int,
        actual_exit: float,
        outcome: str,
    ) -> Dict[str, Any]:
        """Attach the real-world result to a previously recorded signal.

        Args:
            signal_id: Primary-key id of the signal row.
            actual_exit: Price at which the trade actually closed.
            outcome: One of 'WIN', 'LOSS', 'BREAKEVEN'.

        Returns:
            Updated signal dict.

        Raises:
            ValueError: If signal not found or outcome value is invalid.
        """
        outcome = normalize_outcome(outcome)
        validate_exit(actual_exit)

        sig = self._get_signal_by_id(signal_id)
        if sig is None:
            raise ValueError(f"Signal {signal_id} not found.")

        outcome_at = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE signal_outcomes
                SET actual_exit=?, outcome=?, outcome_at=?
                WHERE id=?
                """,
                (actual_exit, outcome, outcome_at, signal_id),
            )
            conn.commit()

        return self._get_signal_by_id(signal_id)

    def discard_pending_signal(self, signal_id: int) -> bool:
        """Remove an unfilled signal record when automated paper entry fails."""
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM signal_outcomes WHERE id=? AND outcome IS NULL",
                (signal_id,),
            )
            conn.commit()
        return result.rowcount == 1

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Compute overall signal accuracy statistics.

        Returns:
            Dict with keys: total_signals, wins, losses, win_rate_pct,
            avg_confluence_on_wins, avg_confluence_on_losses.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT outcome, confluence_score
                FROM signal_outcomes
                WHERE outcome IS NOT NULL
                """
            ).fetchall()
            total_signals = conn.execute(
                "SELECT COUNT(*) FROM signal_outcomes"
            ).fetchone()[0]

        return accuracy([self._row_to_dict(row) for row in rows], total_signals)

    def get_signal_calibration(self) -> Dict[str, Any]:
        """Return win-rate breakdown grouped by signal_type.

        Returns:
            Dict mapping signal_type → {wins, losses, win_rate_pct}.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT signal_type, outcome
                FROM signal_outcomes
                WHERE outcome IS NOT NULL
                """
            ).fetchall()

        return calibration([self._row_to_dict(row) for row in rows])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_signal_by_id(self, signal_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single signal row by primary key."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM signal_outcomes WHERE id=?", (signal_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None


# Module-level singleton — import and use directly.
feedback_recorder = SignalFeedbackRecorder()
