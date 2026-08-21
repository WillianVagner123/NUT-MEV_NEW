from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from validation_gold import _round_output_dir
from validation_metrics import FROZEN_CANDIDATE_SHA
from validation_server import REPO_ROOT, _audit, _connect, _db_path, _now

PASS_STATUS = "CONTINUATION_CRITERIA_PASS"
FAIL_STATUS = "CONTINUATION_CRITERIA_FAIL"
CONTINUE_DECISION = "CONTINUE_TO_EXTERNAL"
STOP_DECISION = "STOP_AT_B"
DECISION_STATUSES = {
    "validation_decision_continue": CONTINUE_DECISION,
    "validation_decision_stop": STOP_DECISION,
}


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _latest_round(conn):
    row = conn.execute(
        "SELECT id, status FROM validation_rounds ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        raise FileNotFoundError("Nenhuma rodada preparada.")
    return row


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} não foi encontrado.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} está ilegível.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} é inválido.")
    return value


def _source_files(repo_root: Path, round_id: str) -> dict[str, Path]:
    output_dir = _round_output_dir(repo_root, round_id)
    return {
        "gold_validation": output_dir / "GOLD_STANDARD_VALIDATION.json",
        "gold_manifest": output_dir / "GOLD_BUILD_MANIFEST.json",
        "results": output_dir / "VALIDATION_BENCHMARK_RESULTS.csv",
        "comparison": output_dir / "VALIDATION_COMPARISON.json",
        "paired": output_dir / "VALIDATION_PAIRED.csv",
        "metrics_manifest": output_dir / "VALIDATION_METRICS_MANIFEST.json",
        "decision": output_dir / "VALIDATION_DECISION.json",
    }


