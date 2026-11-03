"""Groww NSE equity intraday cost model."""
from typing import Dict

def estimate_groww_intraday_charges(quantity: int, entry_price: float, exit_price: float) -> Dict[str, float]:
    if quantity <= 0 or entry_price <= 0 or exit_price <= 0:
        return {"brokerage": 0.0, "statutory": 0.0, "total": 0.0}
    buy_turnover = round(quantity * min(entry_price, exit_price), 2)
    sell_turnover = round(quantity * max(entry_price, exit_price), 2)
    brokerage = sum(round(max(5.0, min(20.0, turnover * 0.001)), 2) for turnover in (buy_turnover, sell_turnover))
    stt = round(sell_turnover * 0.00025, 2)
    stamp_duty = round(buy_turnover * 0.00003, 2)
    exchange = round((buy_turnover + sell_turnover) * 0.0000297, 2)
    sebi = round((buy_turnover + sell_turnover) * 0.000001, 2)
    ipft = round((buy_turnover + sell_turnover) * 0.000001, 2)
    gst = round((brokerage + exchange + sebi + ipft) * 0.18, 2)
    statutory = round(stt + stamp_duty + exchange + sebi + ipft + gst, 2)
    return {"brokerage": brokerage, "statutory": statutory, "total": round(brokerage + statutory, 2)}

def minimum_quantity_for_positive_net(entry_price: float, target_price: float, max_quantity: int) -> int | None:
    if entry_price <= 0 or target_price <= 0 or target_price == entry_price:
        return None
    move = abs(target_price - entry_price)
    low, high = 1, 1
    while high <= max_quantity:
        if move * high > estimate_groww_intraday_charges(high, entry_price, target_price)["total"]:
            break
        if high == max_quantity:
            return None
        low, high = high + 1, min(high * 2, max_quantity)
    if high > max_quantity:
        return None
    while low < high:
        middle = (low + high) // 2
        if move * middle > estimate_groww_intraday_charges(middle, entry_price, target_price)["total"]:
            high = middle
        else:
            low = middle + 1
    return low
