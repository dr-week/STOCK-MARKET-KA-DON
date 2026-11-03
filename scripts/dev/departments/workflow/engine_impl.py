import os
import json
import time
import yaml
from typing import Dict, Any, List, Optional, Tuple
from scripts.dev.departments.tasks.storage import get_connection, RUNTIME_DIR, init_db
from scripts.dev.departments.tasks.state import get_task, transition_task
from scripts.dev.departments.tasks.recovery import record_incident
from scripts.dev.departments.workflow.stages import run_stage

WORKFLOWS_DIR = os.path.join(RUNTIME_DIR, "workflows")
CHANGE_MAP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "change-map.yml"))

class WorkflowEngine:
    """
    Resumable Development Workflow Engine (DEV-AUTO-001).
    Chains:
    1. validate-environment
    2. inspect-task
    3. prepare-context
    4. run-focused-tests
    5. run-required-checks
    6. update-documentation
    7. record-checkpoint
    """

    STAGES = [
        "validate-environment",
        "inspect-task",
        "prepare-context",
        "run-focused-tests",
        "run-required-checks",
        "update-documentation",
        "record-checkpoint"
    ]

    def __init__(self, run_id: Optional[str] = None):
        init_db()
        os.makedirs(WORKFLOWS_DIR, exist_ok=True)
        self.run_id = run_id or f"run_{int(time.time())}"
        self.state_file = os.path.join(WORKFLOWS_DIR, f"{self.run_id}.json")
        self.state = self._load_or_init_state()

    def _load_or_init_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "run_id": self.run_id,
            "task_id": None,
            "status": "INITIATED",
            "current_stage_idx": 0,
            "stages": {s: {"status": "PENDING", "output": None, "exit_code": None} for s in self.STAGES},
            "created_at": time.time(),
            "updated_at": time.time()
        }

    def _save_state(self):
        self.state["updated_at"] = time.time()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def run_or_resume(self, task_id: str, changed_files: Optional[List[str]] = None) -> Dict[str, Any]:
        self.state["task_id"] = task_id
        task = get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in dev-control database.")

        files = changed_files or task.get("scope", [])
        focused_cmd, regression_cmds = self._resolve_checks(files)

        for idx, stage in enumerate(self.STAGES):
            if self.state["stages"][stage]["status"] == "COMPLETED":
                continue  # Skip already completed steps (resumability)

            self.state["current_stage_idx"] = idx
            self.state["status"] = f"RUNNING_{stage.upper()}"
            self._save_state()

            # Execute Stage
            task = get_task(task_id)
            success, exit_code, output = self._execute_stage(stage, task, files, focused_cmd, regression_cmds)

            self.state["stages"][stage] = {
                "status": "COMPLETED" if success else "FAILED",
                "exit_code": exit_code,
                "output": output[:500] if output else None,
                "timestamp": time.time()
            }

            if not success:
                self.state["status"] = "FAILED"
                self._save_state()
                # Record failure incident in controller
                record_incident(task_id, stage, output or "Stage failed", exit_code)
                return self.state

        self.state["status"] = "COMPLETED"
        self._save_state()
        return self.state

    def _execute_stage(self, stage, task, files, focused_cmd, regression_cmds):
        """Compatibility seam for callers/tests that customize one stage."""
        return run_stage(stage, task, files, focused_cmd, regression_cmds)

    def _resolve_checks(self, changed_files: List[str]) -> Tuple[Optional[str], List[str]]:
        focused = None
        regressions = set()

        if not os.path.exists(CHANGE_MAP_PATH):
            return None, []

        try:
            with open(CHANGE_MAP_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                rules = data.get("rules", [])
        except Exception:
            return None, []

        for r in rules:
            rule_paths = r.get("paths", [])
            for p in rule_paths:
                p_norm = p.replace("**", "").replace("*", "")
                for cf in changed_files:
                    if p_norm in cf.replace("\\", "/"):
                        if not focused and "focused_check" in r:
                            focused = r["focused_check"]
                        for reg in r.get("regression_checks", []):
                            regressions.add(reg)

        return focused, list(regressions)

if __name__ == "__main__":
    engine = WorkflowEngine()
    print(f"Workflow engine initialized with run ID: {engine.run_id}")
