from src.entity_resolution.normalizer import normalize_name
from src.entity_resolution.resolver import EntityResolver


def test_normalizer_strips_legal_suffix_and_case():
    assert normalize_name("OpenAI, Inc.") == "openai"
    assert normalize_name("Open AI") == "open ai"


def test_resolver_alias_exact_match():
    r = EntityResolver()
    for raw in ["OpenAI", "Open AI", "OpenAI, Inc.", "OpenAI Inc", "OpenAI Incorporated"]:
        result = r.resolve(raw)
        assert result.canonical_name == "OpenAI"
        assert result.confidence >= 0.95


def test_resolver_does_not_merge_unrelated_short_names():
    r = EntityResolver()
    # "AI" should NOT fuzzy-merge into "xAI" or similar short canonical names
    result = r.resolve("AI")
    assert result.canonical_name != "xAI"


def test_resolver_unknown_entity_is_not_hallucinated_into_a_seed_name():
    r = EntityResolver()
    result = r.resolve("Totally Unknown Startup Co")
    assert result.match_method == "unresolved_new_entity"
    assert result.canonical_name == "Totally Unknown Startup Co"
    assert result.confidence < 0.5


def test_mapping_log_records_every_resolution():
    r = EntityResolver()
    r.resolve("OpenAI Inc", source_url="https://example.com/a")
    r.resolve("Some New Co", source_url="https://example.com/b")
    assert len(r.mapping_log) == 2
    assert r.mapping_log[0].source_url == "https://example.com/a"
