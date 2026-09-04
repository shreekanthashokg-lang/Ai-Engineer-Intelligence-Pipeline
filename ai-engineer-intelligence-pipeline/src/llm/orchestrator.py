"""Provider-neutral extraction orchestrator implementing the flow required by the
brief:

  input -> token/size estimate -> semantic chunking -> primary provider
    -> 429? retry w/ backoff+jitter -> 413? shrink chunk & retry
    -> provider exhausted? fall back to next provider -> validate -> done

All output is validated against a Pydantic schema before being trusted; invalid
JSON or schema mismatches are treated as extraction failures (never coerced/guessed).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.llm.base_provider import BaseLLMProvider
from src.llm.retry import PayloadTooLargeError, RateLimitError, with_retry
from src.llm.token_budget import TokenBudget, chunk_for_budget

logger = logging.getLogger("orchestrator")

T = TypeVar("T", bound=BaseModel)


@dataclass
class ExtractionResult:
    success: bool
    provider_used: str | None
    data: dict | None
    error: str | None
    attempts: int


class ExtractionOrchestrator:
    def __init__(self, providers: list[BaseLLMProvider]):
        if not providers:
            raise ValueError("at least one provider required")
        self.providers = providers  # ordered fallback chain

    async def extract(
        self, *, raw_text: str, title: str, source_url: str,
        schema: Type[T], schema_hint: str,
    ) -> ExtractionResult:
        total_attempts = 0
        last_error = None

        for provider in self.providers:
            budget: TokenBudget = provider.token_budget()
            chunks = chunk_for_budget(raw_text, budget, title=title, metadata=source_url)

            # Extraction only needs the top (densest) chunk unless the caller wants
            # multi-chunk aggregation; here we try progressively smaller inputs on 413.
            for chunk in chunks:
                candidate = chunk
                for shrink_attempt in range(3):  # shrink on repeated 413
                    total_attempts += 1
                    try:
                        raw_output = await with_retry(
                            lambda: provider.extract_structured(candidate, schema_hint),
                            provider.retry_config,
                            provider.breaker,
                        )
                        parsed = self._validate(raw_output, schema)
                        if parsed is not None:
                            return ExtractionResult(
                                True, provider.spec.name, parsed.model_dump(mode="json"),
                                None, total_attempts,
                            )
                        last_error = "schema_validation_failed"
                        break  # don't keep retrying a structurally invalid response on same chunk
                    except PayloadTooLargeError:
                        candidate = candidate[: len(candidate) // 2]
                        last_error = "413_after_shrink"
                        continue
                    except RateLimitError as e:
                        last_error = f"429_exhausted: {e}"
                        break
                    except Exception as e:  # noqa: BLE001 - provider/network errors
                        last_error = f"provider_error: {e}"
                        break
                # only need the single densest chunk to succeed for most record types
                if last_error is None:
                    break

            logger.info("provider_failed", extra={"provider": provider.spec.name, "error": last_error})
            # fall through to next provider in the chain

        return ExtractionResult(False, None, None, last_error or "all_providers_exhausted", total_attempts)

    @staticmethod
    def _validate(raw_output: str, schema: Type[T]) -> T | None:
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError:
            # try to salvage JSON embedded in prose (some models wrap in prose despite instructions)
            start, end = raw_output.find("{"), raw_output.rfind("}")
            if start == -1 or end == -1:
                return None
            try:
                payload = json.loads(raw_output[start : end + 1])
            except json.JSONDecodeError:
                return None
        try:
            return schema.model_validate(payload)
        except ValidationError as e:
            logger.warning("schema_validation_error", extra={"error": str(e)})
            return None
