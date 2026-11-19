'''\
feed_integrity.py
-----------------
Utility functions to enrich market data with provenance and freshness metadata.
Provides:
- `class FeedMode` enumeration of possible feed states.
- `class FeedInfo` dataclass capturing all required fields.
- `def build_feed_info(symbol: str, provider: str, exchange_ts: float, received_ts: float, processed_ts: float, sequence_id: int, connection_ok: bool, last_msg_ts: float) -> FeedInfo`
- `def classify_mode(info: FeedInfo, now_ts: float, market_open: bool, stale_threshold: float = 30.0) -> str`
- `def is_stale(info: FeedInfo, now_ts: float, stale_threshold: float) -> tuple[bool, str]`
- `def enrich_with_provenance(symbol: str, raw: dict, source: str, mode: FeedMode = FeedMode.UNKNOWN, connection_ok: bool = True, last_msg_ts: Optional[float] = None) -> dict`

The functions are deliberately pure and test‑friendly; they do not depend on any global state.
'''\

from __future__ import annotations

import time
from typing import Optional
from app.departments.market_data.feed_models import FeedMode, FeedInfo


def build_feed_info(
    symbol: str,
    source: str,
    provider_ts: float,
    received_ts: float,
    processed_ts: float,
    sequence_id: Optional[int] = None,
    connection_ok: bool = True,
    last_msg_ts: Optional[float] = None,
    mode: FeedMode = FeedMode.UNKNOWN,
) -> FeedInfo:
    """Create a FeedInfo instance for a single quote/candle.

    Args:
        symbol: Ticker symbol.
        source: Name of the upstream provider (e.g. 'GROWW_API').
        provider_ts: Timestamp supplied by the provider (epoch seconds).
        received_ts: Collector receipt timestamp (epoch seconds).
        processed_ts: Time when the data was processed into the pipeline.
        sequence_id: Optional monotonically increasing event id.
        connection_ok: Whether the websocket/HTTP connection is healthy.
        last_msg_ts: Timestamp of the last successful message from the feed.
        mode: Explicit mode if known (e.g. SIMULATED during tests).
    """
    return FeedInfo(
        symbol=symbol,
        source=source,
        mode=mode,
        provider_timestamp=provider_ts,
        received_at=received_ts,
        processed_at=processed_ts,
        sequence_id=sequence_id,
        connection_status="CONNECTED" if connection_ok else "DISCONNECTED",
        last_successful_message_at=last_msg_ts,
    )


def is_stale(info: FeedInfo, now_ts: float, stale_threshold: float = 30.0) -> tuple[bool, str]:
    """Determine if a feed entry is stale.

    Stale if the age (now - provider_timestamp) exceeds the threshold *or*
    the time since the last successful message exceeds the same threshold.
    Returns a tuple (is_stale, reason).
    """
    age = now_ts - info.provider_timestamp
    if age > stale_threshold:
        return True, f"PROVIDER_AGE_{int(age)}s"
    if info.last_successful_message_at is not None:
        gap = now_ts - info.last_successful_message_at
        if gap > stale_threshold:
            return True, f"NO_MESSAGE_FOR_{int(gap)}s"
    return False, ""


def classify_mode(info: FeedInfo, now_ts: float, market_open: bool, stale_threshold: float = 30.0) -> FeedMode:
    """Classify the feed mode based on timestamps and connection status.

    Priority order:
    1. If connection broken → UNKNOWN
    2. If explicitly marked SIMULATED → SIMULATED
    3. If stale → CACHED or DELAYED depending on market hours.
    4. If provider timestamp is far behind current market time → HISTORICAL
    5. Otherwise → LIVE
    """
    if info.connection_status != "CONNECTED":
        return FeedMode.UNKNOWN
    if info.mode == FeedMode.SIMULATED:
        return FeedMode.SIMULATED

    stale, _ = is_stale(info, now_ts, stale_threshold)
    if stale:
        return FeedMode.DELAYED if market_open else FeedMode.CACHED

    if now_ts - info.provider_timestamp > 60:
        return FeedMode.HISTORICAL

    return FeedMode.LIVE


def enrich_with_provenance(
    symbol: str,
    raw: dict,
    source: str,
    mode: FeedMode = FeedMode.UNKNOWN,
    connection_ok: bool = True,
    last_msg_ts: Optional[float] = None,
) -> dict:
    """Merge raw market data dict with provenance fields.

    The caller supplies raw data that contains at least `exchange_timestamp`.
    The function returns a new dict with additional keys compatible with the UI.
    """
    now = time.time()
    provider_ts = raw.get("exchange_timestamp")
    if provider_ts is None:
        provider_ts = now
    seq_id = raw.get("sequence_id")
    feed_info = build_feed_info(
        symbol=symbol,
        source=source,
        provider_ts=provider_ts,
        received_ts=now,
        processed_ts=now,
        sequence_id=seq_id,
        connection_ok=connection_ok,
        last_msg_ts=last_msg_ts,
        mode=mode,
    )
    # Simple market‑open heuristic for IST (9:15‑15:30)
    ist_now = time.gmtime(now + 5.5 * 3600)
    seconds_since_midnight = ist_now.tm_hour * 3600 + ist_now.tm_min * 60 + ist_now.tm_sec
    market_open = 9 * 3600 + 15 * 60 <= seconds_since_midnight <= 15 * 3600 + 30 * 60
    feed_info.mode = classify_mode(feed_info, now, market_open, stale_threshold=30.0)
    enriched = dict(raw)
    enriched["feed_provenance"] = {
        "source": feed_info.source,
        "mode": feed_info.mode.value,
        "provider_timestamp": feed_info.provider_timestamp,
        "received_at": feed_info.received_at,
        "processed_at": feed_info.processed_at,
        "sequence_id": feed_info.sequence_id,
        "connection_status": feed_info.connection_status,
        "last_successful_message_at": feed_info.last_successful_message_at,
        "is_stale": feed_info.is_stale,
        "stale_reason": feed_info.stale_reason,
    }
    return enriched
