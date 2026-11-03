"""Loopback-only reads from the local validated-candle archive."""

import re
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.local_access import require_loopback_client
from app.departments.market_data.history_store import market_history_store
from app.departments.market_data.yahoo_history import (
    YahooHistoryUnavailable,
    yahoo_finance_history,
)

router = APIRouter(
    prefix="/market-history",
    tags=["local-market-history"],
    dependencies=[Depends(require_loopback_client)],
)
_SYMBOL = re.compile(r"^[A-Z0-9._&-]{1,24}$")


@router.get("/{symbol}")
def get_local_market_history(
    symbol: str,
    interval: str = Query("5m", pattern=r"^(1m|3m|5m|15m|30m|1h|4h|1d|1w|1mo)$"),
    limit: int = Query(1000, ge=1, le=5000),
) -> dict:
    normalized_symbol = symbol.strip().upper().removesuffix(".NS")
    if not _SYMBOL.fullmatch(normalized_symbol):
        raise HTTPException(status_code=422, detail="A valid exchange symbol is required.")
    if interval in {"1m", "5m", "15m", "1h", "1d"}:
        try:
            history = yahoo_finance_history.fetch(normalized_symbol, interval)
        except YahooHistoryUnavailable as error:
            cached = market_history_store.get_candles(normalized_symbol, interval, limit)
            if not cached:
                raise HTTPException(status_code=502, detail=str(error)) from error
            candles = cached
            provider = "local_archive_cached"
            warning = str(error)
        else:
            try:
                market_history_store.save_candles(
                    normalized_symbol,
                    f"NSE-{normalized_symbol.removesuffix('.NS')}",
                    interval,
                    history["provider"],
                    history["candles"],
                )
            except (OSError, sqlite3.Error) as error:
                raise HTTPException(
                    status_code=500,
                    detail="Public history was fetched but could not be saved to the local candle archive.",
                ) from error
            candles = market_history_store.get_candles(normalized_symbol, interval, limit)
            provider = history["provider"]
            warning = None
    else:
        candles = market_history_store.get_candles(normalized_symbol, interval, limit)
        provider = "local_archive"
        warning = (
            "This interval is not available from the public Yahoo history adapter. "
            "Fetch it through the connected Groww history API first."
            if interval == "3m"
            else None
        )

    return {
        "symbol": normalized_symbol,
        "interval": interval,
        "count": len(candles),
        "provider": provider,
        "warning": warning,
        "candles": candles,
    }
