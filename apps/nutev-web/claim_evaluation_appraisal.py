from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Mapping

from evidence_claim_review import (
    ACCEPTED,
    CANONICAL_CLAIM_RECORD_TYPE,
    _claim_path,
    _claim_root,
    _evidence_record_index,
    _load_candidate,
    _validate_candidate_current,
)
from governed_synthesis_release import DEFAULT_OUTPUT_ROOT, _atomic_json, _digest, _read_json
from synthesis_governance import SynthesisGovernanceError

EVALUATION_CANDIDATE_TYPE = "NUTEV_CLAIM_EVALUATION_CANDIDATE_V1"
EVALUATION_STATE_TYPE = "NUTEV_CLAIM_EVALUATION_STATE_V1"
CANONICAL_EVALUATION_RECORD_TYPE = "NUTEV_CANONICAL_CLAIM_EVALUATION_RECORD_V1"
APPRAISAL_METHOD = "NUTEV_GENERIC_CLAIM_APPRAISAL_V1"
EVALUATION_STAGE_OPERATION = "STAGE_CLAIM_EVALUATION"
EVALUATION_FINALIZE_OPERATION = "FINALIZE_CLAIM_EVALUATION"
PENDING_APPRAISAL = "PENDING_APPRAISAL"
FINALIZED = "FINALIZED"
STATUS_LIMIT = 200

DIMENSIONS: dict[str, str] = {
    "design_appropriateness": (
        "Adequacy of the reported study design for supporting this specific source-level claim."
    ),
    "internal_validity_appraisal": (
        "Human appraisal of internal-validity concerns relevant to this claim; not a formal risk-of-bias instrument."
    ),
    "directness": (
        "Directness of population, intervention/exposure, comparator and outcome to the claim as written."
    ),
    "precision": (
        "Human appraisal of how precisely the reported result supports the claim, considering available estimates and uncertainty."
    ),
    "applicability": (
        "Applicability of the reported evidence to the intended scientific context represented by the claim."
    ),
    "reporting_completeness": (
        "Completeness of the available reporting needed to appraise the claim without inventing missing information."
    ),
}

JUDGMENTS = {
    "FAVORABLE",
    "SOME_CONCERNS",
    "MAJOR_CONCERNS",
    "UNCLEAR",
    "NOT_APPLICABLE",
}

ASSESSMENT_BASES = {
    "FULL_TEXT",
    "ABSTRACT_ONLY",
    "SOURCE_SNAPSHOT_ONLY",
    "MIXED",
    "OTHER",
    "UNCLEAR",
}

_EVALUATION_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evaluation_root(output_root: Path) -> Path:
    return output_root / "scientific" / "claim_evaluations"


def _candidate_path(root: Path, candidate_id: str) -> Path:
    return root / "candidates" / f"{candidate_id}.json"


def _state_path(root: Path, candidate_id: str) -> Path:
    return root / "states" / f"{candidate_id}.json"


def _evaluation_path(root: Path, evaluation_id: str) -> Path:
    return root / "finalized" / f"{evaluation_id}.json"


def _claim_scientific_content(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in record
        if key not in {"content_sha256", "accepted_at", "artifact_semantics"}
    }


def _evaluation_candidate_scientific_content(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: candidate[key]
        for key in candidate
        if key not in {"content_sha256", "generated_at", "artifact_semantics"}
    }


