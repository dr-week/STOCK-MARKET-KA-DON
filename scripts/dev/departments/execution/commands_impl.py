import os
import subprocess
import time
import json
from typing import Dict, Any, Tuple, Optional
from scripts.dev.departments.tasks.storage import get_connection, RUNTIME_DIR
from scripts.dev.departments.execution.summarizer import OutputSummarizer

LOGS_DIR = os.path.join(RUNTIME_DIR, "logs")

def execute_command(task_id: str, command: str, cwd: Optional[str] = None, timeout_sec: int = 120) -> Tuple[int, str, str, Dict[str, Any]]:
    os.makedirs(LOGS_DIR, exist_ok=True)
    start_time = time.time()

    proc = subprocess.Popen(
        command,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        exit_code = 124

    duration_ms = int((time.time() - start_time) * 1000)

    # Save complete diagnostic log to disk
    run_timestamp = int(time.time())
    output_filename = f"{task_id}_cmd_{run_timestamp}.log"
    output_path = os.path.join(LOGS_DIR, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"COMMAND: {command}\n")
        f.write(f"EXIT CODE: {exit_code}\n")
        f.write(f"DURATION: {duration_ms}ms\n\n")
        f.write("--- STDOUT ---\n")
        f.write(stdout)
        f.write("\n--- STDERR ---\n")
        f.write(stderr)

    # Produce compact summary for AI context
    summary = OutputSummarizer.summarize(command, exit_code, stdout, stderr, output_path)

    # Record in SQLite
    conn = get_connection()
    with conn:
        conn.execute("""
        INSERT INTO command_runs (task_id, command, exit_code, duration_ms, output_path)
        VALUES (?, ?, ?, ?, ?)
        """, (task_id, command, exit_code, duration_ms, output_path))
    conn.close()

    return exit_code, stdout, stderr, summary
