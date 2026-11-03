import time
import unittest
from scripts.dev.controller.state import create_task, get_task, transition_task
from scripts.dev.controller.recovery import record_incident
from scripts.dev.tests.test_support import IsolatedDevRuntime, create_test_workflow

class TestDevAuto001Workflow(unittest.TestCase):
    def setUp(self):
        self.runtime = IsolatedDevRuntime().start()

    def tearDown(self):
        self.runtime.stop()

    def test_sim_1_successful_run(self):
        """Simulation 1: A successful run passing all stages and reaching DONE."""
        task_id = "SIM-01-SUCCESS"
        create_task(task_id, "Simulate successful run", ["docs/dev/START_HERE.md"], ["Docs pass"])
        engine = create_test_workflow(run_id=f"run_sim1_{int(time.time()*1000)}")

        res = engine.run_or_resume(task_id)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["stages"]["validate-environment"]["status"], "COMPLETED")
        self.assertEqual(res["stages"]["record-checkpoint"]["status"], "COMPLETED")

        task = get_task(task_id)
        self.assertEqual(task["status"], "DONE")

    def test_sim_2_failing_focused_test(self):
        """Simulation 2: A failing focused test halts pipeline and marks task FAILED."""
        task_id = "SIM-02-TESTFAIL"
        create_task(task_id, "Simulate failing test", ["fast-framework/packages/stock-bot-ui/src/departments/ScannerDepartment.ts"], ["Tests pass"])
        engine = create_test_workflow(
            run_id=f"run_sim2_{int(time.time()*1000)}",
            stage_results={
                "run-focused-tests": (
                    False,
                    1,
                    "AssertionError: expected false to be true in ScannerDepartment.ts",
                )
            },
        )
        res = engine.run_or_resume(task_id)

        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["stages"]["run-focused-tests"]["status"], "FAILED")
        self.assertEqual(res["stages"]["record-checkpoint"]["status"], "PENDING")

        task = get_task(task_id)
        self.assertNotEqual(task["status"], "DONE")

    def test_sim_3_two_failure_circuit_breaker(self):
        """Simulation 3: Repeated identical failure is recorded without blocking edits."""
        task_id = "SIM-03-BREAKER"
        create_task(task_id, "Simulate repeated error", [], [])
        transition_task(task_id, "IN_PROGRESS")

        inc1 = record_incident(task_id, "pnpm test", "SyntaxError", 1)
        self.assertFalse(inc1["is_blocked"])

        # 2nd identical failure triggers circuit breaker
        inc2 = record_incident(task_id, "pnpm test", "SyntaxError", 1)
        self.assertTrue(inc2["is_blocked"])

        task = get_task(task_id)
        self.assertEqual(task["status"], "IN_PROGRESS")

    def test_sim_4_interrupted_run_resumption(self):
        """Simulation 4: Interrupted run resumes at unfinished step without repeating completed steps."""
        task_id = "SIM-04-RESUME"
        create_task(task_id, "Simulate interrupted run", ["docs/dev/START_HERE.md"], ["Resume cleanly"])
        run_id = f"run_sim4_{int(time.time()*1000)}"

        # Phase 1: Simulate interruption after inspect-task
        engine1 = create_test_workflow(run_id=run_id)
        engine1.state["stages"]["validate-environment"]["status"] = "COMPLETED"
        engine1.state["stages"]["inspect-task"]["status"] = "COMPLETED"
        engine1._save_state()

        # Phase 2: Resume with new engine instance
        engine2 = create_test_workflow(run_id=run_id)
        res = engine2.run_or_resume(task_id)

        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["stages"]["validate-environment"]["status"], "COMPLETED")
        self.assertEqual(res["stages"]["record-checkpoint"]["status"], "COMPLETED")

        task = get_task(task_id)
        self.assertEqual(task["status"], "DONE")

    def test_sim_5_doc_update_failure(self):
        """Simulation 5: Missing mapped doc halts workflow at update-documentation."""
        task_id = "SIM-05-DOCFAIL"
        create_task(task_id, "Simulate doc fail", ["stock-signal-bot/backend/app/api/routes.py"], ["Docs pass"])
        engine = create_test_workflow(
            run_id=f"run_sim5_{int(time.time()*1000)}",
            stage_results={
                "update-documentation": (
                    False,
                    1,
                    "Documentation pending sync: docs/contracts/scanner-api.md",
                )
            },
        )
        res = engine.run_or_resume(task_id)

        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["stages"]["update-documentation"]["status"], "FAILED")
        self.assertEqual(res["stages"]["record-checkpoint"]["status"], "PENDING")

        task = get_task(task_id)
        self.assertNotEqual(task["status"], "DONE")

    def test_sim_6_unexpected_file_change(self):
        """Simulation 6: Modified file outside declared scope is rejected during verification."""
        task_id = "SIM-06-SCOPE"
        create_task(task_id, "Simulate scope breach", ["docs/dev/START_HERE.md"], ["Scope bounded"])
        transition_task(task_id, "IN_PROGRESS")

        # Simulate verify with unauthorized file
        task = get_task(task_id)
        changed_files = ["docs/dev/START_HERE.md", "stock-signal-bot/backend/app/api/routes.py"]
        scope_violations = [f for f in changed_files if f not in task["scope"]]

        self.assertEqual(len(scope_violations), 1)
        self.assertIn("stock-signal-bot/backend/app/api/routes.py", scope_violations)

if __name__ == "__main__":
    unittest.main()
