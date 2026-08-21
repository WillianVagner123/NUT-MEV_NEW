from __future__ import annotations

import csv
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from validation_adjudication import _ensure_schema, _locked_assessments, _round_row
from validation_server import (
    REPO_ROOT,
    _audit,
    _connect,
    _db_path,
    _manifest_and_packets,
    _now,
    _questions,
)

ASSESSMENT_FIELDS = [
    "question_id",
    "reference_id",
    "assessor_id",
    "relevance_grade",
    "reason",
    "decision_timestamp",
    "blind_to_nutev",
    "doi",
    "pmid",
    "pmcid",
    "url",
    "title",
    "notes",
]
GOLD_FIELDS = [
    "question_id",
    "reference_id",
    "relevance_grade",
    "adjudication_status",
    "adjudicator_id",
    "adjudication_timestamp",
    "doi",
    "pmid",
    "pmcid",
    "url",
    "title",
    "notes",
]
POOL_FIELDS = ["question_id", "reference_id"]


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _round_output_dir(repo_root: Path, round_id: str) -> Path:
    return (
        repo_root
        / "project_output_reference"
        / "16_validation_server"
        / round_id
    ).resolve()


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_validator(repo_root: Path):
    validator_path = repo_root / "tools" / "validate_gold_standard.py"
    if not validator_path.is_file():
        raise FileNotFoundError("Validator canônico do gold standard não foi encontrado.")
    module_name = "nutev_validate_gold_standard_runtime"
    spec = importlib.util.spec_from_file_location(module_name, validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar o validator canônico do gold standard.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, validator_path


def _group_locked_rows(
    rows: list[dict[str, Any]],
    validation_question_ids: set[str],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    seen_decisions: set[tuple[str, str, str]] = set()
    for row in rows:
        question_id = str(row.get("question_id") or "").strip()
        reference_id = str(row.get("reference_id") or "").strip()
        assessor_id = str(row.get("assessor_id") or "").strip()
        if question_id not in validation_question_ids:
            raise ValueError(
                f"A rodada contém pergunta fora do split validation: {question_id or '(vazia)'}"
            )
        if not reference_id or not assessor_id:
            raise ValueError("A rodada contém identidade de julgamento incompleta.")
        decision_key = (question_id, reference_id, assessor_id)
        if decision_key in seen_decisions:
            raise ValueError(
                f"Julgamento duplicado para {question_id}/{reference_id}/{assessor_id}."
            )
        seen_decisions.add(decision_key)
        if row.get("relevance_grade") not in {0, 1, 2}:
            raise ValueError(f"Nota ausente ou inválida em {question_id}/{reference_id}/{assessor_id}.")
        if not str(row.get("reason") or "").strip():
            raise ValueError(f"Justificativa ausente em {question_id}/{reference_id}/{assessor_id}.")
        if not str(row.get("decision_timestamp") or "").strip():
            raise ValueError(f"Timestamp ausente em {question_id}/{reference_id}/{assessor_id}.")
        grouped.setdefault((question_id, reference_id), []).append(row)

    if not grouped:
        raise ValueError("A rodada não contém julgamentos humanos travados.")

    identity_fields = ("pool_item_id", "title", "doi", "pmid", "pmcid", "url")
    for (question_id, reference_id), judgments in grouped.items():
        assessor_ids = {str(item.get("assessor_id") or "").strip() for item in judgments}
        if len(assessor_ids) < 2:
            raise ValueError(
                f"O par {question_id}/{reference_id} não possui dois assessores independentes."
            )
        first = judgments[0]
        for item in judgments[1:]:
            for field in identity_fields:
                if str(item.get(field) or "").strip() != str(first.get(field) or "").strip():
                    raise ValueError(
                        f"Metadado {field} diverge entre assessores em {question_id}/{reference_id}."
                    )
    return grouped


def _build_rows(
    conn,
    round_id: str,
    grouped: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    adjudication_rows = conn.execute(
        """
        SELECT question_id, reference_id, relevance_grade, adjudicator_id,
               adjudication_timestamp, notes
        FROM validation_adjudications
        WHERE round_id = ?
        """,
        (round_id,),
    ).fetchall()
    adjudications = {
        (str(row["question_id"]), str(row["reference_id"])): dict(row)
        for row in adjudication_rows
    }

    assessments: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    pool: list[dict[str, str]] = []
    conflict_keys: set[tuple[str, str]] = set()

    for key in sorted(grouped):
        question_id, reference_id = key
        judgments = grouped[key]
        sample = judgments[0]
        grades = {int(item["relevance_grade"]) for item in judgments}
        pool.append({"question_id": question_id, "reference_id": reference_id})
        for item in sorted(judgments, key=lambda value: str(value.get("assessor_id") or "")):
            assessments.append(
                {
                    "question_id": question_id,
                    "reference_id": reference_id,
                    "assessor_id": str(item.get("assessor_id") or ""),
                    "relevance_grade": int(item["relevance_grade"]),
                    "reason": str(item.get("reason") or ""),
                    "decision_timestamp": str(item.get("decision_timestamp") or ""),
                    "blind_to_nutev": "true" if bool(item.get("blind_to_nutev", 1)) else "false",
                    "doi": str(item.get("doi") or ""),
                    "pmid": str(item.get("pmid") or ""),
                    "pmcid": str(item.get("pmcid") or ""),
                    "url": str(item.get("url") or ""),
                    "title": str(item.get("title") or ""),
                    "notes": str(item.get("notes") or ""),
                }
            )

        base = {
            "question_id": question_id,
            "reference_id": reference_id,
            "doi": str(sample.get("doi") or ""),
            "pmid": str(sample.get("pmid") or ""),
            "pmcid": str(sample.get("pmcid") or ""),
            "url": str(sample.get("url") or ""),
            "title": str(sample.get("title") or ""),
        }
        if len(grades) == 1:
            if key in adjudications:
                raise ValueError(
                    f"Há adjudicação registrada para um par com concordância: {question_id}/{reference_id}."
                )
            gold.append(
                {
                    **base,
                    "relevance_grade": next(iter(grades)),
                    "adjudication_status": "AGREED",
                    "adjudicator_id": "",
                    "adjudication_timestamp": "",
                    "notes": "",
                }
            )
            continue

        conflict_keys.add(key)
        decision = adjudications.get(key)
        if decision is None:
            raise ValueError(f"Conflito sem adjudicação humana: {question_id}/{reference_id}.")
        adjudicator_id = str(decision.get("adjudicator_id") or "").strip()
        timestamp = str(decision.get("adjudication_timestamp") or "").strip()
        grade = decision.get("relevance_grade")
        if grade not in {0, 1, 2} or not adjudicator_id or not timestamp:
            raise ValueError(f"Adjudicação incompleta: {question_id}/{reference_id}.")
        gold.append(
            {
                **base,
                "relevance_grade": int(grade),
                "adjudication_status": "RESOLVED",
                "adjudicator_id": adjudicator_id,
                "adjudication_timestamp": timestamp,
                "notes": str(decision.get("notes") or ""),
            }
        )

    extra_adjudications = set(adjudications) - conflict_keys
    if extra_adjudications:
        sample = sorted(extra_adjudications)[0]
        raise ValueError(
            f"Adjudicação órfã ou indevida detectada: {sample[0]}/{sample[1]}."
        )
    return assessments, gold, pool


def gold_status(
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
    round_id: str | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    if not path.is_file():
        raise FileNotFoundError("Nenhuma rodada preparada.")
    with _connect(path) as conn:
        round_row = _round_row(conn, round_id)
        rid = str(round_row["id"])
        status = str(round_row["status"])
    output_dir = _round_output_dir(root, rid)
    report_path = output_dir / "GOLD_STANDARD_VALIDATION.json"
    if not report_path.is_file():
        return {
            "round_id": rid,
            "round_status": status,
            "gold_ready": status == "adjudication_complete",
            "validated": False,
            "validator_status": None,
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Relatório de validação do gold está ilegível.") from exc
    return {
        "round_id": rid,
        "round_status": status,
        "gold_ready": True,
        "validated": report.get("status") == "PASS" and status == "gold_validated",
        "validator_status": report.get("status"),
        "final_labels": report.get("final_labels"),
        "unanimous_groups": report.get("unanimous_groups"),
        "conflict_groups": report.get("conflict_groups"),
        "raw_exact_agreement_fraction": report.get("raw_exact_agreement_fraction"),
        "minimum_assessors_per_reference": report.get("minimum_assessors_per_reference"),
        "pool_assessment_coverage_fraction": report.get("pool_assessment_coverage_fraction"),
        "pool_gold_coverage_fraction": report.get("pool_gold_coverage_fraction"),
    }


def build_and_validate_gold(
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
    round_id: str | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    if not path.is_file():
        raise FileNotFoundError("Nenhuma rodada preparada.")

    with _connect(path) as conn:
        _ensure_schema(conn)
        round_row = _round_row(conn, round_id)
        rid = str(round_row["id"])
        status = str(round_row["status"])
        if status == "gold_validated":
            return gold_status(repo_root=root, db_path=path, round_id=rid)
        if status != "adjudication_complete":
            raise ValueError("O gold standard só pode ser construído após a adjudicação completa.")

        validation_question_ids = set(_questions(root))
        grouped = _group_locked_rows(_locked_assessments(conn, rid), validation_question_ids)
        assessments, gold, pool = _build_rows(conn, rid, grouped)

        manifest, _ = _manifest_and_packets(root)
        declared_pool_rows = manifest.get("pool_rows")
        if declared_pool_rows not in {None, ""}:
            try:
                declared_pool_rows_int = int(declared_pool_rows)
            except (TypeError, ValueError) as exc:
                raise ValueError("pool_rows inválido no manifesto dos assessores.") from exc
            if declared_pool_rows_int != len(pool):
                raise ValueError(
                    f"O manifesto declara {declared_pool_rows_int} pares, mas a rodada contém {len(pool)}."
                )

        output_dir = _round_output_dir(root, rid)
        assessments_path = output_dir / "ASSESSMENTS.csv"
        gold_path = output_dir / "GOLD_STANDARD.csv"
        pool_path = output_dir / "BLINDED_POOL_KEYS.csv"
        report_path = output_dir / "GOLD_STANDARD_VALIDATION.json"
        manifest_path = output_dir / "GOLD_BUILD_MANIFEST.json"

        _write_csv(assessments_path, ASSESSMENT_FIELDS, assessments)
        _write_csv(gold_path, GOLD_FIELDS, gold)
        _write_csv(pool_path, POOL_FIELDS, pool)

        validator, validator_path = _load_validator(root)
        try:
            validation_report = validator.validate(
                validator.load_assessments(assessments_path),
                validator.load_gold(gold_path),
                validator.load_pool(pool_path),
            )
        except Exception as exc:
            raise ValueError(f"Validator canônico recusou o gold standard: {exc}") from exc
        if validation_report.get("status") != "PASS":
            raise ValueError("O validator canônico não retornou PASS.")

        report_path.write_text(
            json.dumps(validation_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        build_manifest = {
            "round_id": rid,
            "built_at": _now(),
            "source": "server_locked_human_assessments_and_human_adjudications",
            "pool_key_provenance": (
                "question_id/reference_id keys reconstructed from the verified blinded assessor packets "
                "stored in the validation round; this does not claim re-verification of the original pool file hash"
            ),
            "declared_source_pool_sha256": str(manifest.get("pool_sha256") or ""),
            "declared_source_pool_rows": manifest.get("pool_rows"),
            "external_test_consumed": False,
            "synthetic_labels_created": False,
            "metrics_calculated": False,
            "validator_path": str(validator_path.relative_to(root)),
            "outputs": {
                "ASSESSMENTS.csv": _sha256(assessments_path),
                "GOLD_STANDARD.csv": _sha256(gold_path),
                "BLINDED_POOL_KEYS.csv": _sha256(pool_path),
                "GOLD_STANDARD_VALIDATION.json": _sha256(report_path),
            },
            "validator_result": validation_report,
        }
        manifest_path.write_text(
            json.dumps(build_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        timestamp = _now()
        conn.execute(
            "UPDATE validation_rounds SET status = 'gold_validated', updated_at = ? WHERE id = ?",
            (timestamp, rid),
        )
        _audit(
            conn,
            rid,
            "gold_standard_validated",
            details={
                "validator_status": "PASS",
                "final_labels": int(validation_report.get("final_labels") or 0),
                "external_test_consumed": False,
                "metrics_calculated": False,
            },
        )
        conn.commit()

    return gold_status(repo_root=root, db_path=path, round_id=rid)
