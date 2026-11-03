"""Persistent data locations for source checkouts and desktop installations."""

import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("SMKD_DATA_DIR", APP_ROOT / "data")).expanduser().resolve()
BACKUP_DIR = DATA_DIR / "backups"
RESEARCH_DIR = DATA_DIR / "research"

DATA_DIR.mkdir(parents=True, exist_ok=True)
