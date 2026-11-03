"""Intraday level and risk-budget sizing calculations."""
import math
from typing import Any, Dict, Tuple
from app.core.config import ACCOUNT_CAPITAL, MIN_RISK_REWARD_RATIO, RISK_PER_TRADE_PCT
from app.indicators.groww_costs import estimate_groww_intraday_charges, minimum_quantity_for_positive_net

def compute_intraday_levels(price: float, atr: float, signal_type: str) -> Tuple[float, float, float, float]:
    risk = max(atr * 1.5, price * 0.005)
    entry = round(price, 2)
    if "SELL" in signal_type or "SHORT" in signal_type:
        return entry, round(price - risk * 2, 2), round(price - risk * 3, 2), round(price + risk, 2)
    return entry, round(price + risk * 2, 2), round(price + risk * 3, 2), round(price - risk, 2)

def calculate_trade_risk_and_sizing(entry_price: float, stop_loss: float, target_1: float, target_2: float, capital: float = ACCOUNT_CAPITAL) -> Dict[str, Any]:
    risk_distance = abs(entry_price - stop_loss)
    is_short = stop_loss > entry_price
    reward_distance = max(0.0, entry_price - target_1 if is_short else target_1 - entry_price)
    if risk_distance <= 0:
        risk_distance = max(entry_price * 0.005, 1.0)
    allowable = round(capital * RISK_PER_TRADE_PCT, 2)
    max_risk = max(0, math.floor(allowable / risk_distance))
    max_margin = max(0, math.floor((max(capital, 0.0) * 5.0) / entry_price)) if entry_price > 0 else 0
    low, high = 0, min(max_risk, max_margin) + 1
    while low + 1 < high:
        candidate = (low + high) // 2
        charges = estimate_groww_intraday_charges(candidate, entry_price, stop_loss)["total"]
        if candidate * risk_distance + charges <= allowable:
            low = candidate
        else:
            high = candidate
    shares = low
    target_costs = estimate_groww_intraday_charges(shares, entry_price, target_1)
    stop_costs = estimate_groww_intraday_charges(shares, entry_price, stop_loss)
    break_even = round(estimate_groww_intraday_charges(shares, entry_price, entry_price)["total"] / shares, 4) if shares else None
    rr = round(reward_distance / risk_distance, 2)
    return {
        "capital_allocated": capital, "allowable_risk_inr": allowable, "actual_risk_inr": round(shares * risk_distance, 2), "shares_qty": shares,
        "trade_value": round(shares * entry_price, 2), "margin_required": round(shares * entry_price / 5.0, 2), "risk_distance_pts": round(risk_distance, 2), "reward_distance_pts": round(reward_distance, 2),
        "risk_reward_ratio": f"1:{rr}", "passes_rr_filter": rr >= MIN_RISK_REWARD_RATIO, "estimated_friction_inr": target_costs["total"], "estimated_brokerage_inr": target_costs["brokerage"], "estimated_statutory_charges_inr": target_costs["statutory"],
        "expected_net_t1_inr": round(reward_distance * shares - target_costs["total"], 2), "estimated_loss_at_stop_inr": round(risk_distance * shares + stop_costs["total"], 2), "break_even_move_per_share": break_even,
        "minimum_profitable_qty_at_t1": minimum_quantity_for_positive_net(entry_price, target_1, 1_000_000) if reward_distance > 0 else None,
    }
