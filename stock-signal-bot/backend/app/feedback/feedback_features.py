"""Point-in-time features attached to each automatically paper-traded signal."""

import math
from typing import Any, Optional

FEATURE_NAMES = (
    "side",
    "confluence_score",
    "ai_score",
    "rsi",
    "adx",
    "rvol",
    "vwap_distance_pct",
    "ema_spread_pct",
    "atr_pct",
)


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def snapshot(result: dict[str, Any], action: str) -> Optional[dict[str, float]]:
    technicals = result.get("technicals")
    decision = result.get("signal_decision")
    ai_decision = result.get("ai_decision")
    price = _number(result.get("current_price"))
    if not all(isinstance(item, dict) for item in (technicals, decision, ai_decision)):
        return None
    if price is None or price <= 0:
        return None
    vwap = _number(technicals.get("vwap"))
    ema_9 = _number(technicals.get("ema_9"))
    ema_21 = _number(technicals.get("ema_21"))
    atr = _number(technicals.get("atr"))
    if not all(value is not None for value in (vwap, ema_9, ema_21, atr)):
        return None
    values = {
        "side": 1.0 if action == "BUY" else -1.0,
        "confluence_score": _number(decision.get("confluence_score")),
        "ai_score": _number(ai_decision.get("ai_score")),
        "rsi": _number(technicals.get("rsi")),
        "adx": _number(technicals.get("adx")),
        "rvol": _number(technicals.get("rvol")),
        "vwap_distance_pct": (price / vwap - 1) * 100 if vwap and vwap > 0 else None,
        "ema_spread_pct": (ema_9 / ema_21 - 1) * 100 if ema_21 and ema_21 > 0 else None,
        "atr_pct": atr / price * 100,
    }
    if any(value is None or not math.isfinite(value) for value in values.values()):
        return None
    return {name: float(values[name]) for name in FEATURE_NAMES}
