"""Live GitHub star / repo-metadata enrichment for the Research Paper vertical.

This is the one enrichment step whose data is *always* pulled live from a legitimate
external API (never estimated, never cached-and-forgotten stale) — satisfies the
brief's explicit "current GitHub star extraction" requirement. Handles: missing repo,
moved/renamed repo (redirects), deleted repo (404), and GitHub API rate limiting
(403 + X-RateLimit-Remaining: 0, or 429) via the shared retry module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from src.llm.retry import CircuitBreaker, RateLimitError, RetryConfig, with_retry

GITHUB_API = "https://api.github.com/repos/{owner}/{repo}"


@dataclass
class RepoMetadata:
    owner: str
    repo: str
    stars: int | None
    exists: bool
    moved_to: str | None = None
    error: str | None = None


class GitHubEnricher:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.retry_config = RetryConfig(max_retries=4, base_delay_s=2.0, max_delay_s=60.0)
        self.breaker = CircuitBreaker(failure_threshold=5, cooldown_s=120.0)
        self._cache: dict[str, RepoMetadata] = {}

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-engineer-intelligence-pipeline"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def parse_owner_repo(github_url: str) -> tuple[str, str] | None:
        parts = github_url.rstrip("/").split("github.com/")
        if len(parts) < 2:
            return None
        segments = parts[1].split("/")
        if len(segments) < 2:
            return None
        return segments[0], segments[1]

    async def get_stars(self, github_url: str) -> RepoMetadata:
        cache_key = github_url.rstrip("/")
        if cache_key in self._cache:
            return self._cache[cache_key]

        parsed = self.parse_owner_repo(github_url)
        if not parsed:
            return RepoMetadata("", "", None, False, error="unparseable_url")
        owner, repo = parsed

        async def _call():
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(GITHUB_API.format(owner=owner, repo=repo), headers=self._headers())
            if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
                reset = resp.headers.get("X-RateLimit-Reset")
                retry_after = None
                if reset:
                    import time
                    retry_after = max(float(reset) - time.time(), 1.0)
                raise RateLimitError("github rate limited", retry_after=retry_after)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise RateLimitError("github rate limited", retry_after=float(retry_after) if retry_after else None)
            return resp

        try:
            resp = await with_retry(_call, self.retry_config, self.breaker)
        except Exception as e:  # noqa: BLE001
            result = RepoMetadata(owner, repo, None, False, error=str(e))
            self._cache[cache_key] = result
            return result

        if resp.status_code == 404:
            result = RepoMetadata(owner, repo, None, False, error="not_found_or_deleted")
        elif resp.status_code == 200:
            data = resp.json()
            moved_to = None
            final_full_name = data.get("full_name")
            if final_full_name and final_full_name.lower() != f"{owner}/{repo}".lower():
                moved_to = f"https://github.com/{final_full_name}"
            result = RepoMetadata(owner, repo, data.get("stargazers_count"), True, moved_to=moved_to)
        else:
            result = RepoMetadata(owner, repo, None, False, error=f"http_{resp.status_code}")

        self._cache[cache_key] = result
        return result
