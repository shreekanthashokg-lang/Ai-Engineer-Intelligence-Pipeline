"""Wires the research-paper adapter into the async worker pool and reports outcome
metrics. Run via `python scripts/run_bulk_ingestion.py --source arxiv`."""
from __future__ import annotations

import logging

from src.crawlers.base import AsyncWorkerPool
from src.crawlers.research_crawler import ResearchPaperAdapter
from src.observability.logging import configure_logging, new_run_id

logger = logging.getLogger("pipeline.research")


async def run_research_pipeline(target: int = 1000, concurrency: int = 10, query: str = "cat:cs.AI"):
    configure_logging()
    run_id = new_run_id()
    adapter = ResearchPaperAdapter(query=query)
    pool = AsyncWorkerPool(adapter, concurrency=concurrency)
    results = await pool.run(max_items=target)
    logger.info("research_pipeline_complete", extra={"run_id": run_id, **pool.metrics})
    return results


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_research_pipeline())
