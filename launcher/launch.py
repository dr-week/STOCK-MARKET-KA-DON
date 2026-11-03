"""Start the SMKD local services quietly and open the dashboard when ready."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "stock-signal-bot" / "backend"
FRONTEND_DIR = ROOT_DIR / "fast-framework" / "packages" / "stock-bot-ui"
RUNTIME_DIR = ROOT_DIR / ".runtime" / "launcher"
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:5173"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
STARTUP_TIMEOUT_SECONDS = 45


def responds(url: str, expected_content: bytes | None = None) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            body = response.read(8192)
            return response.status < 500 and (expected_content is None or expected_content in body)
    except (OSError, urllib.error.URLError):
        return False


def start_hidden(command: list[str], cwd: Path, log_path: Path) -> subprocess.Popen:
    log_file = log_path.open("ab")
    try:
        return subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
    finally:
        log_file.close()


def wait_until_ready(
    url: str,
    process: subprocess.Popen | None,
    expected_content: bytes,
) -> bool:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if responds(url, expected_content):
            return True
        if process is not None and process.poll() is not None:
            return False
        time.sleep(0.5)
    return responds(url, expected_content)


def startup_error(message: str) -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    error_log = RUNTIME_DIR / "launcher.log"
    with error_log.open("a", encoding="utf-8") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    if os.name == "nt":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"{message}\n\nDetails: {error_log}",
            "SMKD could not start",
            0x10,
        )
    return 1


def open_dashboard(url: str) -> None:
    candidates = []
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidates.append(Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    edge = next((candidate for candidate in candidates if candidate.is_file()), None)
    if edge is None:
        edge_path = shutil.which("msedge.exe")
        edge = Path(edge_path) if edge_path else None

    if edge is not None:
        subprocess.Popen(
            [str(edge), f"--app={url}", "--no-first-run"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
    else:
        webbrowser.open(url, new=1)


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    backend_process = None
    if not responds(f"{BACKEND_URL}/health", b"NSE Signal Engine"):
        backend_log = RUNTIME_DIR / "backend.log"
        backend_process = start_hidden(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            BACKEND_DIR,
            backend_log,
        )
        if not wait_until_ready(f"{BACKEND_URL}/health", backend_process, b"NSE Signal Engine"):
            return startup_error("The backend did not become ready. Check backend.log.")

    frontend_process = None
    if not responds(FRONTEND_URL, b"<title>SMKD"):
        pnpm = shutil.which("pnpm.cmd") or shutil.which("pnpm")
        if pnpm:
            frontend_command = [
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                f'"{pnpm}" dev --host 127.0.0.1 --strictPort',
            ]
        else:
            node = shutil.which("node.exe") or shutil.which("node")
            vite_cli = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
            if not node or not vite_cli.is_file():
                return startup_error(
                    "pnpm or installed frontend dependencies were not found. "
                    "Install Node.js and run pnpm install in fast-framework."
                )
            frontend_command = [node, str(vite_cli), "--host", "127.0.0.1", "--strictPort"]

        frontend_process = start_hidden(
            frontend_command,
            FRONTEND_DIR,
            RUNTIME_DIR / "frontend.log",
        )
        if not wait_until_ready(FRONTEND_URL, frontend_process, b"<title>SMKD"):
            return startup_error("The dashboard did not become ready. Check frontend.log.")

    open_dashboard(FRONTEND_URL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
