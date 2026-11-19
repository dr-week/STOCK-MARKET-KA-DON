from typing import Any, Dict, List, Optional

def find_flag_pattern(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    pattern_builder,
) -> Optional[Dict[str, Any]]:
    count = len(closes)
    for consolidation_size in range(min(8, count - 4), 2, -1):
        for impulse_size in range(min(5, count - consolidation_size - 1), 2, -1):
            impulse_start = count - consolidation_size - impulse_size - 1
            impulse_end = count - consolidation_size - 1
            baseline_start = max(0, impulse_start - 20)
            baseline_ranges = [
                highs[index] - lows[index]
                for index in range(baseline_start, impulse_start)
            ]
            if len(baseline_ranges) < 3:
                continue
            average_range = sum(baseline_ranges) / len(baseline_ranges)
            pole = closes[impulse_end] - closes[impulse_start]
            if average_range <= 0 or abs(pole) < 2 * average_range:
                continue

            flag_start = count - consolidation_size
            flag_closes = closes[flag_start:]
            flag_highs = highs[flag_start:]
            flag_lows = lows[flag_start:]
            slope = (flag_closes[-1] - flag_closes[0]) / (consolidation_size - 1)
            flag_range = max(flag_highs) - min(flag_lows)
            if flag_range > max(abs(pole) * 0.75, average_range * 2):
                continue

            if pole > 0:
                retracement = (closes[impulse_end] - min(flag_lows)) / pole
                if slope >= -0.15 * average_range or not 0.15 <= retracement <= 0.65:
                    continue
                return pattern_builder(
                    "Bull flag-like pullback",
                    "BULL_FLAG",
                    "BULLISH",
                    "A sharp rise is followed by a short, narrowing pullback. This is only a possible continuation setup; confirmation requires a completed 5-minute close above the pullback high, preferably with expanding volume.",
                    max(flag_highs),
                    min(flag_lows),
                    "forming",
                )

            retracement = (max(flag_highs) - closes[impulse_end]) / abs(pole)
            if slope <= 0.15 * average_range or not 0.15 <= retracement <= 0.65:
                continue
            return pattern_builder(
                "Bear flag-like rally",
                "BEAR_FLAG",
                "BEARISH",
                "A sharp decline is followed by a short, narrowing rally. This is only a possible continuation setup; confirmation requires a completed 5-minute close below the pullback low, preferably with expanding volume.",
                min(flag_lows),
                max(flag_highs),
                "forming",
            )
    return None
