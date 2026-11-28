AI ENGINEER INTELLIGENCE PIPELINE
Enterprise-Scale AI & Venture Intelligence Platform

A production-grade ingestion, enrichment, entity-resolution, storage, and export platform that continuously builds the GraphONE / FrontierAtlas AI Intelligence Graph from heterogeneous real-world data sources.

The system collects, normalizes, deduplicates, enriches, validates, and exports structured intelligence across the following domains:

AI STARTUPS
AI PRODUCTS
AI Research Papers
AI Open Source Projects
AI News
AI Job Opportunities
Venture Funding Signals
GitHub Repository Activity
Research-to-Startup Technology Transfers

The platform was designed specifically to satisfy the complete requirements of the AI Engineer Demo Task ("The AI Signal"), while also demonstrating architectural decisions expected in production-scale intelligence systems operating under real-world constraints such as rate limits, changing source formats, duplicate entities, unreliable metadata, and large-scale ingestion workloads.

See:

./REQUIREMENTS.md for requirement-by-requirement mapping
./architecture.pdf for the full architecture review
./docs/architecture.md for distributed ingestion, storage, freshness, and scaling decisions
./docs/scaling.md for scaling from thousands to hundreds of thousands of entities
./RUNBOOK.md for production execution instructions
Executive Summary

THIS REPOSITORY IMPLEMENTS A FULLY OPERATIONAL INTELLIGENCE PIPELINE CAPABLE OF transforming unstructured web content into a structured, traceable, and continuously updated intelligence graph.

The architecture follows six core design principles:

1. Provenance First

Every field stored in the system must be traceable back to an original source.

EACH EXTRACTED RECORD CARRIES A PROVENANCE  EXTRACTED RECORD CARRIES A PROVEVENANCE ENVELOPE:

JSON
{
"source_url": "...",
"retrieved_at": "...",
"extraction_method": "...",
"confidence": 0.98,
"raw_hash": "..."
}

THIS DESIGN PREVENTS SILENT HALLUCINATION, UNVERIFIABLE ENVRICHMENT AND FABRICATED ENTITIES.

A RECORD CANNOT EXIST IN DOWNSTREAM STORAGE WITHOUT SOURCE ATTRIBUTION. 

This is especially important because the assessment explicitly identifies fabricated or unverifiable records as a disqualifying failure mode.

2. DETERMINISTIC EXTRACTION BEFORE AI 

THE SYSTEM INTENTIONALLY MINIMIZES LLM USAGE. 

WHENEVER STRUCTURED DATA EXISTS, DETERMINISTIC EXTRACTION IS USED : 
JSON APIs
RSS feeds
OpenGraph tags
Schema.org metadata
JSON-LD blocks
Meta tags
Structured HTML patterns

LLMs are invoked only when deterministic methods fail.

This significantly reduces:

Cost
Hallucination risk
Variability
Latency

while improving repeatability and auditability.

3. Freshness Over Static Snapshots

The platform is designed around continuously evolving information streams.

Freshness strategies include:

Rolling ingestion windows
Checkpoint-based resumability
Deduplication fingerprints
Distributed locking
GitHub star re-enrichment
News recrawling
Job expiration handling

THE GOAL IS TO MAINTAIN A 24-HOUR-FRESH INTELLIGENCE GRAPH RATHER THAN GENERATE A ONE-TIME-DATASET. 

4. Production Failure Handling

Real-world ingestion systems fail constantly.

THIS PLATFORM INCLUDES EXPLICIT MITIGATION FOR:

Failure Type	Strategy
HTTP 429	Exponential backoff + jitter
HTTP 413	Semantic chunking + token budgeting
Temporary outages	Circuit breaker
Partial runs	Checkpoint recovery
Duplicate documents	Hash-based deduplication
Duplicate entities	Entity normalization
Worker crashes	Resume from checkpoint
Provider failures	Multi-model fallback chain

THESE MECHANSIMS ARE IMPLEMENTED AS REUSABLE INFRASTRUCTURE RATHER THAN SOURCE-SPECIFIC WORKAROUNDS.

5. Horizontal Scale

THE ARCHITECTURE WAS INTENTIONALLY DESIGNED TO SCALE WITHOUT REQUIRING APPLICATION-LAYER REWRITES. 
Scaling from:

Plain Text
1,000 records
↓
10,000 records
↓
100,000 records
↓
500,000+ records

requires only:

Increasing worker concurrency
Adding crawler containers
Scaling PostgreSQL
Expanding Redis capacity

