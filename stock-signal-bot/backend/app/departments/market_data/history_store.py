"""Local SQLite archive for validated market candles (never broker account data)."""

import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from app.storage_paths import DATA_DIR

_DB_PATH = str(DATA_DIR / "market_history.db")
_SUPPORTED_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1mo"}


class MarketHistoryStore:
    """Stores provider-tagged OHLCV rows and returns bounded chart history."""

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(_DB_PATH, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save_candles(
        self,
        symbol: str,
        ticker: str,
        interval: str,
        provider: str,
        candles: list[dict[str, Any]],
    ) -> int:
        if not symbol.strip() or not ticker.strip() or not provider.strip() or interval not in _SUPPORTED_INTERVALS:
            raise ValueError("valid symbol, ticker, provider, and interval are required for candle archiving")
        observed_at = datetime.now(timezone.utc).isoformat()
        rows = []
        previous_timestamp = 0
        for candle in candles:
            timestamp = candle.get("timestamp")
            values = tuple(candle.get(field) for field in ("open", "high", "low", "close", "volume"))
            if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp <= previous_timestamp:
                raise ValueError("candle timestamps must be positive and strictly increasing")
            open_price, high_price, low_price, close_price, volume = values
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in values
            ):
                raise ValueError("candle OHLCV values must be finite numbers")
            if min(open_price, high_price, low_price, close_price) <= 0 or volume < 0:
                raise ValueError("candle prices must be positive and volume must be non-negative")
            if low_price > min(open_price, close_price) or high_price < max(open_price, close_price):
                raise ValueError("candle OHLC bounds are inconsistent")
            rows.append((
                symbol.upper(),
                ticker,
                interval,
                timestamp,
                float(open_price),
                float(high_price),
                float(low_price),
                float(close_price),
                float(volume),
                provider,
                observed_at,
            ))
            previous_timestamp = timestamp

        if not rows:
            return 0
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS market_candles (
                    symbol TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    provider TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, interval, timestamp, provider)
                )
            """)
            connection.executemany("""
                INSERT INTO market_candles
                    (symbol, ticker, interval, timestamp, open, high, low, close, volume, provider, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, interval, timestamp, provider) DO UPDATE SET
                    ticker=excluded.ticker,
                    open=excluded.open,
                    high=excluded.high,
                    low=excluded.low,
                    close=excluded.close,
                    volume=excluded.volume,
                    observed_at=excluded.observed_at
            """, rows)
        return len(rows)

    def get_candles(self, symbol: str, interval: str, limit: int = 1000) -> list[dict[str, Any]]:
        with self._connect() as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_candles'"
            ).fetchone()
            if table is None:
                return []
            rows = connection.execute("""
                WITH ranked AS (
                    SELECT symbol, ticker, interval, timestamp, open, high, low, close, volume,
                           provider, observed_at,
                           ROW_NUMBER() OVER (
                               PARTITION BY symbol, interval, timestamp
                               ORDER BY observed_at DESC, provider ASC
                           ) AS source_rank
                    FROM market_candles
                    WHERE symbol=? AND interval=?
                )
                SELECT symbol, ticker, interval, timestamp, open, high, low, close, volume,
                       provider, observed_at
                FROM ranked
                WHERE source_rank=1
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol.upper(), interval, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]


market_history_store = MarketHistoryStore()
