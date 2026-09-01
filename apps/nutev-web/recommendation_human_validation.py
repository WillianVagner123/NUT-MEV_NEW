from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Mapping

from governed_synthesis_release import DEFAULT_OUTPUT_ROOT, _atomic_json, _digest, _read_json
from recommendation_candidate_drafting import (
    CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE,
    READINESS_NOT_EVALUATED,
    _candidate_path,
    _recommendation_root,
    _record_scientific_content,
    _set_snapshot,
)
from synthesis_governance import SynthesisGovernanceError

VALIDATION_CASE_TYPE = "NUTEV_RECOMMENDATION_HUMAN_VALIDATION_CASE_V1"
VALIDATION_STATE_TYPE = "NUTEV_RECOMMENDATION_HUMAN_VALIDATION_STATE_V1"
CANONICAL_HUMAN_VALIDATION_RECORD_TYPE = "NUTEV_CANONICAL_HUMAN_VALIDATION_RECORD_V1"
VALIDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_HUMAN_VALIDATION"
VALIDATION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_HUMAN_VALIDATION"
TARGET_TYPE = "RecommendationCandidate"
PENDING = "PENDING"
ACCEPT = "ACCEPT"
REJECT = "REJECT"
REVISE = "REVISE"
DECISIONS = {ACCEPT, REJECT, REVISE}
MODEL_DECISIONS = {ACCEPT: "accept", REJECT: "reject", REVISE: "revise"}
STATUS_LIMIT = 200

_VALIDATION_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validation_root(output_root: Path) -> Path:
    return output_root / "scientific" / "human_validations" / "recommendation_candidates"


def _case_path(root: Path, validation_id: str) -> Path:
    return root / "cases" / f"{validation_id}.json"


def _state_path(root: Path, validation_id: str) -> Path:
    return root / "states" / f"{validation_id}.json"


def _record_path(root: Path, validation_id: str) -> Path:
    return root / "finalized" / f"{validation_id}.json"


def _scientific_content(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in record
        if key not in {"content_sha256", "generated_at", "reviewed_at", "artifact_semantics"}
    }


