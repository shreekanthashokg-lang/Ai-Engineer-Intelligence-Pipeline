"""Extract lightweight page metadata (title, canonical URL, description) from raw
HTML using JSON-LD / OpenGraph / <title> in that priority order — mirrors the same
"structured first, heuristic fallback" pattern used in date_parser.py."""
from __future__ import annotations

import json
import re


def extract_title(html: str) -> str | None:
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return None


def extract_canonical_url(html: str, fallback_url: str) -> str:
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return fallback_url


def extract_json_ld_blocks(html: str) -> list[dict]:
    blocks = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        try:
            data = json.loads(m.group(1).strip())
            blocks.extend(data if isinstance(data, list) else [data])
        except json.JSONDecodeError:
            continue
    return blocks
