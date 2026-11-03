import tempfile
import unittest
from pathlib import Path

from scripts.dev.docs_tools.find import find_matches
from scripts.dev.docs_tools.check import validate_links
from scripts.dev.departments.documentation.mapping import check_doc_sync_status, get_affected_docs


class TestDocumentationTools(unittest.TestCase):
    def test_api_change_maps_to_real_contract_docs(self):
        docs = get_affected_docs(["stock-signal-bot/backend/app/api/routes_scan.py"])
        self.assertIn("stock-signal-bot/docs/04_API_SPECIFICATION.md", docs)
        self.assertNotIn("docs/contracts/scanner-api.md", docs)

    def test_prefix_mapping_does_not_match_unrelated_path(self):
        self.assertEqual(get_affected_docs(["scripts/devil/example.py"]), set())

    def test_change_requires_affected_docs_to_be_in_changed_files(self):
        result = check_doc_sync_status(
            "DOCS-TEST",
            ["stock-signal-bot/backend/app/api/routes_scan.py"],
        )
        self.assertEqual(result["status"], "PENDING_SYNC")
        self.assertIn("docs/ARCHITECTURE.md", result["pending_docs"])

    def test_document_search_returns_ranked_file_and_line(self):
        from scripts.dev.docs_tools import find

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "market.md").write_text(
                "# Market data\nYahoo data is unofficial.\nNSE EOD archive research.",
                encoding="utf-8",
            )
            previous = find.ROOT
            previous_docs = find.DOCS
            try:
                find.ROOT = root
                find.DOCS = (docs, root / "absent")
                results = find.find_matches("NSE Yahoo data")
            finally:
                find.ROOT = previous
                find.DOCS = previous_docs

        self.assertEqual(results[0][1], "docs/market.md")
        self.assertEqual(results[0][2], 2)
        self.assertIn("Yahoo data", results[0][3])

    def test_link_check_detects_missing_local_destination(self):
        from scripts.dev.docs_tools import check

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in check.CHECKED_LINK_FILES:
                page = root / relative
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text("[Missing](./missing.md)", encoding="utf-8")
            broken = validate_links(root)

        self.assertEqual(len(broken), len(check.CHECKED_LINK_FILES))


if __name__ == "__main__":
    unittest.main()
