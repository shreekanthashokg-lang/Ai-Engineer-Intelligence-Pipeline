"""Wires a product-directory adapter into the async worker pool. Run via
`python scripts/run_bulk_ingestion.py --source producthunt`."""
from __future__ import annotations

import logging

from src.crawlers.base import AsyncWorkerPool
from src.crawlers.product_crawler import ProductDirectoryAdapter
from src.entity_resolution.mapping_log import flush_mapping_log
from src.observability.logging import configure_logging, new_run_id

logger = logging.getLogger("pipeline.products")


async def run_products_pipeline(source_name: str, list_endpoint: str, target: int = 1000, concurrency: int = 10):
    configure_logging()
    run_id = new_run_id()
    adapter = ProductDirectoryAdapter(source_name=source_name, list_endpoint=list_endpoint)
    pool = AsyncWorkerPool(adapter, concurrency=concurrency)
    results = await pool.run(max_items=target)
    flush_mapping_log(adapter.resolver)
    logger.info("products_pipeline_complete", extra={"run_id": run_id, **pool.metrics})
    return results


if __name__ == "__main__":
    import asyncio
    import sys
    asyncio.run(run_products_pipeline(sys.argv[1] if len(sys.argv) > 1 else "producthunt",
                                       sys.argv[2] if len(sys.argv) > 2 else "https://example.invalid/api/products"))
