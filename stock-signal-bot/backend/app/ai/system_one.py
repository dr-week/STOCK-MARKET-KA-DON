from typing import Any, Dict, Optional

from app.ai.scoring_components import (
    classify_signal_quality,
    compute_expected_value,
    compute_win_probability,
    score_multi_timeframe,
    score_sector_regime,
)
from app.ai.system_one_rules import score_intraday_factors


class SystemOneDecisionModel:
    """Compatibility facade for the deterministic SystemOne scoring rules."""

    def _compute_win_probability(self, score: float) -> float:
        return compute_win_probability(score)

    def _compute_expected_value(self, win_prob: float, avg_rr: float) -> float:
        return compute_expected_value(win_prob, avg_rr)

    def _compute_signal_quality(self, ev: float) -> str:
        return classify_signal_quality(ev)

    def score_multi_timeframe(self, timeframe_alignment: Dict[str, str]) -> float:
        return score_multi_timeframe(timeframe_alignment)

    def score_sector_regime(self, sector: str, sector_strengths: Dict[str, str]) -> float:
        return score_sector_regime(sector, sector_strengths)

    def evaluate(
        self,
        symbol: str,
        price: float,
        vwap: float,
        rsi: float,
        ema_9: float,
        ema_21: float,
        atr: float,
        change_pct: float,
        news_sentiment: str,
        market_phase: str,
        adx: float = 20.0,
        relative_volume: float = 1.0,
        support: Optional[float] = None,
        resistance: Optional[float] = None,
        trend_strength: float = 0.5,
        volume_confirmation: bool = False,
        structure_bias: str = "NEUTRAL",
        market_regime: str = "SIDEWAYS",
        avg_rr: float = 2.5,
        m15_trend: str = "NEUTRAL",
        h1_trend: str = "NEUTRAL",
        sector: str = "",
        sector_strengths: Optional[Dict[str, str]] = None,
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        score, rules_fired = score_intraday_factors(
            price=price,
            vwap=vwap,
            rsi=rsi,
            ema_9=ema_9,
            ema_21=ema_21,
            change_pct=change_pct,
            news_sentiment=news_sentiment,
            market_phase=market_phase,
            adx=adx,
            relative_volume=relative_volume,
            support=support,
            resistance=resistance,
            trend_strength=trend_strength,
            volume_confirmation=volume_confirmation,
            structure_bias=structure_bias,
            market_regime=market_regime,
            m15_trend=m15_trend,
            h1_trend=h1_trend,
            sector=sector,
            sector_strengths=sector_strengths or {},
        )

        if score >= 0.72:
            verdict, action = "STRONG_BUY_CONFLUENCE", "HIGH PROBABILITY LONG"
        elif score >= 0.58:
            verdict, action = "MODERATE_BUY", "WATCH FOR PULLBACK TO VWAP"
        elif score <= 0.32:
            verdict, action = "STRONG_SELL_CONFLUENCE", "HIGH PROBABILITY SHORT"
        elif score <= 0.44:
            verdict, action = "MODERATE_SELL", "WATCH FOR BREAKDOWN"
        else:
            verdict, action = "CHOP_NEUTRAL", "NO EDGE / WAIT"

        win_probability = round(compute_win_probability(score), 4)
        expected_value = compute_expected_value(win_probability, avg_rr)
        return {
            "ai_score": score,
            "ai_verdict": verdict,
            "recommended_action": action,
            "system_one_rules": rules_fired,
            "win_probability": win_probability,
            "expected_value": expected_value,
            "signal_quality": classify_signal_quality(expected_value),
        }


decision_engine = SystemOneDecisionModel()
