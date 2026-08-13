from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from nutev.engine.models import DocumentCandidate, EvidenceRecord, ProviderHit
from nutev.engine.validators import (
    canonical_document_key,
    normalize_doi,
    normalize_pmcid,
    normalize_pmid,
    normalize_url,
    validate_workstream,
)


def test_normalize_doi_extracts_canonical_doi_from_noisy_metadata():
    assert normalize_doi("pii: qdag137. doi: 10.1093/jsxmed/qdag137") == "10.1093/jsxmed/qdag137"
    assert normalize_doi("https://doi.org/10.1000/ABC.123") == "10.1000/abc.123"
    assert normalize_doi("not a doi") is None


def test_identifier_normalizers_are_strict():
    assert normalize_pmid("123456") == "123456"
    assert normalize_pmid("PMID: 123456") is None
    assert normalize_pmcid("12345") == "PMC12345"
    assert normalize_pmcid("pmc12345") == "PMC12345"
    assert normalize_pmcid("abc") is None
    assert normalize_url("https://example.org/a") == "https://example.org/a"
    assert normalize_url("javascript:void(0)") is None


def test_normalize_url_removes_tracking_and_canonicalizes_netloc():
    assert (
        normalize_url("https://www.Example.org:443/a/?utm_source=newsletter&b=2&a=1")
        == "https://example.org/a?a=1&b=2"
    )
    assert normalize_url("http://www.example.org:80/a/") == "http://example.org/a"


def test_workstream_aliases_normalize_to_canonical_semantics():
    assert validate_workstream("busca1") == "policy_systems"
    assert validate_workstream("busca2a") == "clinical_outcomes"
    assert validate_workstream("busca2b") == "implementation"
    assert validate_workstream("a3") == "framework"
    assert validate_workstream("article3_framework") == "framework"
    assert validate_workstream("a4_framework") == "framework"
    assert validate_workstream("global_watch") == "global_watch"
    assert validate_workstream("implementation") == "implementation"
    with pytest.raises(ValueError):
        validate_workstream("unknown")


def test_provider_hit_enforces_http_url_and_normalizes_doi():
    hit = ProviderHit(
        provider="pubmed",
        query="diet",
        title="Diet trial",
        url="https://pubmed.ncbi.nlm.nih.gov/123/",
        doi="doi:10.1000/ABC",
        workstream="busca1",
    )
    assert hit.doi == "10.1000/abc"
    assert hit.workstream == "policy_systems"

    with pytest.raises(ValidationError):
        ProviderHit(
            provider="pubmed",
            query="diet",
            title="Bad URL",
            url="ftp://example.org/file.pdf",
        )


def test_document_candidate_normalizes_ids_and_workstream():
    candidate = DocumentCandidate(
        document_id="doc-1",
        title="Example",
        original_url="https://doi.org/10.1000/XYZ",
        doi="DOI: 10.1000/XYZ",
        pmid=12345,
        pmcid="12345",
        workstream="article3_framework",
        created_at=datetime.now(timezone.utc),
    )
    assert candidate.doi == "10.1000/xyz"
    assert candidate.pmid == "12345"
    assert candidate.pmcid == "PMC12345"
    assert candidate.workstream == "framework"


def test_evidence_record_rejects_incoherent_status_transition():
    with pytest.raises(ValidationError):
        EvidenceRecord(
            document_id="doc-1",
            title="Blocked paper",
            download_status="metadata_only",
            extraction_status="ok_ocr",
        )


def test_evidence_record_requires_artifact_for_downloaded_pdf():
    with pytest.raises(ValidationError):
        EvidenceRecord(
            document_id="doc-2",
            title="Downloaded paper",
            download_status="pdf",
            extraction_status="missing",
        )


def test_canonical_document_key_priority():
    assert canonical_document_key({"doi": "DOI:10.1000/ABC", "url": "https://x.test"}) == "doi:10.1000/abc"
    assert canonical_document_key({"pmid": "123", "url": "https://x.test"}) == "pmid:123"
    assert canonical_document_key({"pmcid": "pmc123", "url": "https://x.test"}) == "pmcid:PMC123"
    assert canonical_document_key({"url": "https://x.test/a"}) == "url:https://x.test/a"


def test_canonical_document_key_collapses_equivalent_urls():
    first = canonical_document_key(
        {"url": "https://www.example.org:443/path/?utm_medium=email&b=2&a=1"}
    )
    second = canonical_document_key({"url": "https://example.org/path?a=1&b=2"})

    assert first == second == "url:https://example.org/path?a=1&b=2"


def test_canonical_document_key_extracts_doi_from_candidate_urls():
    assert canonical_document_key({"url": "https://doi.org/10.1000/ABC.123"}) == "doi:10.1000/abc.123"
    assert canonical_document_key({"original_url": "https://doi.org/10.1093/jsxmed/qdag137"}) == "doi:10.1093/jsxmed/qdag137"
    assert canonical_document_key({"resolved_url": "https://doi.org/10.1016/j.jand.2025.01.001?utm_source=newsletter"}) == "doi:10.1016/j.jand.2025.01.001"
