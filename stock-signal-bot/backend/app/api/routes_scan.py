import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query, HTTPException, status

from app.core.config import TRACKED_UNIVERSE, ACCOUNT_CAPITAL
from app.departments.market_intelligence.service import market_intelligence_dep
from app.db.database import record_analysis_tree
from app.paper_trading.automation import paper_automation
from app.api.scan_request import normalize_symbol
from app.api.scan_orchestrator import process_unified_stock

router = APIRouter()
logger = logging.getLogger(__name__)
_SCAN_LOCK = threading.Lock()
_LAST_SCAN_MONOTONIC = 0.0
BACKGROUND_SCAN_MIN_AGE_SECONDS = 30


@router.get("/overview")
def get_overview():
    """Returns top-level market overview and intelligence."""
    return market_intelligence_dep.get_intelligence()


@router.get("/scan")
def scan_all(capital: float = Query(ACCOUNT_CAPITAL)):
    """Runs parallel scan through all departments with partial failure resilience."""
    global _LAST_SCAN_MONOTONIC
    with _SCAN_LOCK:
        try:
            return _scan_all(capital)
        finally:
            _LAST_SCAN_MONOTONIC = time.monotonic()


def scan_if_due() -> Optional[Dict[str, Any]]:
    """Run a background scan only if the dashboard has not scanned recently."""
    global _LAST_SCAN_MONOTONIC
    if not _SCAN_LOCK.acquire(blocking=False):
        return None
    try:
        if time.monotonic() - _LAST_SCAN_MONOTONIC < BACKGROUND_SCAN_MIN_AGE_SECONDS:
            return None
        try:
            return _scan_all(ACCOUNT_CAPITAL)
        finally:
            _LAST_SCAN_MONOTONIC = time.monotonic()
    finally:
        _SCAN_LOCK.release()


def _scan_all(capital: float) -> Dict[str, Any]:
    """Run one complete market scan and process virtual paper orders."""
    intelligence = market_intelligence_dep.get_intelligence()
    failed_symbols: List[str] = []

    def _safe_process(s: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            res = process_unified_stock(s, intelligence, capital=capital)
            if res is None:
                failed_symbols.append(s["symbol"])
            return res
        except Exception:
            logger.exception("Scan analysis failed for %s", s["symbol"])
            failed_symbols.append(s["symbol"])
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        raw_results = list(executor.map(_safe_process, TRACKED_UNIVERSE))

    results = [r for r in raw_results if r is not None]

    if not results and TRACKED_UNIVERSE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data unavailable for all {len(TRACKED_UNIVERSE)} tracked symbols",
        )

    try:
        record_analysis_tree(
            market_phase=intelligence["session"]["phase"],
            ist_time=intelligence["session"]["ist_time"],
            stocks_data=results,
        )
    except Exception as e:
        print(f"[DB Warning]: {e}")

    results.sort(key=lambda x: (x.get("signal_decision", {}).get("confluence_score", 0)), reverse=True)
    automation_result = {"enabled": True, "opened": 0, "closed": 0, "skipped": 0}
    try:
        automation_result = paper_automation.process_scan_results(results)
    except Exception:
        logger.exception("Automatic paper-trade scan processing failed")

    return {
        "intelligence": intelligence,
        "count": len(results),
        "results": results,
        "failed_symbols": failed_symbols,
        "is_partial": len(failed_symbols) > 0,
        "paper_automation": automation_result,
    }


@router.get("/stock/{symbol}")
def get_single_stock(symbol: str, capital: float = Query(ACCOUNT_CAPITAL)):
    """Full analysis for a single stock."""
    try:
        sym = normalize_symbol(symbol)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    stock = next((s for s in TRACKED_UNIVERSE if s["symbol"] == sym), {"symbol": sym, "name": sym, "sector": "NSE", "groww": sym.lower()})
    intelligence = market_intelligence_dep.get_intelligence()
    result = process_unified_stock(stock, intelligence, capital=capital)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data unavailable for symbol {sym}",
        )
    return result
