"""SQLAlchemy models — PostgreSQL primary store.

Why PostgreSQL (see docs/architecture.md for the full justification): relational
integrity for the startup->product->paper->job->news relationship graph, native
UNIQUE constraints for idempotent dedup, JSONB columns for flexible/evolving
LLM-extracted fields without a migration per schema tweak, and pgvector as an
extension (not a bolt-on service) for entity-embedding similarity search — one
operational system instead of three.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer, String,
                         Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CanonicalEntity(Base):
    __tablename__ = "canonical_entities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50))  # STARTUP, ORG, etc.


class EntityMappingLog(Base):
    __tablename__ = "entity_mapping_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_name: Mapped[str] = mapped_column(String(500))
    normalized_name: Mapped[str] = mapped_column(String(500))
    canonical_name: Mapped[str] = mapped_column(String(500), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    match_method: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StartupRow(Base):
    __tablename__ = "startups"
    __table_args__ = (UniqueConstraint("source_url", "entity_name", name="uq_startup_source_entity"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_name: Mapped[str] = mapped_column(String(500), index=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(2000))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_hash: Mapped[str] = mapped_column(String(64), index=True)


class ProductRow(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("source_url", "startup_name", name="uq_product_source_startup"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    startup_name: Mapped[str] = mapped_column(String(500), index=True)
    pricing_model: Mapped[str] = mapped_column(String(50))
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(2000))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_hash: Mapped[str] = mapped_column(String(64), index=True)


class ResearchPaperRow(Base):
    __tablename__ = "research_papers"
    __table_args__ = (UniqueConstraint("paper_url", name="uq_paper_url"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(1000))
    authors: Mapped[list] = mapped_column(JSON)
    paper_url: Mapped[str] = mapped_column(String(2000))
    github_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    github_stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    github_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class JobRow(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_job_fingerprint"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(500), index=True)
    role: Mapped[str] = mapped_column(String(500))
    raw_title: Mapped[str] = mapped_column(String(500))
    role_family: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_remote: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(2000))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NewsRow(Base):
    __tablename__ = "news"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_news_fingerprint"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(1000))
    url: Mapped[str] = mapped_column(String(2000))
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_name: Mapped[str] = mapped_column(String(200))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
