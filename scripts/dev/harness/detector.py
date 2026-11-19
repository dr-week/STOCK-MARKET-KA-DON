"""
Duplicate Detection and Extensibility Advisor.
Scans the codebase for existing symbols, classes, interfaces, and filenames
to prevent accidental duplication and enforce DRY principles.
"""

import os
import re
from typing import Dict, Any, List, Optional


class DuplicateDetector:
    """Scans workspace code for filenames and symbol exports to advise reuse."""

    EXCLUDE_DIRS = {
        ".git",
        "node_modules",
        ".runtime",
        "dist",
        "build",
        ".cache",
        "__pycache__",
        "backups",
    }

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = os.path.abspath(repo_root or os.getcwd())

    @staticmethod
    def _to_snake_case(name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def check(self, target_name: str, search_root: Optional[str] = None) -> Dict[str, Any]:
        root_dir = os.path.abspath(search_root or self.repo_root)
        files_found: List[str] = []
        symbols_found: List[str] = []

        target_lower = target_name.lower()
        target_snake = self._to_snake_case(target_name)
        target_normalized = target_lower.replace("_", "").replace("-", "")

        symbol_regex = re.compile(
            r"(?:class|interface|def|function|const|let|var)\s+([A-Za-z0-9_]*"
            + re.escape(target_name)
            + r"[A-Za-z0-9_]*)",
            re.IGNORECASE,
        )

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in self.EXCLUDE_DIRS]

            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, self.repo_root)
                fname_lower = fname.lower()
                fname_normalized = fname_lower.replace("_", "").replace("-", "")

                # 1. Filename match (direct, snake_case, or normalized without separators)
                if (
                    target_lower in fname_lower
                    or target_snake in fname_lower
                    or target_normalized in fname_normalized
                ):
                    files_found.append(rel_path)

                # 2. Content / symbol match for source files
                ext = os.path.splitext(fname)[1].lower()
                if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".rs"}:
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, start=1):
                                match = symbol_regex.search(line)
                                if match:
                                    symbols_found.append(f"{rel_path}:{idx}: {line.strip()}")
                    except Exception:
                        pass

        # Formulate recommendation
        if files_found:
            recommendation = "EXTEND_EXISTING"
        elif symbols_found:
            recommendation = "REPAIR_OR_EXTEND_EXISTING"
        else:
            recommendation = "CREATE_NEW"

        return {
            "target": target_name,
            "files_found": sorted(list(set(files_found))),
            "symbols_found": symbols_found[:20],  # Bound to avoid huge outputs
            "symbols_count": len(symbols_found),
            "recommendation": recommendation,
        }
