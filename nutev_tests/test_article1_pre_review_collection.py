from __future__ import annotations

import json
from pathlib import Path

import pytest

import nutev.pipelines.article1_pre_review_collection as collection
from nutev.search.base import ProviderResult
from nutev.search.strategy_registry import (
    default_registry_path,
    list_strategy_versions,
    save_strategy_version,
)


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _canonical_query() -> str:
    return collection._canonical_gf02_query(_repo())[1]


def _save_pilot(
    project: Path,
    *,
    strategy_id: str | None = None,
    include_crossref: bool = False,
):
    query = _canonical_query()
    providers = {
        "pubmed": {"specific": query},
        "openalex": {"specific": f"query={query}"},
        "scielo_native": {"specific": f"query={query} | export=missing-scielo.csv"},
    }
    if include_crossref:
        providers["crossref"] = {"specific": f"query={query}"}
    return save_strategy_version(
        default_registry_path(project),
        title="Article 1 discovery",
        query_text="Article 1 canonical GF-02",
        strategy_payload={
            "query": [query],
            "filters": {},
            "providers": providers,
        },
        search_type="PILOT",
        prisma_eligible=False,
        created_by="test",
        strategy_id=strategy_id,
    )


def _result(provider: str, index: int = 1) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        query="q",
        rows=[
            {
                "title": f"Document {provider} {index}",
                "doi": f"10.1000/{provider}-{index}",
                "url": f"https://example.org/{provider}/{index}",
            }
        ],
        total_found=1,
        total_returned=1,
        status="completed",
        checkpoint_path=f"checkpoint-{provider}.json",
        meta={"test": True},
    )


