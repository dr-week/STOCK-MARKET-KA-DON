import logging
import threading
from datetime import datetime, time
from typing import Any, Callable, Dict, Optional

from app.market.sessions import IST

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 60
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def is_market_scan_time(now: Optional[datetime] = None) -> bool:
    local_now = now or datetime.now(IST)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=IST)
    local_now = local_now.astimezone(IST)
    return (
        local_now.weekday() < 5
        and MARKET_OPEN <= local_now.time().replace(tzinfo=None) < MARKET_CLOSE
    )


class AutomaticPaperRunner:
    def __init__(
        self,
        scan: Callable[[], Any],
        interval_seconds: int = SCAN_INTERVAL_SECONDS,
        is_scan_time: Callable[[], bool] = is_market_scan_time,
    ) -> None:
        self._scan = scan
        self._interval_seconds = interval_seconds
        self._is_scan_time = is_scan_time
        self._stop = threading.Event()
        self._state_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._last_scan_at: Optional[str] = None
        self._last_scan_error: Optional[str] = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="automatic-paper-trader",
            daemon=True,
        )
        self._thread.start()
        logger.info("Automatic paper-trading scanner started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)

    def status(self) -> Dict[str, Any]:
        with self._state_lock:
            return {
                "worker_running": self._thread is not None and self._thread.is_alive(),
                "last_scan_at": self._last_scan_at,
                "last_scan_error": self._last_scan_error,
            }

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._is_scan_time():
                attempted = False
                try:
                    attempted = self._scan() is not None
                except Exception as exc:
                    attempted = True
                    logger.exception("Continuous paper-trading market scan failed")
                    with self._state_lock:
                        self._last_scan_error = str(exc)
                else:
                    if attempted:
                        with self._state_lock:
                            self._last_scan_error = None
                finally:
                    if attempted:
                        with self._state_lock:
                            self._last_scan_at = datetime.now(IST).isoformat()
            self._stop.wait(self._interval_seconds)


def scan_market_universe() -> Any:
    from app.api.routes_scan import scan_if_due

    return scan_if_due()


paper_auto_runner = AutomaticPaperRunner(scan_market_universe)
