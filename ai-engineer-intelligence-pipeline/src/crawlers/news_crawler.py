"""News adapter. Access method: RSS (priority-2 per the anti-bot strategy — official
feeds are cheap, don't require JS rendering, and were explicitly designed by the
publisher to be machine-read, unlike defeating their bot protection would be).

Applies the strict 24h freshness gate + fingerprint dedup before yielding SUCCESS,
so a source returning 50 items in its feed but only 3 fresh ones correctly reports
47 STALE outcomes rather than 47 successes.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import AsyncIterator

from src.crawlers.async_http import get
from src.crawlers.base import BaseSourceAdapter, CrawlItem, CrawlOutcome
from src.extraction.content_extractor import extract_page
from src.extraction.date_parser import is_within_last_24h, parse_with_dateutil
from src.extraction.schemas import (ExtractionMethod, NewsContent, NewsRecord, Outcome,
                                     Provenance, SourceRef)
from src.freshness.dedup import DedupCoordinator
from src.freshness.fingerprint import fingerprint


class NewsRSSAdapter(BaseSourceAdapter):
    def __init__(self, source_name: str, feed_url: str, dedup: DedupCoordinator | None = None):
        self.source_name = source_name
        self.feed_url = feed_url
        self.dedup = dedup or DedupCoordinator()

    async def discover(self) -> AsyncIterator[CrawlItem]:
        resp = await get(self.feed_url)
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item"):
            link = item.findtext("link")
            title = item.findtext("title") or ""
            pub_date = item.findtext("pubDate")
            if not link:
                continue
            yield CrawlItem(url=link, source_name=self.source_name, meta={"rss_title": title, "rss_pubdate": pub_date})

    async def fetch_and_parse(self, item: CrawlItem) -> CrawlOutcome:
        now = datetime.now(timezone.utc)
        parsed_date = parse_with_dateutil(item.meta["rss_pubdate"]) if item.meta.get("rss_pubdate") else None
        if not parsed_date or not parsed_date.value:
            return CrawlOutcome(item, Outcome.INVALID, error="unparseable_pubdate")

        if not is_within_last_24h(parsed_date, now=now):
            return CrawlOutcome(item, Outcome.STALE, error="outside_24h_window")

        fp = fingerprint(item.url, item.meta["rss_title"], parsed_date.value.isoformat())
        if not await self.dedup.claim(fp):
            return CrawlOutcome(item, Outcome.DUPLICATE)

        page_resp = await get(item.url)
        extracted = extract_page(page_resp.text, item.url)

        record = NewsRecord(
            source=SourceRef(name=self.source_name, url=item.url),
            content=NewsContent(
                title=extracted.title or item.meta["rss_title"], url=extracted.canonical_url,
                published_at=parsed_date.value, full_text=extracted.full_text, content_hash=fp,
            ),
            provenance=Provenance(
                source_name=self.source_name, source_url=item.url, retrieved_at=now,
                extraction_method=ExtractionMethod.DETERMINISTIC, confidence=parsed_date.confidence,
                raw_hash=Provenance.hash_raw(page_resp.text),
            ),
        )
        return CrawlOutcome(item, Outcome.SUCCESS, record=record.model_dump(mode="json"))
