import logging
import math
import time
from typing import Any, Dict, Iterable, Optional, Tuple

from app.core.config import (
    ACCOUNT_CAPITAL,
    MAX_DAILY_LOSS_PCT,
    MIN_CONFLUENCE_SCORE,
    MIN_RISK_REWARD_RATIO,
    RISK_PER_TRADE_PCT,
)
from app.feedback.recorder import SignalFeedbackRecorder, feedback_recorder
from app.feedback.feedback_features import snapshot
from app.feedback.learning_service import feedback_learning
from app.market.sessions import IST, get_market_session_state
from app.paper_trading.engine import PaperTradingEngine, paper_engine
from app.paper_trading.automation_rules import exit_trigger, fresh_market_result, positive_number

logger = logging.getLogger(__name__)

MAX_OPEN_AUTO_POSITIONS = 3
MAX_MARKET_DATA_AGE_SECONDS = 15 * 60
MAX_CLOCK_SKEW_SECONDS = 60


class PaperAutomationService:
    def __init__(
        self,
        engine: PaperTradingEngine = paper_engine,
        feedback: SignalFeedbackRecorder = feedback_recorder,
    ) -> None:
        self.engine = engine
        self.feedback = feedback

    def set_enabled(self, enabled: bool) -> Dict[str, Any]:
        return self.engine.set_automation_enabled(enabled)

    def settings(self) -> Dict[str, Any]:
        settings = self.engine.get_automation_settings()
        return {
            **settings,
            "enabled": True,
            "mode": "always_on_paper",
            "broker_orders_placed": False,
            "real_money_used": False,
            "virtual_capital_inr": ACCOUNT_CAPITAL,
            "risk_per_trade_pct": RISK_PER_TRADE_PCT * 100,
            "max_daily_loss_pct": MAX_DAILY_LOSS_PCT * 100,
            "max_open_positions": MAX_OPEN_AUTO_POSITIONS,
        }

    @staticmethod
    def _scan_summary(opened: int, closed: int, skipped: int) -> Dict[str, Any]:
        return {
            "enabled": True,
            "mode": "always_on_paper",
            "broker_orders_placed": False,
            "real_money_used": False,
            "opened": opened,
            "closed": closed,
            "skipped": skipped,
        }

    def process_scan_results(self, results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        now = time.time()
        valid_results = {
            str(result.get("symbol", "")).upper(): result
            for result in results
            if fresh_market_result(result, now)
        }
        open_positions = [
            position for position in self.engine.get_open_positions()
            if position.get("source") == "AUTO"
        ]
        closed_symbols = set()
        opened = 0
        closed = 0
        skipped = 0

        for position in open_positions:
            result = valid_results.get(position["symbol"])
            if result is None:
                skipped += 1
                continue
            price = positive_number(result.get("current_price"))
            if price is None:
                skipped += 1
                continue
            self.engine.update_unrealized(position["symbol"], price)
            exit_price, reason = exit_trigger(position, price)
            if exit_price is None:
                continue
            try:
                closed_position = self.engine.close_position(position["id"], exit_price)
                self.record_outcome(closed_position)
                closed += 1
                closed_symbols.add(position["symbol"])
            except Exception:
                logger.exception("Automatic paper exit failed for position %s", position["id"])
                skipped += 1
            else:
                logger.info(
                    "Automatic paper position closed: id=%s symbol=%s reason=%s",
                    position["id"],
                    position["symbol"],
                    reason,
                )

        open_positions = [
            position for position in self.engine.get_open_positions()
            if position.get("source") == "AUTO"
        ]
        active_symbols = {
            position["symbol"] for position in self.engine.get_open_positions()
        }
        if not get_market_session_state()["can_trade_intraday"]:
            return self._scan_summary(opened, closed, skipped)

        daily_loss_limit = ACCOUNT_CAPITAL * MAX_DAILY_LOSS_PCT
        if self._today_realized_loss() >= daily_loss_limit:
            return self._scan_summary(opened, closed, skipped)

        for symbol, result in valid_results.items():
            if len(open_positions) >= MAX_OPEN_AUTO_POSITIONS:
                break
            if symbol in active_symbols or symbol in closed_symbols:
                continue
            position, reason = self._open_candidate(symbol, result)
            if position is None:
                if reason:
                    skipped += 1
                continue
            open_positions.append(position)
            active_symbols.add(symbol)
            opened += 1

        return self._scan_summary(opened, closed, skipped)

    def _open_candidate(
        self,
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
        signal_record = self.feedback.record_signal(
            symbol=symbol,
            signal_type=signal,
            confluence_score=score,
            entry=entry,
            target=target,
            stop_loss=stop,
            ai_score=ai_score or 0.0,
            feature_snapshot=snapshot(result, action),
            provider_id=(
                result.get("market_data", {}).get("data_quality", {}).get("provider")
                if isinstance(result.get("market_data"), dict)
                and isinstance(result.get("market_data", {}).get("data_quality"), dict)
                else None
            ),
            source_timestamp=(
                result.get("market_data", {}).get("data_quality", {}).get("source_timestamp")
                if isinstance(result.get("market_data"), dict)
                and isinstance(result.get("market_data", {}).get("data_quality"), dict)
                else None
            ),
            rule_version="signal_risk_v1_systemone_supplemental",
        )
        try:
            position = self.engine.place_order(
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
            self.feedback.discard_pending_signal(signal_record["id"])
            logger.exception("Automatic paper entry failed for %s", symbol)
            return None, "paper entry could not be saved"
        return position, None

    def record_outcome(self, position: Dict[str, Any]) -> None:
        signal_id = position.get("feedback_signal_id")
        if signal_id is None:
            return
        pnl = float(position["pnl"])
        outcome = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
        try:
            recorded = self.feedback.record_outcome(
                int(signal_id), float(position["exit_price"]), outcome
            )
            feedback_learning.schedule_after_outcome(
                recorded.get("provider_id"), self.feedback.database_path
            )
        except Exception:
            logger.exception(
                "Paper position %s closed but feedback outcome %s could not be recorded",
                position["id"],
                signal_id,
            )

    def _today_realized_loss(self) -> float:
        from datetime import datetime

        market_date = datetime.now(IST).date()
        loss = 0.0
        for position in self.engine.get_closed_positions(limit=1000):
            if position.get("source") != "AUTO":
                continue
            closed_at = datetime.fromisoformat(position["closed_at"])
            if closed_at.astimezone(IST).date() == market_date:
                loss += max(0.0, -float(position["pnl"]))
        return loss

paper_automation = PaperAutomationService()
