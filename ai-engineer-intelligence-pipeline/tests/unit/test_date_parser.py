from datetime import datetime, timedelta, timezone

from src.extraction.date_parser import (is_within_last_24h, normalize_publication_date,
                                         parse_iso, parse_relative)


def test_parse_iso():
    result = parse_iso("2026-09-03T10:00:00Z")
    assert result.value == datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)
    assert result.confidence == 1.0


def test_parse_relative_hours():
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    result = parse_relative("2 hours ago", now=now)
    assert result.value == now - timedelta(hours=2)


def test_parse_relative_yesterday():
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    result = parse_relative("Posted yesterday", now=now)
    assert result.value == now - timedelta(days=1)


def test_parse_relative_months_low_confidence():
    result = parse_relative("3 months ago")
    assert result.confidence < 0.6


def test_json_ld_extraction():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "NewsArticle", "datePublished": "2026-09-02T08:30:00Z"}
    </script>
    </head></html>
    """
    result = normalize_publication_date(html=html)
    assert result.value == datetime(2026, 9, 2, 8, 30, tzinfo=timezone.utc)
    assert result.method == "json_ld"


def test_meta_tag_extraction():
    html = '<meta property="article:published_time" content="2026-09-02T20:00:00+00:00">'
    result = normalize_publication_date(html=html)
    assert result.value is not None
    assert result.method == "meta_tag"


def test_freshness_gate_rejects_low_confidence():
    from src.extraction.date_parser import ParsedDate
    stale_but_uncertain = ParsedDate(datetime.now(timezone.utc), 0.3, "relative")
    assert is_within_last_24h(stale_but_uncertain) is False


def test_freshness_gate_accepts_recent_high_confidence():
    now = datetime.now(timezone.utc)
    from src.extraction.date_parser import ParsedDate
    fresh = ParsedDate(now - timedelta(hours=1), 0.9, "iso")
    assert is_within_last_24h(fresh, now=now) is True


def test_unresolved_never_guesses():
    result = parse_relative("some ambiguous text with no date signal")
    assert result.value is None
    assert result.confidence == 0.0
