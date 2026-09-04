from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

styles = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=15, spaceAfter=6)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11.5, spaceBefore=10, spaceAfter=4)
body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.3, leading=12.5, spaceAfter=4)
small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8.3, leading=11, textColor="#444444")

doc = SimpleDocTemplate(
    "docs/architecture.pdf", pagesize=letter,
    topMargin=0.55 * inch, bottomMargin=0.55 * inch, leftMargin=0.65 * inch, rightMargin=0.65 * inch,
)
story = []

def P(text, style=body):
    story.append(Paragraph(text, style))

def bullets(items):
    story.append(ListFlowable([ListItem(Paragraph(i, body)) for i in items], bulletType="bullet", start="•", leftIndent=14))

P("AI Engineer Intelligence Pipeline — Architecture", h1)
P("GraphOne / FrontierAtlas demo task · production design summary (≤3 pages)", small)

P("1. Scale Strategy — collecting 500,000+ startups, products, and papers without manual intervention", h2)
P("The system is built as a source-adapter + bounded-worker-pool pattern (<font face='Courier'>src/crawlers/base.py</font>), "
  "not a linear script. Each source (ArXiv, Papers with Code, YC directory, Product Hunt, etc.) implements "
  "<font face='Courier'>BaseSourceAdapter.discover()</font> — an async, paginated generator of <font face='Courier'>CrawlItem</font>s — "
  "and <font face='Courier'>fetch_and_parse()</font>. An <font face='Courier'>AsyncWorkerPool</font> fans this out across N concurrent "
  "workers with a bounded queue (backpressure), file/Redis-backed checkpointing (resumability — a killed run "
  "restarts without reprocessing successes), and per-item outcomes "
  "(SUCCESS/RETRYING/FAILED/SKIPPED/INVALID/STALE/DUPLICATE) so nothing is silently lost.")
P("Going from this trial's ~3,000 records to 500,000+ requires zero adapter or orchestration code changes — only:")
bullets([
    "Raising <font face='Courier'>concurrency</font> (worker count) per source, bounded by each source's own rate limits.",
    "Horizontally scaling worker containers (the queue + checkpoint design is safe for multiple processes/nodes; "
    "dedup coordination across nodes is handled by the fingerprint + Redis SETNX layer described in §3).",
    "Pagination cursors already being part of the adapter contract, so \"more records\" is a config change "
    "(target count / page depth), not a new code path.",
    "PostgreSQL handling the write volume via batched upserts on the UNIQUE constraints already defined per table.",
])

P("2. Handling 413 (Payload Too Large) and 429 (Rate Limited) across thousands of concurrent extractions", h2)
P("<b>413 strategy</b> (<font face='Courier'>src/llm/token_budget.py</font>): before every LLM call we strip boilerplate "
  "(nav/cookie/newsletter text, deduplicated repeated lines), estimate tokens (chars/4 heuristic), and compute a hard "
  "input budget = provider context window − reserved output tokens − reserved system tokens. If the cleaned text still "
  "exceeds budget we split it into paragraph-bounded chunks (never mid-sentence), rank chunks by an information-density "
  "score (alnum-token ratio + presence of digits, which correlates with specs/prices/dates), and always prepend the "
  "title + source URL so entity names survive truncation. We never blindly truncate from the end.")
P("<b>429 strategy</b> (<font face='Courier'>src/llm/retry.py</font>): exponential backoff with full jitter "
  "(<font face='Courier'>random.uniform(0, min(base·2^attempt, cap))</font>), honoring a provider's <font face='Courier'>Retry-After</font> "
  "header when present instead of guessing. A per-provider <font face='Courier'>CircuitBreaker</font> opens after 5 consecutive "
  "failures and imposes a cooldown, so a hammered provider gets relief instead of every worker retrying it in lockstep "
  "(the exact failure mode that causes 429 storms). On exhaustion, the <font face='Courier'>ExtractionOrchestrator</font> falls "
  "through the configured chain — Gemini Flash → Groq Llama 3 → DeepSeek — trying the same chunk on the next provider "
  "rather than failing the record outright. This path was live-verified against a real 429 from the GitHub REST API "
  "during this build (shared sandbox IP hit GitHub's 60 req/hr unauthenticated limit); the breaker opened exactly as designed.")
