from __future__ import annotations

from nutev.audit_guardrails import annotate_record, record_traceability


def test_valid_identifiers_are_traceable() -> None:
    cases = [
        ({"doi": "10.1000/example"}, "doi"),
        ({"doi": "https://doi.org/10.1000/example"}, "doi"),
        ({"pmid": "12345678"}, "pmid"),
        ({"pmcid": "PMC123456"}, "pmcid"),
    ]
    for extra, expected_reason in cases:
        status, reasons = record_traceability(
            {"title": "A reference", "source_provider": "pubmed", **extra}
        )
        assert status == "A_IDENTIFIER"
        assert reasons == [expected_reason]


def test_malformed_identifier_without_url_is_quarantined() -> None:
    status, reasons = record_traceability(
        {
            "title": "A reference",
            "source_provider": "pubmed",
            "doi": "not-a-doi",
            "pmid": "12A45",
            "pmcid": "PMC-XYZ",
        }
    )
    assert status == "Q_INVALID_IDENTIFIER"
    assert set(reasons) == {"invalid_doi", "invalid_pmid", "invalid_pmcid"}


def test_malformed_identifier_can_only_fall_back_to_real_http_url() -> None:
    status, reasons = record_traceability(
        {
            "title": "A reference",
            "source_provider": "crossref",
            "doi": "not-a-doi",
            "url": "https://example.org/reference/123",
        }
    )
    assert status == "B_TRACEABLE_URL"
    assert reasons == ["url", "invalid_doi"]


def test_non_http_url_does_not_pass_traceability_gate() -> None:
    status, reasons = record_traceability(
        {
            "title": "A reference",
            "source_provider": "provider",
            "url": "javascript:alert(1)",
        }
    )
    assert status == "Q_UNTRACEABLE"
    assert reasons == ["no_valid_identifier_or_http_url"]


def test_missing_origin_fields_are_quarantined_before_identifier_checks() -> None:
    status, reasons = record_traceability({"doi": "10.1000/example"})
    assert status == "Q_INCOMPLETE_ORIGIN"
    assert set(reasons) == {"missing_provider", "missing_title"}


def test_annotation_never_repairs_invalid_identifier() -> None:
    row = {
        "title": "A reference",
        "source_provider": "provider",
        "doi": "fabricated-doi",
    }
    annotated = annotate_record(row)
    assert annotated["doi"] == "fabricated-doi"
    assert annotated["audit_traceability"] == "Q_INVALID_IDENTIFIER"
    assert annotated["audit_quarantined"] is True
    assert annotated["audit_reasons"] == ["invalid_doi"]
