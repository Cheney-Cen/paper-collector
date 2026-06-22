import os
import unittest
from unittest.mock import patch

from paper_collector.llm import add_semantic_scores, summarize_in_chinese
from paper_collector.models import Paper, Topic


class LlmTests(unittest.TestCase):
    def test_no_key_keeps_papers_local_and_unchanged(self):
        paper = Paper("id", "title", "abstract", [], "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", [], "", "")
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(summarize_in_chinese([paper])[0], paper)
            self.assertIsNone(paper.summary_zh)

    def test_semantic_scores_seed_best_topic(self):
        topics = [Topic("serving", "推理系统", ["kv cache"]), Topic("align", "对齐", ["alignment"])]
        candidate = Paper("p", "title", "abstract", [], "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", [], "", "")
        response = {"data": [
            {"index": 0, "embedding": [1.0, 0.0]},   # topic serving
            {"index": 1, "embedding": [0.0, 1.0]},   # topic align
            {"index": 2, "embedding": [1.0, 0.0]},   # paper -> closest to serving
        ]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "k", "OPENAI_EMBEDDING_MODEL": "m"}, clear=True):
            with patch("paper_collector.llm._post", return_value=response):
                add_semantic_scores([candidate], topics)
        self.assertGreater(candidate.semantic_score, 0)
        self.assertEqual(max(candidate.topic_scores, key=candidate.topic_scores.get), "serving")
