import unittest
from scripts.dev.controller.state import create_task, get_task, transition_task
from scripts.dev.controller.recovery import record_incident
from scripts.dev.controller.documentation import check_doc_sync_status
from scripts.dev.tests.test_support import IsolatedDevRuntime

class TestDevelopmentController(unittest.TestCase):
    def setUp(self):
        self.runtime = IsolatedDevRuntime().start()

    def tearDown(self):
        self.runtime.stop()

    def test_task_lifecycle_transitions(self):
        task_id = "CTRL-TEST-001"
        task = create_task(task_id, "Test Lifecycle", ["file_a.py"], ["All tests pass"])
        self.assertEqual(task["status"], "READY")

        # READY -> IN_PROGRESS
        t_prog = transition_task(task_id, "IN_PROGRESS", reason="Started")
        self.assertEqual(t_prog["status"], "IN_PROGRESS")

        # IN_PROGRESS -> VERIFYING
        t_ver = transition_task(task_id, "VERIFYING", reason="Checking")
        self.assertEqual(t_ver["status"], "VERIFYING")

        # VERIFYING -> DONE
        t_done = transition_task(task_id, "DONE", reason="Verified")
        self.assertEqual(t_done["status"], "DONE")

    def test_status_can_be_changed_without_workflow_lock(self):
        task_id = "CTRL-TEST-002"
        create_task(task_id, "Test Illegal Transition", [], [])
        task = transition_task(task_id, "DONE")
        self.assertEqual(task["status"], "DONE")

    def test_circuit_breaker_on_repeated_failure(self):
        task_id = "CTRL-TEST-003"
        create_task(task_id, "Test Circuit Breaker", [], [])
        transition_task(task_id, "IN_PROGRESS")

        inc1 = record_incident(task_id, "pnpm run build", "SyntaxError in manifest", 1)
        self.assertFalse(inc1["is_blocked"])
        self.assertEqual(inc1["attempt_count"], 1)

        # Repeated failures are recorded without locking the task.
        inc2 = record_incident(task_id, "pnpm run build", "SyntaxError in manifest", 1)
        self.assertTrue(inc2["is_blocked"])
        self.assertEqual(inc2["attempt_count"], 2)

        task = get_task(task_id)
        self.assertEqual(task["status"], "IN_PROGRESS")

    def test_doc_sync_mapping(self):
        res_no_doc = check_doc_sync_status("CTRL-TEST-004", ["styles/main.css"])
        self.assertEqual(res_no_doc["status"], "NOT_REQUIRED")

        code = "stock-signal-bot/backend/app/api/routes.py"
        res_api_doc = check_doc_sync_status("CTRL-TEST-004", [code])
        self.assertIn("stock-signal-bot/docs/04_API_SPECIFICATION.md", res_api_doc["affected_docs"])
        self.assertEqual(res_api_doc["status"], "PENDING_SYNC")
        res_synced = check_doc_sync_status(
            "CTRL-TEST-004",
            [code, *res_api_doc["affected_docs"]],
        )
        self.assertEqual(res_synced["status"], "SYNCED")

if __name__ == "__main__":
    unittest.main()
