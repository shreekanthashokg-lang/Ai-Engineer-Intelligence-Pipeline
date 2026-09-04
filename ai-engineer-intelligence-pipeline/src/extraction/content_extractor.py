"""Ties html_cleaner + metadata + date_parser together into one call per fetched page."""
from __future__ import annotations

from dataclasses import dataclass

from src.extraction.date_parser import ParsedDate, normalize_publication_date
from src.extraction.html_cleaner import extract_full_text
from src.extraction.metadata import extract_canonical_url, extract_title


@dataclass
class ExtractedPage:
    title: str | None
    canonical_url: str
    full_text: str
    published: ParsedDate


def extract_page(html: str, source_url: str) -> ExtractedPage:
    title = extract_title(html)
    canonical_url = extract_canonical_url(html, source_url)
    full_text = extract_full_text(html)
    published = normalize_publication_date(html=html, visible_text=full_text[:2000])
    return ExtractedPage(title=title, canonical_url=canonical_url, full_text=full_text, published=published)
