from __future__ import annotations

import importlib.util
from pathlib import Path

from nutev.audit_guardrails import annotate_record
from nutev.reference_identity import canonical_identity, dedupe_records


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doi_url_and_plain_doi_share_identity() -> None:
    plain = canonical_identity({"doi": "10.1000/ABC.DEF", "title": "One"})
    as_url = canonical_identity(
        {"doi": "https://doi.org/10.1000/abc.def", "title": "Different"}
    )
    assert plain == as_url == "doi:10.1000/abc.def"


def test_malformed_pmid_is_not_silently_repaired() -> None:
    row = {"pmid": "12A45", "title": "Fallback Title"}
    assert canonical_identity(row) == "title:fallback title"


def test_http_url_is_normalized_before_title_fallback() -> None:
    first = canonical_identity(
        {"url": "HTTPS://WWW.Example.org/path/#fragment", "title": "A"}
    )
    second = canonical_identity(
        {"url": "https://example.org/path", "title": "B"}
    )
    assert first == second == "url:https://example.org/path"


def test_collection_and_ranking_use_same_identity_contract() -> None:
    collection = _load_tool("collection_gate_test", "tools/run_everything_now.py")
    ranking = _load_tool("ranking_gate_test", "tools/rank_references.py")
    row = {
        "doi": "https://doi.org/10.1000/Example",
        "pmid": "12A45",
        "url": "https://www.example.org/reference/",
        "title": "Example Reference",
    }
    expected = canonical_identity(row)
    assert collection._identity(row) == expected
    assert ranking._identity(row) == expected


def test_shared_dedupe_prefers_richer_record() -> None:
    rows = [
        {
            "doi": "10.1000/example",
            "title": "Short",
            "abstract": "short",
        },
        {
            "doi": "https://doi.org/10.1000/EXAMPLE",
            "title": "Richer manifestation",
            "abstract": "a much richer abstract for the same record",
        },
    ]
    unique = dedupe_records(rows)
    assert len(unique) == 1
    assert unique[0]["title"] == "Richer manifestation"


def test_invalid_identifier_with_url_gets_no_identifier_bonus() -> None:
    ranking = _load_tool("ranking_score_gate_test", "tools/rank_references.py")
    row = annotate_record(
        {
            "title": "Traceable by URL",
            "abstract": "x",
            "source_provider": "crossref",
            "doi": "not-a-doi",
            "url": "https://example.org/reference/1",
        }
    )
    assert row["audit_traceability"] == "B_TRACEABLE_URL"
    scored = ranking.score_record(row, {}, [], {})
    assert scored["score_breakdown"]["identifier"] == 0.0


def test_valid_identifier_keeps_identifier_bonus() -> None:
    ranking = _load_tool("ranking_valid_identifier_test", "tools/rank_references.py")
    row = annotate_record(
        {
            "title": "Traceable by DOI",
            "abstract": "x",
            "source_provider": "crossref",
            "doi": "10.1000/example",
        }
    )
    assert row["audit_traceability"] == "A_IDENTIFIER"
    scored = ranking.score_record(row, {}, [], {})
    assert scored["score_breakdown"]["identifier"] == 2.0
