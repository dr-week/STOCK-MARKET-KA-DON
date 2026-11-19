"""
Environment Doctor for SMKD Project.
Read-only preflight diagnostic checks across repository, toolchain, and dependencies.
Cross-platform implementation replacing Windows-only PowerShell doctor.
"""

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

from scripts.dev.harness.doctor_checks import check_requirements, check_toolchain


class EnvironmentDoctor:
    """Preflight diagnostic checks to catch environment issues early."""

    def __init__(self, repo_root: str = None):
        self.repo_root = os.path.abspath(repo_root or os.getcwd())
        self.results: List[Dict[str, str]] = []
        self.has_fail = False
        self.has_warn = False

    def log(self, level: str, message: str):
        level_clean = level.upper()
        if level_clean == "FAIL":
            self.has_fail = True
        elif level_clean == "WARN":
            self.has_warn = True
        self.results.append({"level": level_clean, "message": message})

    def run_all_checks(self) -> Dict[str, Any]:
        self.results = []
        self.has_fail = False
        self.has_warn = False

        self._check_git_root()
        self._check_git_status()
        self._check_submodules()
        self._check_json_manifests()
        check_toolchain(self.log)
        check_requirements(self.repo_root, self.log)

        return {
            "passed": not self.has_fail,
            "has_warnings": self.has_warn,
            "exit_code": 1 if self.has_fail else 0,
            "checks": self.results,
        }

    def _check_git_root(self):
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                detected = os.path.abspath(res.stdout.strip())
                self.log("PASS", f"Git repository root detected: {detected}")
            else:
                self.log("FAIL", "Git repository not found.")
        except Exception as e:
            self.log("FAIL", f"Failed to execute git: {str(e)}")

    def _check_git_status(self):
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                changes = res.stdout.strip().splitlines()
                if changes:
                    self.log("WARN", f"Working tree has uncommitted or untracked changes ({len(changes)} items).")
                else:
                    self.log("PASS", "Clean working tree.")
            else:
                self.log("WARN", "Unable to retrieve git status.")
        except Exception as e:
            self.log("WARN", f"Git status error: {str(e)}")

    def _check_submodules(self):
        try:
            res = subprocess.run(
                ["git", "submodule", "status", "--recursive"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                self.log("PASS", "Submodule status retrieved successfully.")
            else:
                self.log("WARN", "No submodules or submodule status unavailable.")
        except Exception as e:
            self.log("WARN", f"Submodule check error: {str(e)}")

    def _check_json_manifests(self):
        count = 0
        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".runtime", "dist", "build"}]
            if "package.json" in files:
                count += 1
                pj_path = os.path.join(root, "package.json")
                try:
                    with open(pj_path, "r", encoding="utf-8") as f:
                        json.load(f)
                    rel_path = os.path.relpath(pj_path, self.repo_root)
                    self.log("PASS", f"Valid JSON manifest: {rel_path}")
                except Exception as e:
                    rel_path = os.path.relpath(pj_path, self.repo_root)
                    self.log("FAIL", f"Invalid JSON manifest {rel_path}: {str(e)}")

        if count == 0:
            self.log("WARN", "No package.json files found to validate.")


def run_doctor(repo_root: str = None) -> int:
    doc = EnvironmentDoctor(repo_root)
    result = doc.run_all_checks()
    for item in result["checks"]:
        lvl = item["level"]
        msg = item["message"]
        print(f"[{lvl}] {msg}")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(run_doctor())
