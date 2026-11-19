"""
Tests for SMKD AI Agent Harness & Quality Validation Engine.
"""

import unittest
from scripts.dev.harness.doctor import EnvironmentDoctor
from scripts.dev.harness.detector import DuplicateDetector
from scripts.dev.harness.integrity_validator import MarketDataIntegrityValidator
from scripts.dev.harness.evaluator import AgentEvaluationHarness
from scripts.dev.tests.test_support import IsolatedDevRuntime


class TestAgentHarness(unittest.TestCase):
    def setUp(self):
        self.runtime = IsolatedDevRuntime().start()

    def tearDown(self):
        self.runtime.stop()

    def test_environment_doctor(self):
        doctor = EnvironmentDoctor()
        res = doctor.run_all_checks()
        self.assertIn("passed", res)
        self.assertIn("checks", res)
        self.assertTrue(res["passed"], "Doctor should pass in the current working environment")

    def test_duplicate_detector_existing(self):
        detector = DuplicateDetector()
        res = detector.check("SystemOne")
        self.assertIn("recommendation", res)
        self.assertIn(res["recommendation"], {"EXTEND_EXISTING", "REPAIR_OR_EXTEND_EXISTING"})
        self.assertTrue(len(res["files_found"]) > 0 or len(res["symbols_found"]) > 0)

    def test_duplicate_detector_nonexistent(self):
        detector = DuplicateDetector()
        res = detector.check("QuantumArbitrageSuperHyperDimensionModule_XYZ123")
        self.assertEqual(res["recommendation"], "CREATE_NEW")
        self.assertEqual(len(res["files_found"]), 0)
        self.assertEqual(len(res["symbols_found"]), 0)

    def test_candle_geometry_validation(self):
        validator = MarketDataIntegrityValidator()

        # Valid series
        valid_candles = [
            {"timestamp": "2026-11-19T09:15:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000},
            {"timestamp": "2026-11-19T09:20:00", "open": 103.0, "high": 106.0, "low": 101.0, "close": 104.0, "volume": 1200},
        ]
        res = validator.validate_candle_geometry(valid_candles)
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["violations"]), 0)

        # Inverted High < Low
        inverted_candles = [
            {"timestamp": "2026-11-19T09:15:00", "open": 100.0, "high": 90.0, "low": 95.0, "close": 92.0, "volume": 1000},
        ]
        res_inverted = validator.validate_candle_geometry(inverted_candles)
        self.assertFalse(res_inverted["valid"])
        self.assertTrue(any("inverted High" in v for v in res_inverted["violations"]))

        # Disordered timestamps
        disordered_candles = [
            {"timestamp": "2026-11-19T09:20:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1000},
            {"timestamp": "2026-11-19T09:15:00", "open": 103.0, "high": 106.0, "low": 101.0, "close": 104.0, "volume": 1200},
        ]
        res_disordered = validator.validate_candle_geometry(disordered_candles)
        self.assertFalse(res_disordered["valid"])
        self.assertTrue(any("not strictly greater" in v for v in res_disordered["violations"]))

        # Negative volume
        neg_vol = [
            {"timestamp": "2026-11-19T09:15:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": -50},
        ]
        res_neg = validator.validate_candle_geometry(neg_vol)
        self.assertFalse(res_neg["valid"])
        self.assertTrue(any("negative volume" in v for v in res_neg["violations"]))

    def test_production_fixture_integrity(self):
        validator = MarketDataIntegrityValidator()
        res = validator.scan_production_paths_for_synthetic_leaks()
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["leaks_found"]), 0)

    def test_evaluation_suite_run(self):
        harness = AgentEvaluationHarness()
        report = harness.run_suite()
        self.assertEqual(report["failed"], 0)
        self.assertGreaterEqual(report["passed"], 6)


if __name__ == "__main__":
    unittest.main()
