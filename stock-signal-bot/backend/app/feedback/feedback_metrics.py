from typing import Any, Dict, Iterable


def accuracy(rows: Iterable[Dict[str, Any]], total_signals: int) -> Dict[str, Any]:
    rows = list(rows)
    wins = [row["confluence_score"] for row in rows if row["outcome"] == "WIN"]
    losses = [row["confluence_score"] for row in rows if row["outcome"] == "LOSS"]
    decided = len(wins) + len(losses)
    average = lambda values: round(sum(values) / len(values), 2) if values else 0.0
    return {
        "total_signals": total_signals,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / decided * 100, 2) if decided else 0.0,
        "avg_confluence_on_wins": average(wins),
        "avg_confluence_on_losses": average(losses),
    }


def calibration(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, int]] = {}
    for row in rows:
        signal_type = row["signal_type"]
        grouped.setdefault(signal_type, {"wins": 0, "losses": 0})
        if row["outcome"] == "WIN":
            grouped[signal_type]["wins"] += 1
        elif row["outcome"] == "LOSS":
            grouped[signal_type]["losses"] += 1
    return {
        signal_type: {
            **counts,
            "win_rate_pct": round(counts["wins"] / (counts["wins"] + counts["losses"]) * 100, 2)
            if counts["wins"] + counts["losses"] else 0.0,
        }
        for signal_type, counts in grouped.items()
    }
