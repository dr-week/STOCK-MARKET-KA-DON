import time
import os
import logging
import math
import sqlite3
from typing import Dict, Any, List, Optional
from app.core.config import TRACKED_UNIVERSE
from app.departments.market_data.history_store import market_history_store
from app.departments.market_data.provider_client import fetch_chart
from app.departments.market_data.candle_normalizer import candle_rows, extract_candles, extract_daily_closes

logger = logging.getLogger(__name__)


class MarketDataDepartment:
    """
    DEPARTMENT 1: MARKET DATA
    Responsibility: Live prices, 5-minute candles, 15-minute candles, daily
    candles, volume, and tick history.  Single shared source of truth for all
    downstream analysis departments.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_expiry: Dict[str, float] = {}

    def get_stock_data(self, symbol: str, ticker: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        replay = os.getenv("SMKD_DATA_MODE", "live").lower() == "replay"
        # 10 second memory caching for live candles
        cache_key = f"replay:{ticker}" if replay else ticker
        if cache_key in self._cache and (now - self._cache_expiry.get(cache_key, 0)) < 10:
            return self._cache[cache_key]

        chart_5m = fetch_chart(ticker, interval="5m", range_param="1d")
        chart_15m = fetch_chart(ticker, interval="15m", range_param="5d")
        chart_daily = fetch_chart(ticker, interval="1d", range_param="3mo")

        if not chart_5m:
            return None

        meta = chart_5m.get("meta", {})
        price = meta.get("regularMarketPrice", 0.0)
        prev_close = meta.get("previousClose", price)
        change_pct = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0

        candles_5m = extract_candles(chart_5m, 300, now, not replay)
        candles_15m = extract_candles(chart_15m or {}, 900, now, not replay)
        daily_closes = extract_daily_closes(chart_daily or {}, now, replay)
        if not replay and not candles_5m["closes"]:
            return None

        archive_status = "replay_not_archived" if replay else "saved"
        archived_counts = {"5m": 0, "15m": 0}
        if not replay:
            try:
                archived_counts["5m"] = market_history_store.save_candles(
                    symbol, ticker, "5m", "yahoo_finance", candle_rows(candles_5m)
                )
                archived_counts["15m"] = market_history_store.save_candles(
                    symbol, ticker, "15m", "yahoo_finance", candle_rows(candles_15m)
                )
            except (OSError, sqlite3.Error) as error:
                archive_status = "unavailable"
                logger.error(
                    "Local candle archive failed for %s (%s).",
                    symbol,
                    type(error).__name__,
                )

        source_timestamp = meta.get("regularMarketTime")
        if (
            not isinstance(source_timestamp, (int, float))
            or not math.isfinite(source_timestamp)
            or source_timestamp <= 0
        ):
            source_timestamp = candles_5m["timestamps"][-1] if candles_5m["timestamps"] else None

        observed_volume = sum(candles_5m["volumes"])
        volume_today = meta.get("regularMarketVolume")
        if volume_today is None:
            volume_today = observed_volume
        recent_volume = sum(candles_5m["volumes"][-20:])
        relative_volume = observed_volume / max(recent_volume, 1) if candles_5m["volumes"] else 1.0
        day_high = meta.get("regularMarketDayHigh", price)
        day_low = meta.get("regularMarketDayLow", price)

        payload = {
            "symbol": symbol,
            "ticker": ticker,
            "current_price": price,
            "change_pct": change_pct,
            "day_high": day_high,
            "day_low": day_low,
            "volume_today": volume_today,
            "relative_volume": relative_volume,
            "timestamp": now,
            "data_quality": {
                "provider": "replay_fixture" if replay else "yahoo_finance",
                "instrument_id": ticker,
                "interval": "5m",
                "mode": "replay" if replay else "provider",
                "status": "available" if candles_5m["closes"] else "insufficient",
                "fetched_at": now,
                "source_timestamp": source_timestamp,
                "last_complete_candle_timestamp": candles_5m["timestamps"][-1] if candles_5m["timestamps"] else None,
                "invalid_5m_candles": candles_5m["invalid_count"],
                "excluded_incomplete_5m_candles": candles_5m["incomplete_count"],
                "history_archive_status": archive_status,
                "history_archived_candles": archived_counts,
            },
            "live_market_snapshot": {
                "price": price,
                "change_pct": change_pct,
                "day_high": day_high,
                "day_low": day_low,
                "volume_today": volume_today,
                "relative_volume": relative_volume,
            },
            "candles_5m": {
                "opens": candles_5m["opens"],
                "highs": candles_5m["highs"],
                "lows": candles_5m["lows"],
                "closes": candles_5m["closes"],
                "volumes": candles_5m["volumes"],
                "timestamps": candles_5m["timestamps"]
            },
            "candles_15m": {
                "opens": candles_15m["opens"],
                "highs": candles_15m["highs"],
                "lows": candles_15m["lows"],
                "closes": candles_15m["closes"],
                "volumes": candles_15m["volumes"],
                "timestamps": candles_15m["timestamps"],
            },
            "candles_daily": {
                "closes": daily_closes
            }
        }

        self._cache[cache_key] = payload
        self._cache_expiry[cache_key] = now
        return payload

market_data_dep = MarketDataDepartment()
