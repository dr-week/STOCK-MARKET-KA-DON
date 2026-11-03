import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import joblib

from app.ai.training.data import load_candles
from app.ai.training.features import build_samples
from app.ai.training.trainer import train_time_split


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train an experimental, offline stock model.")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parents[2] / "data" / "market_history.db"))
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--provider", required=True, help="Train one source at a time; e.g. groww_trade_api.")
    parser.add_argument("--horizon-bars", type=int, default=15)
    parser.add_argument("--cost-bps", type=float, default=10.0, help="Estimated round-trip cost threshold.")
    parser.add_argument("--min-sessions", type=int, default=60)
    parser.add_argument("--model-out", help="Optional path for an experimental artifact; never used in production.")
    args = parser.parse_args(argv)
    if args.min_sessions < 2:
        parser.error("--min-sessions must be at least 2.")

    try:
        candles = load_candles(args.db, args.interval, args.provider)
        samples = build_samples(candles, args.horizon_bars, args.cost_bps)
        sessions = len({sample["session_date"] for sample in samples})
        if sessions < args.min_sessions:
            print(json.dumps({
                "status": "NOT_READY",
                "provider": args.provider,
                "interval": args.interval,
                "candles": len(candles),
                "samples": len(samples),
                "sessions": sessions,
                "required_sessions": args.min_sessions,
                "reason": "Collect a broader, clean history before fitting a candidate model.",
            }, indent=2))
            return 2
        model, metrics = train_time_split(samples, args.cost_bps)
        if args.model_out:
            output = Path(args.model_out)
            output.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump({
                "model": model,
                "provider": args.provider,
                "interval": args.interval,
                "horizon_bars": args.horizon_bars,
                "cost_bps": args.cost_bps,
                "trained_at": datetime.now(timezone.utc).isoformat(),
            }, output)
        print(json.dumps({
            "status": "RESEARCH_ONLY",
            "provider": args.provider,
            "interval": args.interval,
            "candles": len(candles),
            "samples": len(samples),
            "sessions": sessions,
            "artifact": args.model_out,
            "metrics": metrics,
        }, indent=2))
        return 0
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(2, f"Training unavailable: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
