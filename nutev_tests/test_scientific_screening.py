from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.cli import main as cli_main
from nutev.science import (
    ScreeningDecision,
    ScreeningDecisionValue,
    ScreeningImportError,
    ScreeningStage,
    derive_prisma_counts,
    events_from_screening_decision,
    run_screening_import,
)


DECIDED_AT = "2026-08-26T20:00:00+00:00"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_scientific_documents(tmp_path: Path) -> tuple[Path, Path]:
    documents = tmp_path / "document_candidates.jsonl"
    document = {
        "id": "doi:10.1000/a",
        "source_provider": "pubmed",
        "title": "Candidate A",
    }
    documents.write_text(json.dumps(document) + "\n", encoding="utf-8")
    manifest = tmp_path / "SCIENTIFIC_EXPORT_MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "export_type": "NUTEV_SCIENTIFIC_OBJECT_EXPORT",
                "status": "PASS",
                "outputs": {
                    "document_candidates": {
                        "path": str(documents),
                        "sha256": _sha(documents),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return documents, manifest


def test_title_abstract_include_records_screening_without_inclusion():
    decision = ScreeningDecision(
        id="screen-1",
        document_id="doi:10.1000/a",
        stage=ScreeningStage.TITLE_ABSTRACT,
        decision=ScreeningDecisionValue.INCLUDE,
        adjudicator="reviewer-final",
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["screened"]
    assert prisma.screened == 1
    assert prisma.included == 0
    assert prisma.assessed_for_eligibility == 0


def test_title_abstract_exclusion_requires_and_preserves_reason():
    decision = ScreeningDecision(
        id="screen-2",
        document_id="doi:10.1000/b",
        stage=ScreeningStage.TITLE_ABSTRACT,
        decision=ScreeningDecisionValue.EXCLUDE,
        reason="wrong population",
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["screened", "excluded_screening"]
    assert events[1].reason == "wrong population"
    assert prisma.screened == 1
    assert prisma.excluded_screening == 1


def test_exclusion_without_reason_fails_closed():
    decision = ScreeningDecision(
        id="screen-3",
        document_id="doi:10.1000/c",
        stage=ScreeningStage.FULL_TEXT,
        decision=ScreeningDecisionValue.EXCLUDE,
        decided_at=DECIDED_AT,
    )

    with pytest.raises(ValueError, match="requires an explicit reason"):
        events_from_screening_decision(decision)


def test_full_text_include_generates_eligibility_and_inclusion_events():
    decision = ScreeningDecision(
        id="screen-4",
        document_id="doi:10.1000/d",
        stage=ScreeningStage.FULL_TEXT,
        decision=ScreeningDecisionValue.INCLUDE,
        adjudicator="adjudicator-1",
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["assessed_for_eligibility", "included"]
    assert prisma.assessed_for_eligibility == 1
    assert prisma.included == 1


def test_full_text_uncertain_does_not_infer_inclusion_or_exclusion():
    decision = ScreeningDecision(
        id="screen-5",
        document_id="doi:10.1000/e",
        stage=ScreeningStage.FULL_TEXT,
        decision=ScreeningDecisionValue.UNCERTAIN,
        decided_at=DECIDED_AT,
    )

    events = events_from_screening_decision(decision)
    prisma = derive_prisma_counts(events)

    assert [event.action for event in events] == ["assessed_for_eligibility"]
    assert prisma.assessed_for_eligibility == 1
    assert prisma.included == 0
    assert prisma.excluded_full_text == 0


def test_screening_import_validates_documents_and_derives_prisma(tmp_path: Path):
    documents, manifest = _write_scientific_documents(tmp_path)
    decisions = tmp_path / "screening_decisions_input.jsonl"
    rows = [
        {
            "id": "ta-a",
            "document_id": "doi:10.1000/a",
            "stage": "title_abstract",
            "decision": "include",
            "adjudicator": "reviewer-final",
            "decided_at": DECIDED_AT,
        },
        {
            "id": "ft-a",
            "document_id": "doi:10.1000/a",
            "stage": "full_text",
            "decision": "include",
            "adjudicator": "reviewer-final",
            "decided_at": DECIDED_AT,
        },
    ]
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    output = tmp_path / "screening"

    result = run_screening_import(documents, manifest, decisions, output)

    assert result["status"] == "COMPLETE"
    assert result["prisma"]["screened"] == 1
    assert result["prisma"]["assessed_for_eligibility"] == 1
    assert result["prisma"]["included"] == 1
    assert (output / "SCREENING_IMPORT_MANIFEST.json").is_file()
    normalized = [
        json.loads(line)
        for line in (output / "screening_decisions.jsonl").read_text().splitlines()
    ]
    assert [row["stage"] for row in normalized] == ["title_abstract", "full_text"]


def test_screening_import_rejects_duplicate_final_decision_for_stage(tmp_path: Path):
    documents, manifest = _write_scientific_documents(tmp_path)
    decisions = tmp_path / "screening_decisions_input.jsonl"
    rows = [
        {
            "id": "ta-a-1",
            "document_id": "doi:10.1000/a",
            "stage": "title_abstract",
            "decision": "include",
            "decided_at": DECIDED_AT,
        },
        {
            "id": "ta-a-2",
            "document_id": "doi:10.1000/a",
            "stage": "title_abstract",
            "decision": "exclude",
            "reason": "wrong population",
            "decided_at": DECIDED_AT,
        },
    ]
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    with pytest.raises(ScreeningImportError, match="multiple final decisions"):
        run_screening_import(documents, manifest, decisions, tmp_path / "screening")


def test_cli_science_screening_runs_final_decision_import(tmp_path: Path, capsys):
    documents, manifest = _write_scientific_documents(tmp_path)
    decisions = tmp_path / "screening_decisions_input.jsonl"
    decisions.write_text(
        json.dumps(
            {
                "id": "ta-a",
                "document_id": "doi:10.1000/a",
                "stage": "title_abstract",
                "decision": "exclude",
                "reason": "wrong outcome",
                "decided_at": DECIDED_AT,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "screening"

    code = cli_main(
        [
            "science-screening",
            "--documents-jsonl",
            str(documents),
            "--science-manifest",
            str(manifest),
            "--decisions-jsonl",
            str(decisions),
            "--output-dir",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert '"mode": "FINAL_SCREENING_IMPORT"' in captured.out
    assert (output / "PRISMA_COUNTS.json").is_file()
