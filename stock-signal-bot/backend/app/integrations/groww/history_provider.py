"""Historical-candle adapter for Groww's documented backtesting API."""

import math
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from growwapi import GrowwAPI

_INTERVALS = {
    "1m": ("1minute", 30, 60),
    "2m": ("2minute", 30, 120),
    "3m": ("3minute", 30, 180),
    "5m": ("5minute", 30, 300),
    "10m": ("10minute", 90, 600),
    "15m": ("15minute", 90, 900),
    "30m": ("30minute", 90, 1800),
    "1h": ("1hour", 180, 3600),
    "4h": ("4hour", 180, 14400),
    "1d": ("1day", 180, 86400),
    "1w": ("1week", 180, 604800),
    "1mo": ("1month", 180, 2592000),
}
_SYMBOL = re.compile(r"^[A-Z0-9._&-]{1,24}$")
_IST = ZoneInfo("Asia/Kolkata")


class GrowwHistoryError(RuntimeError):
    """Raised when the provider history response cannot be trusted or fetched."""


class GrowwHistoryProvider:
    """Fetches and validates bounded, timestamped NSE cash candles."""

    @classmethod
    def fetch(
        cls,
        client: GrowwAPI,
        symbol: str,
        interval: str,
        days: int,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        normalized_symbol = symbol.strip().upper()
        if not _SYMBOL.fullmatch(normalized_symbol):
            raise ValueError("A valid NSE trading symbol is required.")
        if interval not in _INTERVALS:
            raise ValueError("Unsupported candle interval.")
        groww_interval, max_days, interval_seconds = _INTERVALS[interval]
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= max_days:
            raise ValueError(f"{interval} history supports 1 to {max_days} days per request.")

        end_time = datetime.now(_IST)
        if end_date is not None:
            if end_date > end_time.date():
                raise ValueError("History end date cannot be in the future.")
            requested_end = datetime.combine(end_date, time.max, tzinfo=_IST)
            end_time = min(end_time, requested_end)
        start_time = end_time - timedelta(days=days)
        try:
            payload = client.get_historical_candles(
                exchange="NSE",
                segment="CASH",
                groww_symbol=f"NSE-{normalized_symbol.removesuffix('.NS')}",
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                candle_interval=groww_interval,
                timeout=20,
            )
        except Exception as error:
            raise GrowwHistoryError(
                "Groww historical candles could not be fetched. Check API access and the instrument symbol."
            ) from error

        if not isinstance(payload, dict) or not isinstance(payload.get("candles"), list):
            raise GrowwHistoryError("Groww returned an unsupported historical-candle response.")
        candles = [cls._normalize_candle(row, index) for index, row in enumerate(payload["candles"])]
        candles.sort(key=lambda candle: candle["timestamp"])
        if any(candles[index - 1]["timestamp"] >= candles[index]["timestamp"] for index in range(1, len(candles))):
            raise GrowwHistoryError("Groww returned duplicate or unordered candle timestamps.")
        start_epoch = start_time.astimezone(timezone.utc).timestamp()
        end_epoch = end_time.astimezone(timezone.utc).timestamp()
        if any(candle["timestamp"] < start_epoch or candle["timestamp"] > end_epoch for candle in candles):
            raise GrowwHistoryError("Groww returned candles outside the requested history window.")
        complete_candles = [
            candle for candle in candles
            if candle["timestamp"] + interval_seconds <= end_epoch
        ]
        return {
            "symbol": normalized_symbol,
            "interval": interval,
            "provider": "groww_trade_api",
            "count": len(complete_candles),
            "timestamp_basis": "Provider timestamps without an offset are interpreted as Asia/Kolkata.",
            "candles": complete_candles,
        }

    @staticmethod
    def _normalize_candle(row: Any, index: int) -> dict[str, Any]:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            raise GrowwHistoryError(f"Groww historical candle {index + 1} is malformed.")
        try:
            timestamp_value = row[0]
            if isinstance(timestamp_value, bool):
                raise ValueError("boolean timestamp")
            if any(isinstance(value, bool) for value in row[1:6]):
                raise ValueError("boolean OHLCV value")
            if isinstance(timestamp_value, (int, float)):
                timestamp = int(timestamp_value / 1000 if timestamp_value > 100_000_000_000 else timestamp_value)
            elif isinstance(timestamp_value, str):
                try:
                    epoch = float(timestamp_value)
                except ValueError:
                    parsed = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=_IST)
                    timestamp = int(parsed.astimezone(timezone.utc).timestamp())
                else:
                    timestamp = int(epoch / 1000 if epoch > 100_000_000_000 else epoch)
            else:
                raise ValueError("invalid timestamp type")
            values = [float(value) for value in row[1:6]]
        except (TypeError, ValueError, OverflowError) as error:
            raise GrowwHistoryError(f"Groww historical candle {index + 1} contains invalid values.") from error

        if timestamp <= 0 or any(not math.isfinite(value) for value in values):
            raise GrowwHistoryError(f"Groww historical candle {index + 1} contains non-finite values.")
        open_price, high_price, low_price, close_price, volume = values
        if (
            min(open_price, high_price, low_price, close_price) <= 0
            or volume < 0
            or low_price > min(open_price, close_price)
            or high_price < max(open_price, close_price)
        ):
            raise GrowwHistoryError(f"Groww historical candle {index + 1} violates OHLCV bounds.")
        return {
            "timestamp": timestamp,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        }
