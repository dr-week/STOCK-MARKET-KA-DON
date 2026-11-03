import time
import unittest
from scripts.dev.controller.state import create_task, get_task
from scripts.dev.tests.test_support import IsolatedDevRuntime, create_test_workflow

class TestWorkflowEngine(unittest.TestCase):
    def setUp(self):
        self.runtime = IsolatedDevRuntime().start()

    def tearDown(self):
        self.runtime.stop()

    def test_workflow_execution_and_resumability(self):
        task_id = "WF-TEST-001"
        create_task(task_id, "Test Workflow Pipeline", ["docs/dev/START_HERE.md"], ["Docs verified"])

        run_id = f"test_run_{int(time.time() * 1000)}"
        engine = create_test_workflow(run_id=run_id)

        # Run pipeline
        res = engine.run_or_resume(task_id)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["stages"]["validate-environment"]["status"], "COMPLETED")
        self.assertEqual(res["stages"]["record-checkpoint"]["status"], "COMPLETED")

        # Verify task is now marked DONE in controller
        task = get_task(task_id)
        self.assertEqual(task["status"], "DONE")

        # Re-running the same run_id resumes idempotently without re-executing completed stages
        engine_resume = create_test_workflow(run_id=run_id)
        res_resume = engine_resume.run_or_resume(task_id)
        self.assertEqual(res_resume["status"], "COMPLETED")

if __name__ == "__main__":
    unittest.main()
