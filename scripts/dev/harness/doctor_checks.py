import os
import shutil
import sys
from typing import Callable


def check_toolchain(log_fn: Callable[[str, str], None]):
    ver = sys.version_info
    if ver.major == 3 and ver.minor >= 11:
        log_fn("PASS", f"Python version is compatible: {ver.major}.{ver.minor}.{ver.micro}")
    else:
        log_fn("WARN", f"Python version is {ver.major}.{ver.minor}.{ver.micro}; recommended is >= 3.11")

    uv_path = shutil.which("uv")
    if uv_path:
        log_fn("PASS", f"uv package manager available at: {uv_path}")
    else:
        log_fn("WARN", "uv package manager not detected on PATH.")

    node_path = shutil.which("node")
    if node_path:
        log_fn("PASS", f"Node.js available at: {node_path}")
    else:
        log_fn("WARN", "Node.js not detected on PATH.")

    pnpm_path = shutil.which("pnpm")
    if pnpm_path:
        log_fn("PASS", f"pnpm available at: {pnpm_path}")
    else:
        log_fn("WARN", "pnpm not detected on PATH.")


def check_requirements(repo_root: str, log_fn: Callable[[str, str], None]):
    req_file = os.path.join(repo_root, "stock-signal-bot", "backend", "requirements.txt")
    if os.path.exists(req_file):
        log_fn("PASS", "Backend requirements.txt found.")
    else:
        log_fn("WARN", f"Backend requirements file not found at {req_file}")
