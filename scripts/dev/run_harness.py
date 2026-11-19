#!/usr/bin/env python3
"""
Entry point for SMKD AI Agent Harness & Quality Validation Engine.
Cross-platform: runs seamlessly on Linux, macOS, and Windows.
"""

import sys
import os

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.dev.harness.cli import main

if __name__ == "__main__":
    main()
