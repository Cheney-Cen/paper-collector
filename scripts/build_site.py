#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_collector.storage import canonical_paper_id, read_json


def build_dashboard(daily_root: Path, destination: Path) -> tuple[int, int, str]:
    if not any(daily_root.glob("*.json")):
        raise SystemExit("No daily paper data exists. Run scripts/collect.py first.")
    destination.mkdir(parents=True, exist_ok=True)
    daily_files = sorted(daily_root.glob("*.json"))
    history = [path.stem for path in daily_files]
    all_papers: dict[str, dict] = {}
    for path in daily_files:
        payload = read_json(path, {"date": path.stem, "papers": []})
        assert isinstance(payload, dict)
        (destination / path.name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        for paper in payload.get("papers", []):
            all_papers[canonical_paper_id(paper["paper_id"])] = paper
    latest = read_json(daily_files[-1], {"date": history[-1], "papers": []})
    assert isinstance(latest, dict)
    (destination / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    catalog = {
        "date": "全部历史",
        "selected_count": len(all_papers),
        "papers": sorted(all_papers.values(), key=lambda paper: paper.get("updated", ""), reverse=True),
    }
    (destination / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
    return len(history), len(all_papers), str(latest["date"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish all daily JSON snapshots to the static dashboard.")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="Kept for CLI compatibility; all editions are always rebuilt.")
    parser.parse_args()
    editions, papers, latest = build_dashboard(ROOT / "data" / "daily", ROOT / "site" / "data")
    print(f"Dashboard built with {editions} editions and {papers} unique papers; latest is {latest}.")


if __name__ == "__main__":
    main()
