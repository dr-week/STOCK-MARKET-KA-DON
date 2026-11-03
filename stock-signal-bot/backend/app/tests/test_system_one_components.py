from app.ai.scoring_components import (
    classify_signal_quality,
    compute_expected_value,
    compute_win_probability,
    score_multi_timeframe,
    score_sector_regime,
)


def test_score_summary_components_keep_current_piecewise_boundaries():
    assert compute_win_probability(0.72) == 0.6
    assert compute_win_probability(0.58) == 0.48
    assert compute_win_probability(0.44) == 0.38
    assert compute_expected_value(0.6, 2.5) == 1.1
    assert classify_signal_quality(0.61) == "PREMIUM"
    assert classify_signal_quality(0.3) == "MARGINAL"
    assert classify_signal_quality(0.0) == "SKIP"


def test_multi_timeframe_and_sector_components_keep_existing_adjustments():
    assert score_multi_timeframe({"m15_trend": "BULLISH", "h1_trend": "BULLISH"}) == 0.08
    assert score_multi_timeframe({"m15_trend": "BEARISH", "h1_trend": "NEUTRAL"}) == -0.10
    assert score_multi_timeframe({"m15_trend": "NEUTRAL", "h1_trend": "NEUTRAL"}) == 0
    assert score_sector_regime("IT", {"IT": "STRONG (+1.2%)"}) == 0.06
    assert score_sector_regime("IT", {"IT": "BULLISH (-0.5%)"}) == -0.06
    assert score_sector_regime("IT", {"IT": "NEUTRAL (+0.2%)"}) == 0
