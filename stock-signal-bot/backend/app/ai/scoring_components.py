import re
from typing import Dict


def compute_win_probability(score: float) -> float:
    if score >= 0.72:
        return min(0.78, 0.60 + (score - 0.72) * 1.2)
    if score >= 0.58:
        return 0.48 + (score - 0.58) * 0.8
    if score >= 0.44:
        return 0.38 + (score - 0.44) * 0.7
    return max(0.20, score * 0.8)


def compute_expected_value(win_probability: float, average_reward_risk: float) -> float:
    return round(win_probability * average_reward_risk - (1.0 - win_probability), 2)


def classify_signal_quality(expected_value: float) -> str:
    if expected_value > 0.6:
        return "PREMIUM"
    if expected_value > 0.3:
        return "GOOD"
    if expected_value > 0.0:
        return "MARGINAL"
    return "SKIP"


def score_multi_timeframe(timeframe_alignment: Dict[str, str]) -> float:
    m15 = (timeframe_alignment.get("m15_trend") or "NEUTRAL").upper()
    h1 = (timeframe_alignment.get("h1_trend") or "NEUTRAL").upper()

    if m15 == h1 and m15 in {"BULLISH", "BEARISH"}:
        return 0.08
    if "BEARISH" in {m15, h1}:
        return -0.10
    return 0.0


def score_sector_regime(sector: str, sector_strengths: Dict[str, str]) -> float:
    if not sector or not sector_strengths:
        return 0.0

    value = sector_strengths.get(sector, "")
    value_upper = value.upper()
    if "STRONG" in value_upper:
        return 0.06
    if "BEARISH" in value_upper:
        return -0.06

    percentage_match = re.search(r"\(([+-]?\d+(?:\.\d+)?)%\)", value)
    if percentage_match and float(percentage_match.group(1)) < 0:
        return -0.06
    return 0.0
