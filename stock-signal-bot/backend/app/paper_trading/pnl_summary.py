from typing import Any, Dict, Iterable, List


def _trade_stats(closed: List[Dict[str, Any]], opened: List[Dict[str, Any]]) -> Dict[str, Any]:
    realized = [float(trade["pnl"]) for trade in closed]
    wins = sum(1 for pnl in realized if pnl > 0)
    losses = sum(1 for pnl in realized if pnl < 0)
    notional = sum(float(trade["entry_price"]) * float(trade["qty"]) for trade in closed)
    total_realized = sum(realized)
    return {
        "attempted_trades": len(closed) + len(opened),
        "closed_trades": len(closed),
        "open_trades": len(opened),
        "wins": wins,
        "losses": losses,
        "breakeven": len(closed) - wins - losses,
        "win_rate_pct": round(wins / len(closed) * 100, 2) if closed else None,
        "realized_pnl": round(total_realized, 2),
        "entry_notional": round(notional, 2),
        "return_on_entry_notional_pct": round(total_realized / notional * 100, 4) if notional else None,
    }


def summarize(closed_trades: Iterable[Dict[str, Any]], open_trades: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    closed = list(closed_trades)
    opened = list(open_trades)
    realized = [float(trade["pnl"]) for trade in closed]
    unrealized = [float(trade["unrealized_pnl"]) for trade in opened]
    trade_count = len(realized)
    wins = sum(1 for pnl in realized if pnl > 0)
    automated_closed = [trade for trade in closed if trade["source"] == "AUTO"]
    automated_open = [trade for trade in opened if trade["source"] == "AUTO"]
    manual_closed = [trade for trade in closed if trade["source"] == "MANUAL"]
    manual_open = [trade for trade in opened if trade["source"] == "MANUAL"]
    return {
        "total_realized": round(sum(realized), 2),
        "total_unrealized": round(sum(unrealized), 2),
        "win_rate": round(wins / trade_count * 100, 2) if trade_count else 0.0,
        "trade_count": trade_count,
        "best_trade": round(max(realized, default=0.0), 2),
        "worst_trade": round(min(realized, default=0.0), 2),
        "automatic": _trade_stats(automated_closed, automated_open),
        "manual": _trade_stats(manual_closed, manual_open),
    }
