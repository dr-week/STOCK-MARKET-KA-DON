"""Stage backend source and the pinned runtime lock for Tauri packaging."""

from __future__ import annotations

import shutil
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3]
SOURCE = APP_ROOT / "stock-signal-bot" / "backend"
DESTINATION = Path(__file__).resolve().parents[1] / "bundle" / "backend"


def ignore_backend_files(directory: str, names: list[str]) -> set[str]:
    ignored = {
        name
        for name in names
        if name in {"tests", "__pycache__", ".pytest_cache", "data", "backups"}
        or name.endswith((".pyc", ".db", ".db-shm", ".db-wal", ".log", ".gz"))
    }
    return ignored


def main() -> None:
    if not (SOURCE / "app" / "main.py").is_file():
        raise SystemExit(f"Backend source not found: {SOURCE}")
    if not (SOURCE / "requirements-lock.txt").is_file():
        raise SystemExit(f"Pinned backend lock not found: {SOURCE / 'requirements-lock.txt'}")
    shutil.rmtree(DESTINATION, ignore_errors=True)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE / "app", DESTINATION / "app", ignore=ignore_backend_files)
    shutil.copy2(SOURCE / "requirements-lock.txt", DESTINATION / "requirements-lock.txt")
    print(f"Staged backend runtime at {DESTINATION}")


if __name__ == "__main__":
    main()
