import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_site import build_dashboard


class BuildSiteTests(unittest.TestCase):
    def test_builds_latest_and_deduplicated_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            daily, output = root / "daily", root / "site"
            daily.mkdir()
            base = {"title": "Paper", "updated": "2026-01-01", "score": 50}
            (daily / "2026-01-01.json").write_text(json.dumps({"date": "2026-01-01", "papers": [{**base, "paper_id": "2601.1v1"}]}))
            (daily / "2026-01-02.json").write_text(json.dumps({"date": "2026-01-02", "papers": [{**base, "paper_id": "2601.1v2"}]}))
            editions, papers, latest = build_dashboard(daily, output)
            self.assertEqual((editions, papers, latest), (2, 1, "2026-01-02"))
            self.assertEqual(json.loads((output / "latest.json").read_text())["date"], "2026-01-02")
            self.assertEqual(len(json.loads((output / "catalog.json").read_text())["papers"]), 1)
