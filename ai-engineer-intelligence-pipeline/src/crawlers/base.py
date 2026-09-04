"""Scalable ingestion base: bounded async worker pool over a queue of source
targets, with retries, checkpointing, and idempotent writes. This is the piece
that lets the architecture scale from ~3k records in this trial to 500k+ purely by
raising `concurrency` / adding worker processes — no code changes, per the brief.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from src.extraction.schemas import Outcome

logger = logging.getLogger("crawler")


@dataclass
class CrawlItem:
    url: str
    source_name: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlOutcome:
    item: CrawlItem
    outcome: Outcome
    record: dict | None = None
    error: str | None = None


class Checkpoint:
    """Simple file-backed checkpoint so a killed/restarted run doesn't reprocess
    already-successful items. Swap for a Redis SET in a multi-node deployment —
    the interface stays identical."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._done: set[str] = set()
        if self.path.exists():
            self._done = set(json.loads(self.path.read_text() or "[]"))

    def is_done(self, key: str) -> bool:
        return key in self._done

    def mark_done(self, key: str) -> None:
        self._done.add(key)
        self.path.write_text(json.dumps(sorted(self._done)))


class BaseSourceAdapter(ABC):
    """One adapter per source. Implements discovery (paginated) + fetch + parse.
    Priority for access method, per the brief's anti-bot strategy:
    official API > RSS/feed > structured endpoint > plain HTTP > Playwright
    (public JS-rendered pages only) > documented as inaccessible."""

    source_name: str

    @abstractmethod
    async def discover(self) -> AsyncIterator[CrawlItem]:
        """Yield CrawlItems (paginated) to fetch. Must be resumable/idempotent."""
        raise NotImplementedError

    @abstractmethod
    async def fetch_and_parse(self, item: CrawlItem) -> CrawlOutcome:
        raise NotImplementedError


class AsyncWorkerPool:
    def __init__(self, adapter: BaseSourceAdapter, *, concurrency: int = 10, checkpoint_path: str | None = None):
        self.adapter = adapter
        self.concurrency = concurrency
        self.checkpoint = Checkpoint(checkpoint_path or f"data/processed/.checkpoint_{adapter.source_name}.json")
        self.metrics = {
            "pages_processed": 0, "records_valid": 0, "records_invalid": 0,
            "records_duplicate": 0, "network_errors": 0, "retries": 0,
        }

    async def run(self, *, max_items: int | None = None) -> list[CrawlOutcome]:
        queue: asyncio.Queue[CrawlItem] = asyncio.Queue(maxsize=self.concurrency * 4)
        results: list[CrawlOutcome] = []
        producer_done = asyncio.Event()

        async def producer():
            count = 0
            async for item in self.adapter.discover():
                if max_items and count >= max_items:
                    break
                if self.checkpoint.is_done(item.url):
                    continue
                await queue.put(item)
                count += 1
            producer_done.set()

        async def worker(worker_id: int):
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    if producer_done.is_set() and queue.empty():
                        return
                    continue
                try:
                    outcome = await self.adapter.fetch_and_parse(item)
                except Exception as e:  # noqa: BLE001 - never let one item kill the pool
                    outcome = CrawlOutcome(item, Outcome.FAILED, error=str(e))
                    self.metrics["network_errors"] += 1

                self.metrics["pages_processed"] += 1
                if outcome.outcome == Outcome.SUCCESS:
                    self.metrics["records_valid"] += 1
                    self.checkpoint.mark_done(item.url)
                elif outcome.outcome == Outcome.DUPLICATE:
                    self.metrics["records_duplicate"] += 1
                    self.checkpoint.mark_done(item.url)
                elif outcome.outcome in (Outcome.INVALID, Outcome.FAILED):
                    self.metrics["records_invalid"] += 1
                    # NOT marked done -> eligible for reprocessing on next run

                results.append(outcome)
                queue.task_done()

        workers = [asyncio.create_task(worker(i)) for i in range(self.concurrency)]
        await producer()
        await asyncio.gather(*workers)
        logger.info("pool_finished", extra={"source": self.adapter.source_name, **self.metrics})
        return results
