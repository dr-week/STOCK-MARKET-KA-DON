import math
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


def load_candles(db_path: str, interval: str, provider: str) -> list[dict[str, Any]]:
    if not provider.strip():
        raise ValueError("Select exactly one provider identifier.")
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_candles'"
        ).fetchone()
        if table is None:
            raise ValueError(f"No market_candles table in {db_path}.")
        rows = connection.execute(
            f"""
            SELECT symbol, timestamp, open, high, low, close, volume, provider
            FROM market_candles
            WHERE interval=? AND provider=?
            ORDER BY symbol, timestamp
            """,
            (interval, provider),
        ).fetchall()

    candles: dict[tuple[str, int], dict[str, Any]] = {}
    for symbol, timestamp, open_, high, low, close, volume, source in rows:
        values = (open_, high, low, close, volume)
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, int)
            or timestamp <= 0
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in values
            )
            or not isinstance(symbol, str)
            or not symbol.strip()
            or min(open_, high, low, close) <= 0
            or volume < 0
            or low > min(open_, close)
            or high < max(open_, close)
        ):
            raise ValueError(f"Invalid OHLCV row for {symbol} from {source}.")
        key = (symbol, timestamp)
        candle = {
            "symbol": symbol,
            "timestamp": timestamp,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
        previous = candles.get(key)
        if previous is not None and any(
            not math.isclose(previous[field], candle[field], rel_tol=1e-9, abs_tol=1e-8)
            for field in ("open", "high", "low", "close", "volume")
        ):
            raise ValueError(f"Conflicting duplicate candle for {symbol} at {timestamp}.")
        candles[key] = candle

    return sorted(candles.values(), key=lambda row: (row["symbol"], row["timestamp"]))
