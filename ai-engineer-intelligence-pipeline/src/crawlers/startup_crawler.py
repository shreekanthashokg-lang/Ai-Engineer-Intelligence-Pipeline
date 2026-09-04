"""Startup adapter template. Demonstrates the raw -> clean -> metadata -> LLM ->
validate -> resolve -> dedup -> store pipeline required by the brief for the
Startup vertical. Written against a generic paginated JSON directory endpoint
shape (matches YC's public company listing API contract); swap `list_endpoint`
for any other structured startup directory without touching the pipeline logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from src.crawlers.async_http import get
from src.crawlers.base import BaseSourceAdapter, CrawlItem, CrawlOutcome
from src.entity_resolution.resolver import EntityResolver
from src.extraction.schemas import (ExtractionMethod, Outcome, Provenance, SourceRef,
                                     StartupContent, StartupData, StartupRecord)


class StartupDirectoryAdapter(BaseSourceAdapter):
    """Generic adapter for a paginated JSON startup directory. `list_endpoint` must
    return {"items": [...], "next_page": <url-or-null>}; `parse_item` extracts
    (entity_name, employee_count) from one directory item — override per source."""

    def __init__(self, source_name: str, list_endpoint: str, resolver: EntityResolver | None = None):
        self.source_name = source_name
        self.list_endpoint = list_endpoint
        self.resolver = resolver or EntityResolver()

    async def discover(self) -> AsyncIterator[CrawlItem]:
        url = self.list_endpoint
        while url:
            resp = await get(url)
            data = resp.json()
            for entry in data.get("items", []):
                yield CrawlItem(url=entry.get("url", url), source_name=self.source_name, meta={"entry": entry})
            url = data.get("next_page")

    async def fetch_and_parse(self, item: CrawlItem) -> CrawlOutcome:
        entry = item.meta["entry"]
        raw_name = entry.get("name")
        if not raw_name:
            return CrawlOutcome(item, Outcome.INVALID, error="missing_entity_name")

        resolution = self.resolver.resolve(raw_name, entity_type="STARTUP", source_url=item.url)
        employee_count = entry.get("employee_count")  # null if the source doesn't expose it — never guessed

        now = datetime.now(timezone.utc)
        try:
            record = StartupRecord(
                source=SourceRef(name=self.source_name, url=item.url),
                content=StartupContent(entityName=resolution.canonical_name, data=StartupData(employeeCount=employee_count)),
                provenance=Provenance(
                    source_name=self.source_name, source_url=item.url, retrieved_at=now,
                    extraction_method=ExtractionMethod.DIRECT_FIELD, confidence=resolution.confidence,
                    raw_hash=Provenance.hash_raw(str(entry)),
                ),
            )
        except Exception as e:  # noqa: BLE001
            return CrawlOutcome(item, Outcome.INVALID, error=str(e))

        return CrawlOutcome(item, Outcome.SUCCESS, record=record.model_dump(mode="json"))
