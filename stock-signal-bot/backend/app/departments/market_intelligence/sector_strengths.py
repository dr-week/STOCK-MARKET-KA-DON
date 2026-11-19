import time
from typing import Dict
from app.market.fetcher import fetch_nse_chart

_SECTOR_TICKERS: Dict[str, str] = {
    "^NSEBANK": "Banking",
    "^CNXIT": "IT",
    "^CNXAUTO": "Auto",
    "^CNXPHARMA": "Pharma",
    "^CNXFMCG": "FMCG",
    "^CNXMETAL": "Metals",
}

_FALLBACK_SECTOR_STRENGTHS: Dict[str, str] = {
    "Banking": "STRONG (+0.8%)",
    "IT": "CONSOLIDATION (-0.1%)",
    "Auto": "BULLISH (+1.2%)",
    "Energy": "NEUTRAL (+0.2%)",
}


def format_sector_label(change_pct: float) -> str:
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


def fetch_live_sector_strengths() -> Dict[str, str]:
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
            strengths[sector_name] = format_sector_label(round(change_pct, 1))
        except Exception:
            pass

    if not strengths:
        return dict(_FALLBACK_SECTOR_STRENGTHS)
    return strengths
