"""Thin async HTTP client wrapper shared by adapters. Translates HTTP-level 429/413
into the shared retry exceptions so every adapter gets consistent backoff behavior
without reimplementing it."""
from __future__ import annotations

import httpx

from src.llm.retry import PayloadTooLargeError, RateLimitError

DEFAULT_HEADERS = {"User-Agent": "ai-engineer-intelligence-pipeline/0.1 (+https://github.com/example/repo)"}


async def get(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: float = 20.0) -> httpx.Response:
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, params=params, headers=merged_headers)
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        raise RateLimitError(f"429 from {url}", retry_after=float(retry_after) if retry_after else None)
    if resp.status_code == 413:
        raise PayloadTooLargeError(f"413 from {url}")
    return resp
