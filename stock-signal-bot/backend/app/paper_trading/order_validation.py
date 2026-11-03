import math


def validate_order(
    symbol: str,
    action: str,
    entry: float,
    stop_loss: float,
    target: float,
    qty: float,
    confluence_score: float,
    source: str,
) -> tuple[str, str]:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol must not be empty")
    normalized_action = action.upper()
    if normalized_action not in ("BUY", "SELL"):
        raise ValueError(f"action must be BUY or SELL, got {normalized_action!r}")
    if not all(math.isfinite(value) for value in (entry, stop_loss, target, qty, confluence_score)):
        raise ValueError("prices, quantity, and confluence score must be finite")
    if entry <= 0 or stop_loss <= 0 or target <= 0:
        raise ValueError("entry, stop loss, and target must be greater than zero")
    if qty <= 0 or qty % 1 != 0:
        raise ValueError("quantity must be a positive whole number of shares")
    if not 0 <= confluence_score <= 10:
        raise ValueError("confluence score must be between 0 and 10")
    if source not in {"MANUAL", "AUTO"}:
        raise ValueError("source must be MANUAL or AUTO")
    if normalized_action == "BUY" and not stop_loss < entry < target:
        raise ValueError("BUY trades require stop loss < entry < target")
    if normalized_action == "SELL" and not target < entry < stop_loss:
        raise ValueError("SELL trades require target < entry < stop loss")
    return normalized_symbol, normalized_action
