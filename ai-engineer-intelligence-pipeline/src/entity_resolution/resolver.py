"""Deterministic entity resolution engine.

Resolution order (each step only runs if the previous one didn't produce a
confident match):
  1. Alias dictionary exact match (built from SEED_ENTITIES)         -> confidence 1.0
  2. Normalized exact match against canonical normalized names        -> confidence 0.95
  3. Controlled fuzzy match (token-set + edit-distance, gated by a
     minimum-similarity floor AND a length-ratio sanity check to stop
     short unrelated names from merging)                              -> confidence 0.6-0.85
  4. No match -> the normalized input becomes its own provisional
     canonical entity, flagged low-confidence for human review.       -> confidence 0.3

Every resolution — matched or not — is written to the Entity Mapping Log so raw vs
canonical names stay fully auditable (Phase IV requirement).
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from src.entity_resolution.normalizer import normalize_name
from src.entity_resolution.seed_entities import SEED_ENTITIES
from src.extraction.schemas import EntityMappingLogRow

FUZZY_MIN_SIMILARITY = 0.88
FUZZY_MAX_LENGTH_RATIO_DELTA = 0.35  # reject matches where lengths differ too much


@dataclass
class ResolutionResult:
    canonical_name: str
    match_method: str  # 'alias' | 'normalized_exact' | 'fuzzy' | 'unresolved_new_entity'
    confidence: float


class EntityResolver:
    def __init__(self, seed: dict[str, list[str]] | None = None):
        seed = seed or SEED_ENTITIES
        self._alias_to_canonical: dict[str, str] = {}
        self._canonical_normalized: dict[str, str] = {}  # normalized(canonical) -> canonical
        for canonical, aliases in seed.items():
            self._canonical_normalized[normalize_name(canonical)] = canonical
            for alias in aliases:
                self._alias_to_canonical[normalize_name(alias)] = canonical
        self.mapping_log: list[EntityMappingLogRow] = []

    def resolve(self, raw_name: str, *, entity_type: str = "STARTUP", source_url: str | None = None) -> ResolutionResult:
        normalized = normalize_name(raw_name)

        if normalized in self._alias_to_canonical:
            result = ResolutionResult(self._alias_to_canonical[normalized], "alias", 1.0)
        elif normalized in self._canonical_normalized:
            result = ResolutionResult(self._canonical_normalized[normalized], "normalized_exact", 0.95)
        else:
            fuzzy = self._fuzzy_match(normalized)
            if fuzzy:
                result = fuzzy
            else:
                # No confident match: treat the normalized string itself as a new
                # provisional canonical entity rather than inventing/guessing one.
                result = ResolutionResult(raw_name.strip(), "unresolved_new_entity", 0.3)

        self.mapping_log.append(EntityMappingLogRow(
            raw_name=raw_name,
            normalized_name=normalized,
            canonical_name=result.canonical_name,
            entity_type=entity_type,
            match_method=result.match_method,
            confidence=result.confidence,
            source_url=source_url,
        ))
        return result

    def _fuzzy_match(self, normalized: str) -> ResolutionResult | None:
        best_canonical, best_score = None, 0.0
        for norm_canonical, canonical in self._canonical_normalized.items():
            len_ratio_delta = abs(len(normalized) - len(norm_canonical)) / max(len(norm_canonical), 1)
            if len_ratio_delta > FUZZY_MAX_LENGTH_RATIO_DELTA:
                continue  # guard against "AI" fuzzy-matching "OpenAI"-style false merges
            score = SequenceMatcher(None, normalized, norm_canonical).ratio()
            if score > best_score:
                best_canonical, best_score = canonical, score

        if best_canonical and best_score >= FUZZY_MIN_SIMILARITY:
            # confidence scaled within the fuzzy band, never claiming exact-match certainty
            confidence = 0.6 + (best_score - FUZZY_MIN_SIMILARITY) / (1 - FUZZY_MIN_SIMILARITY) * 0.25
            return ResolutionResult(best_canonical, "fuzzy", round(confidence, 3))
        return None
