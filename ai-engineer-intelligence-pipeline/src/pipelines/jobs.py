"""Runs the configured job-board adapters. Greenhouse/Lever are structured_endpoint
sources (see config/sources.yaml); each posting already passes through the strict
24h freshness gate + fingerprint dedup inside GreenhouseJobsAdapter.fetch_and_parse.
Run via `python scripts/run_fresh_signals.py --kind jobs`."""
from __future__ import annotations

import asyncio
import logging

from src.crawlers.base import AsyncWorkerPool
from src.crawlers.jobs_crawler import GreenhouseJobsAdapter
from src.freshness.dedup import DedupCoordinator
from src.observability.logging import configure_logging, new_run_id

logger = logging.getLogger("pipeline.jobs")

# Known AI-company Greenhouse board tokens (public; the token is the URL slug the
# company chose, not a secret). Extend this list as needed.
DEFAULT_COMPANIES = ["openai", "anthropic", "scaleai", "cohere", "huggingface"]


async def run_jobs_pipeline(companies: list[str] | None = None, concurrency: int = 5):
    configure_logging()
    run_id = new_run_id()
    dedup = DedupCoordinator()
    adapter = GreenhouseJobsAdapter(companies=companies or DEFAULT_COMPANIES, dedup=dedup)
    pool = AsyncWorkerPool(adapter, concurrency=concurrency)
    results = await pool.run()
    logger.info("jobs_pipeline_complete", extra={"run_id": run_id, **pool.metrics})
    return results


if __name__ == "__main__":
    asyncio.run(run_jobs_pipeline())
