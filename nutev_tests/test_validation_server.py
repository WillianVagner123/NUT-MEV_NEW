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

from validation_server import prepare_round, reviewer_payload, round_status, save_decision, submit_reviewer


def _write_packet(path: Path, assessor_id: str) -> str:
    fields = [
        "question_id", "pool_item_id", "assessor_order", "reference_id", "title", "abstract",
        "journal", "year", "doi", "pmid", "pmcid", "url", "assessor_id", "relevance_grade",
        "reason", "decision_timestamp", "blind_to_nutev", "notes",
    ]
    row = {
        "question_id": "Q-V01", "pool_item_id": "pool-common-1", "assessor_order": "1",
        "reference_id": "ref-common-1", "title": "Synthetic common-pool validation reference",
        "abstract": "Synthetic test abstract.", "journal": "Test Journal", "year": "2026",
        "doi": "", "pmid": "", "pmcid": "", "url": "https://example.invalid/ref",
        "assessor_id": assessor_id, "relevance_grade": "", "reason": "",
        "decision_timestamp": "", "blind_to_nutev": "true", "notes": "",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerow(row)
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
        "outputs": [
            {"assessor_id": "assessor_A", "path": a.name, "rows": 1, "sha256": _write_packet(a, "assessor_A")},
            {"assessor_id": "assessor_B", "path": b.name, "rows": 1, "sha256": _write_packet(b, "assessor_B")},
        ],
    }
    (packet_dir / "VALIDATION_ASSESSOR_PACKETS_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_private_tokens_isolate_assessor_decisions_and_coordinator_sees_only_progress(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    status = prepare_round(repo_root=root, db_path=db)
    assert status["status"] == "assessment"
    assert len(status["reviewers"]) == 2
    assert "relevance_grade" not in json.dumps(status)
    assert "reason" not in json.dumps(status)

    tokens = {item["assessor_id"]: item["token"] for item in status["reviewers"]}
    a = reviewer_payload(tokens["assessor_A"], repo_root=root, db_path=db)
    b = reviewer_payload(tokens["assessor_B"], repo_root=root, db_path=db)
    assert a["assessor_id"] == "assessor_A"
    assert b["assessor_id"] == "assessor_B"
    assert a["assignments"][0]["relevance_grade"] is None
    assert b["assignments"][0]["relevance_grade"] is None

    a = save_decision(
        tokens["assessor_A"],
        {"pool_item_id": "pool-common-1", "relevance_grade": 2, "reason": "Directly relevant", "blind_to_nutev": True, "review_later": False, "notes": ""},
        repo_root=root, db_path=db,
    )
    assert a["assignments"][0]["relevance_grade"] == 2
    b = reviewer_payload(tokens["assessor_B"], repo_root=root, db_path=db)
    assert b["assignments"][0]["relevance_grade"] is None

    status = round_status(repo_root=root, db_path=db)
    a_status = next(item for item in status["reviewers"] if item["assessor_id"] == "assessor_A")
    assert a_status["completed_items"] == 1
    assert "relevance_grade" not in a_status
    assert "reason" not in a_status


def test_submit_locks_each_assessor_and_round_advances_only_after_both(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    status = prepare_round(repo_root=root, db_path=db)
    tokens = {item["assessor_id"]: item["token"] for item in status["reviewers"]}

    for assessor_id, grade in (("assessor_A", 2), ("assessor_B", 1)):
        save_decision(
            tokens[assessor_id],
            {"pool_item_id": "pool-common-1", "relevance_grade": grade, "reason": f"Reason {assessor_id}", "blind_to_nutev": True, "review_later": False, "notes": ""},
            repo_root=root, db_path=db,
        )
        submitted = submit_reviewer(tokens[assessor_id], repo_root=root, db_path=db)
        assert submitted["locked"] is True
        with pytest.raises(ValueError, match="travada"):
            save_decision(
                tokens[assessor_id],
                {"pool_item_id": "pool-common-1", "relevance_grade": 0, "reason": "Attempted change", "blind_to_nutev": True},
                repo_root=root, db_path=db,
            )
        interim = round_status(repo_root=root, db_path=db)
        if assessor_id == "assessor_A":
            assert interim["status"] == "assessment"

    final = round_status(repo_root=root, db_path=db)
    assert final["status"] == "ready_for_adjudication"
    assert all(item["submitted"] for item in final["reviewers"])


def test_submit_fails_closed_if_blindness_is_declared_broken(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    status = prepare_round(repo_root=root, db_path=db)
    token = next(item["token"] for item in status["reviewers"] if item["assessor_id"] == "assessor_A")
    save_decision(
        token,
        {"pool_item_id": "pool-common-1", "relevance_grade": 2, "reason": "Relevant but exposed", "blind_to_nutev": False},
        repo_root=root, db_path=db,
    )
    with pytest.raises(ValueError, match="cegueira"):
        submit_reviewer(token, repo_root=root, db_path=db)


def test_invalid_private_token_is_rejected(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = tmp_path / "private" / "validation.sqlite3"
    prepare_round(repo_root=root, db_path=db)
    with pytest.raises(PermissionError):
        reviewer_payload("x" * 40, repo_root=root, db_path=db)
