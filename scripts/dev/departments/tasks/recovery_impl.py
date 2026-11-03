import os
import json
from typing import Dict, Any, Optional, Tuple
from scripts.dev.departments.tasks.storage import get_connection, RUNTIME_DIR
from scripts.dev.departments.tasks.state import get_task, transition_task

INCIDENTS_DIR = os.path.join(RUNTIME_DIR, "incidents")

def classify_error(output: str, exit_code: int) -> str:
    text = output.lower()
    if "syntaxerror" in text or "json_parse_error" in text or "unexpected token" in text:
        return "JSON_PARSE_ERROR"
    if "err_pnpm" in text or "package.json" in text or "workspace" in text:
        return "PNPM_WORKSPACE_ERROR"
    if "assertionerror" in text or "failed tests" in text or "failures=" in text:
        return "TEST_FAILURE"
    if "no such file" in text or "filenotfounderror" in text or "cannot find module" in text:
        return "FILE_NOT_FOUND"
    if exit_code == 124 or "timeout" in text:
        return "BUILD_TIMEOUT"
    return "COMMAND_ERROR"

def record_incident(task_id: str, command: str, output: str, exit_code: int) -> Dict[str, Any]:
    os.makedirs(INCIDENTS_DIR, exist_ok=True)
    category = classify_error(output, exit_code)
    fingerprint = f"{category}:{command.strip().split()[0]}"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT incident_id, attempt_count FROM incidents
    WHERE task_id = ? AND fingerprint = ? AND status = 'OPEN'
    """, (task_id, fingerprint))
    row = cursor.fetchone()

    attempt_count = 1
    incident_id = None
    if row:
        incident_id = row["incident_id"]
        attempt_count = row["attempt_count"] + 1
        with conn:
            conn.execute("""
            UPDATE incidents SET attempt_count = ?
            WHERE incident_id = ?
            """, (attempt_count, incident_id))
    else:
        diag_file = os.path.join(INCIDENTS_DIR, f"{task_id}_{category}.log")
        with open(diag_file, "w", encoding="utf-8") as f:
            f.write(f"INCIDENT: {fingerprint}\nCOMMAND: {command}\nEXIT: {exit_code}\n\n{output}")
        with conn:
            cursor.execute("""
            INSERT INTO incidents (task_id, fingerprint, category, attempt_count, status, diagnostic_path)
            VALUES (?, ?, ?, 1, 'OPEN', ?)
            """, (task_id, fingerprint, category, diag_file))
            incident_id = cursor.lastrowid

    conn.close()

    # Repeated failures remain visible, but do not lock editing or command execution.
    is_blocked = False
    if attempt_count >= 2:
        is_blocked = True
        task = get_task(task_id)
        if task and task["status"] not in {"DONE", "BLOCKED"}:
            transition_task(task_id, task["status"], reason=f"Repeated failure recorded: {fingerprint}")

    return {
        "incident_id": incident_id,
        "fingerprint": fingerprint,
        "category": category,
        "attempt_count": attempt_count,
        "is_blocked": is_blocked
    }