P("All raw LLM output is JSON-parsed (with a best-effort salvage for prose-wrapped JSON) and Pydantic-validated before "
  "acceptance; a schema mismatch is treated as an extraction failure, never coerced into a guess.")

P("3. Freshness Tracking — never processing the same article/job twice across distributed crawler nodes", h2)
P("Every news/job item is reduced to a deterministic fingerprint: "
  "<font face='Courier'>sha256(normalize_url(url) + '|' + normalize_title(title) + '|' + published_date_iso)</font> "
  "(<font face='Courier'>src/freshness/fingerprint.py</font>). URL normalization strips tracking params (utm_*, fbclid, "
  "gclid) and trailing slashes so mirrors/syndicated copies collapse to the same key; combining URL + title + date guards "
  "against URL-only false negatives (same URL, edited title) and title-only false positives (generic titles across "
  "different articles).")
P("Coordination across nodes uses Redis <font face='Courier'>SETNX</font> as an atomic distributed claim "
  "(<font face='Courier'>src/freshness/dedup.py</font>) — whichever node claims a fingerprint first proceeds, every other "
  "node immediately sees <font face='Courier'>DUPLICATE</font> and skips without a fetch. A PostgreSQL "
  "<font face='Courier'>UNIQUE</font> constraint on the fingerprint column is the second line of defense, so correctness "
  "never depends on Redis being up — only throughput does. The strict 24-hour freshness gate itself "
  "(<font face='Courier'>src/extraction/date_parser.py::is_within_last_24h</font>) additionally requires the parsed "
  "publication date to carry confidence ≥ 0.6; low-confidence relative-date guesses (e.g. bare \"month\"/\"year\" units) "
  "are excluded from the strict output rather than risked.")

P("4. Storage Strategy", h2)
P("<b>Primary store: PostgreSQL.</b> The domain is fundamentally relational — startup → product, paper → GitHub repo, "
  "company → job/news — and we need transactional, constraint-enforced idempotent writes (the UNIQUE constraints in "
  "<font face='Courier'>src/storage/models.py</font> are the actual dedup enforcement, not just documentation). JSONB "
  "columns absorb the parts of the schema that evolve as LLM extraction improves, without a migration per tweak.")
P("<b>Vector layer: pgvector</b> (extension, not a separate service) for entity-embedding similarity — used as a "
  "second-pass suggestion source feeding into the resolver's controlled fuzzy-match stage, never as the sole basis for "
  "merging two entities. Keeping vectors inside Postgres avoids a second database with its own consistency story for a "
  "workload that doesn't yet need a dedicated vector DB's scale.")
P("<b>Graph relationships: modeled relationally</b> (foreign-keyed junction tables), not a separate graph database. At "
  "this entity/relationship density (5 record types, a handful of relationship kinds) a graph engine like Neo4j adds "
  "operational surface area without a capability Postgres foreign keys + recursive CTEs don't already cover; it's the "
  "kind of addition the brief explicitly warns against making \"merely to make the README look impressive.\" If "
  "multi-hop graph queries (e.g. \"papers by authors who also founded a startup in our seed list\") become a first-class "
  "product need, that's the trigger to introduce Neo4j — not before.")
P("<b>Cache/coordination: Redis</b> for dedup claims and cross-worker rate-limit signaling. Ephemeral by design — losing "
  "Redis loses throughput headroom, never correctness (Postgres UNIQUE constraints are the source of truth).")

doc.build(story)
print("wrote docs/architecture.pdf")
