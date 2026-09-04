from __future__ import annotations

import os

import httpx

from src.llm.base_provider import BaseLLMProvider, ProviderSpec
from src.llm.retry import PayloadTooLargeError, RateLimitError

API_URL = "https://api.deepseek.com/chat/completions"


class DeepSeekProvider(BaseLLMProvider):
    def __init__(self, model: str = "deepseek-chat", api_key: str | None = None):
        super().__init__(ProviderSpec(name="deepseek", max_context_tokens=64_000))
        self.model = model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")

    async def extract_structured(self, prompt: str, schema_hint: str) -> str:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"Respond ONLY with JSON matching: {schema_hint}"},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(API_URL, headers=headers, json=body)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError("deepseek rate limited", retry_after=float(retry_after) if retry_after else None)
        if resp.status_code == 413:
            raise PayloadTooLargeError("deepseek payload too large")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
