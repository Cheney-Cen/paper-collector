import unittest

from paper_collector.models import Paper, Topic
from paper_collector.ranking import rank, rescore


def paper(**overrides):
    values = {
        "paper_id": "x", "title": "Speculative decoding for LLM inference", "abstract": "We improve KV cache serving.", "authors": [],
        "published": "2026-06-22T00:00:00Z", "updated": "2026-06-22T00:00:00Z", "categories": [], "pdf_url": "", "abs_url": "",
    }
    values.update(overrides)
    return Paper(**values)


class RankingTests(unittest.TestCase):
    def test_relevant_paper_is_scored_and_explained(self):
        topic = Topic("serving", "推理系统", ["llm inference", "speculative decoding", "kv cache"])
        ranked = rank([paper()], [topic], 3)
        self.assertEqual(len(ranked), 1)
        self.assertGreater(ranked[0].score, 0)
        self.assertIn("命中主题", ranked[0].score_reasons[0])

    def test_excluded_paper_is_not_selected(self):
        topic = Topic("serving", "推理系统", ["serving"], ["speech recognition"])
        ranked = rank([paper(abstract="Serving for speech recognition")], [topic], 3)
        self.assertEqual(ranked, [])

    def test_venue_and_code_increase_score(self):
        topic = Topic("serving", "推理系统", ["speculative decoding"])
        base, enhanced = rank([paper(), paper(paper_id="y", venue="MLSys", code_url="https://example.com")], [topic], 2)
        self.assertEqual(enhanced.paper_id, "x")
        self.assertGreater(base.score, enhanced.score)

    def test_non_llm_paper_fails_anchor_gate(self):
        topic = Topic("serving", "推理系统", ["serving"])
        self.assertEqual(rank([paper(title="Efficient database serving", abstract="Serving SQL queries")], [topic], 3), [])

    def test_single_incidental_abstract_hit_is_filtered(self):
        topic = Topic("serving", "推理系统", ["serving"])
        candidate = paper(title="Language model evaluation", abstract="The appendix mentions serving once.")
        self.assertEqual(rank([candidate], [topic], 3), [])

    def test_score_contains_explainable_dimensions(self):
        topic = Topic("serving", "推理系统", ["speculative decoding", "kv cache"])
        selected = rank([paper()], [topic], 1)[0]
        self.assertEqual({"relevance", "quality", "novelty", "practical", "credibility"}, set(selected.score_breakdown))
        self.assertGreater(selected.confidence, 0)

    def test_selection_preserves_topic_diversity(self):
        topics = [Topic("serving", "推理系统", ["speculative decoding"]), Topic("alignment", "对齐", ["alignment"])]
        candidates = [paper(paper_id=f"s{i}", title=f"LLM speculative decoding system {i}") for i in range(6)]
        candidates += [paper(paper_id="a1", title="LLM alignment method", abstract="Language model alignment with experiment and benchmark")]
        selected = rank(candidates, topics, 5)
        self.assertTrue(any("alignment" in item.topic_scores for item in selected))

    def test_rescoring_does_not_duplicate_explanations(self):
        topic = Topic("serving", "推理系统", ["speculative decoding"])
        selected = rank([paper()], [topic], 1)
        rescore(selected)
        self.assertEqual(sum(reason.startswith("优势：") for reason in selected[0].score_reasons), 1)
