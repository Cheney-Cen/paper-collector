import unittest
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

from paper_collector.arxiv import build_query, fetch_recent


FEED = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/abs/2601.00001v1</id><title>LLM inference</title>
  <updated>2026-01-01T00:00:00Z</updated><published>2026-01-01T00:00:00Z</published>
  <summary>KV cache serving.</summary><author><name>Ada</name></author>
  <link href="https://arxiv.org/pdf/2601.00001v1" title="pdf"/><category term="cs.CL"/></entry>
</feed>'''


class Response(BytesIO):
    def __enter__(self): return self
    def __exit__(self, *_): self.close()


class ArxivTests(unittest.TestCase):
    def test_query_combines_categories(self):
        self.assertEqual(build_query(["cs.CL", "cs.AI"]), "cat:cs.CL OR cat:cs.AI")

    @patch("paper_collector.arxiv.time.sleep")
    @patch("paper_collector.arxiv.urlopen")
    def test_rate_limit_is_retried(self, mocked_open, mocked_sleep):
        mocked_open.side_effect = [HTTPError("url", 429, "limited", {}, None), Response(FEED)]
        papers = fetch_recent(["cs.CL"], 1, "test-agent", retries=2)
        self.assertEqual(papers[0].paper_id, "2601.00001v1")
        mocked_sleep.assert_called_once_with(5)
