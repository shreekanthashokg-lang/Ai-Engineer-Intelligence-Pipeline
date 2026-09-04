"""Runs all 5 configured news RSS sources concurrently, each already enforcing the
strict 24h freshness gate + fingerprint dedup inside NewsRSSAdapter.fetch_and_parse.
Run via `python scripts/run_fresh_signals.py --kind news`."""
from __future__ import annotations

import asyncio
import logging

import yaml

from src.crawlers.base import AsyncWorkerPool
from src.crawlers.news_crawler import NewsRSSAdapter
from src.freshness.dedup import DedupCoordinator
from src.observability.logging import configure_logging, new_run_id

logger = logging.getLogger("pipeline.news")


async def run_news_pipeline(config_path: str = "config/sources.yaml", concurrency: int = 5):
    configure_logging()
    run_id = new_run_id()
    with open(config_path) as f:
        sources = yaml.safe_load(f)["news"]

    dedup = DedupCoordinator()  # shared across all 5 sources so cross-source syndication also dedups
    all_results = []
    for src in sources:
        if src["access_method"] != "rss":
            logger.info("skipping_non_rss_news_source", extra={"source": src["name"]})
            continue
        adapter = NewsRSSAdapter(source_name=src["name"], feed_url=src["endpoint"], dedup=dedup)
        pool = AsyncWorkerPool(adapter, concurrency=concurrency)
        results = await pool.run()
        all_results.extend(results)
        logger.info("news_source_complete", extra={"run_id": run_id, "source": src["name"], **pool.metrics})
    return all_results


if __name__ == "__main__":
    asyncio.run(run_news_pipeline())
