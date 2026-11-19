import time
from typing import Dict, Any, Optional
from app.market.sessions import get_market_session_state
from app.market.fetcher import fetch_nse_chart
from app.departments.market_intelligence.sector_strengths import (
    _SECTOR_TICKERS,
    format_sector_label as _format_sector_label,
    fetch_live_sector_strengths,
)


def _classify_vix_regime(level: Optional[float]) -> str:
    if level is None:
        return "UNAVAILABLE"
    if level < 12.0:
        return "LOW_VOLATILITY (<12)"
    if level <= 18.0:
        return "OPTIMAL_TRENDING (12-18 Ideal)"
    if level <= 24.0:
        return "ELEVATED_VOLATILITY (18-24)"
    return "HIGH_RISK (>24)"


class MarketIntelligenceDepartment:
    """
    DEPARTMENT 4: MARKET INTELLIGENCE
    Responsibility: Tracks macro context: Nifty 50 trend, India VIX volatility,
    sectoral alignment, and institutional market phases (Opening Trap, Prime, Square-Off).
    """

    def __init__(self) -> None:
        self._cached_intelligence: Dict[str, Any] = {}
        self._sector_cache: Dict[str, str] = {}
        self._sector_cache_ts: float = 0.0
        self._SECTOR_CACHE_TTL: float = 60.0

    def _fetch_sector_strengths(self) -> Dict[str, str]:
        now = time.time()
        if self._sector_cache and (now - self._sector_cache_ts) < self._SECTOR_CACHE_TTL:
            return self._sector_cache

        strengths = fetch_live_sector_strengths()
        if strengths:
            self._sector_cache = strengths
            self._sector_cache_ts = now
        return strengths

    def get_intelligence(self) -> Dict[str, Any]:
        session_info = get_market_session_state()

        nifty_chart = fetch_nse_chart("^NSEI", interval="5m", range_param="1d")
        nifty_price: Optional[float] = None
        nifty_change: Optional[float] = None
        if nifty_chart:
            meta = nifty_chart.get("meta", {})
            nifty_price = meta.get("regularMarketPrice")
            prev = meta.get("previousClose")
            if nifty_price is not None and prev:
                nifty_change = round(((nifty_price - prev) / prev) * 100, 2)

        if nifty_change is None:
            nifty_trend = "UNAVAILABLE"
            macro_bias = "NEUTRAL"
        else:
            nifty_trend = "BULLISH" if nifty_change > 0.05 else ("BEARISH" if nifty_change < -0.05 else "SIDEWAYS")
            macro_bias = "FAVOR_LONGS" if nifty_change >= 0 else "FAVOR_SHORTS"

        vix_chart = fetch_nse_chart("^INDIAVIX", interval="5m", range_param="1d")
        vix_level: Optional[float] = None
        if vix_chart:
            raw_vix = vix_chart.get("meta", {}).get("regularMarketPrice")
            if raw_vix is not None:
                vix_level = round(float(raw_vix), 2)

        sector_strengths = self._fetch_sector_strengths()

        return {
            "session": session_info,
            "nifty_50": {
                "price": nifty_price,
                "change_pct": nifty_change,
                "trend": nifty_trend,
                "status": "available" if nifty_price is not None else "unavailable",
            },
            "india_vix": {
                "level": vix_level,
                "regime": _classify_vix_regime(vix_level),
                "status": "available" if vix_level is not None else "unavailable",
            },
            "sector_strengths": sector_strengths,
            "macro_bias": macro_bias,
        }


market_intelligence_dep = MarketIntelligenceDepartment()
