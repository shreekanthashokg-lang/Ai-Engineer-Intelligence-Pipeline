"""CLI wrapper for Phase II 24h-fresh signal ingestion.

Usage:
  python scripts/run_fresh_signals.py --kind news
  python scripts/run_fresh_signals.py --kind jobs
"""
import argparse
import asyncio
import sys

sys.path.insert(0, ".")

from src.pipelines.jobs import run_jobs_pipeline
from src.pipelines.news import run_news_pipeline


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["news", "jobs"], required=True)
    args = parser.parse_args()

    if args.kind == "news":
        results = await run_news_pipeline()
    else:
        results = await run_jobs_pipeline()

    successes = sum(1 for r in results if r.outcome.value == "SUCCESS")
    print(f"{args.kind}: {successes} fresh records ingested out of {len(results)} discovered.")


if __name__ == "__main__":
    asyncio.run(main())
