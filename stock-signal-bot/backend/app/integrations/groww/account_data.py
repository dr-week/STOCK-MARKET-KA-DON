"""Normalize read-only Groww holdings, positions, orders, and executions."""

import logging
import math
from typing import Any

from growwapi import GrowwAPI

from app.integrations.groww.errors import GrowwIntegrationError

logger = logging.getLogger(__name__)


def _records(payload: Any, label: str, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = next((payload[key] for key in keys if isinstance(payload.get(key), list)), None)
    else:
        records = None
    if records is None or any(not isinstance(record, dict) for record in records):
        raise GrowwIntegrationError(f"Groww returned an unsupported {label} response.")
    return records


def _text(record: dict[str, Any], field: str, *aliases: str) -> str:
    value = next((record[key] for key in (field, *aliases) if record.get(key) is not None), None)
    if not isinstance(value, str) or not value.strip():
        raise GrowwIntegrationError(f"Groww returned a {field} without a valid value.")
    return value.strip()


def _number(record: dict[str, Any], field: str, *aliases: str) -> float:
    value = next((record[key] for key in (field, *aliases) if record.get(key) is not None), None)
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise GrowwIntegrationError(f"Groww returned an invalid {field}.")
    return float(value)


def _positive_number(record: dict[str, Any], field: str) -> float:
    value = _number(record, field)
    if value <= 0:
        raise GrowwIntegrationError(f"Groww returned an invalid {field}.")
    return value


def _optional_text(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is not None and not isinstance(value, str):
        raise GrowwIntegrationError(f"Groww returned an invalid {field}.")
    return value


def normalize_holdings(payload: Any) -> list[dict[str, Any]]:
    return [
        {
            "symbol": _text(record, "trading_symbol"),
            "quantity": _number(record, "quantity"),
            "average_price": _number(record, "average_price"),
            "isin": _optional_text(record, "isin"),
            "t1_quantity": _number(record, "t1_quantity") if record.get("t1_quantity") is not None else None,
        }
        for record in _records(payload, "holdings", "holdings")
    ]


def normalize_positions(payload: Any, segment: str) -> list[dict[str, Any]]:
    return [
        {
            "symbol": _text(record, "trading_symbol"),
            "segment": _optional_text(record, "segment") or segment,
            "quantity": _number(record, "quantity"),
            "average_price": _number(record, "net_price", "average_price"),
            "realized_pnl": _number(record, "realised_pnl", "realized_pnl")
            if record.get("realised_pnl", record.get("realized_pnl")) is not None else None,
        }
        for record in _records(payload, f"{segment} positions", "positions")
    ]


def load_orders_and_executions(client: GrowwAPI) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    orders: list[dict[str, Any]] = []
    executions: list[dict[str, Any]] = []
    fetched_order_count = 0
    for segment in ("CASH", "FNO"):
        segment_orders = _records(
            client.get_order_list(page=0, page_size=25, segment=segment, timeout=10),
            f"{segment} orders", "orders", "order_list",
        )
        for record in segment_orders:
            order_id = _text(record, "groww_order_id")
            status = _text(record, "order_status").upper()
            side = _text(record, "transaction_type").upper()
            if side not in {"BUY", "SELL"}:
                raise GrowwIntegrationError("Groww returned an invalid order side.")
            order_segment = _optional_text(record, "segment") or segment
            orders.append({
                "order_id": order_id,
                "symbol": _text(record, "trading_symbol"),
                "side": side,
                "segment": order_segment,
                "status": status,
                "created_at": _optional_text(record, "created_at"),
            })
            if status not in {"EXECUTED", "COMPLETED", "PARTIALLY_EXECUTED"} or fetched_order_count >= 20:
                continue
            fetched_order_count += 1
            for page in range(10):
                trades = _records(
                    client.get_trade_list_for_order(
                        groww_order_id=order_id, segment=order_segment,
                        page=page, page_size=50, timeout=10,
                    ),
                    "executions", "trades", "trade_list",
                )
                executions.extend(_normalize_executions(trades, order_id))
                if len(trades) < 50:
                    break
            else:
                logger.warning("Groww order %s execution history exceeded the local page limit.", order_id)
    return orders, executions


def _normalize_executions(trades: list[dict[str, Any]], order_id: str) -> list[dict[str, Any]]:
    normalized = []
    for trade in trades:
        if _text(trade, "groww_order_id") != order_id:
            raise GrowwIntegrationError("Groww returned an execution for a different order.")
        side = _text(trade, "transaction_type").upper()
        if side not in {"BUY", "SELL"}:
            raise GrowwIntegrationError("Groww returned an invalid execution side.")
        normalized.append({
            "trade_id": _text(trade, "groww_trade_id"),
            "order_id": order_id,
            "symbol": _text(trade, "trading_symbol"),
            "side": side,
            "segment": _text(trade, "segment"),
            "exchange": _text(trade, "exchange"),
            "quantity": _positive_number(trade, "quantity"),
            "price": _positive_number(trade, "price"),
            "status": _text(trade, "trade_status"),
            "executed_at": _text(trade, "trade_date_time"),
        })
    return normalized