def _load_accepted_claim(
    claim_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    claim_id = str(claim_id or "").strip()
    if not claim_id:
        raise SynthesisGovernanceError("EvidenceClaim id obrigatório")

    claim_root = _claim_root(output_root)
    record = _read_json(_claim_path(claim_root, claim_id), "canonical EvidenceClaim")
    if record.get("claim_record_type") != CANONICAL_CLAIM_RECORD_TYPE:
        raise SynthesisGovernanceError("EvidenceClaim record type inválido")
    if record.get("canonical") is not True:
        raise SynthesisGovernanceError("ClaimEvaluation exige EvidenceClaim canônico")
    if record.get("source_evidence_record_verified") is not True:
        raise SynthesisGovernanceError("EvidenceClaim sem EvidenceRecord verificado")

    expected_sha = _digest(_claim_scientific_content(record))
    if str(record.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("EvidenceClaim content SHA-256 inválido")

    claim = record.get("evidence_claim")
    if not isinstance(claim, Mapping) or str(claim.get("id") or "") != claim_id:
        raise SynthesisGovernanceError("EvidenceClaim payload inválido")
    if not str(claim.get("statement") or "").strip():
        raise SynthesisGovernanceError("EvidenceClaim sem statement")
    metadata = claim.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SynthesisGovernanceError("EvidenceClaim sem provenance metadata")
    if metadata.get("claim_semantics") != "SOURCE_REPORTED_PROPOSITION":
        raise SynthesisGovernanceError("ClaimEvaluation aceita apenas source-reported propositions")
    if metadata.get("human_entered") is not True:
        raise SynthesisGovernanceError("EvidenceClaim não está marcado como human-entered")
    if metadata.get("identity_cryptographically_authenticated") is not False:
        raise SynthesisGovernanceError("EvidenceClaim faz claim de identidade não suportado")

    guardrails = record.get("guardrails")
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("EvidenceClaim sem guardrails")
    if guardrails.get("accepted_evidence_claim_created") is not True:
        raise SynthesisGovernanceError("EvidenceClaim não registra aceitação explícita")
    for key in (
        "screening_eligibility_verified",
        "claim_evaluation_created",
        "risk_of_bias_assessed",
        "certainty_assessed",
        "evidence_set_created",
        "canonical_scientific_synthesis_created",
        "clinical_recommendation_created",
        "meta_analysis_performed",
        "prisma_event_emitted",
        "pairwise_synthesis_statement_promoted",
        "identity_cryptographically_authenticated",
    ):
        if guardrails.get(key) is not False:
            raise SynthesisGovernanceError(f"EvidenceClaim guardrail inválido: {key}")

    evidence_record_id = str(claim.get("evidence_record_id") or "").strip()
    evidence_records = _evidence_record_index(output_root)
    evidence_record = evidence_records.get(evidence_record_id)
    source_document_id = str(metadata.get("source_document_id") or "").strip()
    if (
        not evidence_record
        or str(evidence_record.get("id") or "") != evidence_record_id
        or str(evidence_record.get("document_id") or "") != source_document_id
    ):
        raise SynthesisGovernanceError(
            "EvidenceRecord correspondente ao EvidenceClaim não foi localizado ou divergiu"
        )

    accepted_from_candidate_id = str(record.get("accepted_from_candidate_id") or "").strip()
    candidate, state = _load_candidate(accepted_from_candidate_id, output_root=output_root)
    if state.get("status") != ACCEPTED:
        raise SynthesisGovernanceError("Source claim candidate não está ACCEPTED")
    if state.get("canonical_evidence_claim_id") != claim_id:
        raise SynthesisGovernanceError("Claim state diverge do EvidenceClaim canônico")
    if candidate.get("evidence_record_id") != evidence_record_id:
        raise SynthesisGovernanceError("Claim candidate diverge do EvidenceRecord")
    _validate_candidate_current(candidate, output_root=output_root)

    snapshot = candidate.get("source_snapshot")
    if not isinstance(snapshot, Mapping):
        raise SynthesisGovernanceError("Claim candidate sem source snapshot")
    snapshot_sha = _digest(dict(snapshot))
    if str(metadata.get("source_snapshot_sha256") or "") != snapshot_sha:
        raise SynthesisGovernanceError("EvidenceClaim diverge do source snapshot aceito")
    if str(snapshot.get("document_id") or "") != source_document_id:
        raise SynthesisGovernanceError("Source snapshot document id diverge do EvidenceClaim")
    if str(metadata.get("source_manifest_id") or "") != str(candidate.get("source_manifest_id") or ""):
        raise SynthesisGovernanceError("EvidenceClaim diverge do source publication manifest")

    return record, dict(claim), candidate, evidence_record


def _build_evaluation_candidate(
    claim_id: str, *, staged_by: str, output_root: Path
) -> dict[str, Any]:
    record, claim, source_candidate, evidence_record = _load_accepted_claim(
        claim_id, output_root=output_root
    )
    metadata = claim.get("metadata") or {}
    source_snapshot = source_candidate.get("source_snapshot") or {}
    scientific = {
        "candidate_type": EVALUATION_CANDIDATE_TYPE,
        "canonical": False,
        "candidate_scope": "HUMAN_CLAIM_LEVEL_SCIENTIFIC_APPRAISAL",
        "appraisal_method": APPRAISAL_METHOD,
        "claim_id": claim_id,
        "claim_content_sha256": record.get("content_sha256"),
        "evidence_record_id": claim.get("evidence_record_id"),
        "source_document_id": metadata.get("source_document_id"),
        "source_manifest_id": metadata.get("source_manifest_id"),
        "source_manifest_content_sha256": metadata.get("source_manifest_content_sha256"),
        "source_context_fingerprint": source_candidate.get("source_context_fingerprint"),
        "claim_snapshot": {
            "statement": claim.get("statement"),
            "locator": claim.get("locator"),
            "population": claim.get("population"),
            "intervention_or_exposure": claim.get("intervention_or_exposure"),
            "comparator": claim.get("comparator"),
            "outcome": claim.get("outcome"),
            "evidence_type": claim.get("evidence_type"),
            "accepted_by": metadata.get("reviewer"),
            "acceptance_rationale": metadata.get("review_rationale"),
            "accepted_at": record.get("accepted_at"),
        },
        "source_snapshot": {
            "citation_id": source_snapshot.get("citation_id"),
            "decision_id": source_snapshot.get("decision_id"),
            "document_id": source_snapshot.get("document_id"),
            "title": source_snapshot.get("title"),
            "bundle_id": source_snapshot.get("bundle_id"),
            "source_sentence_sha256": source_snapshot.get("source_sentence_sha256"),
            "result_text": source_snapshot.get("result_text"),
            "outcomes": source_snapshot.get("outcomes") or [],
            "effect_measures": source_snapshot.get("effect_measures") or [],
            "confidence_intervals": source_snapshot.get("confidence_intervals") or [],
            "p_values": source_snapshot.get("p_values") or [],
            "source_reference": source_snapshot.get("source_reference"),
        },
        "evidence_record_snapshot": {
            "id": evidence_record.get("id"),
            "document_id": evidence_record.get("document_id"),
            "source_provider": evidence_record.get("source_provider"),
            "origin_sha256": evidence_record.get("origin_sha256"),
        },
        "required_dimensions": list(DIMENSIONS),
        "dimension_definitions": DIMENSIONS,
        "judgment_scale": sorted(JUDGMENTS),
        "assessment_basis_options": sorted(ASSESSMENT_BASES),
        "staged_by": staged_by,
        "guardrails": {
            "human_appraisal_required": True,
            "numeric_appraisal_score_created": False,
            "automatic_dimension_aggregation_performed": False,
            "formal_external_instrument_applied": False,
            "formal_risk_of_bias_assessed": False,
            "certainty_assessed": False,
            "overall_certainty_grade_created": False,
            "evidence_set_created": False,
            "canonical_scientific_synthesis_created": False,
            "clinical_recommendation_created": False,
            "screening_eligibility_changed": False,
            "accepted_claim_statement_changed": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "identity_cryptographically_authenticated": False,
        },
    }
    candidate_id = "claim_eval_candidate_" + _digest(scientific)[:24]
    content = {**scientific, "candidate_id": candidate_id}
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": _now(),
        "artifact_semantics": (
            "Non-canonical human-appraisal candidate for one accepted source-level EvidenceClaim. "
            "It does not create risk-of-bias, certainty, evidence synthesis, or recommendation."
        ),
    }


def stage_claim_evaluation(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    claim_id = str(payload.get("claim_id") or "").strip()
    staged_by = str(payload.get("staged_by") or "").strip()
    if not claim_id:
        raise SynthesisGovernanceError("EvidenceClaim id obrigatório")
    if not staged_by:
        raise SynthesisGovernanceError("Identifique quem iniciou o ClaimEvaluation")

    candidate = _build_evaluation_candidate(
        claim_id, staged_by=staged_by, output_root=output_root
    )
    candidate_id = str(candidate.get("candidate_id") or "")
    root = _evaluation_root(output_root)
    candidate_path = _candidate_path(root, candidate_id)
    state_path = _state_path(root, candidate_id)
    with _EVALUATION_LOCK:
        if candidate_path.is_file():
            existing = _read_json(candidate_path, "ClaimEvaluation candidate")
            if existing.get("content_sha256") != candidate.get("content_sha256"):
                raise SynthesisGovernanceError("ClaimEvaluation candidate id collision")
        else:
            _atomic_json(candidate_path, candidate)
        if not state_path.is_file():
            _atomic_json(
                state_path,
                {
                    "state_type": EVALUATION_STATE_TYPE,
                    "candidate_id": candidate_id,
                    "claim_id": claim_id,
                    "status": PENDING_APPRAISAL,
                    "staged_by": staged_by,
                    "staged_at": _now(),
                    "canonical_claim_evaluation_id": None,
                    "identity_cryptographically_authenticated": False,
                },
            )
    return claim_evaluation_status(output_root=output_root)


def _load_evaluation_candidate(
    candidate_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_id = str(candidate_id or "").strip()
    if not candidate_id:
        raise SynthesisGovernanceError("ClaimEvaluation candidate id obrigatório")
    root = _evaluation_root(output_root)
    candidate = _read_json(_candidate_path(root, candidate_id), "ClaimEvaluation candidate")
    state = _read_json(_state_path(root, candidate_id), "ClaimEvaluation state")
    if candidate.get("candidate_type") != EVALUATION_CANDIDATE_TYPE:
        raise SynthesisGovernanceError("ClaimEvaluation candidate type inválido")
    if candidate.get("canonical") is not False:
        raise SynthesisGovernanceError("ClaimEvaluation candidate foi canonizado prematuramente")
    if state.get("state_type") != EVALUATION_STATE_TYPE or state.get("candidate_id") != candidate_id:
        raise SynthesisGovernanceError("ClaimEvaluation state inválido")
    expected_sha = _digest(_evaluation_candidate_scientific_content(candidate))
    if candidate.get("content_sha256") != expected_sha:
        raise SynthesisGovernanceError("ClaimEvaluation candidate content SHA-256 inválido")
    return candidate, state


def _revalidate_evaluation_candidate(candidate: Mapping[str, Any], *, output_root: Path) -> None:
    claim_id = str(candidate.get("claim_id") or "").strip()
    staged_by = str(candidate.get("staged_by") or "").strip()
    rebuilt = _build_evaluation_candidate(
        claim_id, staged_by=staged_by, output_root=output_root
    )
    if rebuilt.get("content_sha256") != candidate.get("content_sha256"):
        raise SynthesisGovernanceError(
            "ClaimEvaluation candidate não corresponde mais ao EvidenceClaim/source atual; restage necessário"
        )


def _normalize_dimensions(raw: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw, Mapping):
        raise SynthesisGovernanceError("Dimensions obrigatórias para ClaimEvaluation")
    supplied = {str(key) for key in raw}
    expected = set(DIMENSIONS)
    if supplied != expected:
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        raise SynthesisGovernanceError(
            f"Dimensions inválidas; missing={missing or []}; extra={extra or []}"
        )

    normalized: dict[str, dict[str, str]] = {}
    for key in DIMENSIONS:
        value = raw.get(key)
        if not isinstance(value, Mapping):
            raise SynthesisGovernanceError(f"Dimension {key} inválida")
        judgment = str(value.get("judgment") or "").strip().upper()
        rationale = str(value.get("rationale") or "").strip()
        if judgment not in JUDGMENTS:
            raise SynthesisGovernanceError(f"Judgment inválido em {key}")
        if len(rationale) < 15:
            raise SynthesisGovernanceError(
                f"Rationale de {key} precisa ter pelo menos 15 caracteres"
            )
        normalized[key] = {
            "judgment": judgment,
            "rationale": rationale,
        }
    return normalized


def finalize_claim_evaluation(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    candidate_id = str(payload.get("candidate_id") or "").strip()
    assessor = str(payload.get("assessor") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    assessment_basis = str(payload.get("assessment_basis") or "").strip().upper()
    basis_details = str(payload.get("basis_details") or "").strip()
    nonformal_method_confirmed = payload.get("nonformal_method_confirmed") is True
    scientific_boundary_confirmed = payload.get("scientific_boundary_confirmed") is True
    claim_scope_confirmed = payload.get("claim_scope_confirmed") is True

    if not assessor:
        raise SynthesisGovernanceError("Identifique o assessor do ClaimEvaluation")
    if len(rationale) < 30:
        raise SynthesisGovernanceError("Rationale geral precisa ter pelo menos 30 caracteres")
    if assessment_basis not in ASSESSMENT_BASES:
        raise SynthesisGovernanceError("Assessment basis inválido")
    if assessment_basis == "OTHER" and len(basis_details) < 10:
        raise SynthesisGovernanceError("Descreva o assessment basis OTHER")
    if not nonformal_method_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que este appraisal não é um instrumento formal de RoB/GRADE"
        )
    if not scientific_boundary_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que ClaimEvaluation não equivale a certainty, síntese ou recomendação"
        )
    if not claim_scope_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que os julgamentos se aplicam ao claim avaliado, não automaticamente ao estudo inteiro"
        )

    dimensions = _normalize_dimensions(payload.get("dimensions"))
    root = _evaluation_root(output_root)
    with _EVALUATION_LOCK:
        candidate, state = _load_evaluation_candidate(candidate_id, output_root=output_root)
        _revalidate_evaluation_candidate(candidate, output_root=output_root)
        if state.get("status") == FINALIZED:
            existing_id = str(state.get("canonical_claim_evaluation_id") or "")
            if existing_id:
                return claim_evaluation_status(output_root=output_root)
            raise SynthesisGovernanceError("ClaimEvaluation state final sem evaluation id")

        scientific = {
            "evaluation_record_type": CANONICAL_EVALUATION_RECORD_TYPE,
            "canonical": True,
            "human_finalized": True,
            "appraisal_method": APPRAISAL_METHOD,
            "source_candidate_id": candidate_id,
            "source_candidate_content_sha256": candidate.get("content_sha256"),
            "source_claim_content_sha256": candidate.get("claim_content_sha256"),
            "source_context_fingerprint": candidate.get("source_context_fingerprint"),
            "claim_evaluation": {
                "id": "pending",
                "claim_id": candidate.get("claim_id"),
                "dimensions": dimensions,
                "assessor": assessor,
                "rationale": rationale,
            },
            "assessment_basis": assessment_basis,
            "basis_details": basis_details or None,
            "methodology": {
                "method_id": APPRAISAL_METHOD,
                "formal_external_instrument": False,
                "numeric_score": False,
                "automatic_overall_judgment": False,
                "dimensions_are_human_judgments": True,
                "dimension_definitions": DIMENSIONS,
                "judgment_scale": sorted(JUDGMENTS),
            },
            "confirmations": {
                "nonformal_method_confirmed": True,
                "scientific_boundary_confirmed": True,
                "claim_scope_confirmed": True,
                "human_entered": True,
                "identity_cryptographically_authenticated": False,
            },
            "guardrails": {
                "claim_evaluation_created": True,
                "formal_risk_of_bias_assessed": False,
                "certainty_assessed": False,
                "overall_certainty_grade_created": False,
                "numeric_appraisal_score_created": False,
                "automatic_dimension_aggregation_performed": False,
                "formal_external_instrument_applied": False,
                "evidence_set_created": False,
                "canonical_scientific_synthesis_created": False,
                "clinical_recommendation_created": False,
                "screening_eligibility_changed": False,
                "accepted_claim_statement_changed": False,
                "accepted_claim_status_changed": False,
                "meta_analysis_performed": False,
                "prisma_event_emitted": False,
                "identity_cryptographically_authenticated": False,
            },
        }
        evaluation_id = "claim_eval_" + _digest(scientific)[:24]
        scientific["claim_evaluation"]["id"] = evaluation_id
        content_sha256 = _digest(scientific)
        record = {
            **scientific,
            "content_sha256": content_sha256,
            "evaluated_at": _now(),
            "artifact_semantics": (
                "Canonical record of a human claim-level scientific appraisal. Canonical means the "
                "authoritative NutEV record of this appraisal, not evidence certainty, formal risk of bias, "
                "study validity, synthesis, or recommendation."
            ),
        }
        evaluation_path = _evaluation_path(root, evaluation_id)
        if evaluation_path.is_file():
            existing = _read_json(evaluation_path, "canonical ClaimEvaluation")
            if existing.get("content_sha256") != content_sha256:
                raise SynthesisGovernanceError("Canonical ClaimEvaluation id collision")
        else:
            _atomic_json(evaluation_path, record)
        _atomic_json(
            _state_path(root, candidate_id),
            {
                **state,
                "status": FINALIZED,
                "canonical_claim_evaluation_id": evaluation_id,
                "finalized_at": record["evaluated_at"],
                "identity_cryptographically_authenticated": False,
            },
        )
    return claim_evaluation_status(output_root=output_root)


def claim_evaluation_status(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    root = _evaluation_root(output_root)
    candidates: list[dict[str, Any]] = []
    counts = {PENDING_APPRAISAL: 0, FINALIZED: 0}
    states_dir = root / "states"
    with _EVALUATION_LOCK:
        state_paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
        for state_path in state_paths:
            try:
                state = _read_json(state_path, state_path.name)
                candidate_id = str(state.get("candidate_id") or "")
                candidate = _read_json(_candidate_path(root, candidate_id), "ClaimEvaluation candidate")
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            status = str(state.get("status") or PENDING_APPRAISAL)
            if status in counts:
                counts[status] += 1
            claim_snapshot = candidate.get("claim_snapshot")
            source_snapshot = candidate.get("source_snapshot")
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "status": status,
                    "claim_id": candidate.get("claim_id"),
                    "claim_content_sha256": candidate.get("claim_content_sha256"),
                    "evidence_record_id": candidate.get("evidence_record_id"),
                    "source_document_id": candidate.get("source_document_id"),
                    "source_context_fingerprint": candidate.get("source_context_fingerprint"),
                    "claim_snapshot": dict(claim_snapshot) if isinstance(claim_snapshot, Mapping) else {},
                    "source_snapshot": dict(source_snapshot) if isinstance(source_snapshot, Mapping) else {},
                    "required_dimensions": candidate.get("required_dimensions") or [],
                    "canonical_claim_evaluation_id": state.get("canonical_claim_evaluation_id"),
                    "staged_by": state.get("staged_by"),
                }
            )

    finalized: list[dict[str, Any]] = []
    finalized_dir = root / "finalized"
    if finalized_dir.is_dir():
        for path in sorted(finalized_dir.glob("*.json")):
            try:
                record = _read_json(path, path.name)
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            if record.get("evaluation_record_type") != CANONICAL_EVALUATION_RECORD_TYPE:
                continue
            evaluation = record.get("claim_evaluation")
            if not isinstance(evaluation, Mapping):
                continue
            finalized.append(
                {
                    "evaluation_id": evaluation.get("id"),
                    "claim_id": evaluation.get("claim_id"),
                    "dimensions": evaluation.get("dimensions") or {},
                    "assessor": evaluation.get("assessor"),
                    "rationale": evaluation.get("rationale"),
                    "assessment_basis": record.get("assessment_basis"),
                    "evaluated_at": record.get("evaluated_at"),
                    "canonical": record.get("canonical"),
                    "formal_risk_of_bias_assessed": bool(
                        (record.get("guardrails") or {}).get("formal_risk_of_bias_assessed")
                    ),
                    "certainty_assessed": bool(
                        (record.get("guardrails") or {}).get("certainty_assessed")
                    ),
                }
            )
    finalized.sort(key=lambda item: str(item.get("evaluated_at") or ""), reverse=True)
    candidates.sort(key=lambda item: str(item.get("candidate_id") or ""))
    return {
        "status": "READY",
        "appraisal_method": APPRAISAL_METHOD,
        "evaluation_candidate_type": EVALUATION_CANDIDATE_TYPE,
        "canonical_evaluation_record_type": CANONICAL_EVALUATION_RECORD_TYPE,
        "dimensions": DIMENSIONS,
        "judgment_scale": sorted(JUDGMENTS),
        "assessment_basis_options": sorted(ASSESSMENT_BASES),
        "candidate_count": len(candidates),
        "candidate_counts": counts,
        "candidates": candidates[:STATUS_LIMIT],
        "candidate_list_truncated": len(candidates) > STATUS_LIMIT,
        "finalized_evaluation_count": len(finalized),
        "finalized_evaluations": finalized[:STATUS_LIMIT],
        "finalized_evaluation_list_truncated": len(finalized) > STATUS_LIMIT,
        "scientific_boundary": (
            "ClaimEvaluation records explicit human appraisal dimensions for one accepted EvidenceClaim. "
            "The generic appraisal is not a validated risk-of-bias instrument, does not calculate a score, "
            "does not create certainty/GRADE, EvidenceSet synthesis, recommendation, or PRISMA state."
        ),
    }
