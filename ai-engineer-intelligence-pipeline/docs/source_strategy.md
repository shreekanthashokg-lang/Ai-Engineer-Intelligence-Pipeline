# Source Strategy

Full registry lives in `config/sources.yaml` (machine-readable, loaded by the
pipeline scripts directly — this doc explains the reasoning, the config is the
source of truth).

## Research papers
- **ArXiv** (official API): the natural primary source for AI research papers,
  supports server-side filtering by category (`cat:cs.AI`, `cat:cs.LG`, etc.) and
  sort-by-submission-date, which both keeps results relevant and makes "most
  recent N papers" a single paginated query.
- **Papers with Code** (structured endpoint): used specifically for GitHub repo
  correlation when ArXiv's abstract doesn't itself contain a repo link — PwC's
  data model exists precisely to link papers to implementations.

## Startups
- **YC company directory**: large, public, well-structured, no auth required for
  listing pages.
- **Product Hunt** (official API): also doubles as a product-signal source.
- **Crunchbase**: documented as `unavailable_documented` — the free tier doesn't
  expose bulk listing, and the full dataset needs a paid API tier. Correct move
  during a trial is to document this rather than scrape their web UI, which is
  explicitly bot-defended.

## Products
- **Product Hunt** (official API) — same source, doubles for the product vertical
  since a PH launch post already contains startup + product + pricing signals.
- **G2**: documented as `unavailable_documented` (Cloudflare-protected).

## News (5 sources, all RSS)
TechCrunch AI, VentureBeat AI, The Verge AI, MIT Technology Review AI, AI News.
All five publish standard RSS feeds — chosen specifically because they don't
require JS rendering or bot-defense bypass, and RSS `pubDate` gives a first-pass
freshness signal before we even fetch the full article (cheap filtering before
expensive parsing).

## Jobs (5 sources)
Greenhouse + Lever (structured per-company JSON APIs — the most reliable
freshness signal via `updated_at`), RemoteOK (official API), HN "Who is Hiring"
monthly thread (official Firebase API), and Wellfound (Playwright, public search
results only, as a last resort for board coverage Greenhouse/Lever don't reach).

## Why not just scrape company career pages directly?
Career pages vary wildly in HTML structure per company (expensive to maintain N
custom parsers) and rarely expose a reliable "posted_at" timestamp — which is a
hard requirement for the 24h freshness gate. Greenhouse/Lever normalize both
problems for the subset of companies that use them, which covers a large fraction
of the AI-company hiring landscape.
