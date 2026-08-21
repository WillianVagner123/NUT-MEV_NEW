from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from validation_adjudication import adjudication_payload, finalize_adjudication, save_adjudication
from validation_server import prepare_round, round_status, save_decision, submit_reviewer


def _write_packet(path: Path, assessor_id: str) -> str:
    fields = [
        "question_id", "pool_item_id", "assessor_order", "reference_id", "title", "abstract",
        "journal", "year", "doi", "pmid", "pmcid", "url", "assessor_id", "relevance_grade",
        "reason", "decision_timestamp", "blind_to_nutev", "notes",
    ]
    rows = [
        {
            "question_id": "Q-V01", "pool_item_id": "pool-agreed", "assessor_order": "1",
            "reference_id": "ref-agreed", "title": "Synthetic agreed reference",
            "abstract": "Synthetic agreed abstract.", "journal": "Test Journal", "year": "2026",
            "doi": "", "pmid": "", "pmcid": "", "url": "https://example.invalid/agreed",
            "assessor_id": assessor_id, "relevance_grade": "", "reason": "",
            "decision_timestamp": "", "blind_to_nutev": "true", "notes": "",
        },
        {
            "question_id": "Q-V01", "pool_item_id": "pool-conflict", "assessor_order": "2",
            "reference_id": "ref-conflict", "title": "Synthetic conflict reference",
            "abstract": "Synthetic conflict abstract.", "journal": "Test Journal", "year": "2026",
            "doi": "", "pmid": "", "pmcid": "", "url": "https://example.invalid/conflict",
            "assessor_id": assessor_id, "relevance_grade": "", "reason": "",
            "decision_timestamp": "", "blind_to_nutev": "true", "notes": "",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    return sha256(path.read_bytes()).hexdigest()


def _root(tmp_path: Path) -> Path:
    questions_src = REPO_ROOT / "validation" / "data" / "QUESTIONS.csv"
    questions_dst = tmp_path / "validation" / "data" / "QUESTIONS.csv"
    questions_dst.parent.mkdir(parents=True, exist_ok=True)
    questions_dst.write_bytes(questions_src.read_bytes())
    packet_dir = questions_dst.parent / "validation_assessor_packets"
    a = packet_dir / "ASSESSOR_assessor_A.csv"
    b = packet_dir / "ASSESSOR_assessor_B.csv"
    manifest = {
        "label_blind": True,
        "independent_order_per_assessor": True,
        "minimum_assessors_required": 2,
        "pool_path": "VALIDATION_POOL_BLINDED.csv",
        "pool_sha256": "synthetic-test-only",
        "outputs": [
            {"assessor_id": "assessor_A", "path": a.name, "rows": 2, "sha256": _write_packet(a, "assessor_A")},
            {"assessor_id": "assessor_B", "path": b.name, "rows": 2, "sha256": _write_packet(b, "assessor_B")},
        ],
    }
    (packet_dir / "VALIDATION_ASSESSOR_PACKETS_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def _complete_initial_assessment(root: Path, db: Path) -> dict[str, str]:
    status = prepare_round(repo_root=root, db_path=db)
    tokens = {item["assessor_id"]: item["token"] for item in status["reviewers"]}
    decisions = {
        "assessor_A": {"pool-agreed": 2, "pool-conflict": 2},
        "assessor_B": {"pool-agreed": 2, "pool-conflict": 0},
    }
    for assessor_id, by_item in decisions.items():
        for pool_item_id, grade in by_item.items():
            save_decision(
                tokens[assessor_id],
                {
                    "pool_item_id": pool_item_id,
                    "relevance_grade": grade,
                    "reason": f"Human reason {assessor_id} {pool_item_id}",
                    "blind_to_nutev": True,
                    "review_later": False,
                    "notes": "",
                },
                repo_root=root,
                db_path=db,
            )
        submit_reviewer(tokens[assessor_id], repo_root=root, db_path=db)
    assert round_status(repo_root=root, db_path=db)["status"] == "ready_for_adjudication"
    return tokens


def test_adjudication_opens_only_after_all_initial_assessments_are_locked(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    prepare_round(repo_root=root, db_path=db)
    with pytest.raises(ValueError, match="ainda não está pronta"):
        adjudication_payload(repo_root=root, db_path=db)


def test_adjudication_queue_contains_only_conflicts_and_no_auto_grade(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    _complete_initial_assessment(root, db)

    payload = adjudication_payload(repo_root=root, db_path=db)
    assert payload["total_pairs"] == 2
    assert payload["agreed_pairs"] == 1
    assert payload["conflict_pairs"] == 1
    assert payload["resolved_conflicts"] == 0
    assert payload["unresolved_conflicts"] == 1
    assert len(payload["conflicts"]) == 1
    conflict = payload["conflicts"][0]
    assert conflict["reference_id"] == "ref-conflict"
    assert conflict["agreed"] is False
    assert conflict["agreed_grade"] is None
    assert conflict["adjudication"] is None
    assert {item["relevance_grade"] for item in conflict["judgments"]} == {0, 2}


def test_agreed_pair_cannot_be_adjudicated_and_finalize_fails_until_conflict_resolved(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    _complete_initial_assessment(root, db)

    with pytest.raises(ValueError, match="não é um conflito"):
        save_adjudication(
            {"question_id": "Q-V01", "reference_id": "ref-agreed", "relevance_grade": 1, "adjudicator_id": "adj_01"},
            repo_root=root,
            db_path=db,
        )
    with pytest.raises(ValueError, match="conflitos sem decisão humana"):
        finalize_adjudication(repo_root=root, db_path=db)


def test_human_decision_resolves_conflict_and_finalization_locks_adjudication(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    _complete_initial_assessment(root, db)

    payload = save_adjudication(
        {
            "question_id": "Q-V01",
            "reference_id": "ref-conflict",
            "relevance_grade": 1,
            "adjudicator_id": "human_adjudicator_01",
            "notes": "Explicit human resolution for synthetic test.",
        },
        repo_root=root,
        db_path=db,
    )
    assert payload["status"] == "adjudicating"
    assert payload["resolved_conflicts"] == 1
    assert payload["unresolved_conflicts"] == 0
    decision = payload["conflicts"][0]["adjudication"]
    assert int(decision["relevance_grade"]) == 1
    assert decision["adjudicator_id"] == "human_adjudicator_01"

    final = finalize_adjudication(repo_root=root, db_path=db)
    assert final["status"] == "adjudication_complete"
    with pytest.raises(ValueError, match="não aceita novas decisões"):
        save_adjudication(
            {"question_id": "Q-V01", "reference_id": "ref-conflict", "relevance_grade": 0, "adjudicator_id": "human_adjudicator_01"},
            repo_root=root,
            db_path=db,
        )
