"""Simple in-process metrics counters, exportable as a dict (swap for
prometheus_client.Counter in a real deployment — same call sites)."""
from __future__ import annotations

from collections import defaultdict


class Metrics:
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._latencies_ms: list[float] = []

    def inc(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    def observe_latency(self, ms: float) -> None:
        self._latencies_ms.append(ms)

    def snapshot(self) -> dict:
        avg_latency = sum(self._latencies_ms) / len(self._latencies_ms) if self._latencies_ms else 0.0
        return {**self._counters, "average_latency_ms": round(avg_latency, 2)}


GLOBAL_METRICS = Metrics()
