"""CLI wrapper for Phase I bulk acquisition. Requires open network access to the
configured source (see RUNBOOK.md) — will raise connection errors in a sandboxed
environment, by design (no data is fabricated as a fallback).

Usage:
  python scripts/run_bulk_ingestion.py --source arxiv --target 1000
  python scripts/run_bulk_ingestion.py --source ycombinator_directory --target 1000 --concurrency 20
"""
import argparse
import asyncio
import sys

sys.path.insert(0, ".")

import yaml

from src.pipelines.products import run_products_pipeline
from src.pipelines.research import run_research_pipeline
from src.pipelines.startups import run_startups_pipeline


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    with open("config/sources.yaml") as f:
        config = yaml.safe_load(f)

    if args.source == "arxiv":
        await run_research_pipeline(target=args.target, concurrency=args.concurrency)
        return

    for category in ("startups", "products"):
        for src in config.get(category, []):
            if src["name"] == args.source:
                if src["access_method"] == "unavailable_documented":
                    print(f"[SKIPPED] '{args.source}' is documented as unavailable: {src.get('notes')}")
                    return
                endpoint = src.get("endpoint")
                if not endpoint:
                    print(f"[ERROR] '{args.source}' has no endpoint configured in sources.yaml")
                    return
                runner = run_startups_pipeline if category == "startups" else run_products_pipeline
                await runner(args.source, endpoint, target=args.target, concurrency=args.concurrency)
                return

    print(f"[ERROR] Unknown source '{args.source}'. Check config/sources.yaml.")


if __name__ == "__main__":
    asyncio.run(main())
