# Data Quality

## Non-hallucination guarantees (mechanical, not just policy)
- Every `BaseRecord` requires a `source.url` and `source.name` (Pydantic
  validation fails without them — a record literally cannot be constructed
  without provenance).
- `Provenance.raw_hash` stores a SHA-256 of the exact raw content a record was
  derived from, so any field can be re-verified against its source later.
- `scripts/validate_output.py` mechanically checks every exported row for a
  non-empty, non-"UNKNOWN" source-URL column as a final gate before submission.
- GitHub stars are the one "dynamic metric" field in the schema and are always
  fetched live from `api.github.com` at export time — never cached indefinitely,
  never estimated.

## Freshness accuracy
- Date parsing is structured-first (JSON-LD → OpenGraph/meta tags → visible text
  ISO → relative phrases → generic dateutil fallback), each tier carrying its own
  confidence score.
- The strict 24h gate additionally requires confidence ≥ 0.6 — a bare "3 months
  ago" (confidence 0.4, since "month" is a 30-day approximation) is excluded from
  strict-freshness output even though it parses successfully, rather than risking
  a stale item slipping through.

## Entity resolution precision
- Fuzzy matching is deliberately conservative: a 0.88 minimum similarity floor
  AND a length-ratio sanity check (rejects e.g. "AI" fuzzy-matching "xAI") — see
  `tests/unit/test_entity_resolution.py::test_resolver_does_not_merge_unrelated_short_names`.
- Every resolution (matched or not) is logged with its method and confidence, so
  a human reviewer can audit exactly why "OpenAI Incorporated" became "OpenAI"
  and why "Totally Unknown Startup Co" was left as its own provisional entity
  instead of being force-merged into something in the seed list.

## Outcome taxonomy
Every ingested item lands in exactly one bucket — SUCCESS, RETRYING, FAILED,
SKIPPED, INVALID, STALE, DUPLICATE — logged with structured JSON fields (run_id,
source, url, attempt, error_type). Nothing silently disappears; FAILED/INVALID
items stay eligible for reprocessing on the next run via the checkpoint design.
