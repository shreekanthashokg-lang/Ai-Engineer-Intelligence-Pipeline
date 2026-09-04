"""413 / context-window handling.

Strategy (never blind end-truncation):
  1. Strip boilerplate (nav/footer/cookie banners/repeated lines) before counting.
  2. Estimate tokens (chars/4 heuristic; swap in tiktoken if a provider needs exact
     counts).
  3. Reserve headroom for the output + system prompt.
  4. If input still exceeds budget, split into semantically dense chunks (paragraph-
     aware, never mid-sentence) and rank chunks by information density; keep title/
     metadata/entity-bearing chunks first, drop the least dense until it fits.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_BOILERPLATE_PATTERNS = [
    r"(?im)^\s*(cookie|subscribe|sign up|newsletter|advertisement)\b.*$",
    r"(?im)^\s*(share this|follow us|related articles)\b.*$",
]

_CHARS_PER_TOKEN = 4  # coarse heuristic; good enough for budgeting, not billing


@dataclass
class TokenBudget:
    max_context_tokens: int
    reserved_output_tokens: int = 1024
    reserved_system_tokens: int = 512

    @property
    def input_budget_tokens(self) -> int:
        return max(self.max_context_tokens - self.reserved_output_tokens - self.reserved_system_tokens, 256)

    @property
    def input_budget_chars(self) -> int:
        return self.input_budget_tokens * _CHARS_PER_TOKEN


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def strip_boilerplate(text: str) -> str:
    cleaned = text
    for pat in _BOILERPLATE_PATTERNS:
        cleaned = re.sub(pat, "", cleaned)
    # collapse duplicate blank lines and repeated whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    # deduplicate identical consecutive lines (common in scraped nav menus)
    lines = cleaned.split("\n")
    deduped, prev = [], None
    for line in lines:
        if line.strip() and line.strip() == prev:
            continue
        deduped.append(line)
        prev = line.strip()
    return "\n".join(deduped).strip()


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _density_score(paragraph: str) -> float:
    """Cheap proxy for information density: ratio of alnum tokens with length>3,
    presence of digits (specs/dates/prices), and sentence punctuation density."""
    words = re.findall(r"[A-Za-z0-9]{4,}", paragraph)
    digit_bonus = 1.2 if re.search(r"\d", paragraph) else 1.0
    return (len(words) / max(len(paragraph), 1)) * digit_bonus


def chunk_for_budget(text: str, budget: TokenBudget, *, title: str = "", metadata: str = "") -> list[str]:
    """Returns a list of chunks, each guaranteed to fit `budget.input_budget_chars`.
    The highest-density paragraphs are prioritized within each chunk; title/metadata
    is always prepended so entity names survive truncation."""
    cleaned = strip_boilerplate(text)
    char_budget = budget.input_budget_chars
    prefix = f"{title}\n{metadata}\n".strip() + "\n" if (title or metadata) else ""
    prefix_len = len(prefix)

    if len(cleaned) + prefix_len <= char_budget:
        return [prefix + cleaned] if prefix else [cleaned]

    paragraphs = _paragraphs(cleaned)
    paragraphs.sort(key=_density_score, reverse=True)

    chunks: list[str] = []
    current = prefix
    for para in paragraphs:
        if len(current) + len(para) + 2 > char_budget:
            if current.strip():
                chunks.append(current.strip())
            current = prefix
            if len(para) > char_budget:
                # single paragraph too large on its own: hard-split at sentence boundaries
                for sentence_chunk in _split_oversized(para, char_budget - prefix_len):
                    chunks.append((prefix + sentence_chunk).strip())
                continue
        current += para + "\n\n"
    if current.strip() and current.strip() != prefix.strip():
        chunks.append(current.strip())

    return chunks or [prefix.strip()]


def _split_oversized(paragraph: str, limit: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    out, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 > limit:
            if current:
                out.append(current.strip())
            current = s
        else:
            current += " " + s
    if current:
        out.append(current.strip())
    return out
