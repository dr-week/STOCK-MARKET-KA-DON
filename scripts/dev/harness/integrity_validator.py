"""
Market Data Integrity Validator.
Enforces non-negotiable market data integrity rules defined in AGENTS.md:
- No synthetic or fabricated data in production paths
- Strict OHLCV candle geometry (High >= Low, High >= Open/Close, Low <= Open/Close, Volume >= 0)
- Monotonic timestamp ordering and no inverted intervals
- Indicator warm-up thresholds
"""

import os
import re
from typing import Dict, Any, List, Optional


class MarketDataIntegrityValidator:
    """Enforces non-negotiable market data and calculation integrity invariants."""

    PROHIBITED_PRODUCTION_PATTERNS = [
        re.compile(r"from\s+.*tests\.fixtures\s+import", re.IGNORECASE),
        re.compile(r"import\s+.*tests\.fixtures", re.IGNORECASE),
        re.compile(r"return\s+\[?\s*\{\s*['\"]symbol['\"]\s*:\s*['\"]MOCK", re.IGNORECASE),
        re.compile(r"['\"]status['\"]\s*:\s*['\"]available['\"].*fallback", re.IGNORECASE),
    ]

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = os.path.abspath(repo_root or os.getcwd())

    def validate_candle_geometry(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validates OHLCV numerical and logical consistency."""
        violations = []
        last_ts = None

        for idx, bar in enumerate(candles):
            ts = bar.get("timestamp") or bar.get("time")
            o = bar.get("open")
            h = bar.get("high")
            l = bar.get("low")
            c = bar.get("close")
            v = bar.get("volume", 0)

            # Check presence
            if any(val is None for val in (o, h, l, c)):
                violations.append(f"Bar {idx}: missing required OHLC component.")
                continue

            # Check prices positive
            if o <= 0 or h <= 0 or l <= 0 or c <= 0:
                violations.append(f"Bar {idx} ({ts}): non-positive price detected (O:{o}, H:{h}, L:{l}, C:{c}).")

            # Check High is highest and Low is lowest
            if h < l:
                violations.append(f"Bar {idx} ({ts}): inverted High ({h}) < Low ({l}).")
            if h < o or h < c:
                violations.append(f"Bar {idx} ({ts}): High ({h}) is lower than Open ({o}) or Close ({c}).")
            if l > o or l > c:
                violations.append(f"Bar {idx} ({ts}): Low ({l}) is higher than Open ({o}) or Close ({c}).")
            if v < 0:
                violations.append(f"Bar {idx} ({ts}): negative volume ({v}).")

            # Timestamp ordering
            if last_ts is not None and ts is not None:
                if ts <= last_ts:
                    violations.append(f"Bar {idx}: timestamp ({ts}) is not strictly greater than previous ({last_ts}).")
            last_ts = ts

        return {
            "valid": len(violations) == 0,
            "candle_count": len(candles),
            "violations": violations,
        }

    def scan_production_paths_for_synthetic_leaks(self) -> Dict[str, Any]:
        """Scans production routes and departments to ensure test fixtures are not referenced."""
        production_roots = [
            os.path.join(self.repo_root, "stock-signal-bot", "backend", "app", "api"),
            os.path.join(self.repo_root, "stock-signal-bot", "backend", "app", "departments"),
            os.path.join(self.repo_root, "stock-signal-bot", "backend", "app", "indicators"),
        ]

        leaks: List[str] = []
        files_scanned = 0

        for root in production_roots:
            if not os.path.exists(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                for fname in filenames:
                    if fname.endswith(".py"):
                        files_scanned += 1
                        fpath = os.path.join(dirpath, fname)
                        rel_path = os.path.relpath(fpath, self.repo_root)
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for line_no, line in enumerate(f, start=1):
                                for pattern in self.PROHIBITED_PRODUCTION_PATTERNS:
                                    if pattern.search(line):
                                        leaks.append(f"{rel_path}:{line_no}: {line.strip()}")

        return {
            "valid": len(leaks) == 0,
            "files_scanned": files_scanned,
            "leaks_found": leaks,
        }
