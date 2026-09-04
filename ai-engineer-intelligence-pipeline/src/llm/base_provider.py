from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.llm.retry import CircuitBreaker, RetryConfig
from src.llm.token_budget import TokenBudget


@dataclass
class ProviderSpec:
    name: str
    max_context_tokens: int
    supports_json_mode: bool = True


class BaseLLMProvider(ABC):
    """Every concrete provider (Gemini/Groq/DeepSeek) implements this. Adapters must
    translate provider-specific error codes (HTTP 429/413, provider-specific quota
    errors) into RateLimitError / PayloadTooLargeError so the orchestrator's retry
    and chunking logic stays provider-agnostic."""

    spec: ProviderSpec
    retry_config: RetryConfig
    breaker: CircuitBreaker

    def __init__(self, spec: ProviderSpec, retry_config: RetryConfig | None = None):
        self.spec = spec
        self.retry_config = retry_config or RetryConfig()
        self.breaker = CircuitBreaker()

    def token_budget(self) -> TokenBudget:
        return TokenBudget(max_context_tokens=self.spec.max_context_tokens)

    @abstractmethod
    async def extract_structured(self, prompt: str, schema_hint: str) -> str:
        """Send prompt to the provider, return raw JSON text (unvalidated).
        Must raise RateLimitError on 429 and PayloadTooLargeError on 413."""
        raise NotImplementedError
