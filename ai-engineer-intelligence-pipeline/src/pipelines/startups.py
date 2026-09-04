"""Wires a startup-directory adapter into the async worker pool. Run via
`python scripts/run_bulk_ingestion.py --source ycombinator_directory`."""
from __future__ import annotations

import logging

from src.crawlers.base import AsyncWorkerPool
from src.crawlers.startup_crawler import StartupDirectoryAdapter
from src.entity_resolution.mapping_log import flush_mapping_log
from src.observability.logging import configure_logging, new_run_id

logger = logging.getLogger("pipeline.startups")


async def run_startups_pipeline(source_name: str, list_endpoint: str, target: int = 1000, concurrency: int = 10):
    configure_logging()
    run_id = new_run_id()
    adapter = StartupDirectoryAdapter(source_name=source_name, list_endpoint=list_endpoint)
    pool = AsyncWorkerPool(adapter, concurrency=concurrency)
    results = await pool.run(max_items=target)
    flush_mapping_log(adapter.resolver)
    logger.info("startups_pipeline_complete", extra={"run_id": run_id, **pool.metrics})
    return results


if __name__ == "__main__":
    import asyncio
    import sys
    asyncio.run(run_startups_pipeline(sys.argv[1] if len(sys.argv) > 1 else "ycombinator_directory",
                                       sys.argv[2] if len(sys.argv) > 2 else "https://example.invalid/api/companies"))
