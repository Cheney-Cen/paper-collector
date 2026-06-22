#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_collector.arxiv import fetch_recent
from paper_collector.config import load_settings
from paper_collector.llm import add_semantic_scores, assess_papers, summarize_in_chinese
from paper_collector.ranking import rank, rescore, select_diverse
from paper_collector.storage import save_daily, update_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and rank recent arXiv papers.")
    parser.add_argument("--config", default=ROOT / "topics.toml", type=Path)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--offline", action="store_true", help="Build from the existing daily file without a network request.")
    args = parser.parse_args()
    settings = load_settings(args.config)
    if args.offline:
        print("Offline mode does not fetch new papers.")
        return
    user_agent = os.environ.get("ARXIV_USER_AGENT", "paper-collector/0.1 (personal research use)")
    papers = fetch_recent(settings.arxiv_categories, settings.candidate_limit, user_agent)
    add_semantic_scores(papers, settings.topics)
    shortlist = rank(
        papers, settings.topics, settings.shortlist_limit, settings.anchor_terms,
        settings.shortlist_limit, exploration_slots=0,
    )
    assess_papers(shortlist, settings.llm_assessment_limit)
    rescore(shortlist)
    ranked = select_diverse(shortlist, settings.daily_limit, settings.exploration_slots)
    summarize_in_chinese(ranked)
    save_daily(ROOT / "data", args.date, ranked)
    update_index(ROOT / "data", ranked)
    print(f"Saved {len(ranked)} selected papers for {args.date.isoformat()}.")


if __name__ == "__main__":
    main()
