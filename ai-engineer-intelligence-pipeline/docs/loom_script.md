# Loom Video Script (5–10 min)

## 1. Framing (30s)
"This is my submission for the AI Engineer demo task. I'll walk through the
architecture, show the tests passing, demonstrate the non-hallucination
guarantees live against the GitHub API, and then be straightforward about one
constraint in how I built this."

## 2. Repo tour (1 min)
- Show the directory structure matching the brief's requested layout.
- Point to `REQUIREMENTS.md` — "I read the assessment as the source of truth and
  turned every requirement into a checklist here before writing code."

## 3. Run the test suite (1 min)
```
pytest tests/unit -v
```
Narrate: 25 tests, no network or API keys required — covers date parsing, 413
chunking, 429 backoff/circuit-breaker, and entity resolution.

## 4. Live GitHub proof point (2 min)
```
python scripts/generate_demo_data_report.py
```
Narrate: this hits the real GitHub REST API for real repos tied to real papers —
show the star counts (or, if rate-limited, show and explain the circuit breaker
opening — "this is the 429 handling working exactly as designed, live, not
mocked"). Then show the entity resolution output: "OpenAI, Inc." / "Open AI" /
"OpenAI Incorporated" all collapsing to "OpenAI" with full confidence, and an
unknown startup name correctly NOT being force-merged into anything.

## 5. Architecture walkthrough (2–3 min)
Open `architecture.pdf` / `docs/architecture.md` and narrate the four required
answers: scale strategy, 413/429 handling, distributed freshness, storage choice.
Emphasize the reasoning, not just the components.

## 6. Honest disclosure (1–2 min)
"One thing I want to be upfront about: the environment I built this in has
restricted network access — it can reach GitHub's API and package registries,
but not ArXiv, Papers with Code, news RSS feeds, or job boards. Rather than
fabricate the 1,000-row datasets to hit the numbers — which the brief explicitly
treats as instant disqualification — I built and tested the full pipeline and
documented exactly how to run the real bulk crawl in RUNBOOK.md. [If you did
run the real crawl before submitting, replace this section with a walkthrough of
the actual Google Sheet and real row counts instead.]"

## 7. Close (15s)
"That's the submission — repo, architecture doc, and Sheet links are in the
form. Happy to walk through any part of the code in more depth."
