# Anti-Bot / High-Value Source Strategy

## Priority order (applied per source, documented in `config/sources.yaml`)

1. **Official API** — ArXiv, GitHub, Greenhouse, Lever, RemoteOK, HN Firebase.
   Fastest, most stable, explicitly sanctioned by the publisher.
2. **RSS/Atom feed** — TechCrunch, VentureBeat, The Verge, MIT Tech Review, AI News.
   Publisher-provided machine-readable format; no JS rendering needed.
3. **Structured public endpoint** — e.g. a directory's own paginated JSON API used
   by its front-end (inspected via browser devtools, not reverse-engineered auth).
4. **Plain HTTP + HTML parsing** — for simple server-rendered pages with no API.
5. **Playwright Async, public pages only** — only for content that is publicly
   visible to any visitor but requires JS execution to render (client-side
   pagination, lazy-loaded listings). Includes a polite adaptive delay.
6. **Documented as inaccessible** — for sources that require defeating Cloudflare
   challenges, Datadome fingerprinting, CAPTCHAs, or login walls (e.g. G2,
   Crunchbase's full dataset). We do not attempt to bypass these. See "What we
   explicitly do not do" below.

## What we explicitly do not do

- No CAPTCHA-solving services or headless-browser fingerprint spoofing.
- No credential stuffing / login-wall bypass.
- No IP rotation designed specifically to evade a site's rate limiting or block-list.
- No ignoring `robots.txt` disallow rules.

This is a deliberate engineering judgment call, not a capability gap: for sources
in this category, the correct answer is "acquire via their official paid API tier
during the scale phase" — documented in `config/sources.yaml` as
`unavailable_documented` with a note on the legitimate path forward — rather than
building something that looks like a working scraper but is actually a ToS
violation waiting to get the whole pipeline IP-banned.

## Graceful degradation

- Per-source adaptive rate limiting (small delay before Playwright renders).
- Circuit breaker (`src/llm/retry.py::CircuitBreaker`) reused for HTTP sources too
  — 5 consecutive failures opens a cooldown rather than hammering a struggling host.
- A source returning HTTP 403/503 repeatedly degrades that source's adapter to
  `FAILED` outcomes (retryable later) rather than crashing the whole pool.
