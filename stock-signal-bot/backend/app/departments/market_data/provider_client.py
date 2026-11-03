import json
import os
import urllib.request
from typing import Any, Dict, Optional

from app.departments.market_data.replay_harness import ReplayMarketDataProvider


def fetch_chart(ticker: str, interval: str, range_param: str) -> Optional[Dict[str, Any]]:
    if os.getenv("SMKD_DATA_MODE") == "replay":
        return ReplayMarketDataProvider(mode="replay").fetch_replay_chart(ticker)

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_param}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode())
            results = data.get("chart", {}).get("result")
            if results:
                return results[0]
    except Exception:
        return None
    return None
