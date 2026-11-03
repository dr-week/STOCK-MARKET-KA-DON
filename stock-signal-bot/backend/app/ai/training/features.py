import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

FEATURE_NAMES = ("return_1", "return_3", "return_6", "range_pct", "volume_ratio")
_IST = ZoneInfo("Asia/Kolkata")
_LOOKBACK = 20


def _session_day(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).astimezone(_IST).date().isoformat()


def build_samples(
    candles: list[dict[str, Any]],
    horizon_bars: int = 15,
    cost_bps: float = 10.0,
) -> list[dict[str, Any]]:
    if horizon_bars < 1 or cost_bps < 0 or not math.isfinite(cost_bps):
        raise ValueError("horizon_bars must be positive and cost_bps finite and non-negative.")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candle in candles:
        grouped[candle["symbol"]].append(candle)

    samples = []
    for symbol, bars in grouped.items():
        bars.sort(key=lambda row: row["timestamp"])
        days = [_session_day(row["timestamp"]) for row in bars]
        for index in range(_LOOKBACK, len(bars) - horizon_bars):
            future_index = index + horizon_bars
            if days[index - _LOOKBACK] != days[index] or days[future_index] != days[index]:
                continue
            close = bars[index]["close"]
            if close <= 0:
                continue
            previous = [bars[index - step]["close"] for step in (1, 3, 6)]
            volumes = [bars[position]["volume"] for position in range(index - _LOOKBACK + 1, index + 1)]
            mean_volume = sum(volumes) / len(volumes)
            features = [
                close / previous[0] - 1,
                close / previous[1] - 1,
                close / previous[2] - 1,
                (bars[index]["high"] - bars[index]["low"]) / close,
                bars[index]["volume"] / mean_volume if mean_volume else 0.0,
            ]
            future_return = bars[future_index]["close"] / close - 1
            if not all(math.isfinite(value) for value in (*features, future_return)):
                continue
            threshold = cost_bps / 10_000
            label = 1 if future_return > threshold else -1 if future_return < -threshold else 0
            samples.append({
                "symbol": symbol,
                "session_date": days[index],
                "label_end_date": days[future_index],
                "features": features,
                "label": label,
                "forward_return": future_return,
            })
    return samples
