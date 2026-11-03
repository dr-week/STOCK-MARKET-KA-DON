"""Run an offline Chronos-Bolt benchmark on one archived provider series."""

import argparse
import json

from app.research.chronos_bolt import build_predictor
from app.research.forecast_benchmark import evaluate_forecaster
from app.research.market_history import load_close_series


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--provider", required=True, help="Exact archive provider ID; sources are never mixed.")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--context", type=int, default=256)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--windows", type=int, default=50)
    parser.add_argument("--device", choices=("cpu", "cuda", "mps"), default="cpu")
    args = parser.parse_args()

    timestamps, closes = load_close_series(args.symbol, args.interval, args.provider)
    report = evaluate_forecaster(
        closes,
        build_predictor(device=args.device),
        context_length=args.context,
        horizon=args.horizon,
        max_windows=args.windows,
    )
    report.update({
        "symbol": args.symbol.upper(),
        "provider": args.provider,
        "interval": args.interval,
        "first_timestamp": timestamps[0],
        "last_timestamp": timestamps[-1],
        "model": "amazon/chronos-bolt-small",
    })
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
