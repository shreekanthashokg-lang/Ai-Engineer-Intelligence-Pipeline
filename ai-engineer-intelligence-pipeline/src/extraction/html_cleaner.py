"""Strip navigation/script/style noise before full-text extraction or LLM input."""
from __future__ import annotations

import re

_STRIP_TAGS_RE = re.compile(r"<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]{2,}")
_BLANKLINES_RE = re.compile(r"\n{3,}")


def strip_html_to_text(html: str) -> str:
    cleaned = _STRIP_TAGS_RE.sub(" ", html)
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = _WS_RE.sub(" ", cleaned)
    cleaned = _BLANKLINES_RE.sub("\n\n", cleaned)
    return cleaned.strip()


def extract_full_text(html: str) -> str:
    """Preferred path: trafilatura (handles article-body heuristics well).
    Falls back to the naive tag-stripper if trafilatura isn't available or
    returns nothing (e.g. non-article pages)."""
    try:
        import trafilatura
        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        if extracted:
            return extracted.strip()
    except ImportError:
        pass
    return strip_html_to_text(html)
