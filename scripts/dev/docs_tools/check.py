"""Report documentation affected by changed files and optionally enforce sync."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.dev.departments.documentation.mapping import DOC_MAP, get_affected_docs

LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CHECKED_LINK_FILES = (
    "DOCS.md",
    "docs/INDEX.md",
    "docs/AI_TRAINING_PIPELINE.md",
    "docs/dev/DOCUMENTATION_WORKFLOW.md",
    "docs/research/FREE_DATA_AND_AI.md",
    "docs/research/LOCAL_SELF_IMPROVING_AGENTS.md",
)


def validate_links(root: Path = ROOT) -> list[str]:
    broken = []
    for relative in CHECKED_LINK_FILES:
        markdown = root / relative
        if not markdown.is_file():
            broken.append(f"{relative}: documentation entry point is missing")
            continue
        for target in LINK.findall(markdown.read_text(encoding="utf-8")):
            target = target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            destination = (markdown.parent / target.split("#", 1)[0]).resolve()
            if not destination.exists():
                broken.append(f"{relative}: broken link {target}")
    return broken


def _git_files(*arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def changed_files(base: str | None) -> list[str]:
    source_changes = ["diff", "--name-only", "HEAD"]
    if base:
        source_changes = ["diff", "--name-only", f"{base}...HEAD"]
    tracked = _git_files(*source_changes)
    if base is None:
        tracked.extend(_git_files("ls-files", "--others", "--exclude-standard"))
    return sorted(set(path.replace("\\", "/") for path in tracked))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Compare committed changes with BASE...HEAD.")
    parser.add_argument("--files", nargs="*", help="Explicit changed paths, relative to repository root.")
    parser.add_argument("--strict", action="store_true", help="Fail if mapped docs were not changed.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)
    files = sorted(set(args.files if args.files is not None else changed_files(args.base)))
    docs = sorted(get_affected_docs(files))
    missing = sorted(
        {path for paths in DOC_MAP.values() for path in paths if not (ROOT / path).is_file()}
    )
    updated = set(files)
    pending = [path for path in docs if path not in updated and path not in missing]
    status = "PENDING_DOC_REVIEW" if pending else "SYNCED"
    broken_links = validate_links()
    report = {
        "status": status,
        "changed_files": files,
        "affected_docs": docs,
        "pending_docs": pending,
        "missing_docs": missing,
        "broken_links": broken_links,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Documentation status: {status}")
        for path in docs:
            marker = "MISSING" if path in missing else "UPDATE" if path in pending else "UPDATED"
            print(f"[{marker}] {path}")
        if not docs:
            print("No mapped documentation is affected.")
    if missing or broken_links:
        if missing:
            print(f"Mapped documentation files are missing: {', '.join(missing)}", file=sys.stderr)
        for link in broken_links:
            print(link, file=sys.stderr)
        return 1
    return int(args.strict and bool(pending))


if __name__ == "__main__":
    raise SystemExit(main())
