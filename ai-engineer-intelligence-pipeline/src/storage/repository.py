"""Idempotent write layer. Uses INSERT ... ON CONFLICT DO NOTHING semantics keyed
off each table's UNIQUE constraint (src/storage/models.py) so re-running a batch
after a partial failure never creates duplicates — this is what makes the
AsyncWorkerPool's "not marked done -> eligible for reprocessing" retry behavior
safe."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import EntityMappingLog, JobRow, NewsRow, ProductRow, ResearchPaperRow, StartupRow


async def _upsert(session: AsyncSession, model, values: dict, conflict_cols: list[str]) -> None:
    stmt = sqlite_insert(model).values(**values)
    stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
    await session.execute(stmt)


async def upsert_startup(session: AsyncSession, **values) -> None:
    await _upsert(session, StartupRow, values, ["source_url", "entity_name"])


async def upsert_product(session: AsyncSession, **values) -> None:
    await _upsert(session, ProductRow, values, ["source_url", "startup_name"])


async def upsert_paper(session: AsyncSession, **values) -> None:
    await _upsert(session, ResearchPaperRow, values, ["paper_url"])


async def upsert_job(session: AsyncSession, **values) -> None:
    await _upsert(session, JobRow, values, ["fingerprint"])


async def upsert_news(session: AsyncSession, **values) -> None:
    await _upsert(session, NewsRow, values, ["fingerprint"])


async def insert_mapping_log_row(session: AsyncSession, **values) -> None:
    session.add(EntityMappingLog(**values))


async def count_rows(session: AsyncSession, model) -> int:
    result = await session.execute(select(model))
    return len(result.scalars().all())
