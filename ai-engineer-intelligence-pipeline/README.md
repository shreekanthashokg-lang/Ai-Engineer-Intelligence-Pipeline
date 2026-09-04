# AI Engineer Intelligence Pipeline

Ingestion pipeline for the GraphOne / FrontierAtlas AI-and-venture Intelligence
Graph: startups, products, research papers (with live GitHub star tracking),
24-hour-fresh AI news, and 24-hour-fresh AI jobs.

Built for the AI Engineer demo task. See `REQUIREMENTS.md` for the full
requirement-by-requirement breakdown and `docs/architecture.md` /
`architecture.pdf` for the 3-page design doc covering scale strategy, 413/429
handling, distributed freshness, and storage justification.

## ⚠️ READ THIS FIRST

This repo's code is real and tested (`pytest tests/unit` → 25/25 passing). The
bulk 1,000+ row data acquisition, however, needs to run somewhere with open
internet access to arxiv.org / paperswithcode.com / job boards / news feeds —
the environment this repo was assembled in does not have that. **`RUNBOOK.md`**
explains exactly why and exactly how to run the real crawl. This is disclosed
here in full rather than filling the Sheet with plausible-looking fake rows,
which the assessment explicitly treats as instant disqualification.

## What's implemented and verified

| Component | Status |
|---|---|
| Pydantic schemas w/ provenance envelope | ✅ implemented, tested |
| Date normalizer (ISO/relative/JSON-LD/OG/meta) | ✅ implemented, 9 tests passing |
| Token budget + intelligent chunking (413 handling) | ✅ implemented, 4 tests passing |
| Exponential backoff + jitter + circuit breaker (429 handling) | ✅ implemented, 7 tests passing, **live-verified against a real 429 from the GitHub API** |
| Entity resolver (alias → exact → controlled fuzzy) | ✅ implemented, 5 tests passing, verified against 50-org seed list |
| GitHub star enrichment | ✅ implemented, live-called against `api.github.com` |
| Async worker pool w/ checkpointing | ✅ implemented (`src/crawlers/base.py`) |
| Distributed dedup via fingerprint + Redis SETNX | ✅ implemented (`src/freshness/`) |
| CSV / XLSX exporters (6-tab layout) | ✅ implemented, ran end-to-end (`scripts/generate_demo_data_report.py`) |
| Google Sheets uploader | ✅ implemented, dry-run tested |
| Source adapters (arxiv/paperswithcode/YC/news RSS/job boards) | 🔶 scaffolded per `config/sources.yaml`; execution needs open network, see `RUNBOOK.md` |
| Live bulk data (1,000+ rows/tab) | 🔶 not generated from this sandbox — see `RUNBOOK.md` |

## Quickstart

```bash
pip install -r requirements.txt
pytest tests/unit -v                       # 25 tests, no network/credentials needed
python scripts/generate_demo_data_report.py  # entity resolution + live GitHub calls, no bulk crawl
python scripts/export_google_sheets.py --dry-run
```

For the full bulk crawl + Sheet upload: see `RUNBOOK.md`.

## Architecture (short version)

```
source adapter (API/RSS/HTTP/Playwright)
        │  raw HTML/JSON
        ▼
html_cleaner / metadata / date_parser        (deterministic extraction where possible)
        │
        ▼
LLM orchestrator (Gemini → Groq → DeepSeek)   (only for unstructured fields)
   chunking (413-safe) + retry (429-safe)
        │  raw JSON
        ▼
Pydantic schema validation                    (reject, never coerce/guess)
        │
        ▼
entity resolver (alias → exact → fuzzy)       (deterministic, confidence-scored)
        │
        ▼
fingerprint + dedup (Redis SETNX + DB UNIQUE)  (idempotent across nodes)
        │
        ▼
PostgreSQL (canonical storage) ── pgvector for entity-embedding similarity
        │
        ▼
CSV / XLSX exporters ── Google Sheets API upload
```

Scaling from this trial's ~3k records to 500,000+ is purely a matter of raising
`AsyncWorkerPool(concurrency=...)` and adding worker containers — no adapter,
schema, or orchestration code changes required.

## Repo layout

See the tree in `REQUIREMENTS.md` — mirrors the structure requested in the brief.

## License

MIT — see `LICENSE`.
