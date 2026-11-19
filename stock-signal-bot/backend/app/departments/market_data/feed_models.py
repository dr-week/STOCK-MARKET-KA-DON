from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional


class FeedMode(str, enum.Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    HISTORICAL = "HISTORICAL"
    SIMULATED = "SIMULATED"
    CACHED = "CACHED"
    UNKNOWN = "UNKNOWN"


@dataclass
class FeedInfo:
    symbol: str
    source: str  # provider name or 'SIMULATOR'
    mode: FeedMode
    provider_timestamp: float  # epoch seconds from provider
    received_at: float  # epoch seconds when collector received
    processed_at: float  # epoch seconds after processing (usually now)
    ui_updated_at: Optional[float] = None  # set by frontend later
    sequence_id: Optional[int] = None
    connection_status: str = "CONNECTED"  # or DISCONNECTED
    last_successful_message_at: Optional[float] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
