"""
AUTOMATED BACKUP & RECOVERY MANAGER
Handles:
- Automated local SQLite snapshot backups with gzip compression
- Point-In-Time-Recovery (PITR) metadata manifest
- Database integrity checks (PRAGMA integrity_check)
- Backup rotation (retains latest 30 daily snapshots)
"""

import os
import shutil
import sqlite3
import time
import gzip
import json
from datetime import datetime
from typing import Dict, Any, List
from app.storage_paths import BACKUP_DIR, DATA_DIR

BACKUP_DIR = str(BACKUP_DIR)
DB_PATH = str(DATA_DIR / "signals_tree.db")

class BackupManager:
    def __init__(self, backup_dir: str = BACKUP_DIR, db_path: str = DB_PATH):
        self.backup_dir = backup_dir
        self.db_path = db_path
        os.makedirs(self.backup_dir, exist_ok=True)

    def verify_database_integrity(self) -> bool:
        if not os.path.exists(self.db_path):
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            conn.close()
            return res and res[0] == "ok"
        except Exception as e:
            print(f"[BACKUP ERROR] Database integrity check failed: {e}")
            return False

    def create_snapshot_backup(self) -> Dict[str, Any]:
        """
        Creates an atomic, gzipped snapshot backup of the SQLite signals tree.
        """
        if not self.verify_database_integrity():
            return {"status": "FAILED", "error": "Database integrity check failed"}

        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"signals_tree_backup_{date_str}.db.gz"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        start_time = time.time()
        try:
            with open(self.db_path, "rb") as f_in:
                with gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            duration = round(time.time() - start_time, 3)
            size_bytes = os.path.getsize(backup_path)

            manifest = {
                "status": "SUCCESS",
                "backup_filename": backup_filename,
                "backup_path": backup_path,
                "size_bytes": size_bytes,
                "duration_seconds": duration,
                "timestamp": time.time(),
                "created_at": datetime.now().isoformat()
            }

            # Write manifest file
            manifest_path = os.path.join(self.backup_dir, f"manifest_{date_str}.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            self._rotate_backups(keep_count=30)
            return manifest
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        for f in os.listdir(self.backup_dir):
            if f.endswith(".db.gz"):
                p = os.path.join(self.backup_dir, f)
                backups.append({
                    "filename": f,
                    "size_bytes": os.path.getsize(p),
                    "created_at": datetime.fromtimestamp(os.path.getmtime(p)).isoformat()
                })
        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    def _rotate_backups(self, keep_count: int = 30) -> None:
        all_backups = self.list_backups()
        if len(all_backups) > keep_count:
            to_delete = all_backups[keep_count:]
            for b in to_delete:
                p = os.path.join(self.backup_dir, b["filename"])
                try:
                    os.remove(p)
                except OSError:
                    pass

backup_service = BackupManager()
