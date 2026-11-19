from typing import List, Dict, Any, Optional

def detect_supply_demand_zones(highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> Dict[str, Any]:
    """
    Identifies Order Block / Supply & Demand Base Zones followed by impulsive departures.
    """
    if len(closes) < 8:
        return {"demand_zone": None, "supply_zone": None, "at_demand": False, "at_supply": False}

    current_price = closes[-1]
    demand_zone = None
    supply_zone = None

    # Scan for impulsive moves (candle body > 1.5x average body with above-average volume)
    bodies = [abs(closes[i] - lows[i]) for i in range(len(closes))]
    avg_body = sum(bodies[-10:]) / 10 if bodies else 1.0

    for i in range(len(closes) - 3, 2, -1):
        move = closes[i] - closes[i - 1]

        # Bullish impulsive departure -> Base prior is Demand Zone
        if move > 1.5 * avg_body and demand_zone is None:
            demand_zone = {
                "top": round(highs[i - 1], 2),
                "bottom": round(lows[i - 1], 2),
                "age_bars": len(closes) - i
            }
        # Bearish impulsive departure -> Base prior is Supply Zone
        elif move < -1.5 * avg_body and supply_zone is None:
            supply_zone = {
                "top": round(highs[i - 1], 2),
                "bottom": round(lows[i - 1], 2),
                "age_bars": len(closes) - i
            }

        if demand_zone and supply_zone:
            break

    # Fallbacks if no impulsive move in immediate range
    if not demand_zone:
        recent_min = min(lows[-15:])
        demand_zone = {"top": round(recent_min * 1.002, 2), "bottom": round(recent_min * 0.998, 2), "age_bars": 15}
    if not supply_zone:
        recent_max = max(highs[-15:])
        supply_zone = {"top": round(recent_max * 1.002, 2), "bottom": round(recent_max * 0.998, 2), "age_bars": 15}

    at_demand = demand_zone["bottom"] <= current_price <= demand_zone["top"] * 1.004
    at_supply = supply_zone["bottom"] * 0.996 <= current_price <= supply_zone["top"]

    return {
        "demand_zone": demand_zone,
        "supply_zone": supply_zone,
        "at_demand": at_demand,
        "at_supply": at_supply,
        "description": "At active Demand zone" if at_demand else ("At active Supply zone" if at_supply else "Between S/D zones")
    }
