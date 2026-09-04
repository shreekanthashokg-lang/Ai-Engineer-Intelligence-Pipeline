from __future__ import annotations

import os

import httpx

from src.llm.base_provider import BaseLLMProvider, ProviderSpec
from src.llm.retry import PayloadTooLargeError, RateLimitError

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider(BaseLLMProvider):
    def __init__(self, model: str = "gemini-1.5-flash", api_key: str | None = None):
        super().__init__(ProviderSpec(name="gemini", max_context_tokens=1_000_000))
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    async def extract_structured(self, prompt: str, schema_hint: str) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        url = API_URL.format(model=self.model) + f"?key={self.api_key}"
        body = {
            "contents": [{"parts": [{"text": f"{prompt}\n\nRespond ONLY with JSON matching: {schema_hint}"}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError("gemini rate limited", retry_after=float(retry_after) if retry_after else None)
        if resp.status_code == 413:
            raise PayloadTooLargeError("gemini payload too large")
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
