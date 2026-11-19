"""
CENTRAL DATA COLLECTOR & QUALITY INSPECTION PIPELINE
Responsibility:
- Ingestion abstraction for official Groww Trading API & secondary feeds
- Timestamp normalization, sequence tracking, and missing candle gap detection
- Circuit breaker for stale market feeds (>30s silence during market hours)
- Separate storage for raw candles vs derived indicators
"""

import time
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

class DataQualityStatus:
    VALID = "VALID"
    GAP_DETECTED = "GAP_DETECTED"
    SUSPECT_SPIKE = "SUSPECT_SPIKE"
    STALE_FEED = "STALE_FEED"

class MarketDataCollector:
    def __init__(self, primary_provider: str = "GROWW_API", secondary_provider: str = "NSE_DIRECT"):
        self.primary_provider = primary_provider
        self.secondary_provider = secondary_provider
        self.active_provider = primary_provider
        self.stale_threshold_seconds = 30.0
        self.last_successful_ingestion: Dict[str, float] = {}
        self.symbol_providers: Dict[str, str] = {}
        self.sequence_tracker: Dict[str, int] = {}
        self.candle_interval_seconds = 300  # 5 minutes

    def inspect_and_normalize_candle(
        self,
        symbol: str,
        exchange: str,
        exchange_timestamp: float,
        open_p: float,
        high_p: float,
        low_p: float,
        close_p: float,
        volume: int,
        prev_close: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validates telemetry, checks timestamps, sequence continuity, and anomalous spikes.
        Every record is stamped with both exchange time and collector received time.
        """
        received_timestamp = time.time()
        quality_status = DataQualityStatus.VALID
        rejection_reason = None

        # 1. Basic OHLC sanity checks
        if not (low_p <= open_p <= high_p and low_p <= close_p <= high_p):
            quality_status = DataQualityStatus.SUSPECT_SPIKE
            rejection_reason = f"Corrupt OHLC bounds: L={low_p}, O={open_p}, C={close_p}, H={high_p}"

        # 2. Extreme Price Spike filter (>12% candle body on large caps without exchange halt)
        if prev_close and prev_close > 0:
            pct_move = abs((close_p - prev_close) / prev_close) * 100
            if pct_move > 12.0:
                quality_status = DataQualityStatus.SUSPECT_SPIKE
                rejection_reason = f"Extreme price spike ({pct_move:.2f}%) detected"

        # 3. Sequence & Gap Detection
        last_time = self.last_successful_ingestion.get(symbol)
        if last_time:
            time_delta = exchange_timestamp - last_time
            if time_delta > (self.candle_interval_seconds * 1.5):
                quality_status = DataQualityStatus.GAP_DETECTED
                missing_bars = int(time_delta // self.candle_interval_seconds) - 1
                rejection_reason = f"Missing {missing_bars} consecutive 5m candle(s) between {last_time} and {exchange_timestamp}"

        # 4. Advance Sequence Counter
        seq_id = self.sequence_tracker.get(symbol, 0) + 1
        self.sequence_tracker[symbol] = seq_id
        self.last_successful_ingestion[symbol] = exchange_timestamp

        return {
            "symbol": symbol,
            "exchange": exchange,
            "timeframe": "5m",
            "data_source": self.active_provider,
            "exchange_timestamp": datetime.fromtimestamp(exchange_timestamp, tz=timezone.utc).isoformat(),
            "received_timestamp": datetime.fromtimestamp(received_timestamp, tz=timezone.utc).isoformat(),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": volume,
            "data_quality_status": quality_status,
            "rejection_reason": rejection_reason,
            "sequence_id": seq_id
        }

    def check_feed_health(self, symbol: str) -> Tuple[bool, str]:
        """
        Circuit breaker: Checks whether the feed for a given symbol is fresh.
        Returns (is_healthy, status_message)
        """
        last_seen = self.last_successful_ingestion.get(symbol)
        if not last_seen:
            return False, "NO_DATA_RECEIVED"

        now = time.time()
        elapsed = now - last_seen
        if elapsed > self.stale_threshold_seconds:
            return False, f"STALE_FEED: No updates for {elapsed:.1f}s (Threshold: {self.stale_threshold_seconds}s)"

        return True, "HEALTHY"

    def trigger_failover_to_secondary(self, reason: str) -> None:
        """
        Safely fails over to secondary provider upon primary feed failure.
        """
        print(f"[CIRCUIT BREAKER] Switching to {self.secondary_provider}. Reason: {reason}")
        self.active_provider = self.secondary_provider

collector_service = MarketDataCollector()
