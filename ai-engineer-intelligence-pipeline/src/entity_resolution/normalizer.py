"""Deterministic normalization pipeline applied before any matching happens.
Order matters: unicode -> whitespace -> punctuation -> legal-suffix removal -> case
-> token normalization. This is intentionally boring and reproducible — no fuzzy
logic lives here, that's `resolver.py`'s job with explicit confidence scoring.
"""
from __future__ import annotations

import re
import unicodedata

_LEGAL_SUFFIXES = [
    r"\bincorporated\b", r"\binc\.?\b", r"\bllc\.?\b", r"\bltd\.?\b", r"\blimited\b",
    r"\bcorp\.?\b", r"\bcorporation\b", r"\bco\.?\b", r"\bplc\b", r"\bgmbh\b",
    r"\bpbc\b", r"\bpvt\.?\b", r"\bprivate\b", r"\bs\.?a\.?s\.?\b", r"\bb\.?v\.?\b",
    r"\bag\b",
]
_LEGAL_SUFFIX_RE = re.compile("|".join(_LEGAL_SUFFIXES), re.IGNORECASE)
_PUNCT_RE = re.compile(r"[.,'\"“”‘’!?;:()\[\]{}]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def strip_punctuation(text: str) -> str:
    return _PUNCT_RE.sub("", text)


def strip_legal_suffix(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = _LEGAL_SUFFIX_RE.sub("", text).strip()
    return text


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_name(raw: str) -> str:
    """Full pipeline: unicode -> whitespace -> punctuation -> legal suffix -> case
    -> token normalization. Returns the normalized-but-still-human-readable form
    used as the join key for exact matching."""
    text = normalize_unicode(raw)
    text = collapse_whitespace(text)
    text = strip_punctuation(text)
    text = strip_legal_suffix(text)
    text = collapse_whitespace(text)
    text = text.lower()
    return text