def test_real_collection_saves_provider_snapshots_and_never_promotes_science(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    version = _save_pilot(project)
    called: list[str] = []

    def fake_search(**kwargs):
        provider = str(kwargs["provider"])
        called.append(provider)
        return _result(provider)

    result = collection.run_pre_review_collection(
        project,
        repo_root=_repo(),
        search_fn=fake_search,
    )

    assert version.version_id == result["source_strategy_version_id"]
    assert called == ["pubmed", "openalex"]
    assert result["status"] == "COMPLETE"
    assert result["records_returned"] == 2
    assert result["unique_records"] == 2
    assert result["prisma_eligible"] is False
    assert result["formal_execution_authorized"] is False
    assert result["scientific_gate_effect"] == "NONE"
    assert result["human_decision_inferred"] is False
    assert result["autosave"]["enabled"] is True
    assert result["autosave"]["resume_same_search_run"] is True
    assert result["providers_saved"] == ["pubmed", "openalex"]
    assert result["providers_pending"] == []
    assert Path(result["master_corpus_path"]).is_file()

    for item in result["provider_snapshots"]:
        path = Path(str(item["snapshot_path"]))
        assert path.is_file()
        assert len(str(item["snapshot_sha256"])) == 64

    deferred = {item["provider"]: item["reason"] for item in result["providers_deferred"]}
    assert deferred["scielo_native"] == "official_export_required_or_missing"
    assert deferred["europepmc"] == "no_exact_provider_expression_registered"
    assert deferred["scopus"] == "licensed_execution_required"
    assert deferred["web_of_science"] == "licensed_execution_required"

    persisted = json.loads(
        (project / "07_logs" / "pre_review_collection" / "latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert persisted["collection_type"] == "REAL_PRE_REVIEW_COLLECTION"
    assert persisted["status"] == "COMPLETE"
    assert persisted["records_saved_partial"] == 2


def test_interruption_keeps_first_provider_and_resume_skips_it(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _save_pilot(project)
    first_calls: list[str] = []

    def interrupted_search(**kwargs):
        provider = str(kwargs["provider"])
        first_calls.append(provider)
        if provider == "openalex":
            raise KeyboardInterrupt()
        return _result(provider)

    with pytest.raises(KeyboardInterrupt):
        collection.run_pre_review_collection(
            project,
            repo_root=_repo(),
            search_fn=interrupted_search,
        )

    state_path = project / "07_logs" / "pre_review_collection" / "latest.json"
    interrupted = json.loads(state_path.read_text(encoding="utf-8"))
    assert first_calls == ["pubmed", "openalex"]
    assert interrupted["status"] == "INTERRUPTED"
    assert interrupted["providers_saved"] == ["pubmed"]
    assert interrupted["providers_pending"] == ["openalex"]
    assert interrupted["records_saved_partial"] == 1
    first_run_id = interrupted["search_run_id"]
    pubmed_snapshot = Path(interrupted["provider_snapshots"][0]["snapshot_path"])
    assert pubmed_snapshot.is_file()

    resumed_calls: list[str] = []

    def resumed_search(**kwargs):
        provider = str(kwargs["provider"])
        resumed_calls.append(provider)
        return _result(provider)

    resumed = collection.run_pre_review_collection(
        project,
        repo_root=_repo(),
        search_fn=resumed_search,
    )

    assert resumed_calls == ["openalex"]
    assert resumed["search_run_id"] == first_run_id
    assert resumed["providers_saved"] == ["pubmed", "openalex"]
    assert resumed["providers_pending"] == []
    assert resumed["status"] == "COMPLETE"
    assert resumed["records_saved_partial"] == 2


def test_failed_provider_stays_pending_and_is_retried_without_repeating_saved_source(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    _save_pilot(project)

    def first_attempt(**kwargs):
        provider = str(kwargs["provider"])
        if provider == "openalex":
            raise RuntimeError("temporary provider outage")
        return _result(provider)

    partial = collection.run_pre_review_collection(
        project,
        repo_root=_repo(),
        search_fn=first_attempt,
    )
    assert partial["status"] == "PARTIAL"
    assert partial["providers_saved"] == ["pubmed"]
    assert partial["providers_pending"] == ["openalex"]
    assert partial["provider_failure_history"][-1]["provider"] == "openalex"
    assert partial["complete"] is False if "complete" in partial else True

    calls: list[str] = []

    def second_attempt(**kwargs):
        provider = str(kwargs["provider"])
        calls.append(provider)
        return _result(provider)

    completed = collection.run_pre_review_collection(
        project,
        repo_root=_repo(),
        search_fn=second_attempt,
    )
    assert calls == ["openalex"]
    assert completed["status"] == "COMPLETE"
    assert completed["providers_pending"] == []


def test_collection_is_invalidated_by_a_new_matching_strategy_version(tmp_path: Path) -> None:
    project = tmp_path / "project"
    first = _save_pilot(project)

    def fake_search(**kwargs):
        return _result(str(kwargs["provider"]))

    collection.run_pre_review_collection(project, repo_root=_repo(), search_fn=fake_search)
    assert collection.pre_review_collection_status(project, repo_root=_repo())["complete"] is True

    _save_pilot(project, strategy_id=first.strategy_id, include_crossref=True)
    status = collection.pre_review_collection_status(project, repo_root=_repo())
    assert status["complete"] is False
    assert status["can_run"] is True


def test_missing_registry_strategy_materializes_only_canonical_gf02_mirror(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    called: list[str] = []

    def fake_search(**kwargs):
        provider = str(kwargs["provider"])
        called.append(provider)
        return _result(provider)

    result = collection.run_pre_review_collection(
        project,
        repo_root=_repo(),
        search_fn=fake_search,
    )

    assert called == ["pubmed"]
    assert result["prisma_eligible"] is False
    assert result["formal_execution_authorized"] is False
    versions = list_strategy_versions(default_registry_path(project), limit=10)
    assert len(versions) == 1
    version = versions[0]
    assert version["search_type"] == "PILOT"
    assert version["prisma_eligible"] is False
    assert version["providers"]["pubmed"]["specific"] == _canonical_query()
    assert version["created_by"] == "SYSTEM_DETERMINISTIC_GF02_MIRROR"


def test_snapshot_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _save_pilot(project)

    def fake_search(**kwargs):
        return _result(str(kwargs["provider"]))

    result = collection.run_pre_review_collection(
        project,
        repo_root=_repo(),
        search_fn=fake_search,
    )
    snapshot = Path(result["provider_snapshots"][0]["snapshot_path"])
    snapshot.write_text("tampered\n", encoding="utf-8")

    state_path = project / "07_logs" / "pre_review_collection" / "latest.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "INTERRUPTED"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(RuntimeError, match="SHA-256"):
        collection.run_pre_review_collection(
            project,
            repo_root=_repo(),
            search_fn=fake_search,
        )