def _load_finalized_candidate(
    candidate_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_id = str(candidate_id or "").strip()
    if not candidate_id:
        raise SynthesisGovernanceError("RecommendationCandidate id obrigatório")

    root = _recommendation_root(output_root)
    record = _read_json(_candidate_path(root, candidate_id), "canonical RecommendationCandidate")
    if (
        record.get("recommendation_candidate_record_type")
        != CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE
    ):
        raise SynthesisGovernanceError("RecommendationCandidate record type inválido")
    if record.get("canonical") is not True or record.get("human_finalized") is not True:
        raise SynthesisGovernanceError("HumanValidation exige RecommendationCandidate humano finalizado")

    expected_sha = _digest(_record_scientific_content(record))
    if str(record.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("RecommendationCandidate content SHA-256 inválido")

    candidate = record.get("recommendation_candidate")
    if not isinstance(candidate, Mapping):
        raise SynthesisGovernanceError("RecommendationCandidate payload inválido")
    if str(candidate.get("id") or "") != candidate_id:
        raise SynthesisGovernanceError("RecommendationCandidate id diverge do registro canônico")
    if str(candidate.get("readiness") or "") != READINESS_NOT_EVALUATED:
        raise SynthesisGovernanceError(
            "RecommendationCandidate readiness foi alterado fora do contrato da Fase 19"
        )

    evidence_set_ids = [str(value or "").strip() for value in candidate.get("evidence_set_ids") or []]
    if not evidence_set_ids or any(not value for value in evidence_set_ids):
        raise SynthesisGovernanceError("RecommendationCandidate sem EvidenceSets válidos")

    guardrails = record.get("guardrails")
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("RecommendationCandidate sem guardrails")
    if guardrails.get("recommendation_candidate_created") is not True:
        raise SynthesisGovernanceError("RecommendationCandidate não registra criação explícita")
    for key in (
        "automatic_statement_generation_performed",
        "automatic_readiness_inference_performed",
        "readiness_evaluated",
        "recommendation_validated",
        "human_validation_created",
        "evidence_set_agreement_inferred",
        "evidence_set_contradiction_inferred",
        "evidence_set_scores_aggregated",
        "certainty_assessed",
        "overall_certainty_grade_created",
        "formal_risk_of_bias_assessed",
        "clinical_recommendation_created",
        "canonical_scientific_synthesis_created",
        "meta_analysis_performed",
        "prisma_event_emitted",
        "upstream_evidence_sets_changed",
        "identity_cryptographically_authenticated",
    ):
        if guardrails.get(key) is not False:
            raise SynthesisGovernanceError(f"RecommendationCandidate guardrail inválido: {key}")

    metadata = candidate.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SynthesisGovernanceError("RecommendationCandidate sem metadata")
    stored_sets = metadata.get("source_evidence_sets")
    if not isinstance(stored_sets, list) or len(stored_sets) != len(evidence_set_ids):
        raise SynthesisGovernanceError("RecommendationCandidate source EvidenceSet snapshots inválidos")
    stored_by_id: dict[str, Mapping[str, Any]] = {}
    for raw in stored_sets:
        if not isinstance(raw, Mapping):
            raise SynthesisGovernanceError("RecommendationCandidate EvidenceSet snapshot inválido")
        evidence_set_id = str(raw.get("evidence_set_id") or "").strip()
        if not evidence_set_id or evidence_set_id in stored_by_id:
            raise SynthesisGovernanceError(
                "RecommendationCandidate possui EvidenceSet snapshot ausente ou duplicado"
            )
        stored_by_id[evidence_set_id] = raw
    if set(stored_by_id) != set(evidence_set_ids):
        raise SynthesisGovernanceError(
            "RecommendationCandidate EvidenceSet snapshots divergem dos ids declarados"
        )

    for evidence_set_id in evidence_set_ids:
        current = _set_snapshot(evidence_set_id, output_root=output_root)
        if _digest(current) != _digest(dict(stored_by_id[evidence_set_id])):
            raise SynthesisGovernanceError(
                "RecommendationCandidate não corresponde mais aos EvidenceSets/claims/evaluations/contexto atuais"
            )

    return record, dict(candidate)


def _candidate_snapshot(candidate_id: str, *, output_root: Path) -> dict[str, Any]:
    record, candidate = _load_finalized_candidate(candidate_id, output_root=output_root)
    metadata = candidate.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SynthesisGovernanceError("RecommendationCandidate sem metadata")
    evidence_set_ids = [str(value) for value in candidate.get("evidence_set_ids") or []]
    return {
        "recommendation_candidate_id": candidate_id,
        "recommendation_candidate_content_sha256": record.get("content_sha256"),
        "statement": candidate.get("statement"),
        "rationale": candidate.get("rationale"),
        "readiness": candidate.get("readiness"),
        "evidence_set_ids": evidence_set_ids,
        "evidence_set_count": len(evidence_set_ids),
        "intended_audience": metadata.get("intended_audience"),
        "intended_context": metadata.get("intended_context"),
        "source_context_fingerprint": record.get("source_context_fingerprint"),
        "search_id": record.get("search_id"),
        "context_version": record.get("context_version"),
        "finalized_at": record.get("finalized_at"),
    }


def _validation_id(candidate_id: str) -> str:
    return "human_validation_" + _digest({"target_type": TARGET_TYPE, "target_id": candidate_id})[:24]


def stage_recommendation_human_validation(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    candidate_id = str(payload.get("recommendation_candidate_id") or "").strip()
    staged_by = str(payload.get("staged_by") or "").strip()
    review_scope = str(payload.get("review_scope") or "").strip()
    if not candidate_id:
        raise SynthesisGovernanceError("RecommendationCandidate id obrigatório")
    if not staged_by:
        raise SynthesisGovernanceError("Identifique quem abriu a HumanValidation")
    if len(review_scope) < 20:
        raise SynthesisGovernanceError("Review scope precisa ter pelo menos 20 caracteres")

    snapshot = _candidate_snapshot(candidate_id, output_root=output_root)
    validation_id = _validation_id(candidate_id)
    scientific = {
        "validation_case_type": VALIDATION_CASE_TYPE,
        "canonical": False,
        "validation_id": validation_id,
        "target_type": TARGET_TYPE,
        "target_id": candidate_id,
        "decision": "pending",
        "review_scope": review_scope,
        "source_candidate": snapshot,
        "source_candidate_content_sha256": snapshot["recommendation_candidate_content_sha256"],
        "source_context_fingerprint": snapshot["source_context_fingerprint"],
        "search_id": snapshot["search_id"],
        "context_version": snapshot["context_version"],
        "guardrails": {
            "human_validation_pending": True,
            "automatic_validation_decision_performed": False,
            "recommendation_candidate_changed": False,
            "readiness_changed": False,
            "readiness_evaluated": False,
            "validated_recommendation_created": False,
            "clinical_recommendation_created": False,
            "guideline_recommendation_created": False,
            "certainty_assessed": False,
            "grade_assessed": False,
            "formal_risk_of_bias_assessed": False,
            "canonical_scientific_synthesis_created": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "identity_cryptographically_authenticated": False,
        },
    }
    case = {
        **scientific,
        "content_sha256": _digest(scientific),
        "generated_at": _now(),
        "artifact_semantics": (
            "Pending HumanValidation case for one finalized RecommendationCandidate. PENDING is not acceptance, "
            "recommendation validation, certainty, guideline status, or clinical recommendation."
        ),
    }

    root = _validation_root(output_root)
    with _VALIDATION_LOCK:
        case_path = _case_path(root, validation_id)
        state_path = _state_path(root, validation_id)
        if case_path.is_file():
            existing = _read_json(case_path, "HumanValidation case")
            if existing.get("content_sha256") != case.get("content_sha256"):
                raise SynthesisGovernanceError(
                    "HumanValidation deste RecommendationCandidate já existe com review scope diferente"
                )
        else:
            _atomic_json(case_path, case)
        if not state_path.is_file():
            _atomic_json(
                state_path,
                {
                    "state_type": VALIDATION_STATE_TYPE,
                    "validation_id": validation_id,
                    "target_type": TARGET_TYPE,
                    "target_id": candidate_id,
                    "status": PENDING,
                    "staged_by": staged_by,
                    "staged_at": _now(),
                    "canonical_human_validation_id": None,
                    "identity_cryptographically_authenticated": False,
                },
            )
    return recommendation_human_validation_status(output_root=output_root)


def _load_case(
    validation_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    validation_id = str(validation_id or "").strip()
    if not validation_id:
        raise SynthesisGovernanceError("HumanValidation id obrigatório")
    root = _validation_root(output_root)
    case = _read_json(_case_path(root, validation_id), "HumanValidation case")
    state = _read_json(_state_path(root, validation_id), "HumanValidation state")
    if case.get("validation_case_type") != VALIDATION_CASE_TYPE or case.get("canonical") is not False:
        raise SynthesisGovernanceError("HumanValidation case inválido")
    if state.get("state_type") != VALIDATION_STATE_TYPE or state.get("validation_id") != validation_id:
        raise SynthesisGovernanceError("HumanValidation state inválido")
    expected_sha = _digest(_scientific_content(case))
    if case.get("content_sha256") != expected_sha:
        raise SynthesisGovernanceError("HumanValidation case content SHA-256 inválido")
    return case, state


def _revalidate_case(case: Mapping[str, Any], *, output_root: Path) -> None:
    candidate_id = str(case.get("target_id") or "")
    current = _candidate_snapshot(candidate_id, output_root=output_root)
    stored = case.get("source_candidate")
    if not isinstance(stored, Mapping):
        raise SynthesisGovernanceError("HumanValidation sem source candidate snapshot")
    if _digest(current) != _digest(dict(stored)):
        raise SynthesisGovernanceError(
            "HumanValidation não corresponde mais ao RecommendationCandidate/EvidenceSets/contexto atuais; restage necessário"
        )
    if str(case.get("source_candidate_content_sha256") or "") != str(
        current.get("recommendation_candidate_content_sha256") or ""
    ):
        raise SynthesisGovernanceError("HumanValidation source candidate SHA divergiu")


def _normalize_decision(raw: Any) -> str:
    decision = str(raw or "").strip().upper()
    if decision not in DECISIONS:
        raise SynthesisGovernanceError("HumanValidation decision deve ser ACCEPT, REJECT ou REVISE")
    return decision


def decide_recommendation_human_validation(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    validation_id = str(payload.get("validation_id") or "").strip()
    decision = _normalize_decision(payload.get("decision"))
    reviewer = str(payload.get("reviewer") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    revision_instructions = str(payload.get("revision_instructions") or "").strip()
    decision_human_entered_confirmed = payload.get("decision_human_entered_confirmed") is True
    decision_is_not_certainty_confirmed = payload.get("decision_is_not_certainty_confirmed") is True
    decision_is_not_clinical_recommendation_confirmed = (
        payload.get("decision_is_not_clinical_recommendation_confirmed") is True
    )
    upstream_candidate_immutable_confirmed = (
        payload.get("upstream_candidate_immutable_confirmed") is True
    )

    if not reviewer:
        raise SynthesisGovernanceError("Identifique o reviewer da HumanValidation")
    if len(rationale) < 40:
        raise SynthesisGovernanceError("HumanValidation rationale precisa ter pelo menos 40 caracteres")
    if decision == REVISE and len(revision_instructions) < 20:
        raise SynthesisGovernanceError(
            "REVISE exige revision instructions com pelo menos 20 caracteres"
        )
    if decision != REVISE and revision_instructions:
        raise SynthesisGovernanceError("Revision instructions só são permitidas para decisão REVISE")
    if not decision_human_entered_confirmed:
        raise SynthesisGovernanceError("Confirme que a decisão foi inserida explicitamente por humano")
    if not decision_is_not_certainty_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que HumanValidation não equivale a certainty, GRADE ou formal Risk of Bias"
        )
    if not decision_is_not_clinical_recommendation_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que a decisão não cria clinical/guideline recommendation automaticamente"
        )
    if not upstream_candidate_immutable_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que a HumanValidation não reescreve o RecommendationCandidate upstream"
        )

    root = _validation_root(output_root)
    with _VALIDATION_LOCK:
        case, state = _load_case(validation_id, output_root=output_root)
        _revalidate_case(case, output_root=output_root)

        if state.get("status") != PENDING:
            record = _read_json(_record_path(root, validation_id), "canonical HumanValidation")
            validation = record.get("human_validation")
            if isinstance(validation, Mapping):
                same = (
                    str(validation.get("decision") or "") == MODEL_DECISIONS[decision]
                    and str(validation.get("reviewer") or "") == reviewer
                    and str(validation.get("rationale") or "") == rationale
                    and str((validation.get("metadata") or {}).get("revision_instructions") or "")
                    == revision_instructions
                )
                if same:
                    return recommendation_human_validation_status(output_root=output_root)
            raise SynthesisGovernanceError(
                "HumanValidation já possui decisão canônica; decisões conflitantes não podem sobrescrevê-la"
            )

        candidate_id = str(case.get("target_id") or "")
        current_candidate = _candidate_snapshot(candidate_id, output_root=output_root)
        reviewed_at = _now()
        model_decision = MODEL_DECISIONS[decision]
        scientific = {
            "human_validation_record_type": CANONICAL_HUMAN_VALIDATION_RECORD_TYPE,
            "canonical": True,
            "human_finalized": True,
            "validation_id": validation_id,
            "target_type": TARGET_TYPE,
            "target_id": candidate_id,
            "source_case_content_sha256": case.get("content_sha256"),
            "source_candidate_content_sha256": current_candidate.get(
                "recommendation_candidate_content_sha256"
            ),
            "source_context_fingerprint": current_candidate.get("source_context_fingerprint"),
            "search_id": current_candidate.get("search_id"),
            "context_version": current_candidate.get("context_version"),
            "human_validation": {
                "id": validation_id,
                "target_type": TARGET_TYPE,
                "target_id": candidate_id,
                "decision": model_decision,
                "reviewer": reviewer,
                "rationale": rationale,
                "reviewed_at": reviewed_at,
                "metadata": {
                    "review_scope": case.get("review_scope"),
                    "revision_instructions": revision_instructions or None,
                    "candidate_accepted_for_declared_scope": decision == ACCEPT,
                    "human_entered": True,
                    "identity_cryptographically_authenticated": False,
                },
            },
            "source_candidate": current_candidate,
            "confirmations": {
                "decision_human_entered_confirmed": True,
                "decision_is_not_certainty_confirmed": True,
                "decision_is_not_clinical_recommendation_confirmed": True,
                "upstream_candidate_immutable_confirmed": True,
                "human_entered": True,
                "identity_cryptographically_authenticated": False,
            },
            "guardrails": {
                "human_validation_created": True,
                "human_validation_decision_recorded": True,
                "candidate_accepted_for_declared_scope": decision == ACCEPT,
                "automatic_validation_decision_performed": False,
                "automatic_revision_applied": False,
                "target_revalidated_at_decision": True,
                "recommendation_candidate_changed": False,
                "readiness_changed": False,
                "readiness_evaluated": False,
                "validated_recommendation_created": False,
                "clinical_recommendation_created": False,
                "guideline_recommendation_created": False,
                "certainty_assessed": False,
                "grade_assessed": False,
                "formal_risk_of_bias_assessed": False,
                "canonical_scientific_synthesis_created": False,
                "meta_analysis_performed": False,
                "prisma_event_emitted": False,
                "identity_cryptographically_authenticated": False,
            },
        }
        record = {
            **scientific,
            "content_sha256": _digest(scientific),
            "reviewed_at": reviewed_at,
            "artifact_semantics": (
                "Canonical NutEV record of one explicit human validation decision about a RecommendationCandidate. "
                "ACCEPT means accepted for the declared review scope only; no decision creates certainty, a "
                "clinical/guideline recommendation, canonical scientific synthesis, meta-analysis, or PRISMA state."
            ),
        }
        record_path = _record_path(root, validation_id)
        if record_path.is_file():
            existing = _read_json(record_path, "canonical HumanValidation")
            if existing.get("content_sha256") != record.get("content_sha256"):
                raise SynthesisGovernanceError("Canonical HumanValidation id collision")
        else:
            _atomic_json(record_path, record)
        _atomic_json(
            _state_path(root, validation_id),
            {
                **state,
                "status": decision,
                "decision": model_decision,
                "canonical_human_validation_id": validation_id,
                "reviewed_at": reviewed_at,
                "identity_cryptographically_authenticated": False,
            },
        )
    return recommendation_human_validation_status(output_root=output_root)


def recommendation_human_validation_status(
    *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    root = _validation_root(output_root)
    counts = {PENDING: 0, ACCEPT: 0, REJECT: 0, REVISE: 0}
    cases: list[dict[str, Any]] = []
    candidate_index: dict[str, dict[str, Any]] = {}

    states_dir = root / "states"
    with _VALIDATION_LOCK:
        state_paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
        for state_path in state_paths:
            try:
                state = _read_json(state_path, state_path.name)
                validation_id = str(state.get("validation_id") or "")
                case = _read_json(_case_path(root, validation_id), "HumanValidation case")
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            status = str(state.get("status") or PENDING)
            if status in counts:
                counts[status] += 1
            candidate_id = str(case.get("target_id") or "")
            source = case.get("source_candidate")
            cases.append(
                {
                    "validation_id": validation_id,
                    "status": status,
                    "decision": state.get("decision") or "pending",
                    "recommendation_candidate_id": candidate_id,
                    "statement": source.get("statement") if isinstance(source, Mapping) else None,
                    "readiness": source.get("readiness") if isinstance(source, Mapping) else None,
                    "review_scope": case.get("review_scope"),
                    "staged_by": state.get("staged_by"),
                    "staged_at": state.get("staged_at"),
                    "reviewed_at": state.get("reviewed_at"),
                }
            )
            candidate_index[candidate_id] = {
                "validation_id": validation_id,
                "status": status,
                "decision": state.get("decision") or "pending",
            }

    finalized: list[dict[str, Any]] = []
    finalized_dir = root / "finalized"
    if finalized_dir.is_dir():
        for path in sorted(finalized_dir.glob("*.json")):
            try:
                record = _read_json(path, path.name)
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            if record.get("human_validation_record_type") != CANONICAL_HUMAN_VALIDATION_RECORD_TYPE:
                continue
            validation = record.get("human_validation")
            if not isinstance(validation, Mapping):
                continue
            metadata = validation.get("metadata")
            finalized.append(
                {
                    "validation_id": validation.get("id"),
                    "recommendation_candidate_id": validation.get("target_id"),
                    "decision": validation.get("decision"),
                    "reviewer": validation.get("reviewer"),
                    "rationale": validation.get("rationale"),
                    "review_scope": metadata.get("review_scope") if isinstance(metadata, Mapping) else None,
                    "revision_instructions": metadata.get("revision_instructions")
                    if isinstance(metadata, Mapping)
                    else None,
                    "candidate_accepted_for_declared_scope": bool(
                        (record.get("guardrails") or {}).get("candidate_accepted_for_declared_scope")
                    ),
                    "readiness_changed": bool(
                        (record.get("guardrails") or {}).get("readiness_changed")
                    ),
                    "clinical_recommendation_created": bool(
                        (record.get("guardrails") or {}).get("clinical_recommendation_created")
                    ),
                    "reviewed_at": record.get("reviewed_at"),
                    "canonical": record.get("canonical"),
                }
            )

    cases.sort(key=lambda item: str(item.get("staged_at") or ""), reverse=True)
    finalized.sort(key=lambda item: str(item.get("reviewed_at") or ""), reverse=True)
    return {
        "status": "READY",
        "validation_case_type": VALIDATION_CASE_TYPE,
        "canonical_human_validation_record_type": CANONICAL_HUMAN_VALIDATION_RECORD_TYPE,
        "target_type": TARGET_TYPE,
        "decision_options": [ACCEPT, REJECT, REVISE],
        "counts": counts,
        "case_count": len(cases),
        "cases": cases[:STATUS_LIMIT],
        "case_list_truncated": len(cases) > STATUS_LIMIT,
        "finalized_validation_count": len(finalized),
        "finalized_validations": finalized[:STATUS_LIMIT],
        "finalized_validation_list_truncated": len(finalized) > STATUS_LIMIT,
        "candidate_validation_index": candidate_index,
        "scientific_boundary": (
            "HumanValidation records an explicit human decision about a finalized RecommendationCandidate. "
            "ACCEPT means accepted for the declared review scope only. ACCEPT/REJECT/REVISE do not change "
            "candidate readiness, do not create certainty/GRADE or formal risk of bias, and do not create a "
            "clinical/guideline recommendation, canonical scientific synthesis, meta-analysis, or PRISMA event."
        ),
    }
