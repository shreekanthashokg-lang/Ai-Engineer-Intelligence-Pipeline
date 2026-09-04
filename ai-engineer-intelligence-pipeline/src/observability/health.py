"""Lightweight health checks for storage + provider connectivity, useful before
kicking off a long bulk run."""
from __future__ import annotations

import os

import httpx


async def check_database(database_url: str) -> bool:
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(database_url)
        async with engine.connect():
            return True
    except Exception:
        return False


async def check_provider_key(env_var: str) -> bool:
    return bool(os.environ.get(env_var))


async def check_github_rate_limit() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get("https://api.github.com/rate_limit")
    if resp.status_code == 200:
        return resp.json().get("resources", {}).get("core", {})
    return {"error": f"http_{resp.status_code}"}
