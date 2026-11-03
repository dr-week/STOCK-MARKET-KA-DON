"""Optional local Chronos-Bolt inference; weights are downloaded on first use."""

from typing import Sequence

from app.research.forecast_benchmark import ForecastBatch


def build_predictor(
    model_id: str = "amazon/chronos-bolt-small",
    device: str = "cpu",
) -> ForecastBatch:
    try:
        import torch
        from chronos import BaseChronosPipeline
    except ImportError as error:
        raise RuntimeError(
            "Install the optional chronos-forecasting and PyTorch packages to run this research benchmark."
        ) from error

    pipeline = BaseChronosPipeline.from_pretrained(
        model_id,
        device_map=device,
        torch_dtype=torch.float32,
    )

    def predict(contexts: list[list[float]], horizon: int) -> Sequence[float]:
        context = torch.tensor(contexts, dtype=torch.float32)
        forecasts = pipeline.predict(context=context, prediction_length=horizon)
        median_quantile = forecasts.shape[1] // 2
        return forecasts[:, median_quantile, -1].detach().cpu().tolist()

    return predict
