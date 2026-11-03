"""Leakage-aware rolling-origin evaluation against a persistence baseline."""

import math
from collections.abc import Callable, Sequence

ForecastBatch = Callable[[list[list[float]], int], Sequence[float]]


def evaluate_forecaster(
    closes: Sequence[float],
    predict: ForecastBatch,
    context_length: int = 256,
    horizon: int = 3,
    max_windows: int = 50,
) -> dict[str, float | int | str]:
    if context_length < 2 or horizon < 1 or max_windows < 2:
        raise ValueError("context_length >= 2, horizon >= 1, and max_windows >= 2 are required")
    if any(not math.isfinite(value) or value <= 0 for value in closes):
        raise ValueError("closes must be finite, positive prices")

    holdout_start = int(len(closes) * 0.8)
    origins = list(range(max(context_length, holdout_start), len(closes) - horizon + 1, horizon))
    origins = origins[-max_windows:]
    if len(origins) < 2:
        raise ValueError("insufficient history for at least two non-overlapping holdout windows")

    contexts = [list(closes[index - context_length:index]) for index in origins]
    actuals = [float(closes[index + horizon - 1]) for index in origins]
    forecasts = list(predict(contexts, horizon))
    if len(forecasts) != len(origins):
        raise ValueError("forecaster must return one terminal price per context")
    if any(not math.isfinite(value) or value <= 0 for value in forecasts):
        raise ValueError("forecaster returned a non-finite or non-positive price")

    naive_mae = sum(abs(closes[index - 1] - actual) for index, actual in zip(origins, actuals)) / len(origins)
    model_mae = sum(abs(prediction - actual) for prediction, actual in zip(forecasts, actuals)) / len(origins)
    return {
        "status": "beats_naive_mae" if model_mae < naive_mae else "does_not_beat_naive_mae",
        "holdout_fraction": 0.2,
        "windows": len(origins),
        "context_length": context_length,
        "horizon_bars": horizon,
        "model_mae": model_mae,
        "naive_mae": naive_mae,
        "warning": "Offline research only; one symbol/provider sample is not a trading edge or calibrated probability.",
    }
