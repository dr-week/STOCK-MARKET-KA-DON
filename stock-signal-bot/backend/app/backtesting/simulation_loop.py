from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.backtesting.performance_metrics import summarize_trades
from app.backtesting.simulation import MIN_WARMUP_BARS, build_signal

IST = timezone(timedelta(hours=5, minutes=30))


def _session_key(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=IST).date().isoformat()


def simulate_threshold(
    bars: List[Dict[str, Any]],
    threshold: int,
    intelligence: Dict[str, Any],
    holding_bars: int,
    cost_bps_per_side: float,
    quality_filter_passed: bool = True,
) -> Dict[str, Any]:
    trades: List[Dict[str, Any]] = []
    session_keys = [_session_key(bar["time"]) for bar in bars]
    session_starts: Dict[str, int] = {}
    session_ends: Dict[str, int] = {}
    for bar_index, key in enumerate(session_keys):
        session_starts.setdefault(key, bar_index)
        session_ends[key] = bar_index

    next_available_index = 0
    index = 0
    while index < len(bars) - 1:
        session = session_keys[index]
        session_start = session_starts[session]
        session_end = session_ends[session]
        history = bars[session_start:index + 1]
        if len(history) < MIN_WARMUP_BARS or index < next_available_index:
            index += 1
            continue
        decision = build_signal(history, len(history) - 1, threshold, intelligence, quality_filter_passed)
        if decision is None or decision.get("signal") not in ("BUY CANDIDATE", "SELL CANDIDATE"):
            index += 1
            continue
        if session_keys[index + 1] != session:
            index += 1
            continue

        side = "BUY" if decision["signal"] == "BUY CANDIDATE" else "SELL"
        entry = bars[index + 1]["open"]
        stop = float(decision["stop_loss"])
        target = float(decision["target_1"])
        if (side == "BUY" and (entry >= target or entry <= stop)) or (side == "SELL" and (entry <= target or entry >= stop)):
            index += 1
            continue
        end_index = min(index + holding_bars, session_end)
        exit_price = bars[end_index]["close"]
        outcome = "TIME_EXPIRED"
        holding_index = end_index
        for forward_index in range(index + 1, end_index + 1):
            bar = bars[forward_index]
            if side == "BUY":
                if bar["open"] <= stop:
                    exit_price, outcome, holding_index = bar["open"], "STOP_LOSS_GAP", forward_index
                    break
                if bar["low"] <= stop:
                    exit_price, outcome, holding_index = stop, "STOP_LOSS_HIT", forward_index
                    break
                if bar["high"] >= target:
                    exit_price, outcome, holding_index = target, "TARGET_1_HIT", forward_index
                    break
            else:
                if bar["open"] >= stop:
                    exit_price, outcome, holding_index = bar["open"], "STOP_LOSS_GAP", forward_index
                    break
                if bar["high"] >= stop:
                    exit_price, outcome, holding_index = stop, "STOP_LOSS_HIT", forward_index
                    break
                if bar["low"] <= target:
                    exit_price, outcome, holding_index = target, "TARGET_1_HIT", forward_index
                    break

        gross_return = ((exit_price - entry) / entry * 100.0) if side == "BUY" else ((entry - exit_price) / entry * 100.0)
        round_trip_cost_pct = (2.0 * cost_bps_per_side) / 100.0
        trades.append({
            "signal_time": bars[index]["time"], "entry_time": bars[index + 1]["time"], "side": side,
            "confluence_score": decision["confluence_score"], "entry": round(entry, 4),
            "exit": round(exit_price, 4), "target_1": round(target, 4), "stop_loss": round(stop, 4),
            "outcome": outcome, "bars_held": holding_index - index, "gross_pnl_pct": round(gross_return, 4),
            "estimated_round_trip_cost_pct": round(round_trip_cost_pct, 4),
            "net_pnl_pct": round(gross_return - round_trip_cost_pct, 4),
        })
        next_available_index = holding_index + 1
        index = next_available_index

    result = summarize_trades(trades)
    result["threshold"] = threshold
    return result
