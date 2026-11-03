import math
from typing import Any, Dict, Optional, Tuple

MAX_MARKET_DATA_AGE_SECONDS = 15 * 60
MAX_CLOCK_SKEW_SECONDS = 60


def positive_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0 else None


def fresh_market_result(result: Dict[str, Any], now: float) -> bool:
    market_data = result.get("market_data")
    quality = market_data.get("data_quality") if isinstance(market_data, dict) else None
    if not isinstance(quality, dict) or quality.get("status") != "available" or quality.get("mode") != "provider":
        return False
    timestamps = [positive_number(quality.get(key)) for key in ("fetched_at", "last_complete_candle_timestamp", "source_timestamp")]
    if any(timestamp is None for timestamp in timestamps):
        return False
    valid_timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    if any(timestamp > now + MAX_CLOCK_SKEW_SECONDS for timestamp in valid_timestamps):
        return False
    return all(now - timestamp <= MAX_MARKET_DATA_AGE_SECONDS for timestamp in valid_timestamps)


def exit_trigger(position: Dict[str, Any], price: float) -> Tuple[Optional[float], Optional[str]]:
    if position["action"] == "BUY":
        if price <= position["stop_loss"]:
            return float(position["stop_loss"]), "stop"
        if price >= position["target"]:
            return float(position["target"]), "target"
    else:
        if price >= position["stop_loss"]:
            return float(position["stop_loss"]), "stop"
        if price <= position["target"]:
            return float(position["target"]), "target"
    return None, None
