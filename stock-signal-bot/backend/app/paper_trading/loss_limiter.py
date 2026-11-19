import logging
from datetime import datetime
from typing import Any, Dict, List

from app.feedback.learning_service import feedback_learning
from app.market.sessions import IST

logger = logging.getLogger(__name__)


def calculate_today_realized_loss(closed_positions: List[Dict[str, Any]]) -> float:
    market_date = datetime.now(IST).date()
    loss = 0.0
    for position in closed_positions:
        if position.get("source") != "AUTO":
            continue
        closed_at = datetime.fromisoformat(position["closed_at"])
        if closed_at.astimezone(IST).date() == market_date:
            loss += max(0.0, -float(position["pnl"]))
    return loss


def record_paper_outcome(feedback: Any, position: Dict[str, Any]) -> None:
    signal_id = position.get("feedback_signal_id")
    if signal_id is None:
        return
    pnl = float(position["pnl"])
    outcome = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
    try:
        recorded = feedback.record_outcome(
            int(signal_id), float(position["exit_price"]), outcome
        )
        feedback_learning.schedule_after_outcome(
            recorded.get("provider_id"), feedback.database_path
        )
    except Exception:
        logger.exception(
            "Paper position %s closed but feedback outcome %s could not be recorded",
            position["id"],
            signal_id,
        )
