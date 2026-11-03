from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Indian Standard Time (UTC + 05:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_market_session_state() -> Dict[str, Any]:
    """Evaluates current IST time against institutional execution windows"""
    now = datetime.now(IST)
    minutes_from_midnight = now.hour * 60 + now.minute
    ist_str = now.strftime("%H:%M:%S")

    # Time boundaries
    pre_open = 9 * 60          # 09:00
    market_open = 9 * 60 + 15  # 09:15
    trap_end = 9 * 60 + 30     # 09:30
    prime_1_end = 11 * 60 + 15 # 11:15
    lull_end = 13 * 60 + 15    # 13:15
    prime_2_end = 14 * 60 + 45 # 14:45
    square_off = 15 * 60 + 15  # 15:15
    market_close = 15 * 60 + 30# 15:30

    if now.weekday() >= 5:
        phase = "WEEKEND / CLOSED"
        can_trade = False
        message = "NSE cash market is closed on weekends."
    elif minutes_from_midnight < market_open:
        phase = "PRE_MARKET / CLOSED"
        can_trade = False
        message = "Pre-market price discovery. Do not enter orders."
    elif market_open <= minutes_from_midnight < trap_end:
        phase = "OPENING_TRAP_ZONE"
        can_trade = False
        message = "Caution: High spread & SL hunting. Wait until 09:30 AM."
    elif trap_end <= minutes_from_midnight < prime_1_end:
        phase = "PRIME_MOMENTUM_1"
        can_trade = True
        message = "Optimal execution window: High volume & VWAP breakouts."
    elif prime_1_end <= minutes_from_midnight < lull_end:
        phase = "MIDDAY_CONSOLIDATION"
        can_trade = False
        message = "Midday chop zone. Avoid new breakout trades; trail stops."
    elif lull_end <= minutes_from_midnight < prime_2_end:
        phase = "PRIME_MOMENTUM_2"
        can_trade = True
        message = "European overlap window: Continuation trends active."
    elif prime_2_end <= minutes_from_midnight < square_off:
        phase = "SQUARE_OFF_PHASE"
        can_trade = False
        message = "Broker square-off in progress. Zero new entries."
    else:
        phase = "MARKET_CLOSED"
        can_trade = False
        message = "Market closed. Analyze delivery / swing setups."

    return {
        "ist_time": ist_str,
        "phase": phase,
        "can_trade_intraday": can_trade,
        "advisory": message
    }
