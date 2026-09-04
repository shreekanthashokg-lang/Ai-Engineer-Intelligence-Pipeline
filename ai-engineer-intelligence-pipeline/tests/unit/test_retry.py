import pytest

from src.llm.retry import (CircuitBreaker, PayloadTooLargeError, RateLimitError,
                            RetryConfig, compute_backoff, with_retry)


def test_backoff_respects_retry_after_header():
    cfg = RetryConfig(max_delay_s=30)
    delay = compute_backoff(attempt=1, cfg=cfg, retry_after=5.0)
    assert delay == 5.0


def test_backoff_grows_exponentially_and_caps():
    cfg = RetryConfig(base_delay_s=1, max_delay_s=10, jitter=False)
    assert compute_backoff(1, cfg) == 1
    assert compute_backoff(2, cfg) == 2
    assert compute_backoff(3, cfg) == 4
    assert compute_backoff(10, cfg) == 10  # capped


@pytest.mark.asyncio
async def test_with_retry_eventually_succeeds_after_429s():
    attempts = {"n": 0}

    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RateLimitError("rate limited")
        return "ok"

    cfg = RetryConfig(max_retries=5, base_delay_s=0.001, max_delay_s=0.01)
    result = await with_retry(flaky, cfg)
    assert result == "ok"
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_with_retry_raises_after_exhausting_retries():
    async def always_fails():
        raise RateLimitError("still limited")

    cfg = RetryConfig(max_retries=3, base_delay_s=0.001, max_delay_s=0.01)
    with pytest.raises(RateLimitError):
        await with_retry(always_fails, cfg)


@pytest.mark.asyncio
async def test_413_is_not_silently_retried_by_with_retry():
    async def too_big():
        raise PayloadTooLargeError("too big")

    cfg = RetryConfig(max_retries=3, base_delay_s=0.001)
    with pytest.raises(PayloadTooLargeError):
        await with_retry(too_big, cfg)


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, cooldown_s=999)
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open is True


def test_circuit_breaker_closes_on_success():
    cb = CircuitBreaker(failure_threshold=3, cooldown_s=999)
    for _ in range(3):
        cb.record_failure()
    cb.record_success()
    assert cb.is_open is False
