"""
AI Agent Evaluation and Safeguard Benchmark Suite.
Cross-platform implementation of regression eval scenarios testing agent safeguards,
duplicate detection, circuit breakers, task checkpoints, and market data integrity.
"""

import time
import json
from typing import Dict, Any, List

from scripts.dev.harness.detector import DuplicateDetector
from scripts.dev.harness.doctor import EnvironmentDoctor
from scripts.dev.harness.integrity_validator import MarketDataIntegrityValidator
from scripts.dev.departments.tasks.storage import init_db
from scripts.dev.departments.tasks.state import create_task, get_task, transition_task
from scripts.dev.departments.tasks.recovery import record_incident


class AgentEvaluationHarness:
    """Executes agent safeguard evals and produces measurable pass/fail metrics."""

    def __init__(self, repo_root: str = None):
        self.repo_root = repo_root
        self.detector = DuplicateDetector(repo_root)
        self.doctor = EnvironmentDoctor(repo_root)
        self.validator = MarketDataIntegrityValidator(repo_root)
        self.report: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "passed": 0,
            "failed": 0,
            "tests": [],
        }

    def run_eval(self, name: str, test_fn) -> bool:
        try:
            passed, detail = test_fn()
            if passed:
                self.report["passed"] += 1
                self.report["tests"].append({"name": name, "status": "PASS", "detail": detail})
                return True
            else:
                self.report["failed"] += 1
                self.report["tests"].append({"name": name, "status": "FAIL", "error": detail})
                return False
        except Exception as e:
            self.report["failed"] += 1
            self.report["tests"].append({"name": name, "status": "ERROR", "error": str(e)})
            return False

    def run_suite(self) -> Dict[str, Any]:
        init_db()

        # Eval 1: Duplicate Component Detection on existing capability
        def test_duplicate():
            res = self.detector.check("SystemOne")
            has_files = len(res["files_found"]) > 0
            has_symbols = len(res["symbols_found"]) > 0
            is_valid = res["recommendation"] in {"EXTEND_EXISTING", "REPAIR_OR_EXTEND_EXISTING"}
            if not (has_files or has_symbols) or not is_valid:
                return False, f"Expected duplicate detection to find matches. Found files: {res['files_found']}, symbols: {res['symbols_found']}"
            return True, f"Recommendation: {res['recommendation']}, Found {len(res['files_found'])} file(s), {len(res['symbols_found'])} symbol(s)"

        self.run_eval("Duplicate Component Detection on SystemOne", test_duplicate)

        # Eval 2: Task Transaction Lifecycle Checkpoint
        def test_task_lifecycle():
            task_id = f"EVAL-HARNESS-{int(time.time()*1000)}"
            create_task(task_id, "Harness Lifecycle Test", ["AGENTS.md"], ["Verified"])
            t1 = get_task(task_id)
            if not t1 or t1["status"] != "READY":
                return False, f"Initial state expected READY, got {t1.get('status') if t1 else 'None'}"
            transition_task(task_id, "IN_PROGRESS", reason="Execution started")
            t2 = get_task(task_id)
            if not t2 or t2["status"] != "IN_PROGRESS":
                return False, f"State expected IN_PROGRESS, got {t2.get('status') if t2 else 'None'}"
            return True, f"Lifecycle verified from READY to IN_PROGRESS for {task_id}"

        self.run_eval("Task Transaction Checkpoint Lifecycle", test_task_lifecycle)

        # Eval 3: Failure Fingerprint and Advisory Circuit Breaker
        def test_circuit_breaker():
            task_id = f"EVAL-CB-{int(time.time()*1000)}"
            create_task(task_id, "Circuit Breaker Test", [], [])
            transition_task(task_id, "IN_PROGRESS", reason="Started test")
            inc1 = record_incident(task_id, "pytest run", "JSON_PARSE_ERROR in mock", 1)
            inc2 = record_incident(task_id, "pytest run", "JSON_PARSE_ERROR in mock", 1)
            if inc2["attempt_count"] < 2:
                return False, f"Expected attempt_count >= 2, got {inc2['attempt_count']}"
            status = get_task(task_id)
            if not status or status["status"] != "IN_PROGRESS":
                return False, f"Task status should remain IN_PROGRESS (advisory), got {status.get('status') if status else 'None'}"
            return True, f"Fingerprint {inc2['fingerprint']} recorded attempt {inc2['attempt_count']} while task remained advisory {status['status']}"

        self.run_eval("Repeated Failure Advisory Circuit Breaker", test_circuit_breaker)

        # Eval 4: Market Data Integrity - Prohibited Fixture Leaks in Production
        def test_production_fixtures():
            res = self.validator.scan_production_paths_for_synthetic_leaks()
            if not res["valid"]:
                return False, f"Found {len(res['leaks_found'])} prohibited leaks in production paths"
            return True, f"Scanned {res['files_scanned']} production files with 0 synthetic leaks"

        self.run_eval("Market Data Integrity - No Synthetic Leaks", test_production_fixtures)

        # Eval 5: Candle Geometry Validation & Anomaly Detection
        def test_candle_geometry():
            valid_candles = [
                {"timestamp": "2026-11-19T09:15:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1500},
                {"timestamp": "2026-11-19T09:20:00", "open": 103.0, "high": 106.0, "low": 102.0, "close": 105.0, "volume": 2000},
            ]
            inverted_candles = [
                {"timestamp": "2026-11-19T09:15:00", "open": 100.0, "high": 95.0, "low": 99.0, "close": 98.0, "volume": 1500},
            ]
            res_valid = self.validator.validate_candle_geometry(valid_candles)
            res_invalid = self.validator.validate_candle_geometry(inverted_candles)
            if not res_valid["valid"]:
                return False, f"Valid candles incorrectly failed: {res_valid['violations']}"
            if res_invalid["valid"]:
                return False, "Inverted High < Low candle failed to trigger violation"
            return True, "Geometry validator correctly accepted valid candles and rejected inverted candle"

        self.run_eval("OHLCV Candle Consistency and Anomaly Detection", test_candle_geometry)

        # Eval 6: Environment Preflight Doctor Verification
        def test_environment_doctor():
            res = self.doctor.run_all_checks()
            if not res["passed"]:
                fails = [c["message"] for c in res["checks"] if c["level"] == "FAIL"]
                return False, f"Environment doctor failed: {fails}"
            return True, f"All critical doctor checks passed (Warnings: {res['has_warnings']})"

        self.run_eval("Environment Preflight Doctor Check", test_environment_doctor)

        return self.report
