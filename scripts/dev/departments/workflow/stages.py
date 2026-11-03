"""Workflow stage implementations. No policy gates belong here."""

from typing import Any, Dict, List, Optional, Tuple

from scripts.dev.departments.execution import execute_command
from scripts.dev.departments.context import ContextBuilder
from scripts.dev.departments.documentation import check_doc_sync_status
from scripts.dev.departments.tasks import transition_task


def run_stage(stage: str, task: Dict[str, Any], files: List[str], focused_cmd: Optional[str], regression_cmds: List[str]) -> Tuple[bool, int, str]:
    task_id = task["task_id"]
    if stage == "validate-environment":
        code, out, err, _ = execute_command(task_id, "powershell -ExecutionPolicy Bypass -File scripts/dev/devctl.ps1 doctor")
        return code == 0, code, out + "\n" + err
    if stage == "inspect-task":
        return True, 0, f"Task {task_id} ready in status: {task['status']}"
    if stage == "prepare-context":
        transition_task(task_id, "CONTEXT_READY", reason="Context packet built.")
        ContextBuilder().build_packet(task_id, task["title"], "smkd-safe-edit", task.get("scope", []))
        return True, 0, "Context packet saved."
    if stage == "run-focused-tests":
        transition_task(task_id, "VERIFYING", reason="Focused checks running.")
        if not focused_cmd:
            return True, 0, "No focused checks required."
        code, out, err, _ = execute_command(task_id, focused_cmd)
        return code == 0, code, out + "\n" + err
    if stage == "run-required-checks":
        for command in regression_cmds:
            code, out, err, _ = execute_command(task_id, command)
            if code:
                return False, code, out + "\n" + err
        return True, 0, f"Executed {len(regression_cmds)} regression check(s)."
    if stage == "update-documentation":
        status = check_doc_sync_status(task_id, files)
        if status["status"] == "PENDING_SYNC":
            pending = status.get("pending_docs", [])
            missing = status.get("missing_docs", [])
            return False, 1, f"Documentation update required: {pending}; missing: {missing}"
        return True, 0, f"Documentation status: {status['status']}."
    if stage == "record-checkpoint":
        transition_task(task_id, "DONE", reason="Workflow completed.")
        return True, 0, f"Task {task_id} marked DONE."
    return False, 1, f"Unknown stage: {stage}"
