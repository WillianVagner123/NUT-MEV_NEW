"""Direct coverage for the canonical `nutev.analysis.dedup` public API."""
from __future__ import annotations

from nutev.analysis.dedup import (
    as_text,
    canonical_article_key,
    dedup_rows,
    merge_article_rows,
    normalize_doi,
    normalize_title,
    normalize_url,
    normalize_year,
)


def test_normalize_doi_strips_prefixes_and_lowercases() -> None:
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_doi("doi:10.1000/xyz/") == "10.1000/xyz"
    assert normalize_doi(None) == ""


def test_normalize_url_canonicalizes_scheme_www_and_ports() -> None:
    assert normalize_url("https://www.Example.org:443/path/to/doc/?utm=x") == "example.org/path/to/doc"
    assert normalize_url("http://example.org:80/path/to/doc/") == "example.org/path/to/doc"


def test_normalize_title_and_year() -> None:
    assert normalize_title("  Lifestyle  Intervention! ") == "lifestyle intervention"
    assert normalize_year("2021.0") == "2021"
    assert normalize_year("not-a-year") == ""


def test_canonical_key_prefers_doi_then_pmid_then_url_then_title_year() -> None:
    assert canonical_article_key({"doi": "10.1/a"}) == ("doi", "10.1/a")
    assert canonical_article_key({"pmid": "12345"}) == ("pmid", "12345")
    assert canonical_article_key({"url": "https://x.org/a"}) == ("url", "x.org/a")
    assert canonical_article_key({"title": "A Guide", "year": "2020"}) == (
        "title_year",
        "a guide|2020",
    )
    # No identifying fields → deterministic row hash bucket.
    kind, _ = canonical_article_key({"abstract": "orphan"})
    assert kind == "row_hash"


def test_merge_prefers_pmc_url_and_unions_providers() -> None:
    existing = {"url": "https://doi.org/10.1/a", "matched_providers": "openalex"}
    incoming = {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/", "source": "crossref"}
    merged = merge_article_rows(existing, incoming)
    assert "pmc.ncbi.nlm.nih.gov" in merged["url"]
    providers = merged["matched_providers"].split("|")
    assert "openalex" in providers and "crossref" in providers


def test_dedup_merges_doi_duplicates_and_keeps_order() -> None:
    rows = [
        {"title": "First", "doi": "10.1/a", "source": "pubmed"},
        {"title": "Second", "doi": "10.2/b", "source": "openalex"},
        {"title": "First (dup)", "doi": "https://doi.org/10.1/A", "source": "crossref"},
    ]
    deduped = dedup_rows(rows)
    assert [r["doi"] for r in deduped] == ["10.1/a", "10.2/b"]
    first = deduped[0]
    assert set(first["matched_providers"].split("|")) == {"pubmed", "crossref"}


def test_as_text_normalizes_none_and_numbers() -> None:
    assert as_text(None) == ""
    assert as_text(2020) == "2020"
    assert as_text("  x  ") == "x"
