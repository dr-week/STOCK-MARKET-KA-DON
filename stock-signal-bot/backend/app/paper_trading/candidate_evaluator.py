import logging
import math
from typing import Any, Dict, Optional, Tuple

from app.core.config import (
    ACCOUNT_CAPITAL,
    MIN_CONFLUENCE_SCORE,
    MIN_RISK_REWARD_RATIO,
    RISK_PER_TRADE_PCT,
)
from app.feedback.feedback_features import snapshot
from app.paper_trading.automation_rules import positive_number

logger = logging.getLogger(__name__)


def evaluate_and_open_candidate(
    engine: Any,
    feedback: Any,
    symbol: str,
    result: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    decision = result.get("signal_decision")
    if not isinstance(decision, dict):
        return None, None
    signal = str(decision.get("signal", "")).upper()
    if signal not in {"BUY CANDIDATE", "SELL CANDIDATE"}:
        return None, None
    action = "BUY" if signal.startswith("BUY") else "SELL"

    score = positive_number(decision.get("confluence_score"))
    if score is None or score < MIN_CONFLUENCE_SCORE:
        return None, None
    entry = positive_number(result.get("current_price"))
    stop = positive_number(decision.get("stop_loss"))
    target = positive_number(decision.get("target_1"))
    if entry is None or stop is None or target is None:
        return None, "invalid trade levels"
    if action == "BUY" and not stop < entry < target:
        return None, "buy levels are no longer valid at the current price"
    if action == "SELL" and not target < entry < stop:
        return None, "sell levels are no longer valid at the current price"

    risk_per_share = abs(entry - stop)
    reward_risk = abs(target - entry) / risk_per_share
    if reward_risk < MIN_RISK_REWARD_RATIO:
        return None, "risk/reward fell below the configured minimum"
    max_risk = ACCOUNT_CAPITAL * RISK_PER_TRADE_PCT
    quantity = math.floor(max_risk / risk_per_share)
    risk_sizing = decision.get("risk_sizing")
    if isinstance(risk_sizing, dict):
        suggested_quantity = positive_number(risk_sizing.get("shares_qty"))
        if suggested_quantity is not None:
            quantity = min(quantity, math.floor(suggested_quantity))
    if quantity < 1:
        return None, "risk budget is below one whole share"

    ai_decision = result.get("ai_decision")
    ai_score = positive_number(ai_decision.get("ai_score")) if isinstance(ai_decision, dict) else None
    market_data = result.get("market_data") if isinstance(result.get("market_data"), dict) else {}
    quality = market_data.get("data_quality") if isinstance(market_data.get("data_quality"), dict) else {}

    signal_record = feedback.record_signal(
        symbol=symbol,
        signal_type=signal,
        confluence_score=score,
        entry=entry,
        target=target,
        stop_loss=stop,
        ai_score=ai_score or 0.0,
        feature_snapshot=snapshot(result, action),
        provider_id=quality.get("provider"),
        source_timestamp=quality.get("source_timestamp"),
        rule_version="signal_risk_v1_systemone_supplemental",
    )
    try:
        position = engine.place_order(
            symbol=symbol,
            action=action,
            entry=entry,
            stop_loss=stop,
            target=target,
            qty=quantity,
            confluence_score=score,
            source="AUTO",
            feedback_signal_id=signal_record["id"],
        )
    except Exception:
        feedback.discard_pending_signal(signal_record["id"])
        logger.exception("Automatic paper entry failed for %s", symbol)
        return None, "paper entry could not be saved"
    return position, None
