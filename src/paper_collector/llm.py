from __future__ import annotations

import json
import math
import os
from urllib.request import Request, urlopen

from .models import Paper, Topic


def _post(path: str, payload: dict) -> dict:
    api_key = os.environ["OPENAI_API_KEY"]
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    request = Request(
        f"{base_url}/{path.lstrip('/')}", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=60) as response:  # noqa: S310 - configurable user-selected provider
        return json.loads(response.read())


def _cosine(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0.0


def add_semantic_scores(papers: list[Paper], topics: list[Topic]) -> list[Paper]:
    """Add max topic-to-paper embedding similarity when an embedding API is configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_EMBEDDING_MODEL")
    if not api_key or not model or not papers:
        return papers
    topic_texts = [f"{topic.title}: {', '.join(topic.keywords)}" for topic in topics]
    paper_texts = [f"{paper.title}\n{paper.abstract}" for paper in papers]
    try:
        result = _post("embeddings", {"model": model, "input": topic_texts + paper_texts})
        vectors = [item["embedding"] for item in sorted(result["data"], key=lambda item: item["index"])]
        topic_vectors, paper_vectors = vectors[: len(topics)], vectors[len(topics) :]
        for paper, vector in zip(papers, paper_vectors, strict=True):
            # Map cosine from a conservative semantic range into 0..100.
            similarity = max((_cosine(vector, topic_vector) for topic_vector in topic_vectors), default=0.0)
            paper.semantic_score = round(max(0.0, min(100.0, (similarity - 0.15) / 0.7 * 100)), 1)
    except (KeyError, OSError, ValueError, TypeError):
        return papers
    return papers


def assess_papers(papers: list[Paper], limit: int) -> list[Paper]:
    """Use a structured LLM rubric for the strongest heuristic candidates."""
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
        return papers
    for paper in papers[:limit]:
        prompt = (
            "你是严格的 LLM 训练与推理论文评审。仅依据给出的标题和摘要评估，不因作者或机构声望加分。"
            "只返回 JSON，不要 markdown："
            '{"summary_zh":"不超过100字","risk_zh":"最主要局限","relevance":0,"quality":0,'
            '"novelty":0,"practical":0,"confidence":0}。五个分数范围均为0到100；'
            "quality 关注基线、规模、消融和量化证据，novelty 关注相对常见方法的明确增量。\n\n"
            f"标题：{paper.title}\n摘要：{paper.abstract}"
        )
        try:
            result = _post("chat/completions", {
                "model": os.environ["OPENAI_MODEL"], "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1, "max_tokens": 350,
            })
            content = result["choices"][0]["message"]["content"].strip().removeprefix("```json").removesuffix("```").strip()
            assessment = json.loads(content)
            paper.llm_scores = {
                name: max(0.0, min(100.0, float(assessment[name])))
                for name in ["relevance", "quality", "novelty", "practical", "confidence"]
            }
            paper.summary_zh = str(assessment.get("summary_zh", "")).strip()[:300] or None
            paper.risk_zh = str(assessment.get("risk_zh", "")).strip()[:300] or None
        except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return papers


def summarize_in_chinese(papers: list[Paper]) -> list[Paper]:
    """Add concise Chinese reading notes when an OpenAI-compatible chat API is configured.

    A missing key deliberately leaves the collection usable: paper abstracts remain visible
    and no external text is transmitted.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not api_key or not model:
        return papers
    for paper in papers:
        if paper.summary_zh:
            continue
        prompt = (
            "用简体中文为这篇论文写一条不超过100字的阅读摘要。"
            "说明它解决的问题、核心方法和最重要的证据；保留必要英文技术词，不要夸大未证实的结论。\n\n"
            f"标题：{paper.title}\n摘要：{paper.abstract}"
        )
        try:
            result = _post("chat/completions", {
                "model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 180,
            })
            paper.summary_zh = result["choices"][0]["message"]["content"].strip()
        except (KeyError, OSError, ValueError, json.JSONDecodeError):
            # A source outage must not prevent a daily paper snapshot from being saved.
            continue
    return papers
