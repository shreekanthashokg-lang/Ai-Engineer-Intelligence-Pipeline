"""Research paper adapter. Access method: official_api (ArXiv Atom API — no key
required, documented rate limit ~1 req/3s). Correlates each paper's abstract/PDF
page for a GitHub link, then enriches with live stars via GitHubEnricher.

ArXiv's API is paginated via `start` + `max_results`, which is exactly the
resumable-pagination contract `BaseSourceAdapter.discover()` expects — raising
`--target` just walks further into the same paginated stream, no code change.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import AsyncIterator

from src.crawlers.async_http import get
from src.crawlers.base import BaseSourceAdapter, CrawlItem, CrawlOutcome
from src.crawlers.github_enrichment import GitHubEnricher
from src.extraction.schemas import (ExtractionMethod, Outcome, Provenance,
                                     ResearchPaperContent, ResearchPaperRecord, SourceRef)

ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_GITHUB_LINK_RE = re.compile(r"https?://github\.com/[\w.\-]+/[\w.\-]+")


class ResearchPaperAdapter(BaseSourceAdapter):
    source_name = "arxiv"

    def __init__(self, query: str = "cat:cs.AI", page_size: int = 50):
        self.query = query
        self.page_size = page_size
        self.github = GitHubEnricher()

    async def discover(self) -> AsyncIterator[CrawlItem]:
        start = 0
        while True:
            resp = await get(ARXIV_API, params={
                "search_query": self.query, "start": start, "max_results": self.page_size,
                "sortBy": "submittedDate", "sortOrder": "descending",
            })
            root = ET.fromstring(resp.text)
            entries = root.findall("atom:entry", ATOM_NS)
            if not entries:
                return
            for entry in entries:
                paper_id = entry.find("atom:id", ATOM_NS).text
                yield CrawlItem(url=paper_id, source_name=self.source_name, meta={"entry_xml": ET.tostring(entry).decode()})
            start += self.page_size

    async def fetch_and_parse(self, item: CrawlItem) -> CrawlOutcome:
        entry = ET.fromstring(item.meta["entry_xml"])
        title = entry.find("atom:title", ATOM_NS).text.strip()
        summary = entry.find("atom:summary", ATOM_NS).text or ""
        authors = [a.find("atom:name", ATOM_NS).text for a in entry.findall("atom:author", ATOM_NS)]
        published = entry.find("atom:published", ATOM_NS).text

        github_match = _GITHUB_LINK_RE.search(summary)
        github_url, github_stars = None, None
        if github_match:
            github_url = github_match.group(0)
            meta = await self.github.get_stars(github_url)
            github_stars = meta.stars
            if meta.moved_to:
                github_url = meta.moved_to

        try:
            record = ResearchPaperRecord(
                source=SourceRef(name=self.source_name, url=item.url),
                content=ResearchPaperContent(
                    title=title, authors=authors, paper_url=item.url,
                    github_url=github_url, github_stars=github_stars, published_date=published,
                ),
                provenance=Provenance(
                    source_name=self.source_name, source_url=item.url,
                    retrieved_at=published, extraction_method=ExtractionMethod.DIRECT_FIELD,
                    confidence=1.0, raw_hash=Provenance.hash_raw(item.meta["entry_xml"]),
                ),
            )
        except Exception as e:  # noqa: BLE001
            return CrawlOutcome(item, Outcome.INVALID, error=str(e))

        return CrawlOutcome(item, Outcome.SUCCESS, record=record.model_dump(mode="json"))
