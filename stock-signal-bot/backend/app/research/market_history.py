"""Load one provider's archived close series without mixing data sources."""

import math
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "market_history.db"


def load_close_series(
    symbol: str,
    interval: str,
    provider: str,
    db_path: Path = DEFAULT_DB,
) -> tuple[list[int], list[float]]:
    if not symbol.strip() or not interval.strip() or not provider.strip():
        raise ValueError("symbol, interval, and provider are required")
    if not db_path.is_file():
        return [], []

    with closing(sqlite3.connect(str(db_path))) as connection:
        rows = connection.execute(
            """SELECT timestamp, close FROM market_candles
               WHERE symbol=? AND interval=? AND provider=?
               ORDER BY timestamp""",
            (symbol.upper(), interval, provider),
        ).fetchall()

    timestamps: list[int] = []
    closes: list[float] = []
    for timestamp, close in rows:
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp <= 0:
            raise ValueError("archive contains an invalid candle timestamp")
        if isinstance(close, bool) or not isinstance(close, (int, float)):
            raise ValueError("archive contains a non-numeric close")
        if not math.isfinite(close) or close <= 0:
            raise ValueError("archive contains a non-finite or non-positive close")
        if timestamps and timestamp <= timestamps[-1]:
            raise ValueError("archive candle timestamps are not strictly increasing")
        timestamps.append(timestamp)
        closes.append(float(close))
    return timestamps, closes
