from __future__ import annotations

import csv
from hashlib import sha256
import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "apps" / "nutev-web" / "validation_readiness.py"
SPEC = importlib.util.spec_from_file_location("nutev_validation_readiness", MODULE_PATH)
assert SPEC and SPEC.loader
validation_readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation_readiness)


def _write_packet(path: Path, assessor_id: str, *, prohibited: bool = False) -> str:
    fields = [
        "question_id", "pool_item_id", "assessor_order", "reference_id", "title", "abstract",
        "journal", "year", "doi", "pmid", "pmcid", "url", "assessor_id", "relevance_grade",
        "reason", "decision_timestamp", "blind_to_nutev", "notes",
    ]
    if prohibited:
        fields.append("reference_score")
    row = {
        "question_id": "Q-V01",
        "pool_item_id": f"pool-{assessor_id}",
        "assessor_order": "1",
        "reference_id": f"ref-{assessor_id}",
        "title": "Synthetic assessor-safe validation reference",
        "abstract": "Synthetic test content only.",
        "journal": "Test Journal",
        "year": "2026",
        "doi": "",
        "pmid": "",
        "pmcid": "",
        "url": "https://example.invalid/test",
        "assessor_id": assessor_id,
        "relevance_grade": "",
        "reason": "",
        "decision_timestamp": "",
        "blind_to_nutev": "true",
        "notes": "",
    }
    if prohibited:
        row["reference_score"] = "99"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    return sha256(path.read_bytes()).hexdigest()


def _prepare_root(tmp_path: Path, *, prohibited: bool = False) -> Path:
    questions_src = REPO_ROOT / "validation" / "data" / "QUESTIONS.csv"
    questions_dst = tmp_path / "validation" / "data" / "QUESTIONS.csv"
    questions_dst.parent.mkdir(parents=True, exist_ok=True)
    questions_dst.write_bytes(questions_src.read_bytes())

    packet_dir = questions_dst.parent / "validation_assessor_packets"
    a = packet_dir / "ASSESSOR_assessor_A.csv"
    b = packet_dir / "ASSESSOR_assessor_B.csv"
    sha_a = _write_packet(a, "assessor_A", prohibited=prohibited)
    sha_b = _write_packet(b, "assessor_B")
    manifest = {
        "label_blind": True,
        "independent_order_per_assessor": True,
        "minimum_assessors_required": 2,
        "outputs": [
            {"assessor_id": "assessor_A", "path": a.name, "rows": 1, "sha256": sha_a},
            {"assessor_id": "assessor_B", "path": b.name, "rows": 1, "sha256": sha_b},
        ],
    }
    (packet_dir / "VALIDATION_ASSESSOR_PACKETS_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return tmp_path


def test_readiness_waits_for_private_packets_when_freeze_is_valid(tmp_path: Path) -> None:
    questions_src = REPO_ROOT / "validation" / "data" / "QUESTIONS.csv"
    questions_dst = tmp_path / "validation" / "data" / "QUESTIONS.csv"
    questions_dst.parent.mkdir(parents=True, exist_ok=True)
    questions_dst.write_bytes(questions_src.read_bytes())

    result = validation_readiness.get_validation_readiness(tmp_path)
    assert result["status"] == "waiting_for_private_packets"
    assert result["questions_frozen"] is True
    assert result["ready"] is False


def test_readiness_accepts_two_blind_assessor_safe_packets(tmp_path: Path) -> None:
    root = _prepare_root(tmp_path)
    result = validation_readiness.get_validation_readiness(root)
    assert result["status"] == "ready"
    assert result["ready"] is True
    assert result["private_packets_valid"] is True
    assert result["assessor_count"] == 2
    assert result["packet_rows"] == 2


def test_readiness_rejects_prohibited_blinding_fields(tmp_path: Path) -> None:
    root = _prepare_root(tmp_path, prohibited=True)
    result = validation_readiness.get_validation_readiness(root)
    assert result["status"] == "invalid"
    assert result["ready"] is False
    assert "prohibited" in result["message"]
