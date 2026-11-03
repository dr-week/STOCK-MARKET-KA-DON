import json
import math
import time
import urllib.request
from typing import Any, Dict, List


def load_bars(symbol: str, days: int) -> List[Dict[str, Any]]:
    ticker = f"{symbol}.NS"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range={days}d"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode())

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise ValueError(f"Provider error: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise ValueError("Historical provider returned no chart data")
    result = results[0]
    quote_list = result.get("indicators", {}).get("quote") or []
    if not quote_list:
        raise ValueError("Historical provider response has no OHLCV quote")
    quote = quote_list[0]
    timestamps = result.get("timestamp") or []
    bars: List[Dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        values = [quote.get(field, [])[index] if index < len(quote.get(field, [])) else None
                  for field in ("open", "high", "low", "close", "volume")]
        if any(value is None for value in values):
            continue
        try:
            open_price, high, low, close, volume = (float(value) for value in values)
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(value) for value in (open_price, high, low, close, volume)):
            continue
        if min(open_price, high, low, close) <= 0 or volume < 0:
            continue
        if low > min(open_price, close) or high < max(open_price, close) or low > high:
            continue
        bars.append({"time": int(timestamp), "open": open_price, "high": high, "low": low, "close": close, "volume": volume})
    bars.sort(key=lambda bar: bar["time"])
    completed_before = int(time.time()) - 300
    return [bar for bar in bars if bar["time"] <= completed_before]
