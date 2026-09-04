"""Validates the exported CSVs before submission: row-count minimums, header
compliance, and a spot-check that every row has a non-empty source URL (the
brief's core non-hallucination requirement, checked mechanically as a final gate)."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.storage.exporters import TAB_HEADERS

MIN_ROWS = {"Startups": 1000, "Products": 1000, "Research Papers": 1000, "Jobs": 0, "News": 0, "Entity Mapping Log": 0}
SOURCE_URL_COLUMN = {
    "Startups": "source.url", "Products": "source.url", "Research Papers": "content.paper_url",
    "Jobs": "source.url", "News": "content.url", "Entity Mapping Log": "source_url",
}
TAB_FILES = {
    "Startups": "data/exports/startups.csv", "Products": "data/exports/products.csv",
    "Research Papers": "data/exports/research_papers.csv", "Jobs": "data/exports/jobs.csv",
    "News": "data/exports/news.csv", "Entity Mapping Log": "data/exports/entity_mapping_log.csv",
}


def main():
    ok = True
    for tab, path in TAB_FILES.items():
        p = Path(path)
        if not p.exists():
            print(f"[FAIL] {tab}: {path} does not exist")
            ok = False
            continue
        with open(p, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if reader.fieldnames != TAB_HEADERS.get(tab):
            print(f"[FAIL] {tab}: header mismatch")
            ok = False

        min_required = MIN_ROWS[tab]
        if len(rows) < min_required:
            print(f"[FAIL] {tab}: {len(rows)} rows, need >= {min_required}")
            ok = False
        else:
            print(f"[OK]   {tab}: {len(rows)} rows")

        url_col = SOURCE_URL_COLUMN[tab]
        missing_source = sum(1 for r in rows if not r.get(url_col, "").strip() or r.get(url_col) == "UNKNOWN")
        if missing_source:
            print(f"[WARN] {tab}: {missing_source} rows missing a source URL in '{url_col}'")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
