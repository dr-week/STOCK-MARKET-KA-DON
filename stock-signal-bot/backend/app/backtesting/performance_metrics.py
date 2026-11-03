from typing import Any, Dict, List


def summarize_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    wins = sum(1 for trade in trades if trade["net_pnl_pct"] > 0)
    losses = sum(1 for trade in trades if trade["net_pnl_pct"] < 0)
    gross_profit = sum(max(0.0, trade["net_pnl_pct"]) for trade in trades)
    gross_loss = abs(sum(min(0.0, trade["net_pnl_pct"]) for trade in trades))
    equity = 1.0
    peak = 1.0
    max_drawdown_pct = 0.0
    for trade in trades:
        equity *= 1.0 + trade["net_pnl_pct"] / 100.0
        peak = max(peak, equity)
        if peak:
            max_drawdown_pct = max(max_drawdown_pct, (peak - equity) / peak * 100.0)

    count = len(trades)
    return {
        "total_signals": count,
        "wins": wins,
        "losses": losses,
        "breakeven": count - wins - losses,
        "win_rate_pct": round(wins / count * 100.0, 2) if count else 0.0,
        "avg_net_trade_pnl_pct": round(sum(t["net_pnl_pct"] for t in trades) / count, 4) if count else 0.0,
        "net_compounded_return_pct": round((equity - 1.0) * 100.0, 4),
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else (None if gross_profit == 0 else "inf"),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "trades": trades,
    }
