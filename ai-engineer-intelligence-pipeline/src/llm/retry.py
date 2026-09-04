"""429 rate-limit handling: exponential backoff + full jitter + Retry-After support
+ a simple per-provider circuit breaker so a hammered provider gets a cooldown
instead of every worker retrying it in lockstep (which would just recreate the
thundering herd that caused the 429s in the first place).
"""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field


class RateLimitError(Exception):
    def __init__(self, message: str = "", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class PayloadTooLargeError(Exception):
    """Raised by a provider adapter on HTTP 413."""


@dataclass
class RetryConfig:
    max_retries: int = 4
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    jitter: bool = True


@dataclass
class CircuitBreaker:
    """Per-provider breaker. Opens after N consecutive failures, half-opens after cooldown."""
    failure_threshold: int = 5
    cooldown_s: float = 60.0
    _failures: int = 0
    _opened_at: float | None = field(default=None, repr=False)

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.cooldown_s:
            # half-open: allow a probe request
            return False
        return True


def compute_backoff(attempt: int, cfg: RetryConfig, retry_after: float | None = None) -> float:
    """attempt is 1-indexed. Returns seconds to sleep."""
    if retry_after is not None:
        return min(retry_after, cfg.max_delay_s)
    delay = min(cfg.base_delay_s * (2 ** (attempt - 1)), cfg.max_delay_s)
    if cfg.jitter:
        delay = random.uniform(0, delay)  # "full jitter" per AWS backoff guidance
    return delay


async def with_retry(coro_factory, cfg: RetryConfig, breaker: CircuitBreaker | None = None):
    """coro_factory: zero-arg callable returning a fresh awaitable each call
    (needed because a coroutine object can't be re-awaited after failing)."""
    last_exc: Exception | None = None
    for attempt in range(1, cfg.max_retries + 1):
        if breaker is not None and breaker.is_open:
            raise RuntimeError("circuit_open: provider in cooldown, use fallback")
        try:
            result = await coro_factory()
            if breaker is not None:
                breaker.record_success()
            return result
        except RateLimitError as e:
            last_exc = e
            if breaker is not None:
                breaker.record_failure()
            if attempt == cfg.max_retries:
                break
            delay = compute_backoff(attempt, cfg, retry_after=e.retry_after)
            await asyncio.sleep(delay)
        except PayloadTooLargeError:
            raise  # not retryable here; caller must shrink the chunk and re-invoke
    raise last_exc or RuntimeError("retry exhausted")
