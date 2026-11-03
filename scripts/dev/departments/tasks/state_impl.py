import json
import sqlite3
from typing import Dict, Any, List, Optional
from scripts.dev.departments.tasks.storage import get_connection

VALID_STATUSES = {
    "BACKLOG",
    "READY",
    "CONTEXT_READY",
    "IN_PROGRESS",
    "VERIFYING",
    "DONE",
    "RETRY_PENDING",
    "BLOCKED"
}

def create_task(task_id: str, title: str, scope: List[str], acceptance: List[str], priority: str = "MEDIUM") -> Dict[str, Any]:
    conn = get_connection()
    with conn:
        conn.execute("""
        INSERT OR REPLACE INTO tasks (task_id, title, status, priority, scope_json, acceptance_json, next_action, updated_at)
        VALUES (?, ?, 'READY', ?, ?, ?, 'Begin task execution', CURRENT_TIMESTAMP)
        """, (task_id, title, priority, json.dumps(scope), json.dumps(acceptance)))

        conn.execute("""
        INSERT INTO task_events (task_id, event_type, details_json)
        VALUES (?, 'TASK_CREATED', ?)
        """, (task_id, json.dumps({"title": title, "scope": scope})))
    conn.close()
    return get_task(task_id)

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["scope"] = json.loads(d["scope_json"])
    d["acceptance"] = json.loads(d["acceptance_json"])
    return d

def transition_task(task_id: str, new_status: str, reason: str = "", next_action: Optional[str] = None) -> Dict[str, Any]:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    task = get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    current_status = task["status"]
    conn = get_connection()
    with conn:
        conn.execute("""
        UPDATE tasks 
        SET status = ?, next_action = COALESCE(?, next_action), updated_at = CURRENT_TIMESTAMP
        WHERE task_id = ?
        """, (new_status, next_action, task_id))

        conn.execute("""
        INSERT INTO task_events (task_id, event_type, details_json)
        VALUES (?, 'STATUS_CHANGE', ?)
        """, (task_id, json.dumps({"from": current_status, "to": new_status, "reason": reason})))
    conn.close()
    return get_task(task_id)
