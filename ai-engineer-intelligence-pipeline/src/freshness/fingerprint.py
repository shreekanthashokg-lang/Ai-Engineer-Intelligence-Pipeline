"""Deterministic fingerprinting so multiple crawler nodes never double-process the
same news/job item, and re-runs are idempotent.

fingerprint = sha256(normalized_url + '|' + normalized_title + '|' + published_date_iso)

Rationale: URL alone isn't enough (tracking params / mirrors produce different URLs
for the same content); title alone isn't enough (title changes, syndication);
combining all three plus URL normalization gives a stable key that's cheap to
compute and safe to use as a DB UNIQUE constraint / Redis SETNX key across nodes.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "fbclid", "gclid"}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _TRACKING_PARAMS]
    query.sort()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    t = title.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def fingerprint(url: str, title: str, published_date_iso: str | None) -> str:
    key = f"{normalize_url(url)}|{normalize_title(title)}|{published_date_iso or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
