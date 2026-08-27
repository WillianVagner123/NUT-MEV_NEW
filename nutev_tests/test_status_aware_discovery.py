from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.search.status_adapters import (
    CrossrefStatusClient,
    DOAJStatusClient,
    EuropePMCStatusClient,
    OpenAlexStatusClient,
    SemanticScholarStatusClient,
)
from nutev.search import status_adapters
from nutev.science import run_topic_competency_audit


CLIENTS = (
    EuropePMCStatusClient,
    OpenAlexStatusClient,
    CrossrefStatusClient,
    DOAJStatusClient,
    SemanticScholarStatusClient,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_network_disabled_is_skipped_not_zero_for_all_status_clients(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("NUTEV_DISABLE_NETWORK", "1")
    for client_type in CLIENTS:
        result = client_type().search("nutrition", limit=5)
        assert result.status == "skipped"
        assert result.total_found is None
        assert result.total_returned == 0
        assert result.error == "network_disabled"


def test_provider_failure_is_failed_not_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    monkeypatch.setattr(status_adapters.europepmc_mod, "_europepmc_get", lambda params: None)
    monkeypatch.setattr(status_adapters.openalex_mod, "_openalex_get", lambda params: None)
    monkeypatch.setattr(status_adapters.crossref_mod, "_crossref_get", lambda params: None)
    monkeypatch.setattr(status_adapters.doaj_mod, "_doaj_get", lambda query, page, page_size: None)
    monkeypatch.setattr(status_adapters.semantic_scholar_mod, "_s2_get", lambda query, limit, offset: None)

    for client_type in CLIENTS:
        result = client_type().search("nutrition", limit=5)
        assert result.status == "failed"
        assert result.error == "provider_request_failed"
        assert result.total_found is None
        assert result.total_returned == 0


def test_successful_zero_hit_response_is_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    monkeypatch.setattr(
        status_adapters.europepmc_mod,
        "_europepmc_get",
        lambda params: {"hitCount": 0, "resultList": {"result": []}},
    )
    monkeypatch.setattr(
        status_adapters.openalex_mod,
        "_openalex_get",
        lambda params: {"meta": {"count": 0, "next_cursor": None}, "results": []},
    )
    monkeypatch.setattr(
        status_adapters.crossref_mod,
        "_crossref_get",
        lambda params: {"message": {"total-results": 0, "items": []}},
    )
    monkeypatch.setattr(
        status_adapters.doaj_mod,
        "_doaj_get",
        lambda query, page, page_size: {"total": 0, "results": []},
    )
    monkeypatch.setattr(
        status_adapters.semantic_scholar_mod,
        "_s2_get",
        lambda query, limit, offset: {"total": 0, "data": [], "next": None},
    )

    for client_type in CLIENTS:
        result = client_type().search("nutrition", limit=5)
        assert result.status == "empty"
        assert result.error is None
        assert result.total_found == 0
        assert result.total_returned == 0


def test_europepmc_preserves_partial_results_when_later_page_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    responses = iter(
        [
            {
                "hitCount": 20,
                "resultList": {
                    "result": [
                        {
                            "id": "1",
                            "title": "Nutrition competency framework",
                            "doi": "10.1000/example.1",
                        }
                    ]
                },
                "nextCursorMark": "next",
            },
            None,
        ]
    )
    monkeypatch.setattr(
        status_adapters.europepmc_mod,
        "_europepmc_get",
        lambda params: next(responses),
    )

    result = EuropePMCStatusClient().search("nutrition", limit=5)
    assert result.status == "partial"
    assert result.error == "provider_request_failed_after_partial_results"
    assert result.total_found == 20
    assert result.total_returned == 1
    assert result.rows[0]["source_provider"] == "europepmc"


def _topic_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    records = tmp_path / "nutev_core_records_relational.jsonl"
    _write_jsonl(
        records,
        [
            {
                "id": "record:doi:10.1000/status.1",
                "document_id": "doi:10.1000/status.1",
                "schema_version": 3,
                "identity": {
                    "title": "Food literacy in nutrition practice",
                    "source_provider": "pubmed",
                    "year": 2026,
                },
                "bibliography": {
                    "abstract": "Food literacy and nutrition competencies.",
                    "keywords": ["food literacy", "nutrition"],
                },
                "acquisition": {"full_text_status": "retrieved"},
                "semantic": {"facts": []},
                "relational": {"entities": [], "relations": []},
            }
        ],
    )
    manifest = tmp_path / "RELATIONS_MANIFEST.json"
    _write_json(
        manifest,
        {
            "relations_type": "NUTEV_CORE_RELATIONAL_MAPPING",
            "status": "PASS",
            "outputs": {
                "relational_core_records": {
                    "path": str(records),
                    "sha256": _sha(records),
                }
            },
        },
    )
    profile = tmp_path / "topic_profile.json"
    _write_json(
        profile,
        {
            "schema_version": 1,
            "profile_kind": "NUTEV_TOPIC_COMPETENCY_REGISTRY",
            "profile_id": "status-aware-test",
            "version": "1.0.0-prefreeze",
            "status": "PREFREEZE",
            "formal_gate": {"authorized": False},
            "audit": {
                "min_documents": 1,
                "min_providers": 1,
                "freshness_years": 5,
            },
            "topics": [
                {
                    "id": "food_competence",
                    "label": "Food competence",
                    "kind": "competency",
                    "terms": ["food literacy"],
                    "anchor_terms": ["nutrition*"],
                    "query_mode": "anchor_and_terms",
                }
            ],
        },
    )
    return records, manifest, profile


def test_topic_audit_executes_all_explicit_status_adapters_as_skipped_when_network_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    records, manifest, profile = _topic_fixture(tmp_path)
    monkeypatch.setenv("NUTEV_DISABLE_NETWORK", "1")
    output = tmp_path / "topics"

    result = run_topic_competency_audit(
        records,
        manifest,
        profile,
        output,
        execute_search=True,
        limit=5,
    )

    assert result["active_search_executed"] is True
    assert result["active_search_results"] == 0
    assert set(result["status_aware_providers"]) == {
        "pubmed",
        "europepmc",
        "openalex",
        "crossref",
        "doaj",
        "semantic_scholar",
    }

    plan = json.loads((output / "active_search_plan.json").read_text(encoding="utf-8"))
    by_provider = {row["provider"]: row for row in plan["searches"]}
    for provider in result["status_aware_providers"]:
        assert by_provider[provider]["execution"] == "EXECUTABLE_STATUS_AWARE"
    assert by_provider["lilacs_bvs"]["execution"] == "PLAN_ONLY_STATUS_ADAPTER_REQUIRED"
    assert by_provider["scielo"]["execution"] == "PLAN_ONLY_STATUS_ADAPTER_REQUIRED"
    assert by_provider["scopus"]["execution"] == "MANUAL_LICENSED"
    assert by_provider["wos"]["execution"] == "MANUAL_LICENSED"

    runs = [
        json.loads(line)
        for line in (output / "active_search_runs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    run_by_provider = {row["provider"]: row for row in runs}
    for provider in result["status_aware_providers"]:
        assert run_by_provider[provider]["status"] == "skipped"
        assert run_by_provider[provider]["total_found"] is None
    assert run_by_provider["lilacs_bvs"]["status"] == "planned_not_executed"
    assert run_by_provider["scielo"]["status"] == "planned_not_executed"
    assert run_by_provider["scopus"]["status"] == "planned_not_executed"
    assert run_by_provider["wos"]["status"] == "planned_not_executed"

    audit_manifest = json.loads(
        (output / "TOPIC_AUDIT_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert audit_manifest["execution_contract"]["empty_is_distinct_from_failure"] is True
    assert audit_manifest["counts"]["active_search_status_counts"]["skipped"] == 6
    assert (output / "active_search_results.jsonl").read_text(encoding="utf-8") == ""
