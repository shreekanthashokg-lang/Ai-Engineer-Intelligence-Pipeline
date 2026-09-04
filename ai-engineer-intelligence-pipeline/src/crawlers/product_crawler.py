"""Product adapter template — same shape as StartupDirectoryAdapter, targeting a
paginated product-listing endpoint (e.g. Product Hunt GraphQL, mapped to this
generic {"items":[...], "next_page": ...} shape by a thin per-source translator
kept in `pipelines/products.py`). Pricing model is only ever set from an explicit
signal on the source page; anything else stays PricingModel.UNKNOWN.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import AsyncIterator

from src.crawlers.async_http import get
from src.crawlers.base import BaseSourceAdapter, CrawlItem, CrawlOutcome
from src.entity_resolution.resolver import EntityResolver
from src.extraction.schemas import (ExtractionMethod, Outcome, PricingModel, ProductContent,
                                     ProductRecord, Provenance, SourceRef)

_PRICING_SIGNALS = [
    (re.compile(r"\bfree forever\b|\b100% free\b", re.IGNORECASE), PricingModel.FREE),
    (re.compile(r"\bfreemium\b|\bfree plan\b.*\bpro plan\b", re.IGNORECASE), PricingModel.FREEMIUM),
    (re.compile(r"\benterprise pricing\b|\bcontact sales\b", re.IGNORECASE), PricingModel.ENTERPRISE),
    (re.compile(r"\$\d+(\.\d+)?\s*/\s*(mo|month|user)", re.IGNORECASE), PricingModel.PAID),
]


def infer_pricing_model(text: str) -> PricingModel:
    for pattern, model in _PRICING_SIGNALS:
        if pattern.search(text):
            return model
    return PricingModel.UNKNOWN  # never guessed beyond an explicit textual signal


class ProductDirectoryAdapter(BaseSourceAdapter):
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
        startup_name_raw = entry.get("maker_name") or entry.get("company")
        if not startup_name_raw:
            return CrawlOutcome(item, Outcome.INVALID, error="missing_startup_name")

        resolution = self.resolver.resolve(startup_name_raw, entity_type="STARTUP", source_url=item.url)
        pricing_text = entry.get("pricing_text", "") or entry.get("description", "")
        pricing_model = infer_pricing_model(pricing_text)

        now = datetime.now(timezone.utc)
        try:
            record = ProductRecord(
                source=SourceRef(name=self.source_name, url=item.url),
                content=ProductContent(startupName=resolution.canonical_name, pricingModel=pricing_model),
                provenance=Provenance(
                    source_name=self.source_name, source_url=item.url, retrieved_at=now,
                    extraction_method=ExtractionMethod.DETERMINISTIC, confidence=resolution.confidence,
                    raw_hash=Provenance.hash_raw(str(entry)),
                ),
            )
        except Exception as e:  # noqa: BLE001
            return CrawlOutcome(item, Outcome.INVALID, error=str(e))

        return CrawlOutcome(item, Outcome.SUCCESS, record=record.model_dump(mode="json"))
