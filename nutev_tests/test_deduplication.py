from __future__ import annotations

from nutev.analysis.dedup import dedup_rows


def test_dedup_merges_doi_and_providers():
    rows = dedup_rows([
        {"source_provider": "pubmed", "doi": "https://doi.org/10.1/a", "title": "A", "abstract": "short", "url": "https://doi.org/10.1/a"},
        {"source_provider": "crossref", "doi": "10.1/a", "title": "A", "abstract": "longer abstract", "url": "https://example.org/a.pdf"},
    ])
    assert len(rows) == 1
    assert rows[0]["abstract"] == "longer abstract"
    assert rows[0]["url"].endswith(".pdf")
    assert rows[0]["matched_providers"] == "pubmed|crossref"
