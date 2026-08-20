from __future__ import annotations

import csv
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_QUESTIONS_SHA256 = "55a0f654e49cb5a9b10249c373df168cac585167a245b828d667c7724fb64589"
MANIFEST_NAME = "VALIDATION_ASSESSOR_PACKETS_MANIFEST.json"
PACKET_DIR_ENV = "NUTEV_VALIDATION_PACKET_DIR"
REQUIRED_PACKET_COLUMNS = {
    "question_id",
    "pool_item_id",
    "assessor_order",
    "reference_id",
    "title",
    "abstract",
    "journal",
    "year",
    "doi",
    "pmid",
    "pmcid",
    "url",
    "assessor_id",
    "relevance_grade",
    "reason",
    "decision_timestamp",
    "blind_to_nutev",
    "notes",
}
PROHIBITED_PACKET_COLUMNS = {
    "reference_score",
    "reference_rank",
    "score_breakdown",
    "system",
    "system_membership",
    "system_score",
    "systems_count",
    "taxonomy",
    "taxonomy_primary",
    "taxonomy_secondary",
    "taxonomy_groups",
    "taxonomy_group_scores",
    "system_origin",
    "nutev_score",
    "nutev_rank",
    "score",
    "rank",
}


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _packet_dir(repo_root: Path) -> Path:
    configured = os.environ.get(PACKET_DIR_ENV, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return repo_root / "validation" / "data" / "validation_assessor_packets"


def _validation_question_ids(questions_path: Path) -> set[str]:
    with questions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            str(row.get("question_id") or "").strip()
            for row in reader
            if str(row.get("split") or "").strip() == "validation"
        }


def _validate_packet(path: Path, expected_sha: str, validation_questions: set[str]) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("private assessor packet is missing")
    actual_sha = _sha256(path)
    if actual_sha != expected_sha:
        raise ValueError("private assessor packet SHA-256 mismatch")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_PACKET_COLUMNS - fields)
        if missing:
            raise ValueError("private assessor packet is missing required fields")
        leaked = sorted(fields & PROHIBITED_PACKET_COLUMNS)
        if leaked:
            raise ValueError("private assessor packet contains prohibited blinded fields")

        rows = 0
        assessor_ids: set[str] = set()
        seen_questions: set[str] = set()
        for row in reader:
            rows += 1
            assessor_ids.add(str(row.get("assessor_id") or "").strip())
            question_id = str(row.get("question_id") or "").strip()
            seen_questions.add(question_id)
            if question_id not in validation_questions:
                raise ValueError("private assessor packet contains a non-validation question")
            if str(row.get("blind_to_nutev") or "").strip().lower() != "true":
                raise ValueError("private assessor packet is not marked blind")
            if str(row.get("relevance_grade") or "").strip():
                raise ValueError("private assessor packet contains a pre-existing grade")
            if str(row.get("reason") or "").strip():
                raise ValueError("private assessor packet contains a pre-existing reason")
            if str(row.get("decision_timestamp") or "").strip():
                raise ValueError("private assessor packet contains a pre-existing timestamp")

    assessor_ids.discard("")
    if rows <= 0:
        raise ValueError("private assessor packet is empty")
    if len(assessor_ids) != 1:
        raise ValueError("private assessor packet must contain exactly one assessor")
    if not seen_questions:
        raise ValueError("private assessor packet has no validation questions")

    return {"rows": rows, "assessor_id": next(iter(assessor_ids))}


def get_validation_readiness(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    questions_path = root / "validation" / "data" / "QUESTIONS.csv"
    packet_dir = _packet_dir(root)
    manifest_path = packet_dir / MANIFEST_NAME

    result: dict[str, Any] = {
        "status": "waiting_for_private_packets",
        "ready": False,
        "questions_frozen": False,
        "private_packets_present": False,
        "private_packets_valid": False,
        "assessor_count": 0,
        "packet_rows": 0,
        "message": "Aguardando os pacotes privados da rodada de validation.",
    }

    if not questions_path.is_file():
        result.update(status="invalid", message="QUESTIONS.csv congelado não foi encontrado.")
        return result
    if _sha256(questions_path) != EXPECTED_QUESTIONS_SHA256:
        result.update(status="invalid", message="O SHA-256 de QUESTIONS.csv não corresponde ao freeze científico atual.")
        return result
    result["questions_frozen"] = True

    if not manifest_path.is_file():
        return result
    result["private_packets_present"] = True

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("assessor manifest is invalid")
        if manifest.get("label_blind") is not True:
            raise ValueError("assessor manifest is not label blind")
        if manifest.get("independent_order_per_assessor") is not True:
            raise ValueError("assessor manifest does not guarantee independent ordering")
        outputs = manifest.get("outputs")
        if not isinstance(outputs, list) or len(outputs) < 2:
            raise ValueError("assessor manifest requires at least two assessor packets")

        validation_questions = _validation_question_ids(questions_path)
        assessor_ids: set[str] = set()
        total_rows = 0
        for output in outputs:
            if not isinstance(output, dict):
                raise ValueError("assessor manifest output is invalid")
            rel_path = str(output.get("path") or "").strip()
            expected_sha = str(output.get("sha256") or "").strip()
            if not rel_path or not expected_sha:
                raise ValueError("assessor manifest output identity is incomplete")
            safe_name = Path(rel_path).name
            packet = _validate_packet(packet_dir / safe_name, expected_sha, validation_questions)
            assessor_ids.add(str(packet["assessor_id"]))
            total_rows += int(packet["rows"])

        if len(assessor_ids) < 2:
            raise ValueError("assessor packets do not represent two independent assessors")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result.update(status="invalid", message=f"Pacotes privados inválidos: {exc}")
        return result

    result.update(
        status="ready",
        ready=True,
        private_packets_valid=True,
        assessor_count=len(assessor_ids),
        packet_rows=total_rows,
        message="Rodada de validation pronta para preparação no site.",
    )
    return result
