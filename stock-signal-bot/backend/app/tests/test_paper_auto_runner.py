import threading
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.market.sessions import IST
from app.api import routes_scan
from app.paper_trading.auto_runner import AutomaticPaperRunner, is_market_scan_time


class TestAutomaticPaperRunner(unittest.TestCase):
    def test_scans_during_weekday_market_hours_in_ist(self):
        self.assertTrue(is_market_scan_time(datetime(2026, 11, 3, 10, 0, tzinfo=IST)))
        self.assertTrue(is_market_scan_time(datetime(2026, 11, 3, 15, 29, tzinfo=IST)))

    def test_does_not_scan_outside_market_hours_or_on_weekends(self):
        for now in (
            datetime(2026, 11, 3, 9, 14, tzinfo=IST),
            datetime(2026, 11, 3, 15, 30, tzinfo=IST),
            datetime(2026, 11, 7, 10, 0, tzinfo=IST),
        ):
            with self.subTest(now=now):
                self.assertFalse(is_market_scan_time(now))

    def test_runner_scans_until_shutdown_and_tracks_status(self):
        scanned = threading.Event()

        def scan():
            scanned.set()
            return True

        runner = AutomaticPaperRunner(
            scan=scan,
            interval_seconds=1,
            is_scan_time=lambda: True,
        )

        runner.start()
        self.assertTrue(scanned.wait(timeout=2))
        runner.stop()

        status = runner.status()
        self.assertFalse(status["worker_running"])
        self.assertIsNotNone(status["last_scan_at"])
        self.assertIsNone(status["last_scan_error"])

    def test_runner_logs_scan_failure_in_status_and_keeps_running(self):
        attempts = 0
        recovered = threading.Event()

        def scan():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("provider unavailable")
            recovered.set()
            return True

        runner = AutomaticPaperRunner(
            scan=scan,
            interval_seconds=0.01,
            is_scan_time=lambda: True,
        )
        runner.start()
        try:
            self.assertTrue(recovered.wait(timeout=2))
        finally:
            runner.stop()

        self.assertGreaterEqual(attempts, 2)
        self.assertIsNone(runner.status()["last_scan_error"])

    def test_background_scan_skips_recent_dashboard_scan(self):
        with patch.object(routes_scan, "_LAST_SCAN_MONOTONIC", 100.0), \
             patch.object(routes_scan.time, "monotonic", return_value=110.0), \
             patch.object(routes_scan, "_scan_all") as scan:
            self.assertIsNone(routes_scan.scan_if_due())
        scan.assert_not_called()

    def test_background_scan_runs_when_no_recent_dashboard_scan_exists(self):
        with patch.object(routes_scan, "_LAST_SCAN_MONOTONIC", 100.0), \
             patch.object(routes_scan.time, "monotonic", return_value=200.0), \
             patch.object(routes_scan, "_scan_all", return_value={"count": 1}) as scan:
            self.assertEqual(routes_scan.scan_if_due(), {"count": 1})
        scan.assert_called_once()

    def test_application_lifespan_starts_and_stops_paper_runner(self):
        with patch("app.main.paper_auto_runner.start") as start, \
             patch("app.main.paper_auto_runner.stop") as stop:
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").status_code, 200)

        start.assert_called_once()
        stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
