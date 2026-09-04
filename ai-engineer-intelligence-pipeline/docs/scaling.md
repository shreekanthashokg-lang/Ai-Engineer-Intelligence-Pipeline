# Scaling to 500,000+ Records

This trial targets ~3,000 records (1,000 each of startups/products/papers). The
brief requires the architecture to theoretically reach 500,000+ **without code
changes, only infrastructure scaling**. Here's exactly what changes and what
doesn't.

## What does NOT change
- Adapter code (`src/crawlers/*.py`) — already paginated, resumable generators.
- Orchestration code (`AsyncWorkerPool`, `ExtractionOrchestrator`) — concurrency
  and provider count are already parameters, not hardcoded.
- Schema/validation code — Pydantic models don't care about volume.
- Dedup logic — fingerprint + Redis SETNX + DB UNIQUE constraints scale by design
  (O(1) claim per item, no full-table scans).

## What DOES change (config/infra only)
| Lever | Trial value | Scale-phase value |
|---|---|---|
| `concurrency` per adapter | 10 | 100–200, bounded by each source's own rate limit |
| Worker processes/containers | 1 | N (horizontally scaled; queue+checkpoint design is multi-process safe) |
| `--target` per source | 1,000 | 100,000+ (pagination already walks arbitrarily far) |
| Postgres | single instance | read replicas for exports; the write path is already batched upserts |
| Redis | single instance | Redis Cluster if dedup throughput becomes the bottleneck |
| LLM provider quota | free tier | paid tier / higher rate limits (same fallback-chain code) |

## Bottleneck analysis
1. **Source-side rate limits** are the real ceiling long before our own code is —
   ArXiv's own guidance is ~1 req/3s, so "scaling" ArXiv ingestion means running
   it longer, not necessarily wider. This is documented per-source in
   `config/sources.yaml` rather than assumed away.
2. **LLM cost/throughput**: at 500k records, LLM extraction is only invoked for
   unstructured fields structured sources don't already provide (most startup/
   product/paper fields come from direct API fields, not LLM inference) — keeping
   LLM calls to the minority case is itself a scale strategy, not just a cost one.
3. **Storage write throughput**: batched upserts + UNIQUE-constraint-based
   idempotency mean a batch can be re-run safely after a partial failure without
   a separate reconciliation step.
