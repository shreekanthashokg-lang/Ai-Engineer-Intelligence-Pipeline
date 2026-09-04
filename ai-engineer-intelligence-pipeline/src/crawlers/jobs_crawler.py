"""Jobs adapter. Access method: structured_endpoint — Greenhouse and Lever both
expose public, unauthenticated JSON APIs per company (`boards-api.greenhouse.io`,
`api.lever.co`), which is a far more reliable and legitimate signal source than
scraping aggregator search-result pages that tend to be JS-heavy and bot-defended.

Role-family normalization maps messy raw titles to a small controlled taxonomy
without discarding the original — `raw_title` is always preserved.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import AsyncIterator

from src.crawlers.async_http import get
from src.crawlers.base import BaseSourceAdapter, CrawlItem, CrawlOutcome
from src.extraction.date_parser import is_within_last_24h, parse_iso
from src.extraction.schemas import (ExtractionMethod, JobContent, JobRecord, Outcome,
                                     Provenance, SourceRef)
from src.freshness.dedup import DedupCoordinator
from src.freshness.fingerprint import fingerprint

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

_ROLE_FAMILY_MAP = {
    r"machine learning engineer|ml engineer": "Machine Learning Engineering",
    r"ai engineer|applied ai engineer": "AI Engineering",
    r"research scientist|research engineer": "Research",
    r"data scientist": "Data Science",
    r"data engineer": "Data Engineering",
    r"software engineer|swe": "Software Engineering",
    r"product manager": "Product",
    r"devops|sre|infrastructure": "Infrastructure",
}

_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)


def normalize_role_family(raw_title: str) -> str | None:
    for pattern, family in _ROLE_FAMILY_MAP.items():
        if re.search(pattern, raw_title, re.IGNORECASE):
            return family
    return None


class GreenhouseJobsAdapter(BaseSourceAdapter):
    source_name = "greenhouse"

    def __init__(self, companies: list[str], dedup: DedupCoordinator | None = None):
        self.companies = companies  # e.g. ["openai", "anthropic", "scaleai"]
        self.dedup = dedup or DedupCoordinator()

    async def discover(self) -> AsyncIterator[CrawlItem]:
        for company in self.companies:
            url = GREENHOUSE_API.format(company=company)
            resp = await get(url)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for job in data.get("jobs", []):
                yield CrawlItem(url=job.get("absolute_url", url), source_name=self.source_name,
                                 meta={"company": company, "job": job})

    async def fetch_and_parse(self, item: CrawlItem) -> CrawlOutcome:
        job = item.meta["job"]
        raw_title = job.get("title", "")
        updated_at = job.get("updated_at")
        now = datetime.now(timezone.utc)

        parsed_date = parse_iso(updated_at) if updated_at else None
        if not parsed_date or not parsed_date.value:
            return CrawlOutcome(item, Outcome.INVALID, error="unparseable_date")
        if not is_within_last_24h(parsed_date, now=now):
            return CrawlOutcome(item, Outcome.STALE, error="outside_24h_window")

        fp = fingerprint(item.url, raw_title, parsed_date.value.isoformat())
        if not await self.dedup.claim(fp):
            return CrawlOutcome(item, Outcome.DUPLICATE)

        location = (job.get("location") or {}).get("name", "")
        is_remote = bool(_REMOTE_RE.search(raw_title) or _REMOTE_RE.search(location))

        record = JobRecord(
            source=SourceRef(name=self.source_name, url=item.url),
            content=JobContent(
                company=item.meta["company"], role=raw_title, date=parsed_date.value,
                is_remote=is_remote, role_family=normalize_role_family(raw_title), raw_title=raw_title,
            ),
            provenance=Provenance(
                source_name=self.source_name, source_url=item.url, retrieved_at=now,
                extraction_method=ExtractionMethod.DIRECT_FIELD, confidence=parsed_date.confidence,
                raw_hash=Provenance.hash_raw(str(job)),
            ),
        )
        return CrawlOutcome(item, Outcome.SUCCESS, record=record.model_dump(mode="json"))
