"""Local-only HTTP endpoints for the read-only Groww integration."""

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.api.local_access import require_loopback_client
from app.departments.market_data.history_store import market_history_store
from app.integrations.groww.history_provider import GrowwHistoryError
from app.integrations.groww.service import GrowwIntegrationError, groww_read_only

router = APIRouter(
    prefix="/groww",
    tags=["groww-read-only"],
    dependencies=[Depends(require_loopback_client)],
)


class GrowwConnectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    api_key: SecretStr = Field(min_length=1, max_length=512)
    secret: SecretStr = Field(min_length=1, max_length=512)


@router.get("/status")
def groww_status() -> dict[str, bool]:
    return {"connected": groww_read_only.is_connected()}


@router.post("/connect")
def groww_connect(request: GrowwConnectRequest) -> dict[str, bool]:
    try:
        groww_read_only.connect(
            request.api_key.get_secret_value(),
            request.secret.get_secret_value(),
        )
    except GrowwIntegrationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"connected": True}


@router.post("/disconnect")
def groww_disconnect() -> dict[str, bool]:
    groww_read_only.disconnect()
    return {"connected": False}


@router.get("/account")
def groww_account() -> dict:
    try:
        return groww_read_only.snapshot()
    except GrowwIntegrationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/history/{symbol}")
def groww_historical_candles(
    symbol: str,
    interval: str = Query("5m", pattern=r"^(1m|3m|5m|15m|1h|1d)$"),
    days: int = Query(30, ge=1, le=180),
    end_date: date | None = Query(None),
) -> dict:
    try:
        history = groww_read_only.historical_candles(symbol, interval, days, end_date)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (GrowwIntegrationError, GrowwHistoryError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    try:
        archived_count = market_history_store.save_candles(
            history["symbol"],
            f"NSE-{history['symbol']}",
            interval,
            history["provider"],
            history["candles"],
        )
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(
            status_code=500,
            detail="History was fetched but could not be saved to the local candle archive.",
        ) from error
    history["archived_count"] = archived_count
    return history
