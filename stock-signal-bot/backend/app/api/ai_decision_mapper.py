from typing import Any, Dict, Optional

from app.ai.system_one import decision_engine


def build_lightweight_decision(
    symbol: str,
    current_price: float,
    technicals: Dict[str, Any],
    fundamentals: Dict[str, Any],
    intelligence: Dict[str, Any],
    sector: str = "",
) -> Optional[Dict[str, Any]]:
    if (technicals.get("data_quality") or {}).get("status") == "insufficient":
        return None
    news_summary = fundamentals.get("news_summary", {})
    support_demand = technicals.get("supply_demand", {})
    raw_ai = decision_engine.evaluate(
        symbol=symbol, price=current_price,
        vwap=technicals.get("vwap", current_price), rsi=technicals.get("rsi", 50.0),
        ema_9=technicals.get("ema_9", current_price), ema_21=technicals.get("ema_21", current_price),
        atr=technicals.get("atr", 5.0),
        change_pct=float((current_price - technicals.get("vwap", current_price)) / max(technicals.get("vwap", current_price), 1.0) * 100),
        news_sentiment=(news_summary.get("overall_sentiment") or "NEUTRAL").upper(),
        market_phase=intelligence.get("session", {}).get("phase") or "MORNING_SESSION",
        adx=float(technicals.get("adx") or 0.0), relative_volume=float(technicals.get("rvol") or 1.0),
        support=support_demand.get("demand_zone", {}).get("bottom") or technicals.get("support"),
        resistance=support_demand.get("supply_zone", {}).get("top") or technicals.get("resistance"),
        trend_strength=float(technicals.get("market_structure", {}).get("trend_strength", 0.5) or 0.5),
        volume_confirmation=float(technicals.get("rvol") or 1.0) >= 1.25,
        structure_bias=(technicals.get("market_structure", {}).get("trend") or "NEUTRAL").upper(),
        market_regime=(intelligence.get("nifty_50", {}).get("trend") or "SIDEWAYS").upper(),
        avg_rr=2.5, m15_trend=technicals.get("m15_trend", "NEUTRAL"), h1_trend=technicals.get("h1_trend", "NEUTRAL"),
        sector=sector, sector_strengths=intelligence.get("sector_strengths", {}),
    )
    move_pct = round((raw_ai["ai_score"] - 0.5) * 8.0, 2)
    label = f"{move_pct:+.1f}% probable move"
    return {**raw_ai, "probable_move_pct": move_pct, "probable_move_label": label,
            "summary": f"{raw_ai['recommended_action']} • {label}"}
