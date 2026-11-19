import logging
import time
from typing import Any, Dict, Iterable, Optional, Tuple

from app.core.config import ACCOUNT_CAPITAL, MAX_DAILY_LOSS_PCT, RISK_PER_TRADE_PCT
from app.feedback.recorder import SignalFeedbackRecorder, feedback_recorder
from app.feedback.learning_service import feedback_learning
from app.market.sessions import get_market_session_state
from app.paper_trading.engine import PaperTradingEngine, paper_engine
from app.paper_trading.automation_rules import exit_trigger, fresh_market_result, positive_number
from app.paper_trading.candidate_evaluator import evaluate_and_open_candidate
from app.paper_trading.loss_limiter import calculate_today_realized_loss, record_paper_outcome

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
        return evaluate_and_open_candidate(self.engine, self.feedback, symbol, result)

    def record_outcome(self, position: Dict[str, Any]) -> None:
        record_paper_outcome(self.feedback, position)

    def _today_realized_loss(self) -> float:
        return calculate_today_realized_loss(self.engine.get_closed_positions(limit=1000))


paper_automation = PaperAutomationService()
