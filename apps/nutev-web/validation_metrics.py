from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

from validation_gold import _round_output_dir, gold_status
from validation_server import REPO_ROOT, _audit, _connect, _db_path, _now

FROZEN_CANDIDATE_SHA = "6aa7a5fe6009776e611ca3e1506486606b05f4f6"
PRIMARY_SYSTEMS = ("nutev_full", "lexical_baseline")
RANKINGS_DIR_ENV = "NUTEV_VALIDATION_RANKINGS_DIR"
DEFAULT_RANKINGS_RELATIVE = Path("validation") / "data" / "validation_coordinator_audit"
RANKINGS_NAME = "BENCHMARK_RANKINGS.csv"
RANKINGS_MANIFEST_NAME = "BENCHMARK_RANKINGS_MANIFEST.json"


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


def _rankings_dir(repo_root: Path) -> Path:
    configured = os.environ.get(RANKINGS_DIR_ENV, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (repo_root / DEFAULT_RANKINGS_RELATIVE).resolve()


def _load_tool(repo_root: Path, filename: str, module_name: str):
    path = repo_root / "tools" / filename
    if not path.is_file():
        raise FileNotFoundError(f"Ferramenta canônica ausente: tools/{filename}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar tools/{filename}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, path


def _validate_rankings_source(repo_root: Path) -> tuple[Path, Path, dict[str, Any]]:
    directory = _rankings_dir(repo_root)
    rankings_path = directory / RANKINGS_NAME
    manifest_path = directory / RANKINGS_MANIFEST_NAME
    if not rankings_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError(
            "Rankings label-blind de coordenação ainda não estão disponíveis para a etapa de métricas."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Manifesto dos rankings está ilegível.") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Manifesto dos rankings é inválido.")
    if manifest.get("label_blind_build") is not True:
        raise ValueError("Os rankings não estão declarados como label-blind.")
    if manifest.get("gold_standard_consumed") is not False:
        raise ValueError("O build dos rankings consumiu gold standard e não pode ser usado.")
    if str(manifest.get("candidate_runtime_sha") or "") != FROZEN_CANDIDATE_SHA:
        raise ValueError("Candidate SHA dos rankings diverge do runtime congelado.")
    if str(manifest.get("frozen_runtime_sha_required") or "") != FROZEN_CANDIDATE_SHA:
        raise ValueError("Freeze SHA do manifesto de rankings é inconsistente.")
    expected_ranking_sha = str(manifest.get("ranking_sha256") or "").strip()
    if not expected_ranking_sha or _sha256(rankings_path) != expected_ranking_sha:
        raise ValueError("SHA-256 de BENCHMARK_RANKINGS.csv não corresponde ao manifesto.")
    questions_path = repo_root / "validation" / "data" / "QUESTIONS.csv"
    expected_questions_sha = str(manifest.get("questions_sha256") or "").strip()
    if not expected_questions_sha or not questions_path.is_file() or _sha256(questions_path) != expected_questions_sha:
        raise ValueError("SHA-256 das perguntas não corresponde ao build dos rankings.")
    return rankings_path, manifest_path, manifest


def metrics_status(
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
    output_dir = _round_output_dir(root, round_id)
    summary_path = output_dir / "VALIDATION_COMPARISON.json"
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Resumo de comparação da validation está ilegível.") from exc
        return {
            "round_id": round_id,
            "round_status": round_status,
            "ready": True,
            "completed": round_status == "validation_metrics_complete",
            "source_ready": True,
            "validation_evidence_status": summary.get("validation_evidence_status"),
            "validation_continuation_pass": summary.get("validation_continuation_pass"),
            "questions": summary.get("questions"),
            "wins": summary.get("wins"),
            "losses": summary.get("losses"),
            "ties": summary.get("ties"),
            "median_delta_ndcg_at_20": summary.get("median_delta_ndcg_at_20"),
            "mean_delta_ndcg_at_20": summary.get("mean_delta_ndcg_at_20"),
            "median_delta_recall_at_100": summary.get("median_delta_recall_at_100"),
            "external_test_released": False,
        }

    source_ready = False
    source_error = None
    try:
        _validate_rankings_source(root)
        source_ready = True
    except (FileNotFoundError, ValueError) as exc:
        source_error = str(exc)
    return {
        "round_id": round_id,
        "round_status": round_status,
        "ready": round_status == "gold_validated" and source_ready,
        "completed": False,
        "source_ready": source_ready,
        "source_message": source_error,
        "external_test_released": False,
    }


def run_validation_metrics(
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
        status = str(round_row["status"])
        if status == "validation_metrics_complete":
            return metrics_status(repo_root=root, db_path=path)
        if status != "gold_validated":
            raise ValueError("As métricas só podem ser calculadas após gold_validated.")

    gold = gold_status(repo_root=root, db_path=path, round_id=round_id)
    if gold.get("validated") is not True or gold.get("validator_status") != "PASS":
        raise ValueError("O gold standard não possui PASS canônico válido.")

    rankings_path, rankings_manifest_path, rankings_manifest = _validate_rankings_source(root)
    output_dir = _round_output_dir(root, round_id)
    gold_path = output_dir / "GOLD_STANDARD.csv"
    results_path = output_dir / "VALIDATION_BENCHMARK_RESULTS.csv"
    comparison_path = output_dir / "VALIDATION_COMPARISON.json"
    paired_path = output_dir / "VALIDATION_PAIRED.csv"
    metrics_manifest_path = output_dir / "VALIDATION_METRICS_MANIFEST.json"

    evaluator, evaluator_path = _load_tool(
        root,
        "evaluate_scientific_validation.py",
        "nutev_evaluate_scientific_validation_runtime",
    )
    comparator, comparator_path = _load_tool(
        root,
        "compare_scientific_benchmark.py",
        "nutev_compare_scientific_benchmark_runtime",
    )

    try:
        gold_data = evaluator.load_gold(gold_path)
        ranking_data = evaluator.load_rankings(
            rankings_path,
            split="validation",
            systems=PRIMARY_SYSTEMS,
        )
        result_rows = evaluator.evaluate(
            gold_data,
            ranking_data,
            required_judged_depth=100,
        )
        evaluator.write_results(results_path, result_rows)
        question_results = comparator.load_question_results(
            results_path,
            split="validation",
        )
        summary, paired_rows = comparator.compare(
            question_results,
            split="validation",
            candidate="nutev_full",
            baseline="lexical_baseline",
        )
        comparison_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        comparator.write_paired(paired_path, paired_rows)
    except Exception as exc:
        raise ValueError(f"Avaliação científica da validation foi recusada: {exc}") from exc

    if summary.get("split") != "validation":
        raise ValueError("Comparação retornou split diferente de validation.")
    if summary.get("validation_evidence_status") not in {
        "CONTINUATION_CRITERIA_PASS",
        "CONTINUATION_CRITERIA_FAIL",
    }:
        raise ValueError("Comparação não produziu o gate de continuação esperado.")

    metrics_manifest = {
        "round_id": round_id,
        "calculated_at": _now(),
        "candidate_runtime_sha": FROZEN_CANDIDATE_SHA,
        "split_evaluated": "validation",
        "systems": list(PRIMARY_SYSTEMS),
        "required_judged_through": 100,
        "gold_validator_status": "PASS",
        "rankings_manifest_sha256": _sha256(rankings_manifest_path),
        "rankings_sha256": _sha256(rankings_path),
        "rankings_label_blind_build": rankings_manifest.get("label_blind_build"),
        "rankings_gold_standard_consumed": rankings_manifest.get("gold_standard_consumed"),
        "external_test_labels_consumed": False,
        "external_test_metrics_calculated": False,
        "external_test_released": False,
        "decision_locked": False,
        "canonical_tools": {
            "evaluator": str(evaluator_path.relative_to(root)),
            "comparator": str(comparator_path.relative_to(root)),
        },
        "outputs": {
            "VALIDATION_BENCHMARK_RESULTS.csv": _sha256(results_path),
            "VALIDATION_COMPARISON.json": _sha256(comparison_path),
            "VALIDATION_PAIRED.csv": _sha256(paired_path),
        },
        "comparison": summary,
    }
    metrics_manifest_path.write_text(
        json.dumps(metrics_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with _connect(path) as conn:
        timestamp = _now()
        conn.execute(
            "UPDATE validation_rounds SET status = 'validation_metrics_complete', updated_at = ? WHERE id = ?",
            (timestamp, round_id),
        )
        _audit(
            conn,
            round_id,
            "validation_metrics_complete",
            details={
                "validation_evidence_status": summary.get("validation_evidence_status"),
                "validation_continuation_pass": bool(summary.get("validation_continuation_pass")),
                "external_test_released": False,
            },
        )
        conn.commit()

    return metrics_status(repo_root=root, db_path=path)
