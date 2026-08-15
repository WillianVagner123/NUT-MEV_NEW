from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.language import detect_language, translation_record
from nutev.pipelines.document_bundle import build_document_bundle_index
from nutev.pipelines.execution_coverage import write_search_coverage_ledger
from nutev.pipelines.formal_review_queue import build_formal_review_queue
from nutev.pipelines.human_queue import build_human_queue
from nutev.search.licensed_provider_evidence import (
    LicensedProviderExecution,
    default_licensed_evidence_path,
    licensed_pilot_status,
    save_licensed_execution,
)


def test_language_detection_and_translation_contract_preserve_original() -> None:
    detected = detect_language(
        "Este documento apresenta recomendações para alimentação, saúde e estilo de vida."
    )
    assert detected["detected_language"] == "pt"
    with pytest.raises(ValueError, match="cannot overwrite"):
        translation_record(
            document_id="doc_1",
            source_language="pt",
            target_language="en",
            status="COMPLETED",
            original_text_path="same.txt",
            translated_text_path="same.txt",
            translator="local",
            model_or_version="1",
        )
    row = translation_record(
        document_id="doc_1",
        source_language="pt",
        target_language="en",
        status="COMPLETED",
        original_text_path="original.txt",
        translated_text_path="translated.en.txt",
        translator="controlled-service",
        model_or_version="v1",
    )
    assert row["original_text_path"] != row["translated_text_path"]
    assert row["source_language"] == "pt"
    assert row["target_language"] == "en"


def test_document_bundle_keeps_original_ocr_and_translation_under_document_id(tmp_path: Path) -> None:
    summary = build_document_bundle_index(
        tmp_path,
        master_rows=[
            {
                "document_id": "doc_1",
                "title": "Guide",
                "doi": "10.1/a",
                "source_provider": "pubmed",
            }
        ],
        fulltext_rows=[
            {"document_id": "doc_1", "fulltext_status": "fulltext_oa", "fulltext_url": "https://x/a.pdf"}
        ],
        download_manifest=[
            {"document_id": "doc_1", "path": "a.pdf", "sha256": "abc", "status": "ok"}
        ],
        extraction_manifest=[
            {
                "document_id": "doc_1",
                "text_path": "a.txt",
                "used_ocr": True,
                "extraction_status": "ok_ocr",
                "detected_language": "pt",
            }
        ],
        translation_manifest=[
            {
                "document_id": "doc_1",
                "source_language": "pt",
                "target_language": "en",
                "status": "COMPLETED",
                "original_text_path": "a.txt",
                "translated_text_path": "a.en.txt",
            }
        ],
    )
    rows = [json.loads(line) for line in Path(summary["bundle_path"]).read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    bundle = rows[0]
    assert bundle["document_id"] == "doc_1"
    assert bundle["original_artifacts"][0]["kind"] == "original_download"
    assert bundle["extractions"][0]["kind"] == "ocr_text"
    assert bundle["translations"][0]["translated_text_path"] == "a.en.txt"


def _licensed_record(provider: str, export: Path) -> LicensedProviderExecution:
    digest = sha256(export.read_bytes()).hexdigest()
    return LicensedProviderExecution(
        provider=provider,
        strategy_version="post-press-v1",
        search_type="PILOT",
        executed_at="2026-08-15T19:00:00-03:00",
        executed_by="Researcher",
        exact_expression="TITLE-ABS-KEY(nutrition)",
        interface="licensed web interface",
        status="SUCCEEDED",
        total_found=12,
        records_retrieved=12,
        export_path=str(export),
        export_sha256=digest,
    )


def test_licensed_provider_gate_requires_real_hashed_exports(tmp_path: Path) -> None:
    project = tmp_path / "project"
    scopus_export = tmp_path / "scopus.csv"
    wos_export = tmp_path / "wos.txt"
    scopus_export.write_text("id,title\n1,A\n", encoding="utf-8")
    wos_export.write_text("UT\tTI\n1\tA\n", encoding="utf-8")
    save_licensed_execution(
        default_licensed_evidence_path(project, "scopus"),
        _licensed_record("scopus", scopus_export),
    )
    before = licensed_pilot_status(project)
    assert before["complete"] is False
    assert "web_of_science:missing" in before["blockers"]
    save_licensed_execution(
        default_licensed_evidence_path(project, "web_of_science"),
        _licensed_record("web_of_science", wos_export),
    )
    after = licensed_pilot_status(project)
    assert after["complete"] is True
    assert after["provider_substitution_allowed"] is False

    bad = _licensed_record("scopus", scopus_export)
    object.__setattr__(bad, "export_sha256", "0" * 64)
    with pytest.raises(ValueError, match="mismatch"):
        save_licensed_execution(tmp_path / "bad.json", bad)


def test_formal_queue_flags_missing_text_without_inventing_decisions(tmp_path: Path) -> None:
    summary = build_formal_review_queue(
        tmp_path,
        master_rows=[
            {"document_id": "doc_ready", "title": "Ready", "abstract": "A"},
            {"document_id": "doc_missing", "title": "Missing", "abstract": "B"},
        ],
        extraction_manifest=[
            {
                "document_id": "doc_ready",
                "text_path": str(tmp_path / "ready.txt"),
                "extraction_status": "ok",
                "chars": 1000,
                "used_ocr": False,
            }
        ],
    )
    rows = [json.loads(line) for line in Path(summary["queue_path"]).read_text(encoding="utf-8").splitlines()]
    by_id = {row["document_id"]: row for row in rows}
    assert by_id["doc_ready"]["screen_flag"] == "ready_to_screen"
    assert by_id["doc_missing"]["screen_flag"] == "no_full_text"
    assert all(row["reviewer_1_decision"] == "" for row in rows)
    assert all(row["reviewer_2_decision"] == "" for row in rows)
    assert all(row["human_decision_inferred"] is False for row in rows)


def test_human_queue_is_one_current_blocking_task(tmp_path: Path) -> None:
    queue = build_human_queue(
        tmp_path,
        scientific_status={
            "article1_current_phase": "GF03_PRESS",
            "gf02": {},
        },
    )
    assert queue["open_task_count"] == 1
    assert queue["tasks"][0]["kind"] == "EXTERNAL_REVIEW"
    assert queue["scientific_decision_inferred"] is False


def test_coverage_ledger_records_not_executed_and_licensed_routes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "source_registry.json").write_text(
        json.dumps(
            {
                "version": "test-v1",
                "providers": {
                    "pubmed": {
                        "priority": 1,
                        "method_track": "academic_primary",
                        "default_enabled": True,
                        "coverage_note": "test",
                    },
                    "scielo": {
                        "priority": 2,
                        "method_track": "academic_regional",
                        "default_enabled": False,
                        "coverage_note": "prefix-scoped",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    result = write_search_coverage_ledger(
        repo,
        project,
        scientific_status={
            "article1_current_phase": "GF02_PUBMED_PILOT",
            "gf02": {"pubmed_pilot_complete": False, "latest_manifest": None},
        },
    )
    payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    by_provider = {row["provider"]: row for row in payload["rows"]}
    assert by_provider["pubmed"]["attempted"] is False
    assert by_provider["pubmed"]["search_completed"] is False
    assert by_provider["scopus"]["status"] == "LICENSED_MANUAL_ROUTE"
    assert by_provider["web_of_science"]["status"] == "LICENSED_MANUAL_ROUTE"
    assert payload["semantics"]["failure_is_not_zero_results"] is True
