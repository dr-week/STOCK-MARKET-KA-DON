import math
from typing import Any, Dict, List, Optional


def extract_candles(chart: Dict[str, Any], interval_seconds: int, now: float, exclude_incomplete: bool) -> Dict[str, Any]:
    timestamps = chart.get("timestamp") if isinstance(chart.get("timestamp"), list) else []
    indicators = chart.get("indicators") if isinstance(chart.get("indicators"), dict) else {}
    quotes = indicators.get("quote") if isinstance(indicators.get("quote"), list) else []
    quote = quotes[0] if quotes and isinstance(quotes[0], dict) else {}
    fields = ("open", "high", "low", "close", "volume")
    output_fields = {"open": "opens", "high": "highs", "low": "lows", "close": "closes", "volume": "volumes"}
    series = {field: quote.get(field) if isinstance(quote.get(field), list) else [] for field in fields}
    lengths = [len(timestamps), *(len(series[field]) for field in fields)]
    row_count = min(lengths, default=0)
    candles: Dict[str, Any] = {field: [] for field in output_fields.values()}
    candles["timestamps"] = []
    invalid_count = max(lengths, default=0) - row_count
    incomplete_count = 0
    last_timestamp: Optional[int] = None
    for index in range(row_count):
        try:
            timestamp = int(timestamps[index])
            values = {field: float(series[field][index]) for field in fields}
        except (TypeError, ValueError, OverflowError):
            invalid_count += 1
            continue
        open_price, high_price, low_price = values["open"], values["high"], values["low"]
        close_price, volume = values["close"], values["volume"]
        valid = (
            timestamp > 0 and all(math.isfinite(value) for value in values.values()) and
            min(open_price, high_price, low_price, close_price) > 0 and volume >= 0 and
            low_price <= min(open_price, close_price) and high_price >= max(open_price, close_price)
        )
        if not valid or (last_timestamp is not None and timestamp <= last_timestamp):
            invalid_count += 1
            continue
        if exclude_incomplete and timestamp + interval_seconds > now:
            incomplete_count += 1
            continue
        candles["timestamps"].append(timestamp)
        for field in fields:
            candles[output_fields[field]].append(values[field])
        last_timestamp = timestamp
    candles["invalid_count"] = invalid_count
    candles["incomplete_count"] = incomplete_count
    return candles


def extract_daily_closes(chart: Dict[str, Any], now: float, replay: bool) -> List[float]:
    timestamps = chart.get("timestamp") if isinstance(chart.get("timestamp"), list) else []
    indicators = chart.get("indicators") if isinstance(chart.get("indicators"), dict) else {}
    quotes = indicators.get("quote") if isinstance(indicators.get("quote"), list) else []
    quote = quotes[0] if quotes and isinstance(quotes[0], dict) else {}
    closes = quote.get("close") if isinstance(quote.get("close"), list) else []
    result: List[float] = []
    last_timestamp: Optional[int] = None
    for timestamp_value, close_value in zip(timestamps, closes):
        try:
            timestamp, close = int(timestamp_value), float(close_value)
        except (TypeError, ValueError, OverflowError):
            continue
        if (timestamp <= 0 or not math.isfinite(close) or close <= 0 or
            (last_timestamp is not None and timestamp <= last_timestamp) or
            (not replay and timestamp + 86_400 > now)):
            continue
        result.append(close)
        last_timestamp = timestamp
    return result


def candle_rows(series: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{
        "timestamp": series["timestamps"][index], "open": series["opens"][index],
        "high": series["highs"][index], "low": series["lows"][index],
        "close": series["closes"][index], "volume": series["volumes"][index],
    } for index in range(len(series["timestamps"]))]
