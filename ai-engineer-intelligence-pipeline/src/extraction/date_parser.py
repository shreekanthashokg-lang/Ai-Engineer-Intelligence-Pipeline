"""Publication-date normalization.

Handles: ISO-8601 (with/without tz), common absolute formats, relative phrases
("2 hours ago", "yesterday", "3 days ago"), and extraction from JSON-LD /
OpenGraph / <meta> tags embedded in raw HTML. Everything is normalized to UTC.

Design rule: if we cannot establish a date with reasonable confidence, we return
(None, confidence=0.0) rather than guessing. Freshness checks (`src/freshness/`)
treat confidence < CONFIDENCE_THRESHOLD as "exclude from strict 24h output".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import parser as dateutil_parser

CONFIDENCE_THRESHOLD = 0.6

_RELATIVE_RE = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>second|minute|hour|day|week|month|year)s?\s*ago",
    re.IGNORECASE,
)
_JUST_NOW_RE = re.compile(r"\b(just now|moments ago)\b", re.IGNORECASE)
_YESTERDAY_RE = re.compile(r"\byesterday\b", re.IGNORECASE)
_TODAY_RE = re.compile(r"\btoday\b", re.IGNORECASE)

_UNIT_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,   # 30-day approximation, low confidence
    "year": 31536000,   # 365-day approximation, low confidence
}


@dataclass
class ParsedDate:
    value: Optional[datetime]
    confidence: float
    method: str  # 'iso' | 'relative' | 'json_ld' | 'meta_tag' | 'dateutil' | 'unresolved'


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_relative(text: str, now: Optional[datetime] = None) -> ParsedDate:
    now = now or datetime.now(timezone.utc)
    text = text.strip()

    if _JUST_NOW_RE.search(text):
        return ParsedDate(now, 0.9, "relative")

    if _YESTERDAY_RE.search(text):
        return ParsedDate(now - timedelta(days=1), 0.7, "relative")

    if _TODAY_RE.search(text) and "ago" not in text.lower():
        return ParsedDate(now, 0.6, "relative")

    m = _RELATIVE_RE.search(text)
    if m:
        num = int(m.group("num"))
        unit = m.group("unit").lower()
        seconds = _UNIT_SECONDS[unit] * num
        confidence = 0.9 if unit in ("second", "minute", "hour", "day", "week") else 0.4
        return ParsedDate(now - timedelta(seconds=seconds), confidence, "relative")

    return ParsedDate(None, 0.0, "unresolved")


def parse_iso(text: str) -> ParsedDate:
    text = text.strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return ParsedDate(_utc(dt), 1.0, "iso")
    except ValueError:
        return ParsedDate(None, 0.0, "unresolved")


def parse_with_dateutil(text: str) -> ParsedDate:
    try:
        dt = dateutil_parser.parse(text, fuzzy=True)
        return ParsedDate(_utc(dt), 0.75, "dateutil")
    except (ValueError, OverflowError):
        return ParsedDate(None, 0.0, "unresolved")


def extract_from_json_ld(html: str) -> ParsedDate:
    """Look for datePublished / dateCreated in <script type=application/ld+json> blocks."""
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for c in candidates:
            if not isinstance(c, dict):
                continue
            for key in ("datePublished", "dateCreated", "uploadDate"):
                if key in c:
                    parsed = parse_iso(str(c[key])) 
                    if parsed.value is None:
                        parsed = parse_with_dateutil(str(c[key]))
                    if parsed.value:
                        return ParsedDate(parsed.value, 0.95, "json_ld")
    return ParsedDate(None, 0.0, "unresolved")


def extract_from_meta_tags(html: str) -> ParsedDate:
    """OpenGraph / standard <meta> publication-date tags."""
    patterns = [
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']publish-date["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+itemprop=["\']datePublished["\'][^>]+content=["\']([^"\']+)["\']',
        r'<time[^>]+datetime=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            parsed = parse_iso(m.group(1))
            if parsed.value is None:
                parsed = parse_with_dateutil(m.group(1))
            if parsed.value:
                return ParsedDate(parsed.value, 0.85, "meta_tag")
    return ParsedDate(None, 0.0, "unresolved")


def normalize_publication_date(
    *, visible_text: Optional[str] = None, html: Optional[str] = None,
    now: Optional[datetime] = None,
) -> ParsedDate:
    """Best-effort pipeline: structured metadata first, then visible text, then bail."""
    if html:
        result = extract_from_json_ld(html)
        if result.value:
            return result
        result = extract_from_meta_tags(html)
        if result.value:
            return result

    if visible_text:
        result = parse_iso(visible_text)
        if result.value:
            return result
        result = parse_relative(visible_text, now=now)
        if result.value:
            return result
        result = parse_with_dateutil(visible_text)
        if result.value:
            return result

    return ParsedDate(None, 0.0, "unresolved")


def is_within_last_24h(parsed: ParsedDate, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if parsed.value is None or parsed.confidence < CONFIDENCE_THRESHOLD:
        return False
    return (now - parsed.value) <= timedelta(hours=24) and parsed.value <= now + timedelta(minutes=5)
