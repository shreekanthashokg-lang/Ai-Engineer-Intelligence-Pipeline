"""Canonical schema definitions.

Every record type shares a provenance envelope so any downstream consumer can trace
a field back to the exact source it came from. Nothing here is allowed to be
populated with a value that wasn't either (a) read directly off a source, (b)
deterministically derived, (c) returned by a legitimate external API, or (d)
extracted by an LLM from source text and schema-validated. Unknown -> None/"UNKNOWN",
never guessed.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class RecordType(str, Enum):
    STARTUP = "STARTUP"
    PRODUCT = "PRODUCT"
    RESEARCH_PAPER = "RESEARCH_PAPER"
    JOB = "JOB"
    NEWS = "NEWS"


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"
    UNKNOWN = "UNKNOWN"


class ExtractionMethod(str, Enum):
    DIRECT_FIELD = "DIRECT_FIELD"          # copied verbatim from structured source (API/JSON-LD)
    DETERMINISTIC = "DETERMINISTIC"        # derived via code (e.g. normalization, hashing)
    EXTERNAL_API = "EXTERNAL_API"          # e.g. GitHub stars via GitHub REST API
    LLM_EXTRACTED = "LLM_EXTRACTED"        # pulled from free text by an LLM, schema-validated
    UNKNOWN = "UNKNOWN"


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    INVALID = "INVALID"
    STALE = "STALE"
    DUPLICATE = "DUPLICATE"


class Provenance(BaseModel):
    source_name: str
    source_url: str
    retrieved_at: datetime
    extraction_method: ExtractionMethod
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    raw_hash: str

    @staticmethod
    def hash_raw(raw_text: str) -> str:
        return hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()


class BaseRecord(BaseModel):
    schemaVersion: str = "1.0"
    recordType: RecordType
    source: "SourceRef"
    collectedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provenance: Optional[Provenance] = None


class SourceRef(BaseModel):
    name: str
    url: str


class StartupData(BaseModel):
    employeeCount: Optional[int] = None


class StartupContent(BaseModel):
    entityName: str
    data: StartupData = Field(default_factory=StartupData)


class StartupRecord(BaseRecord):
    recordType: RecordType = RecordType.STARTUP
    content: StartupContent


class ProductContent(BaseModel):
    startupName: str
    pricingModel: PricingModel = PricingModel.UNKNOWN


class ProductRecord(BaseRecord):
    recordType: RecordType = RecordType.PRODUCT
    content: ProductContent


class ResearchPaperContent(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    paper_url: str
    github_url: Optional[str] = None
    github_stars: Optional[int] = None
    published_date: Optional[datetime] = None


class ResearchPaperRecord(BaseRecord):
    recordType: RecordType = RecordType.RESEARCH_PAPER
    content: ResearchPaperContent


class JobContent(BaseModel):
    company: str
    role: str
    date: Optional[datetime] = None
    is_remote: Optional[bool] = None
    role_family: Optional[str] = None
    raw_title: str


class JobRecord(BaseRecord):
    recordType: RecordType = RecordType.JOB
    content: JobContent


class NewsContent(BaseModel):
    title: str
    url: str
    published_at: Optional[datetime] = None
    full_text: Optional[str] = None
    content_hash: Optional[str] = None


class NewsRecord(BaseRecord):
    recordType: RecordType = RecordType.NEWS
    content: NewsContent


class EntityMappingLogRow(BaseModel):
    raw_name: str
    normalized_name: str
    canonical_name: str
    entity_type: str
    match_method: str
    confidence: float
    source_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
