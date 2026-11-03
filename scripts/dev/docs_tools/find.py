"""Search existing Markdown documentation before repeating research."""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = (ROOT / "docs", ROOT / "stock-signal-bot" / "docs")
TOKEN = re.compile(r"[a-z0-9][a-z0-9._/-]*", re.IGNORECASE)


def find_matches(query: str, limit: int = 12) -> list[tuple[int, str, int, str]]:
    terms = {term.casefold() for term in TOKEN.findall(query)}
    if not terms:
        raise ValueError("Query must include at least one searchable word.")
    results = []
    for folder in DOCS:
        if not folder.exists():
            continue
        for path in folder.rglob("*.md"):
            lines = path.read_text(encoding="utf-8").splitlines()
            matches = [
                (number, line.strip())
                for number, line in enumerate(lines, start=1)
                if terms.intersection(term.casefold() for term in TOKEN.findall(line))
            ]
            if matches:
                score, line_number, excerpt = max(
                    (
                        len(terms.intersection(term.casefold() for term in TOKEN.findall(line))),
                        number,
                        line,
                    )
                    for number, line in matches
                )
                relative = path.relative_to(ROOT).as_posix()
                results.append((score, relative, line_number, excerpt))
    return sorted(results, key=lambda row: (-row[0], row[1]))[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Terms describing the topic or decision.")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive.")
    results = find_matches(args.query, args.limit)
    if not results:
        print("No documentation matched. Check docs/INDEX.md before starting new research.")
        return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    for score, path, line, excerpt in results:
        print(f"{path}:{line} (score {score})")
        print(f"  {excerpt[:220]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
