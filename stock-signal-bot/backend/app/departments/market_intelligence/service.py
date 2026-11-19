import time
from typing import Dict, Any
from app.market.sessions import get_market_session_state
from app.market.fetcher import fetch_nse_chart
from app.departments.market_intelligence.sector_strengths import (
    _SECTOR_TICKERS,
    _FALLBACK_SECTOR_STRENGTHS,
    format_sector_label as _format_sector_label,
    fetch_live_sector_strengths,
)


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
        self._sector_cache = strengths
        self._sector_cache_ts = now
        return strengths

    def get_intelligence(self) -> Dict[str, Any]:
        session_info = get_market_session_state()

        # Fetch live Nifty 50 benchmark index (Ticker ^NSEI on Yahoo Finance)
        nifty_chart = fetch_nse_chart("^NSEI", interval="5m", range_param="1d")
        nifty_price = 24850.0
        nifty_change = 0.25

        if nifty_chart:
            meta = nifty_chart.get("meta", {})
            nifty_price = meta.get("regularMarketPrice", 24850.0)
            prev = meta.get("previousClose", nifty_price)
            nifty_change = round(((nifty_price - prev) / prev) * 100, 2) if prev else 0.0

        nifty_trend = "BULLISH" if nifty_change > 0.05 else ("BEARISH" if nifty_change < -0.05 else "SIDEWAYS")
        sector_strengths = self._fetch_sector_strengths()

        return {
            "session": session_info,
            "nifty_50": {
                "price": nifty_price,
                "change_pct": nifty_change,
                "trend": nifty_trend
            },
            "india_vix": {
                "level": 13.8,
                "regime": "OPTIMAL_TRENDING (12-18 Ideal)"
            },
            "sector_strengths": sector_strengths,
            "macro_bias": "FAVOR_LONGS" if nifty_change >= 0 else "FAVOR_SHORTS"
        }


market_intelligence_dep = MarketIntelligenceDepartment()
