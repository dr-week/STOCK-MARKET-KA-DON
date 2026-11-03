from typing import Any, Dict, List, Optional

from app.departments.signal_risk.service import signal_risk_dep
from app.departments.technical_analysis.service import technical_dep

MIN_WARMUP_BARS = 30


def build_signal(
    bars: List[Dict[str, Any]],
    index: int,
    threshold: int,
    intelligence: Dict[str, Any],
    quality_filter_passed: bool = True,
) -> Optional[Dict[str, Any]]:
    """Evaluate one completed bar using only that bar and earlier observations."""
    history = bars[: index + 1]
    if len(history) < MIN_WARMUP_BARS:
        return None
    market_data = {
        "current_price": history[-1]["close"],
        "candles_5m": {
            field + "s": [bar[field] for bar in history]
            for field in ("open", "high", "low", "close", "volume")
        },
    }
    technicals = technical_dep.analyze(market_data)
    return signal_risk_dep.synthesize_decision(
        market_data=market_data,
        technicals=technicals,
        fundamentals={"quality_filter_passed": quality_filter_passed},
        intelligence=intelligence,
        min_confluence_score=threshold,
    )
