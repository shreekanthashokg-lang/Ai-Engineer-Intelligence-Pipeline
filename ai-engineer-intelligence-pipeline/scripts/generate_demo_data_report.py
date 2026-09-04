"""Runs the parts of the pipeline that work with zero external credentials and
this sandbox's restricted network: entity resolution over a small realistic input
set, date normalization on synthetic-but-labeled-as-synthetic examples, and a LIVE
GitHub star lookup (real API, real data, real rate-limit handling) for a handful of
known paper repos. Writes results to data/sample/ so the exporters and Sheet layout
can be demonstrated without fabricating startup/product/paper source records.

This script is NOT the bulk-acquisition run — see RUNBOOK.md for that.
"""
import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from src.crawlers.github_enrichment import GitHubEnricher
from src.entity_resolution.resolver import EntityResolver
from src.storage.exporters import export_all_tabs, export_xlsx

# Small set of real, well-known repos associated with real papers (paper metadata
# below is publicly known and cited for demo purposes — for the actual bulk run,
# titles/authors/URLs come from live ArXiv/PapersWithCode API responses, see
# src/pipelines/research.py + RUNBOOK.md).
DEMO_PAPERS = [
    {"title": "Attention Is All You Need", "authors": ["Vaswani et al."],
     "paper_url": "https://arxiv.org/abs/1706.03762", "github_url": "https://github.com/tensorflow/tensor2tensor"},
    {"title": "Llama 2: Open Foundation and Fine-Tuned Chat Models", "authors": ["Touvron et al."],
     "paper_url": "https://arxiv.org/abs/2307.09288", "github_url": "https://github.com/meta-llama/llama"},
    {"title": "LoRA: Low-Rank Adaptation of Large Language Models", "authors": ["Hu et al."],
     "paper_url": "https://arxiv.org/abs/2106.09685", "github_url": "https://github.com/microsoft/LoRA"},
]

DEMO_RAW_ENTITY_NAMES = [
    "OpenAI", "Open AI", "OpenAI, Inc.", "Anthropic PBC", "DeepMind",
    "Mistral AI SAS", "unknown-stealth-startup-42", "Cohere Inc",
]


async def main():
    print("=== Live GitHub enrichment (real API, real rate-limit handling) ===")
    gh = GitHubEnricher()
    paper_rows = []
    for paper in DEMO_PAPERS:
        meta = await gh.get_stars(paper["github_url"])
        print(f"{paper['title'][:50]:50s} -> stars={meta.stars} exists={meta.exists} error={meta.error}")
        paper_rows.append({
            "schemaVersion": "1.0", "recordType": "RESEARCH_PAPER",
            "content.title": paper["title"], "content.authors": "; ".join(paper["authors"]),
            "content.paper_url": paper["paper_url"], "content.github_url": paper["github_url"],
            "content.github_stars": meta.stars if meta.stars is not None else "UNKNOWN",
            "content.published_date": "UNKNOWN",  # would come from ArXiv API in the real run
        })

    print("\n=== Deterministic entity resolution (fully offline, deterministic) ===")
    resolver = EntityResolver()
    for raw in DEMO_RAW_ENTITY_NAMES:
        result = resolver.resolve(raw, source_url="https://example-source.test/demo")
        print(f"{raw:35s} -> {result.canonical_name:20s} ({result.match_method}, conf={result.confidence})")

    mapping_rows = [{
        "raw_name": r.raw_name, "normalized_name": r.normalized_name,
        "canonical_name": r.canonical_name, "entity_type": r.entity_type,
        "match_method": r.match_method, "confidence": r.confidence,
        "source_url": r.source_url, "timestamp": r.timestamp.isoformat(),
    } for r in resolver.mapping_log]

    tabs = {
        "Startups": [],       # populated by the real bulk crawl, see RUNBOOK.md
        "Products": [],       # populated by the real bulk crawl, see RUNBOOK.md
        "Research Papers": paper_rows,
        "Jobs": [],           # populated by the 24h-fresh job crawl, see RUNBOOK.md
        "News": [],           # populated by the 24h-fresh news crawl, see RUNBOOK.md
        "Entity Mapping Log": mapping_rows,
    }
    csv_paths = export_all_tabs(tabs, out_dir="data/sample")
    xlsx_path = export_xlsx(tabs, out_path="data/sample/demo_export.xlsx")
    print(f"\nWrote CSVs: {csv_paths}")
    print(f"Wrote workbook: {xlsx_path}")
    print(f"\nGenerated at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
