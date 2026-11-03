from typing import Any, Dict, Optional

from app.core.config import ACCOUNT_CAPITAL
from app.departments.market_data.service import market_data_dep
from app.departments.technical_analysis.service import technical_dep
from app.departments.fundamental_analysis.service import fundamental_dep
from app.departments.signal_risk.service import signal_risk_dep
from app.indicators.profitability import evaluate_intraday_profitability
from app.api.ai_decision_mapper import build_lightweight_decision


def process_unified_stock(
    stock: Dict[str, str],
    intelligence: Dict[str, Any],
    capital: float = ACCOUNT_CAPITAL,
) -> Optional[Dict[str, Any]]:
    symbol = stock["symbol"]
    ticker = stock.get("ticker", f"{symbol}.NS")
    name, sector, groww_slug = stock["name"], stock["sector"], stock["groww"]
    market_data = market_data_dep.get_stock_data(symbol, ticker)
    if not market_data:
        return None
    technicals = technical_dep.analyze(market_data)
    fundamentals = fundamental_dep.analyze(symbol, name)
    decision = signal_risk_dep.synthesize_decision(
        market_data=market_data, technicals=technicals, fundamentals=fundamentals,
        intelligence=intelligence, capital=capital,
    )
    ai_decision = build_lightweight_decision(symbol, market_data["current_price"], technicals, fundamentals, intelligence, sector)
    risk_sizing = decision.get("risk_sizing")
    setup_signal = decision["signal"]
    decision["setup_signal"] = setup_signal
    if risk_sizing:
        risk_sizing = evaluate_intraday_profitability(
            risk_sizing, adx=technicals.get("adx"), atr_5m=technicals.get("atr"),
            is_candidate="CANDIDATE" in decision["signal"],
        )
        decision["risk_sizing"] = risk_sizing
        if "CANDIDATE" in decision["signal"] and not risk_sizing["profitability_eligible"]:
            decision["signal"] = "WAIT"
            decision["reasons"].append(risk_sizing["viability_status"])
    return {
        "symbol": symbol, "name": name, "sector": sector,
        "current_price": market_data["current_price"], "change_pct": market_data["change_pct"],
        "day_high": market_data["day_high"], "day_low": market_data["day_low"],
        "groww_url": f"https://groww.in/stocks/{groww_slug}",
        "market_data": {"volume_today": market_data["volume_today"], "timestamp": market_data.get("timestamp", 0),
                         "data_quality": market_data.get("data_quality", {}), "candles_5m": market_data.get("candles_5m", {}),
                         "candles_15m": market_data.get("candles_15m", {}), "candles_daily": market_data.get("candles_daily", {})},
        "technicals": {**technicals, "m15_trend": technicals.get("m15_trend", "NEUTRAL"), "h1_trend": technicals.get("h1_trend", "NEUTRAL")},
        "fundamentals": fundamentals, "signal_decision": decision, "ai_decision": ai_decision,
        "intraday": {
            "signal": decision["signal"], "confluence_score": decision["confluence_score"], "confidence": decision["confidence"],
            "setup_signal": decision.get("setup_signal", decision["signal"]),
            "entry": decision["entry"], "target_1": decision["target_1"], "target_2": decision["target_2"], "stop_loss": decision["stop_loss"],
            "vwap": technicals["vwap"], "rsi": technicals["rsi"], "ema_9": technicals["ema_9"], "ema_21": technicals["ema_21"],
            "atr": technicals["atr"], "adx": technicals["adx"], "rvol": technicals["rvol"], "sparkline": technicals["sparkline"],
            "market_structure": technicals["market_structure"], "supply_demand": technicals["supply_demand"], "key_candle": technicals["key_candle"],
            "m15_trend": technicals.get("m15_trend", "NEUTRAL"), "h1_trend": technicals.get("h1_trend", "NEUTRAL"),
            "risk_sizing": risk_sizing, "reasons": decision["reasons"], "ai_decision": ai_decision,
        },
        "news": fundamentals["news"],
    }
