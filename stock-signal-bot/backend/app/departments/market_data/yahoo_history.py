"""Bounded public Yahoo Finance chart history adapter.

Yahoo's chart endpoint is an unofficial source and may change or rate-limit
requests. It is suitable only for clearly attributed chart history.
"""

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


_INTERVALS = {
    "1m": ("1m", "30d", 60),
    "5m": ("5m", "60d", 300),
    "15m": ("15m", "60d", 900),
    "1h": ("60m", "2y", 3600),
    "1d": ("1d", "max", 86400),
}


class YahooHistoryUnavailable(RuntimeError):
    """Raised when public Yahoo chart history cannot be fetched or validated."""


class YahooFinanceHistoryProvider:
    @classmethod
    def fetch(cls, symbol: str, interval: str, now: float | None = None) -> dict[str, Any]:
        if interval not in _INTERVALS:
            raise ValueError(f"Yahoo public history does not support the {interval} interval.")
        if not symbol.strip():
            raise ValueError("A valid NSE symbol is required.")

        yahoo_interval, period, seconds = _INTERVALS[interval]
        ticker = f"{symbol.strip().upper()}.NS"
        encoded_ticker = urllib.parse.quote(ticker, safe="")
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}"
            f"?interval={yahoo_interval}&range={urllib.parse.quote(period)}"
            "&events=history&includeAdjustedClose=false"
        )
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SMKD/1.0; chart history)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise YahooHistoryUnavailable(
                f"Yahoo Finance public history could not be fetched for {symbol} ({interval})."
            ) from error

        chart = payload.get("chart") if isinstance(payload, dict) else None
        if not isinstance(chart, dict):
            raise YahooHistoryUnavailable("Yahoo Finance returned an invalid chart response.")
        if chart.get("error"):
            raise YahooHistoryUnavailable(
                f"Yahoo Finance did not return history for {symbol} ({interval})."
            )
        results = chart.get("result")
        if not isinstance(results, list) or not results or not isinstance(results[0], dict):
            raise YahooHistoryUnavailable(
                f"Yahoo Finance returned no history for {symbol} ({interval})."
            )

        result = results[0]
        meta = result.get("meta")
        if not isinstance(meta, dict) or str(meta.get("symbol", "")).upper() != ticker:
            raise YahooHistoryUnavailable(
                f"Yahoo Finance returned data for an unexpected instrument instead of {ticker}."
            )
        timestamps = result.get("timestamp")
        indicators = result.get("indicators")
        quotes = indicators.get("quote") if isinstance(indicators, dict) else None
        quote = quotes[0] if isinstance(quotes, list) and quotes and isinstance(quotes[0], dict) else None
        if not isinstance(timestamps, list) or not isinstance(quote, dict):
            raise YahooHistoryUnavailable("Yahoo Finance returned incomplete candle arrays.")

        series = {
            field: quote.get(field) if isinstance(quote.get(field), list) else []
            for field in ("open", "high", "low", "close", "volume")
        }
        row_count = min(len(timestamps), *(len(values) for values in series.values()))
        if row_count == 0:
            raise YahooHistoryUnavailable(f"Yahoo Finance returned no usable candles for {symbol} ({interval}).")

        current_time = time.time() if now is None else now
        candles: list[dict[str, int | float]] = []
        previous_timestamp = 0
        for index in range(row_count):
            try:
                timestamp = int(timestamps[index])
                values = {
                    field: float(series[field][index])
                    for field in ("open", "high", "low", "close", "volume")
                }
            except (TypeError, ValueError, OverflowError):
                continue

            open_price, high_price, low_price, close_price, volume = (
                values["open"],
                values["high"],
                values["low"],
                values["close"],
                values["volume"],
            )
            if (
                timestamp <= previous_timestamp
                or not all(math.isfinite(value) for value in values.values())
                or min(open_price, high_price, low_price, close_price) <= 0
                or volume < 0
                or low_price > min(open_price, close_price)
                or high_price < max(open_price, close_price)
                or timestamp + seconds > current_time
            ):
                continue
            candles.append({
                "timestamp": timestamp,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            })
            previous_timestamp = timestamp

        if not candles:
            raise YahooHistoryUnavailable(
                f"Yahoo Finance returned no complete, valid candles for {symbol} ({interval})."
            )
        return {
            "symbol": symbol.strip().upper(),
            "interval": interval,
            "provider": "yahoo_finance_public_unofficial",
            "count": len(candles),
            "candles": candles,
        }


yahoo_finance_history = YahooFinanceHistoryProvider()