def _validate_metrics_evidence(repo_root: Path, round_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    files = _source_files(repo_root, round_id)
    comparison = _load_json(files["comparison"], "VALIDATION_COMPARISON.json")
    metrics_manifest = _load_json(files["metrics_manifest"], "VALIDATION_METRICS_MANIFEST.json")
    gold_validation = _load_json(files["gold_validation"], "GOLD_STANDARD_VALIDATION.json")
    gold_manifest = _load_json(files["gold_manifest"], "GOLD_BUILD_MANIFEST.json")

    if gold_validation.get("status") != "PASS":
        raise ValueError("O gold standard não possui PASS canônico no momento do lock.")
    if str(metrics_manifest.get("candidate_runtime_sha") or "") != FROZEN_CANDIDATE_SHA:
        raise ValueError("Candidate SHA do manifesto de métricas diverge do runtime congelado.")
    if metrics_manifest.get("split_evaluated") != "validation":
        raise ValueError("O manifesto de métricas não está restrito ao split validation.")
    if metrics_manifest.get("systems") != ["nutev_full", "lexical_baseline"]:
        raise ValueError("O manifesto de métricas não usa o par primário pré-especificado.")
    if int(metrics_manifest.get("required_judged_through") or 0) != 100:
        raise ValueError("O manifesto de métricas não exige cobertura julgada até 100.")
    for field in (
        "external_test_labels_consumed",
        "external_test_metrics_calculated",
        "external_test_released",
    ):
        if metrics_manifest.get(field) is not False:
            raise ValueError(f"O lock foi bloqueado porque {field} não é false.")
    if gold_manifest.get("external_test_consumed") is not False:
        raise ValueError("O gold consumiu external_test e não pode sustentar este lock.")

    manifest_outputs = metrics_manifest.get("outputs")
    if not isinstance(manifest_outputs, dict):
        raise ValueError("Manifesto de métricas não contém hashes de outputs.")
    expected_outputs = {
        "VALIDATION_BENCHMARK_RESULTS.csv": files["results"],
        "VALIDATION_COMPARISON.json": files["comparison"],
        "VALIDATION_PAIRED.csv": files["paired"],
    }
    hashes: dict[str, str] = {}
    for name, path in expected_outputs.items():
        if not path.is_file():
            raise FileNotFoundError(f"{name} não foi encontrado.")
        actual = _sha256(path)
        expected = str(manifest_outputs.get(name) or "")
        if not expected or actual != expected:
            raise ValueError(f"SHA-256 de {name} diverge do manifesto de métricas.")
        hashes[name] = actual

    manifest_comparison = metrics_manifest.get("comparison")
    if not isinstance(manifest_comparison, dict) or manifest_comparison != comparison:
        raise ValueError("Resumo de comparação diverge do manifesto de métricas.")
    if comparison.get("split") != "validation":
        raise ValueError("Resumo de comparação não pertence ao split validation.")
    if comparison.get("candidate") != "nutev_full" or comparison.get("baseline") != "lexical_baseline":
        raise ValueError("Resumo de comparação diverge do par primário pré-especificado.")

    evidence_status = str(comparison.get("validation_evidence_status") or "")
    continuation = comparison.get("validation_continuation_pass")
    if evidence_status == PASS_STATUS and continuation is True:
        pass
    elif evidence_status == FAIL_STATUS and continuation is False:
        pass
    else:
        raise ValueError("Gate de validation inconsistente: status e flag de continuação divergem.")

    hashes["GOLD_STANDARD_VALIDATION.json"] = _sha256(files["gold_validation"])
    hashes["GOLD_BUILD_MANIFEST.json"] = _sha256(files["gold_manifest"])
    hashes["VALIDATION_METRICS_MANIFEST.json"] = _sha256(files["metrics_manifest"])
    return comparison, metrics_manifest, hashes


def decision_status(
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    if not path.is_file():
        raise FileNotFoundError("Nenhuma rodada preparada.")
    with _connect(path) as conn:
        round_row = _latest_round(conn)
        round_id = str(round_row["id"])
        round_status = str(round_row["status"])
    decision_path = _source_files(root, round_id)["decision"]
    if decision_path.is_file():
        decision = _load_json(decision_path, "VALIDATION_DECISION.json")
        return {
            "round_id": round_id,
            "round_status": round_status,
            "locked": True,
            "decision": decision.get("decision"),
            "validation_evidence_status": decision.get("validation_evidence_status"),
            "validation_continuation_pass": decision.get("validation_continuation_pass"),
            "locked_at": decision.get("locked_at"),
            "external_test_released": decision.get("external_test_released"),
        }
    return {
        "round_id": round_id,
        "round_status": round_status,
        "locked": False,
        "decision": None,
        "ready": round_status == "validation_metrics_complete",
        "external_test_released": False,
    }


def lock_validation_decision(
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    if not path.is_file():
        raise FileNotFoundError("Nenhuma rodada preparada.")

    with _connect(path) as conn:
        round_row = _latest_round(conn)
        round_id = str(round_row["id"])
        round_status = str(round_row["status"])
        if round_status in DECISION_STATUSES:
            return decision_status(repo_root=root, db_path=path)
        if round_status != "validation_metrics_complete":
            raise ValueError("A decisão só pode ser bloqueada após validation_metrics_complete.")

    comparison, metrics_manifest, hashes = _validate_metrics_evidence(root, round_id)
    continuation = comparison.get("validation_continuation_pass") is True
    evidence_status = str(comparison.get("validation_evidence_status") or "")
    decision = CONTINUE_DECISION if continuation else STOP_DECISION
    next_status = "validation_decision_continue" if continuation else "validation_decision_stop"
    locked_at = _now()

    files = _source_files(root, round_id)
    payload = {
        "round_id": round_id,
        "locked_at": locked_at,
        "decision": decision,
        "validation_evidence_status": evidence_status,
        "validation_continuation_pass": continuation,
        "candidate_runtime_sha": FROZEN_CANDIDATE_SHA,
        "primary_candidate": "nutev_full",
        "primary_baseline": "lexical_baseline",
        "primary_endpoint": comparison.get("primary_endpoint"),
        "recall_guard_endpoint": comparison.get("recall_guard_endpoint"),
        "questions": comparison.get("questions"),
        "wins": comparison.get("wins"),
        "losses": comparison.get("losses"),
        "ties": comparison.get("ties"),
        "median_delta_ndcg_at_20": comparison.get("median_delta_ndcg_at_20"),
        "median_delta_recall_at_100": comparison.get("median_delta_recall_at_100"),
        "source_hashes": hashes,
        "rankings_sha256": metrics_manifest.get("rankings_sha256"),
        "external_test_released": False,
        "external_test_labels_consumed": False,
        "external_test_metrics_calculated": False,
        "automatic_external_release": False,
        "scientific_boundary": (
            "This lock records the preregistered validation-stage continuation decision. "
            "It does not release external-test evidence and does not by itself establish discovery recall or clinical validity."
        ),
    }
    files["decision"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with _connect(path) as conn:
        conn.execute(
            "UPDATE validation_rounds SET status = ?, updated_at = ? WHERE id = ?",
            (next_status, locked_at, round_id),
        )
        _audit(
            conn,
            round_id,
            "validation_decision_locked",
            details={
                "decision": decision,
                "validation_evidence_status": evidence_status,
                "external_test_released": False,
            },
        )
        conn.commit()

    return decision_status(repo_root=root, db_path=path)