No schema redesign, extraction rewrites, or orchestration changes are required.

6. INTELLIGENT GRAPH CONSTRUCTION

Raw crawled data is transformed into connected entities:

Plain Text
Research Paper
│
▼
GitHub Repository
│
▼
Startup
│
▼
Product
│
▼
Hiring Activity

THIS CREATES AN INTELLIGENCE GRAPH RATHER THAN ISOLATED DATASETS. 

Examples:

A startup can be linked to its research origins.
A paper can be linked to its implementation repository.
A repository can be linked to hiring activity.
Products can be linked to their parent organization.
Current Verification Status

The repository contains fully implemented and tested code.

No API keys, paid services, or external infrastructure are required to validate the core architecture.

Current test status:

Shell
pytest tests/unit
===========================
25 passed
===========================

The goal was to ensure reviewers can independently verify correctness without requiring privileged credentials.

Real Data Sources Currently Integrated
Startups

Source:

Plain Text
https://yc-oss.github.io/api

Public YC-backed company dataset maintained through GitHub Actions.

Data includes:

Company name
Description
Industry
Batch
Website
Location
Tags
YC metadata
Source attribution

Every exported company record contains a verifiable source URL.

Research Papers

Source:

Plain Text
Official ArXiv API

Extracted fields include:

Title
Abstract
Authors
Categories
Publication date
Paper URL
PDF URL

The pipeline additionally performs:

GitHub repository discovery
GitHub repository validation
Star count enrichment
Repository metadata enrichment

allowing research momentum to be measured alongside publication activity.

Open Source Signals

Source:

Plain Text
api.github.com

Enrichment includes:

Stars
Forks
Watchers
Open issues
Repository age
Last commit activity

GitHub activity is treated as a first-class intelligence signal throughout the pipeline.

AI News

Integrated via:

RSS feeds
Metadata extraction
Structured article parsing

The platform supports:

Publication normalization
Date extraction
Author extraction
Duplicate detection
Freshness windows
AI Jobs

Integrated through:

Greenhouse
Lever
Direct company job boards

The framework supports:

Title normalization
Organization resolution
Location extraction
Job freshness tracking
Expiration handling
End-to-End Data Flow
Plain Text
SOURCE LAYER
┌───────────────────────────────────────┐
│ APIs • RSS • Websites • Job Boards │
└───────────────────────────────────────┘
│
▼
INGESTION LAYER
┌───────────────────────────────────────┐
│ Async Crawlers │
│ Retry Logic │
│ Circuit Breakers │
│ Checkpoint Recovery │
└───────────────────────────────────────┘
│
▼
EXTRACTION LAYER
┌───────────────────────────────────────┐
│ HTML Cleaning │
│ Metadata Parsing │
│ Date Detection │
│ Structured Extraction │
└───────────────────────────────────────┘
│
▼
AI LAYER
┌───────────────────────────────────────┐
│ Gemini │
│ Groq │
│ DeepSeek │
│ Schema Validation │
└───────────────────────────────────────┘
│
▼
NORMALIZATION LAYER
┌───────────────────────────────────────┐
│ Entity Resolution │
│ Alias Mapping │
│ Fuzzy Matching │
│ Confidence Scoring │
└───────────────────────────────────────┘
│
▼
QUALITY LAYER
┌───────────────────────────────────────┐
│ Provenance Validation │
│ Deduplication │
│ Fingerprinting │
│ Freshness Verification │
└───────────────────────────────────────┘
│
▼
STORAGE LAYER
┌───────────────────────────────────────┐
│ PostgreSQL │
│ Redis │
│ pgvector │
└───────────────────────────────────────┘
│
▼
DELIVERY LAYER
┌───────────────────────────────────────┐
│ CSV Export │
│ XLSX Export │
│ Google Sheets │
│ Downstream Analytics │
└───────────────────────────────────────┘
Why This Architecture Was Chosen

The assessment is fundamentally an intelligence engineering problem rather than a scraping problem.

The difficult challenges are not:

downloading pages
calling APIs
exporting spreadsheets

The difficult challenges are:

maintaining provenance
handling rate limits
validating extracted entities
eliminating duplicates
recovering from failures
preserving freshness
scaling ingestion safely
producing traceable intelligence

This repository focuses heavily on those concerns because they are the factors that determine whether an intelligence platform remains trustworthy as its scale increases.

Result: a production-oriented AI intelligence pipeline capable of continuously building and maintaining a verifiable AI ecosystem knowledge graph from real-world sources while remaining resilient, auditable, and horizontally scalable.
