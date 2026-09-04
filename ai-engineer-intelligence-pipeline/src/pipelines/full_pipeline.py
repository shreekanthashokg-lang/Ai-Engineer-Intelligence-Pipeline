"""Top-level orchestrator: runs Phase I (bulk) + Phase II (freshness) verticals,
then exports the 6-tab output. This is the single entry point the RUNBOOK points
to for a full end-to-end run once real network access + API keys are available.
"""
from __future__ import annotations

import asyncio
import logging

from src.observability.logging import configure_logging, new_run_id
from src.pipelines.jobs import run_jobs_pipeline
from src.pipelines.news import run_news_pipeline
from src.pipelines.research import run_research_pipeline

logger = logging.getLogger("pipeline.full")


async def run_full_pipeline():
    configure_logging()
    run_id = new_run_id()
    logger.info("full_pipeline_start", extra={"run_id": run_id})

    # Phase I: one-time bulk acquisition (startups/products need real per-source
    # endpoints configured — see config/sources.yaml + RUNBOOK.md).
    research_results = await run_research_pipeline(target=1000)

    # Phase II: 24h-fresh signals (run last, since freshness is relative to "now").
    news_results = await run_news_pipeline()
    jobs_results = await run_jobs_pipeline()

    logger.info("full_pipeline_complete", extra={
        "run_id": run_id,
        "research_count": len(research_results),
        "news_count": len(news_results),
        "jobs_count": len(jobs_results),
    })


if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
