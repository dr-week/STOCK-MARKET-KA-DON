import json
import math
import sqlite3
from typing import Any, Dict, Optional

from app.feedback import feedback_repository
from app.feedback.feedback_validation import normalize_outcome, validate_exit


def insert_signal_record(
    conn: sqlite3.Connection,
    now_iso: str,
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

    cur = conn.execute(
        """
        INSERT INTO signal_outcomes
            (symbol, signal_type, confluence_score, entry,
             target, stop_loss, ai_score, signal_at, features_json,
             provider_id, source_timestamp, rule_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (symbol.upper(), signal_type, confluence_score, entry,
         target, stop_loss, ai_score, now_iso, features_json,
         provider_id, source_timestamp, rule_version),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM signal_outcomes WHERE id=?", (cur.lastrowid,)).fetchone()
    return feedback_repository.row_to_dict(row)


def update_signal_outcome(
    conn: sqlite3.Connection,
    now_iso: str,
    signal_id: int,
    actual_exit: float,
    outcome: str,
) -> Dict[str, Any]:
    norm_outcome = normalize_outcome(outcome)
    validate_exit(actual_exit)

    sig = conn.execute("SELECT * FROM signal_outcomes WHERE id=?", (signal_id,)).fetchone()
    if sig is None:
        raise ValueError(f"Signal {signal_id} not found.")

    conn.execute(
        """
        UPDATE signal_outcomes
        SET actual_exit=?, outcome=?, outcome_at=?
        WHERE id=?
        """,
        (actual_exit, norm_outcome, now_iso, signal_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM signal_outcomes WHERE id=?", (signal_id,)).fetchone()
    return feedback_repository.row_to_dict(updated)


def delete_pending_signal(conn: sqlite3.Connection, signal_id: int) -> bool:
    result = conn.execute(
        "DELETE FROM signal_outcomes WHERE id=? AND outcome IS NULL",
        (signal_id,),
    )
    conn.commit()
    return result.rowcount == 1
