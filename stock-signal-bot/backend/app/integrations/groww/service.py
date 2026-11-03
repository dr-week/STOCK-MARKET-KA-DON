"""Read-only access to Groww account data.

Credentials are used only to obtain an access token. Neither credentials,
tokens, nor account responses are written to disk by this integration.
"""

import logging
import threading
from datetime import date, datetime, timezone
from typing import Any

from growwapi import GrowwAPI

from app.integrations.groww.account_data import (
    load_orders_and_executions,
    normalize_holdings,
    normalize_positions,
)
from app.integrations.groww.errors import GrowwIntegrationError
from app.integrations.groww.history_provider import GrowwHistoryProvider

logger = logging.getLogger(__name__)


class GrowwReadOnlyService:
    """Holds one in-memory Groww session and exposes only account read methods."""

    def __init__(self) -> None:
        self._client: GrowwAPI | None = None
        self._lock = threading.RLock()

    def connect(self, api_key: str, secret: str) -> None:
        try:
            access_token = GrowwAPI.get_access_token(api_key=api_key, secret=secret)
            if not isinstance(access_token, str) or not access_token:
                raise GrowwIntegrationError("Groww did not return a usable access token.")
            client = GrowwAPI(access_token)
        except GrowwIntegrationError:
            raise
        except Exception as error:
            logger.warning("Groww authentication failed (%s).", type(error).__name__)
            raise GrowwIntegrationError(
                "Groww authentication failed. Check your API subscription, daily approval, and credentials."
            ) from error
        with self._lock:
            self._client = client

    def disconnect(self) -> None:
        with self._lock:
            self._client = None

    def is_connected(self) -> bool:
        with self._lock:
            return self._client is not None

    def historical_candles(
        self,
        symbol: str,
        interval: str,
        days: int,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if self._client is None:
                raise GrowwIntegrationError("Connect a Groww API session before fetching historical candles.")
            return GrowwHistoryProvider.fetch(self._client, symbol, interval, days, end_date)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            client = self._client
            if client is None:
                raise GrowwIntegrationError("Connect a Groww API session before loading account data.")
            try:
                holdings = normalize_holdings(client.get_holdings_for_user(timeout=10))
                positions = [
                    position
                    for segment in ("CASH", "FNO")
                    for position in normalize_positions(
                        client.get_positions_for_user(segment=segment, timeout=10), segment
                    )
                ]
                orders, executions = load_orders_and_executions(client)
            except GrowwIntegrationError:
                raise
            except Exception as error:
                logger.warning("Groww read request failed (%s).", type(error).__name__)
                raise GrowwIntegrationError(
                    "Groww account data could not be loaded. The session may have expired; reconnect and retry."
                ) from error

        return {
            "source": "Groww Trading API",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "holdings": holdings,
            "positions": positions,
            "orders": orders,
            "executions": executions,
        }


groww_read_only = GrowwReadOnlyService()
