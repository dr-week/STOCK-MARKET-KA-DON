"""Historical evaluation using the production technical and signal decision services.

This is a research simulator, not an execution model or a guarantee of live results.
"""

import json
import urllib.error
from typing import Any, Dict

from app.core.config import MIN_CONFLUENCE_SCORE
from app.departments.fundamental_analysis.service import FUNDAMENTAL_DB
from app.backtesting.data_provider import load_bars
from app.backtesting.simulation import MIN_WARMUP_BARS
from app.backtesting.simulation_loop import simulate_threshold

DEFAULT_HOLDING_BARS = 15
MAX_HOLDING_BARS = 60
def run_historical_backtest(
    symbol: str,
    days: int = 5,
    holding_bars: int = DEFAULT_HOLDING_BARS,
    cost_bps_per_side: float = 5.0,
    optimize: bool = False,
) -> Dict[str, Any]:
    """Evaluate the live rule engine against historical five-minute OHLCV.

    ``optimize`` compares a fixed set of score thresholds for research only.
    It never persists or changes production settings.
    """
    symbol = symbol.upper()
    if not 1 <= days <= 30:
        return {"error": "days must be between 1 and 30"}
    if not 1 <= holding_bars <= MAX_HOLDING_BARS:
        return {"error": f"holding_bars must be between 1 and {MAX_HOLDING_BARS}"}
    if not 0 <= cost_bps_per_side <= 100:
        return {"error": "cost_bps_per_side must be between 0 and 100"}

    try:
        bars = load_bars(symbol, days)
    except (urllib.error.URLError, TimeoutError, ValueError, IndexError, KeyError, json.JSONDecodeError) as exc:
        return {"symbol": symbol, "error": f"Unable to load valid historical candles: {exc}"}

    if len(bars) < MIN_WARMUP_BARS + 2:
        return {"symbol": symbol, "error": "Insufficient valid historical candles for backtesting", "valid_bars": len(bars)}

    intelligence = {
        "session": {"phase": "HISTORICAL_BACKTEST", "can_trade_intraday": True},
        "nifty_50": {"trend": "SIDEWAYS"},
    }
    fundamental_data = FUNDAMENTAL_DB.get(symbol, {})
    quality_filter_passed = fundamental_data.get("debt_to_equity", 0.50) < 2.0
    baseline = simulate_threshold(
        bars,
        MIN_CONFLUENCE_SCORE,
        intelligence,
        holding_bars,
        cost_bps_per_side,
        quality_filter_passed,
    )
    result: Dict[str, Any] = {
        "symbol": symbol,
        "provider": "Yahoo Finance chart API",
        "timeframe": "5m",
        "sample_period_days": days,
        "valid_bars": len(bars),
        "strategy": "Production technical-analysis and signal-risk rules; Nifty contribution neutral in historical test",
        "threshold": MIN_CONFLUENCE_SCORE,
        "holding_bars_limit": holding_bars,
        "estimated_cost_bps_per_side": cost_bps_per_side,
        "warning": "Historical simulation only. Yahoo intraday history is limited; slippage, exact fees, fills, market impact, and live feed differences are not fully modeled. Not a forecast.",
        **baseline,
    }

    if optimize:
        candidates = [
            simulate_threshold(
                bars,
                threshold,
                intelligence,
                holding_bars,
                cost_bps_per_side,
                quality_filter_passed,
            )
            for threshold in (6, 7, 8, 9)
        ]
        result["threshold_comparison"] = [
            {key: value for key, value in candidate.items() if key != "trades"}
            for candidate in candidates
        ]
        result["optimization_notice"] = (
            "Threshold comparison is exploratory and may overfit this sample. No winning threshold is selected or written to production; "
            "review the metrics and validate any proposed change on separate out-of-sample data and paper trading."
        )

    result["recent_trades_sample"] = result.pop("trades")[-8:]
    return result
