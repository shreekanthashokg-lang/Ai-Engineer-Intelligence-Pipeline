# AI Engineer Intelligence Pipeline

INGESTION PIPELINE for the GraphOne / FrontierAtlas AI-and-venture Intelligence
Graph: startups, products, research papers (with live GitHub star tracking),
24-hour-fresh AI news, and 24-hour-fresh AI jobs.

Built for the **AI Engineer demo task** (The AI Signal). See [`REQUIREMENTS.md`](./REQUIREMENTS.md)
for the full requirement-by-requirement breakdown, and [`architecture.pdf`](./architecture.pdf)
/ [`docs/architecture.md`](./docs/architecture.md) for the 3-page design doc covering
scale strategy, 413/429 handling, distributed freshness, and storage justification.

---

## ⚠️ READ THIS FIRST

This repo's code is real and tested — `pytest tests/unit` → **25/25 passing**, with
zero network access or API keys required to verify that. Every record schema
enforces a provenance envelope (`source.url`, `retrieved_at`, `extraction_method`,
`confidence`, `raw_hash`), so no field can exist without a traceable, legitimate
source — the assessment explicitly treats hallucinated/fabricated rows as instant
disqualification, so this repo is built to make that structurally hard to violate,
not just policy-discouraged.

**Current data status, disclosed plainly:**
- **Startups**: real records pulled from [`yc-oss.github.io/api`](https://yc-oss.github.io/api)
  — a live, public, no-auth dataset of actual YC-backed companies (sourced from
  YC's own data via GitHub Actions, updated daily). Every row has a real, clickable
  `source.url`.
- **Research Papers**: real records pulled from the official ArXiv API, with a
  subset cross-checked live against the real GitHub REST API for star counts.
- **Products / Jobs / News**: pipeline code is complete and tested; full 1,000+
  row population requires running the bulk crawl from an environment with open
  internet access (job boards, news RSS, ArXiv/YC at full pagination depth) — see
  [`RUNBOOK.md`](./RUNBOOK.md) and [`colab_complete_submission.py`](./colab_complete_submission.py)
  for a zero-install way to finish this via Google Colab.

NOTHING IS the Delivered dataset is fabricated. Where data isn't yet populated,
it's left as an empty tab with correct headers rather than padded with
plausible-looking fake rows.

---

## WHAT'S IMPLEMENTED AND VERIFIED

| Component | Status |
|---|---|
| Pydantic schemas with provenance envelope | ✅ implemented, tested |
| Date normalizer (ISO / relative / JSON-LD / OpenGraph / meta tags) | ✅ implemented, 9 tests passing |
| Token budget + intelligent semantic chunking (413 handling) | ✅ implemented, 4 tests passing |
| Exponential backoff + jitter + circuit breaker (429 handling) | ✅ implemented, 7 tests passing — **live-verified against a real 429 from the GitHub API** |
| Multi-tier LLM orchestrator (Gemini → Groq → DeepSeek fallback chain) | ✅ implemented, schema-validated output |
| Entity resolver (alias → normalized exact → controlled fuzzy match) | ✅ implemented, 5 tests passing, verified against a 50-org seed list |
| GitHub star enrichment | ✅ implemented, live-called against `api.github.com` |
| Async worker pool with checkpointing + resumability | ✅ implemented (`src/crawlers/base.py`) |
| Distributed dedup via fingerprint + Redis SETNX | ✅ implemented (`src/freshness/`) |
| PostgreSQL models + idempotent repository layer | ✅ implemented, tested end-to-end |
| CSV / XLSX exporters (6-tab layout) | ✅ implemented, ran end-to-end |
| Google Sheets uploader | ✅ implemented, dry-run tested |
| Source adapters — ArXiv, YC directory, news RSS, Greenhouse/Lever jobs | ✅ implemented against real, documented endpoints |
| Bulk data at full 1,000+ rows/tab | 🔶 requires an execution environment with open internet — see `RUNBOOK.md` |

---

## QUICKSTART

```bash
pip install -r requirements.txt

# Run the full unit test suite — no network or credentials needed
pytest tests/unit -v

# Entity resolution demo + live (real) GitHub API calls
python scripts/generate_demo_data_report.py

# Validate the exported CSVs are correctly structured
python scripts/export_google_sheets.py --dry-run
```

For the full bulk crawl and a live Google Sheet with 1,000+ real rows per tab,
run [`colab_complete_submission.py`](./colab_complete_submission.py) in
[Google Colab](https://colab.research.google.com) (free, no local install, open
internet) — or follow [`RUNBOOK.md`](./RUNBOOK.md) to run it locally with your
own LLM/GitHub API keys.

---

## ARCHITECTURE (short version)

```
source adapter (API / RSS / HTTP / Playwright)
        │  raw HTML/JSON
        ▼
html_cleaner / metadata / date_parser          (deterministic extraction where possible)
        │
        ▼
LLM orchestrator (Gemini → Groq → DeepSeek)     (only for unstructured fields)
   chunking (413-safe) + retry (429-safe)
        │  raw JSON
        ▼
Pydantic schema validation                      (reject, never coerce or guess)
        │
        ▼
entity resolver (alias → exact → fuzzy)         (deterministic, confidence-scored)
        │
        ▼
fingerprint + dedup (Redis SETNX + DB UNIQUE)   (idempotent across nodes)
        │
        ▼
PostgreSQL (canonical storage) ── pgvector for entity-embedding similarity
        │
        ▼
CSV / XLSX exporters ── Google Sheets API upload
```

Scaling from this trial's dataset to 500,000+ records is purely a matter of
raising `AsyncWorkerPool(concurrency=...)` and adding worker containers — no
adapter, schema, or orchestration code changes required. Full reasoning in
[`docs/scaling.md`](./docs/scaling.md).

---

## Repo layout

```
ai-engineer-intelligence-pipeline/
├── README.md
├── REQUIREMENTS.md
├── RUNBOOK.md
├── architecture.pdf
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt
├── colab_complete_submission.py
│
├── config/
│   ├── settings.yaml
│   ├── sources.yaml
│   └── models.yaml
│
├── src/
│   ├── crawlers/          # base worker pool, async HTTP, Playwright, per-vertical adapters
│   ├── extraction/        # schemas, html_cleaner, metadata, date_parser, content_extractor
│   ├── llm/                # orchestrator, retry/backoff, token budget/chunking, provider adapters
│   ├── entity_resolution/ # normalizer, resolver, seed entities, mapping log
│   ├── freshness/          # fingerprinting, distributed dedup
│   ├── storage/            # SQLAlchemy models, database session, repository, exporters
│   ├── pipelines/          # per-vertical + full-pipeline orchestration
│   ├── observability/      # structured logging, metrics, health checks
│   └── cli.py
│
├── scripts/                # seed_entities, run_bulk_ingestion, run_fresh_signals,
│                            # export_google_sheets, validate_output, generate_demo_data_report
│
├── data/{raw,processed,exports,sample}/
├── tests/{unit,integration,fixtures}/
└── docs/                   # architecture, scaling, source_strategy, data_quality,
                             # anti_bot_strategy, loom_script
```

---

## License

MIT — see [`LICENSE`](./LICENSE).
