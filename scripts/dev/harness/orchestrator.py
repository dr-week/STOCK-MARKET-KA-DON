"""
AI Agent Workflow Orchestrator.
Orchestrates agent testing, evaluation, validation, and multi-stage lifecycle:
1. Environment preflight validation
2. Duplicate capability and scope inspection
3. Context assembly
4. Focused targeted tests
5. Broader regression checks
6. Documentation sync verification
7. Task checkpoint transition
"""

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional

from scripts.dev.harness.doctor import EnvironmentDoctor
from scripts.dev.harness.detector import DuplicateDetector
from scripts.dev.departments.tasks.storage import init_db
from scripts.dev.departments.tasks.state import get_task, create_task, transition_task
from scripts.dev.departments.tasks.recovery import record_incident
from scripts.dev.departments.execution import execute_command
from scripts.dev.departments.context import ContextBuilder
from scripts.dev.departments.documentation import check_doc_sync_status
from scripts.dev.departments.workflow.engine import WorkflowEngine


class AgentOrchestrator:
    """Manages the full automated evaluation and execution pipeline for AI agents."""

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = os.path.abspath(repo_root or os.getcwd())
        self.doctor = EnvironmentDoctor(self.repo_root)
        self.detector = DuplicateDetector(self.repo_root)
        init_db()

    def run_pipeline(self, task_id: str, changed_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Runs the orchestrated multi-stage development workflow."""
        task = get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found in dev controller database.")

        files = changed_files or task.get("scope", [])

        # Stage 1: Preflight Environment
        doc_res = self.doctor.run_all_checks()
        if not doc_res["passed"]:
            record_incident(task_id, "doctor", "Environment preflight failed", 1)
            transition_task(task_id, "BLOCKED", reason="Environment preflight failed")
            return {"task_id": task_id, "status": "BLOCKED", "stage": "validate-environment", "error": "Environment preflight failed"}

        # Stage 2: Scope & Duplicate Check
        if files:
            for f in files:
                base_name = os.path.splitext(os.path.basename(f))[0]
                dup_res = self.detector.check(base_name)
                # Advisory duplicate notice

        # Stage 3: Context Packet
        transition_task(task_id, "CONTEXT_READY", reason="Context packet ready")
        ContextBuilder().build_packet(task_id, task["title"], "smkd-safe-edit", files)

        # Stage 4-7: Workflow Execution
        engine = WorkflowEngine(run_id=f"orch_{int(time.time()*1000)}")
        result = engine.run_or_resume(task_id, changed_files=files)

        return result
