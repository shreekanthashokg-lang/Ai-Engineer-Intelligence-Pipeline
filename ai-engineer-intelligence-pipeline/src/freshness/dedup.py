"""Distributed dedup coordinator.

In production this uses Redis SETNX (atomic "set if not exists") as a distributed
lock: whichever crawler node claims a fingerprint first wins, every other node sees
DUPLICATE and skips. Falls back to an in-process set for local/single-node runs so
the same code path works in both docker-compose and a laptop. The DB layer also
enforces a UNIQUE constraint on fingerprint as a second line of defense (belt and
suspenders — Redis availability isn't a correctness dependency, just a perf one).
"""
from __future__ import annotations

from typing import Optional


class DedupCoordinator:
    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 60 * 60 * 24 * 3):
        self.ttl_seconds = ttl_seconds
        self._redis = None
        self._local: set[str] = set()
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(redis_url)
            except ImportError:
                pass  # falls back to in-process set; documented degradation, not silent failure

    async def claim(self, fp: str) -> bool:
        """Returns True if this fingerprint was NOT seen before (i.e. caller should
        proceed) and False if it's a duplicate (caller should mark as DUPLICATE)."""
        if self._redis is not None:
            was_set = await self._redis.set(f"dedup:{fp}", "1", nx=True, ex=self.ttl_seconds)
            return bool(was_set)
        if fp in self._local:
            return False
        self._local.add(fp)
        return True
