"""Stage backend source, pinned lockfile, and web console for Tauri packaging."""

from __future__ import annotations

import shutil
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3]
TAURI_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = APP_ROOT / "stock-signal-bot" / "backend"
BACKEND_DST = TAURI_ROOT / "bundle" / "backend"
DOCS_SRC = APP_ROOT / "docs"
FRONTEND_DST = TAURI_ROOT / "bundle" / "frontend"


def ignore_backend_files(directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in {"tests", "__pycache__", ".pytest_cache", "data", "backups"}
        or name.endswith((".pyc", ".db", ".db-shm", ".db-wal", ".log", ".gz"))
    }


def stage_backend() -> None:
    if not (BACKEND_SRC / "app" / "main.py").is_file():
        raise SystemExit(f"Backend source not found: {BACKEND_SRC}")
    if not (BACKEND_SRC / "requirements-lock.txt").is_file():
        raise SystemExit(f"Pinned backend lock not found: {BACKEND_SRC / 'requirements-lock.txt'}")
    shutil.rmtree(BACKEND_DST, ignore_errors=True)
    BACKEND_DST.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BACKEND_SRC / "app", BACKEND_DST / "app", ignore=ignore_backend_files)
    shutil.copy2(BACKEND_SRC / "requirements-lock.txt", BACKEND_DST / "requirements-lock.txt")
    print(f"Staged backend runtime at {BACKEND_DST}")


def stage_frontend() -> None:
    shutil.rmtree(FRONTEND_DST, ignore_errors=True)
    FRONTEND_DST.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DOCS_SRC / "app.html", FRONTEND_DST / "index.html")
    shutil.copytree(DOCS_SRC / "assets", FRONTEND_DST / "assets")
    shutil.copy2(TAURI_ROOT / "splash.html", FRONTEND_DST / "splash.html")
    logo = TAURI_ROOT / "logos" / "SMKD_LOGO.jpg"
    if logo.is_file():
        shutil.copy2(logo, FRONTEND_DST / "SMKD_LOGO.jpg")
    print(f"Staged desktop frontend at {FRONTEND_DST}")


def main() -> None:
    stage_backend()
    stage_frontend()


if __name__ == "__main__":
    main()
