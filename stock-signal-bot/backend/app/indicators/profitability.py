"""Broker-aware intraday viability rules.

This module answers a narrow question: does the modeled move have enough
trend strength and range to cover Groww friction? It does not predict profit.
"""

from typing import Any


MIN_ADX = 20.0


def evaluate_intraday_profitability(
    risk_sizing: dict[str, Any],
    *,
    adx: float | None,
    atr_5m: float | None,
    is_candidate: bool,
) -> dict[str, Any]:
    """Attach an auditable trade gate to an existing risk calculation.

    ADX is used as a trend-strength filter. ATR is the movement filter because
    ADX alone does not measure how many rupees the stock is moving.
    """
    adx_available = isinstance(adx, (int, float)) and adx >= 0
    atr_available = isinstance(atr_5m, (int, float)) and atr_5m > 0
    trend_strength_passed = adx_available and adx >= MIN_ADX
    break_even = risk_sizing.get("break_even_move_per_share")
    movement_covers_costs = (
        atr_available and isinstance(break_even, (int, float)) and atr_5m >= break_even
    )
    target_net_positive = risk_sizing.get("expected_net_t1_inr", 0) > 0

    if not is_candidate:
        status = "WAIT — no active trade setup"
        eligible = False
    elif not adx_available:
        status = "WAIT — ADX is unavailable (warm-up incomplete)"
        eligible = False
    elif not atr_available:
        status = "WAIT — recent movement is unavailable"
        eligible = False
    elif not trend_strength_passed:
        status = f"DO NOT TRADE — ADX {adx:.1f} is below {MIN_ADX:.0f}"
        eligible = False
    elif not movement_covers_costs:
        status = "DO NOT TRADE — 5m range does not cover Groww friction"
        eligible = False
    elif not target_net_positive:
        status = "DO NOT TRADE — modeled Target 1 is not net profitable"
        eligible = False
    else:
        status = "TRADE FILTER PASSED — modeled edge covers costs"
        eligible = True

    return {
        **risk_sizing,
        "adx": adx,
        "atr_5m": atr_5m,
        "minimum_adx_threshold": MIN_ADX,
        "trend_strength_passed": trend_strength_passed,
        "movement_covers_costs": movement_covers_costs,
        "target_net_positive": target_net_positive,
        "profitability_eligible": eligible,
        "viability_status": status,
    }
