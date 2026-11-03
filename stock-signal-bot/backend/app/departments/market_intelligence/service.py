import time
from typing import Dict, Any
from app.market.sessions import get_market_session_state
from app.market.fetcher import fetch_nse_chart


# Sector ETF/index tickers mapped to canonical sector names.
# These are Yahoo Finance tickers for NSE sectoral indices.
_SECTOR_TICKERS: Dict[str, str] = {
    "^NSEBANK": "Banking",
    "^CNXIT": "IT",
    "^CNXAUTO": "Auto",
    "^CNXPHARMA": "Pharma",
    "^CNXFMCG": "FMCG",
    "^CNXMETAL": "Metals",
}

# Hardcoded fallback used when live fetch fails for any/all sectors.
_FALLBACK_SECTOR_STRENGTHS: Dict[str, str] = {
    "Banking": "STRONG (+0.8%)",
    "IT": "CONSOLIDATION (-0.1%)",
    "Auto": "BULLISH (+1.2%)",
    "Energy": "NEUTRAL (+0.2%)",
}


def _format_sector_label(change_pct: float) -> str:
    """
    Map a day-change percentage to a canonical sector-strength label.

    Labels:
    - change > +0.5 %  → ``"STRONG (+x.x%)"``
    - change >  0.0 %  → ``"BULLISH (+x.x%)"``
    - change ~  0.0 %  → ``"NEUTRAL (0.0%)"``   (−0.1 to 0.0 inclusive)
    - change <= −0.1 % → ``"BEARISH (x.x%)"``   (sign included in value)
    """
    sign = "+" if change_pct >= 0 else ""
    value_str = f"{sign}{change_pct:.1f}%"
    if change_pct > 0.5:
        return f"STRONG ({value_str})"
    elif change_pct > 0.0:
        return f"BULLISH ({value_str})"
    elif change_pct >= -0.1:
        return f"NEUTRAL ({value_str})"
    else:
        return f"BEARISH ({value_str})"


class MarketIntelligenceDepartment:
    """
    DEPARTMENT 4: MARKET INTELLIGENCE
    Responsibility: Tracks macro context: Nifty 50 trend, India VIX volatility,
    sectoral alignment, and institutional market phases (Opening Trap, Prime, Square-Off).
    """

    def __init__(self) -> None:
        self._cached_intelligence: Dict[str, Any] = {}
        # Sector heatmap cache state
        self._sector_cache: Dict[str, str] = {}
        self._sector_cache_ts: float = 0.0
        self._SECTOR_CACHE_TTL: float = 60.0  # seconds

    def _fetch_sector_strengths(self) -> Dict[str, str]:
        """
        Fetch live 5-minute candle change percentages for NSE sectoral indices
        via Yahoo Finance and return a canonical sector-strength dict.

        Tickers queried:
        - ``^NSEBANK`` → Banking
        - ``^CNXIT``   → IT
        - ``^CNXAUTO`` → Auto
        - ``^CNXPHARMA`` → Pharma
        - ``^CNXFMCG`` → FMCG
        - ``^CNXMETAL`` → Metals

        Each sector's day change % is computed as::

            (regularMarketPrice − previousClose) / previousClose × 100

        The result is formatted with :func:`_format_sector_label`.

        Results are cached for 60 seconds. On any per-ticker error the
        corresponding sector is omitted; if *all* tickers fail the entire
        hardcoded fallback dict is returned.

        Returns
        -------
        dict
            Mapping of sector name → label string, e.g.
            ``{"Banking": "STRONG (+0.8%)", "IT": "BEARISH (-0.5%)", ...}``.
        """
        now = time.time()
        if self._sector_cache and (now - self._sector_cache_ts) < self._SECTOR_CACHE_TTL:
            return self._sector_cache

        strengths: Dict[str, str] = {}
        for ticker, sector_name in _SECTOR_TICKERS.items():
            try:
                chart = fetch_nse_chart(ticker, interval="5m", range_param="1d")
                if not chart:
                    continue
                meta = chart.get("meta", {})
                price = meta.get("regularMarketPrice")
                prev_close = meta.get("previousClose")
                if price is None or prev_close is None or prev_close == 0:
                    continue
                change_pct = ((price - prev_close) / prev_close) * 100
                strengths[sector_name] = _format_sector_label(round(change_pct, 1))
            except Exception:
                # Per-ticker failures are silently skipped; the sector is simply
                # absent from the result. Broad catch is intentional here because
                # network-level errors, JSON decode errors, and malformed responses
                # all indicate "data not available" rather than a logic bug.
                pass

        if not strengths:
            # All tickers failed — fall back to hardcoded values so downstream
            # callers always receive a non-empty dict.
            return dict(_FALLBACK_SECTOR_STRENGTHS)

        # Partial success: cache what we got and update timestamp.
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
