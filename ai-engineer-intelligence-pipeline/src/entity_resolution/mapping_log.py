"""Persists an EntityResolver's in-memory mapping_log to CSV (and, in the full
deployment, to the entity_mapping_log DB table via storage/repository.py) so raw
vs canonical resolutions stay auditable across runs, not just within one process.
"""
from __future__ import annotations

import csv
from pathlib import Path

from src.entity_resolution.resolver import EntityResolver

HEADERS = ["raw_name", "normalized_name", "canonical_name", "entity_type",
           "match_method", "confidence", "source_url", "timestamp"]


def flush_mapping_log(resolver: EntityResolver, path: str = "data/processed/entity_mapping_log.csv") -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    file_exists = Path(path).exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        if not file_exists:
            writer.writeheader()
        for row in resolver.mapping_log:
            writer.writerow({
                "raw_name": row.raw_name, "normalized_name": row.normalized_name,
                "canonical_name": row.canonical_name, "entity_type": row.entity_type,
                "match_method": row.match_method, "confidence": row.confidence,
                "source_url": row.source_url, "timestamp": row.timestamp.isoformat(),
            })
    resolver.mapping_log.clear()  # flushed rows shouldn't be double-written on next flush
    return path
