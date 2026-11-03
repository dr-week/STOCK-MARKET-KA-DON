from typing import Literal

Side = Literal["BUY", "SELL"]


def realized_pnl(side: Side, entry_price: float, exit_price: float, quantity: float) -> float:
    multiplier = 1 if side == "BUY" else -1
    return (exit_price - entry_price) * quantity * multiplier


def unrealized_pnl(side: Side, entry_price: float, current_price: float, quantity: float) -> float:
    multiplier = 1 if side == "BUY" else -1
    return (current_price - entry_price) * quantity * multiplier
