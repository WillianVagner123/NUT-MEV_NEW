from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Mapping

from governed_synthesis_release import DEFAULT_OUTPUT_ROOT, _atomic_json, _digest, _read_json
from recommendation_human_validation import (
    ACCEPT,
    CANONICAL_HUMAN_VALIDATION_RECORD_TYPE,
    _candidate_snapshot,
    _record_path as _validation_record_path,
    _scientific_content as _validation_scientific_content,
    _validation_root,
)
from synthesis_governance import SynthesisGovernanceError

DEVELOPMENT_METHOD = "NUTEV_GENERIC_RECOMMENDATION_DEVELOPMENT_V1"
DEVELOPMENT_DRAFT_TYPE = "NUTEV_RECOMMENDATION_DEVELOPMENT_DRAFT_V1"
DEVELOPMENT_STATE_TYPE = "NUTEV_RECOMMENDATION_DEVELOPMENT_STATE_V1"
CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE = (
    "NUTEV_CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_V1"
)
DEVELOPMENT_STAGE_OPERATION = "STAGE_RECOMMENDATION_DEVELOPMENT"
DEVELOPMENT_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_DEVELOPMENT"
DRAFT = "DRAFT"
FINALIZED = "FINALIZED"
STRENGTH_NOT_EVALUATED = "not_evaluated"
STATUS_LIMIT = 200

_DEVELOPMENT_LOCK = threading.RLock()

FIELD_MINIMUMS: dict[str, int] = {
    "proposed_recommendation_text": 30,
    "population_scope": 20,
    "intervention_or_action": 20,
    "comparator_or_alternative": 3,
    "benefits_summary": 40,
    "harms_burdens_summary": 40,
    "values_preferences_summary": 40,
    "resources_summary": 30,
    "equity_summary": 30,
    "acceptability_summary": 30,
    "feasibility_summary": 30,
    "implementation_considerations": 30,
    "uncertainty_notes": 30,
    "developer_rationale": 40,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _development_root(output_root: Path) -> Path:
    return output_root / "scientific" / "recommendation_development"


def _draft_path(root: Path, development_id: str) -> Path:
    return root / "drafts" / f"{development_id}.json"


def _state_path(root: Path, development_id: str) -> Path:
    return root / "states" / f"{development_id}.json"


def _record_path(root: Path, development_id: str) -> Path:
    return root / "finalized" / f"{development_id}.json"


def _scientific_content(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in record
        if key not in {"content_sha256", "generated_at", "finalized_at", "artifact_semantics"}
    }


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    minimum = FIELD_MINIMUMS[key]
    if len(value) < minimum:
        raise SynthesisGovernanceError(
            f"Recommendation Development {key} precisa ter pelo menos {minimum} caracteres"
        )
    return value


def _load_accepted_human_validation(
    validation_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validation_id = str(validation_id or "").strip()
    if not validation_id:
        raise SynthesisGovernanceError("HumanValidation id obrigatório")

    root = _validation_root(output_root)
    record = _read_json(
        _validation_record_path(root, validation_id), "canonical HumanValidation"
    )
    if record.get("human_validation_record_type") != CANONICAL_HUMAN_VALIDATION_RECORD_TYPE:
        raise SynthesisGovernanceError("HumanValidation record type inválido")
    if record.get("canonical") is not True or record.get("human_finalized") is not True:
        raise SynthesisGovernanceError(
            "Recommendation Development exige HumanValidation canônica e finalizada"
        )

    expected_sha = _digest(_validation_scientific_content(record))
    if str(record.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("HumanValidation content SHA-256 inválido")

    validation = record.get("human_validation")
    if not isinstance(validation, Mapping):
        raise SynthesisGovernanceError("HumanValidation payload inválido")
    if str(validation.get("id") or "") != validation_id:
        raise SynthesisGovernanceError("HumanValidation id diverge do registro canônico")
    if str(validation.get("decision") or "") != "accept":
        raise SynthesisGovernanceError(
            "Recommendation Development exige HumanValidation com decisão ACCEPT"
        )

    guardrails = record.get("guardrails")
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("HumanValidation sem guardrails")
    if guardrails.get("human_validation_created") is not True:
        raise SynthesisGovernanceError("HumanValidation não registra criação explícita")
    if guardrails.get("human_validation_decision_recorded") is not True:
        raise SynthesisGovernanceError("HumanValidation não registra decisão explícita")
    if guardrails.get("candidate_accepted_for_declared_scope") is not True:
        raise SynthesisGovernanceError(
            "HumanValidation ACCEPT não está marcada como aceita para o escopo declarado"
        )
    if guardrails.get("target_revalidated_at_decision") is not True:
        raise SynthesisGovernanceError("HumanValidation não revalidou o target na decisão")
    for key in (
        "automatic_validation_decision_performed",
        "automatic_revision_applied",
        "recommendation_candidate_changed",
        "readiness_changed",
        "readiness_evaluated",
        "validated_recommendation_created",
        "clinical_recommendation_created",
        "guideline_recommendation_created",
        "certainty_assessed",
        "grade_assessed",
        "formal_risk_of_bias_assessed",
        "canonical_scientific_synthesis_created",
        "meta_analysis_performed",
        "prisma_event_emitted",
        "identity_cryptographically_authenticated",
    ):
        if guardrails.get(key) is not False:
            raise SynthesisGovernanceError(f"HumanValidation guardrail inválido: {key}")

    candidate_id = str(validation.get("target_id") or "").strip()
    current_candidate = _candidate_snapshot(candidate_id, output_root=output_root)
    stored_candidate = record.get("source_candidate")
    if not isinstance(stored_candidate, Mapping):
        raise SynthesisGovernanceError("HumanValidation sem source candidate snapshot")
    if _digest(current_candidate) != _digest(dict(stored_candidate)):
        raise SynthesisGovernanceError(
            "HumanValidation ACCEPT não corresponde mais ao RecommendationCandidate/EvidenceSets/contexto atuais"
        )
    if str(record.get("source_candidate_content_sha256") or "") != str(
        current_candidate.get("recommendation_candidate_content_sha256") or ""
    ):
        raise SynthesisGovernanceError("HumanValidation source candidate SHA divergiu")

    return record, dict(validation), current_candidate


def _source_snapshot(validation_id: str, *, output_root: Path) -> dict[str, Any]:
    record, validation, candidate = _load_accepted_human_validation(
        validation_id, output_root=output_root
    )
    metadata = validation.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SynthesisGovernanceError("HumanValidation sem metadata")
    return {
        "human_validation_id": validation_id,
        "human_validation_content_sha256": record.get("content_sha256"),
        "human_validation_decision": validation.get("decision"),
        "human_validation_reviewer": validation.get("reviewer"),
        "human_validation_review_scope": metadata.get("review_scope"),
        "human_validation_reviewed_at": validation.get("reviewed_at"),
        "recommendation_candidate_id": candidate.get("recommendation_candidate_id"),
        "recommendation_candidate_content_sha256": candidate.get(
            "recommendation_candidate_content_sha256"
        ),
        "candidate_statement": candidate.get("statement"),
        "candidate_rationale": candidate.get("rationale"),
        "candidate_readiness": candidate.get("readiness"),
        "candidate_intended_audience": candidate.get("intended_audience"),
        "candidate_intended_context": candidate.get("intended_context"),
        "evidence_set_ids": candidate.get("evidence_set_ids") or [],
        "source_context_fingerprint": candidate.get("source_context_fingerprint"),
        "search_id": candidate.get("search_id"),
        "context_version": candidate.get("context_version"),
    }


def _development_id(validation_id: str) -> str:
    return "recommendation_development_" + _digest(
        {"source_human_validation_id": validation_id, "method": DEVELOPMENT_METHOD}
    )[:24]


def _build_draft(payload: Mapping[str, Any], *, output_root: Path) -> dict[str, Any]:
    validation_id = str(payload.get("human_validation_id") or "").strip()
    source = _source_snapshot(validation_id, output_root=output_root)
    fields = {key: _required_text(payload, key) for key in FIELD_MINIMUMS}
    prepared_by = str(payload.get("prepared_by") or "").strip()
    human_authorship_confirmed = payload.get("human_authorship_confirmed") is True
    generic_method_confirmed = payload.get("generic_method_confirmed") is True

    if not prepared_by:
        raise SynthesisGovernanceError("Identifique quem preparou o Recommendation Development")
    if not human_authorship_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que o wording e as considerações foram escritos por humano"
        )
    if not generic_method_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que esta fase usa método genérico NutEV e não declara aplicação de GRADE EtD"
        )

    scientific = {
        "development_draft_type": DEVELOPMENT_DRAFT_TYPE,
        "canonical": False,
        "method": DEVELOPMENT_METHOD,
        "source_human_validation_id": validation_id,
        "source_human_validation_content_sha256": source["human_validation_content_sha256"],
        "source_recommendation_candidate_id": source["recommendation_candidate_id"],
        "source_recommendation_candidate_content_sha256": source[
            "recommendation_candidate_content_sha256"
        ],
        "source_context_fingerprint": source["source_context_fingerprint"],
        "search_id": source["search_id"],
        "context_version": source["context_version"],
        "source_snapshot": source,
        "development": {
            **fields,
            "recommendation_strength": STRENGTH_NOT_EVALUATED,
            "methodological_status": "GENERIC_DEVELOPMENT_WORKSHEET",
            "prepared_by": prepared_by,
            "human_entered": True,
            "identity_cryptographically_authenticated": False,
        },
        "confirmations": {
            "human_authorship_confirmed": True,
            "generic_method_confirmed": True,
            "human_entered": True,
            "identity_cryptographically_authenticated": False,
        },
        "guardrails": {
            "source_human_validation_accept_revalidated": True,
            "source_candidate_revalidated": True,
            "automatic_recommendation_generation_performed": False,
            "candidate_statement_auto_promoted": False,
            "recommendation_strength_evaluated": False,
            "formal_etd_framework_applied": False,
            "grade_etd_applied": False,
            "certainty_assessed": False,
            "grade_assessed": False,
            "formal_risk_of_bias_assessed": False,
            "formal_benefit_harm_balance_determined": False,
            "values_preferences_formally_assessed": False,
            "resource_use_formally_assessed": False,
            "equity_formally_assessed": False,
            "acceptability_formally_assessed": False,
            "feasibility_formally_assessed": False,
            "recommendation_development_record_created": False,
            "validated_recommendation_created": False,
            "clinical_recommendation_created": False,
            "guideline_recommendation_created": False,
            "canonical_scientific_synthesis_created": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "source_human_validation_changed": False,
            "source_recommendation_candidate_changed": False,
            "identity_cryptographically_authenticated": False,
        },
    }
    development_id = _development_id(validation_id)
    content = {**scientific, "development_id": development_id}
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": _now(),
        "artifact_semantics": (
            "Non-canonical human-authored recommendation development worksheet derived from an ACCEPT HumanValidation. "
            "It does not create a validated, clinical, or guideline recommendation; strength remains not_evaluated."
        ),
    }


def stage_recommendation_development(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    draft = _build_draft(payload, output_root=output_root)
    development_id = str(draft.get("development_id") or "")
    root = _development_root(output_root)

    with _DEVELOPMENT_LOCK:
        draft_path = _draft_path(root, development_id)
        state_path = _state_path(root, development_id)
        if draft_path.is_file():
            existing = _read_json(draft_path, "Recommendation Development draft")
            if existing.get("content_sha256") != draft.get("content_sha256"):
                raise SynthesisGovernanceError(
                    "Recommendation Development deste HumanValidation já existe com conteúdo diferente"
                )
        else:
            _atomic_json(draft_path, draft)
        if not state_path.is_file():
            _atomic_json(
                state_path,
                {
                    "state_type": DEVELOPMENT_STATE_TYPE,
                    "development_id": development_id,
                    "status": DRAFT,
                    "source_human_validation_id": draft.get("source_human_validation_id"),
                    "staged_by": (draft.get("development") or {}).get("prepared_by"),
                    "staged_at": _now(),
                    "canonical_recommendation_development_id": None,
                    "identity_cryptographically_authenticated": False,
                },
            )
    return recommendation_development_status(output_root=output_root)


def _load_draft(
    development_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    development_id = str(development_id or "").strip()
    if not development_id:
        raise SynthesisGovernanceError("Recommendation Development id obrigatório")
    root = _development_root(output_root)
    draft = _read_json(_draft_path(root, development_id), "Recommendation Development draft")
    state = _read_json(_state_path(root, development_id), "Recommendation Development state")
    if draft.get("development_draft_type") != DEVELOPMENT_DRAFT_TYPE:
        raise SynthesisGovernanceError("Recommendation Development draft type inválido")
    if draft.get("canonical") is not False or draft.get("method") != DEVELOPMENT_METHOD:
        raise SynthesisGovernanceError("Recommendation Development draft inválido")
    if state.get("state_type") != DEVELOPMENT_STATE_TYPE or state.get("development_id") != development_id:
        raise SynthesisGovernanceError("Recommendation Development state inválido")
    expected_sha = _digest(_scientific_content(draft))
    if draft.get("content_sha256") != expected_sha:
        raise SynthesisGovernanceError("Recommendation Development draft content SHA-256 inválido")
    return draft, state


def _revalidate_draft(draft: Mapping[str, Any], *, output_root: Path) -> None:
    validation_id = str(draft.get("source_human_validation_id") or "")
    current = _source_snapshot(validation_id, output_root=output_root)
    stored = draft.get("source_snapshot")
    if not isinstance(stored, Mapping):
        raise SynthesisGovernanceError("Recommendation Development sem source snapshot")
    if _digest(current) != _digest(dict(stored)):
        raise SynthesisGovernanceError(
            "Recommendation Development não corresponde mais ao HumanValidation/candidate/contexto atuais; restage necessário"
        )
    if str(draft.get("source_human_validation_content_sha256") or "") != str(
        current.get("human_validation_content_sha256") or ""
    ):
        raise SynthesisGovernanceError("Recommendation Development source HumanValidation SHA divergiu")


def finalize_recommendation_development(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    development_id = str(payload.get("development_id") or "").strip()
    finalizer = str(payload.get("finalizer") or "").strip()
    finalization_rationale = str(payload.get("finalization_rationale") or "").strip()
    no_grade_etd_claim_confirmed = payload.get("no_grade_etd_claim_confirmed") is True
    strength_not_evaluated_confirmed = payload.get("strength_not_evaluated_confirmed") is True
    not_formal_recommendation_confirmed = payload.get("not_formal_recommendation_confirmed") is True
    upstream_immutable_confirmed = payload.get("upstream_immutable_confirmed") is True

    if not finalizer:
        raise SynthesisGovernanceError("Identifique quem finalizou o Recommendation Development")
    if len(finalization_rationale) < 40:
        raise SynthesisGovernanceError(
            "Recommendation Development finalization rationale precisa ter pelo menos 40 caracteres"
        )
    if not no_grade_etd_claim_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que este registro não declara aplicação de GRADE Evidence-to-Decision"
        )
    if not strength_not_evaluated_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que a força da recomendação permanece not_evaluated"
        )
    if not not_formal_recommendation_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que finalizar o worksheet não cria clinical/guideline recommendation"
        )
    if not upstream_immutable_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que HumanValidation e RecommendationCandidate upstream permanecem imutáveis"
        )

    root = _development_root(output_root)
    with _DEVELOPMENT_LOCK:
        draft, state = _load_draft(development_id, output_root=output_root)
        _revalidate_draft(draft, output_root=output_root)
        if state.get("status") == FINALIZED:
            existing_id = str(state.get("canonical_recommendation_development_id") or "")
            if existing_id:
                return recommendation_development_status(output_root=output_root)
            raise SynthesisGovernanceError(
                "Recommendation Development state final sem canonical record id"
            )

        development = draft.get("development")
        if not isinstance(development, Mapping):
            raise SynthesisGovernanceError("Recommendation Development payload inválido")
        finalized_at = _now()
        scientific = {
            "recommendation_development_record_type": (
                CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE
            ),
            "canonical": True,
            "human_finalized": True,
            "method": DEVELOPMENT_METHOD,
            "development_id": development_id,
            "source_draft_content_sha256": draft.get("content_sha256"),
            "source_human_validation_id": draft.get("source_human_validation_id"),
            "source_human_validation_content_sha256": draft.get(
                "source_human_validation_content_sha256"
            ),
            "source_recommendation_candidate_id": draft.get(
                "source_recommendation_candidate_id"
            ),
            "source_recommendation_candidate_content_sha256": draft.get(
                "source_recommendation_candidate_content_sha256"
            ),
            "source_context_fingerprint": draft.get("source_context_fingerprint"),
            "search_id": draft.get("search_id"),
            "context_version": draft.get("context_version"),
            "source_snapshot": draft.get("source_snapshot"),
            "development": {
                **dict(development),
                "recommendation_strength": STRENGTH_NOT_EVALUATED,
                "finalizer": finalizer,
                "finalization_rationale": finalization_rationale,
                "human_entered": True,
                "identity_cryptographically_authenticated": False,
            },
            "confirmations": {
                "human_authorship_confirmed": True,
                "generic_method_confirmed": True,
                "no_grade_etd_claim_confirmed": True,
                "strength_not_evaluated_confirmed": True,
                "not_formal_recommendation_confirmed": True,
                "upstream_immutable_confirmed": True,
                "human_entered": True,
                "identity_cryptographically_authenticated": False,
            },
            "guardrails": {
                "source_human_validation_accept_revalidated": True,
                "source_candidate_revalidated": True,
                "automatic_recommendation_generation_performed": False,
                "candidate_statement_auto_promoted": False,
                "recommendation_strength_evaluated": False,
                "formal_etd_framework_applied": False,
                "grade_etd_applied": False,
                "certainty_assessed": False,
                "grade_assessed": False,
                "formal_risk_of_bias_assessed": False,
                "formal_benefit_harm_balance_determined": False,
                "values_preferences_formally_assessed": False,
                "resource_use_formally_assessed": False,
                "equity_formally_assessed": False,
                "acceptability_formally_assessed": False,
                "feasibility_formally_assessed": False,
                "recommendation_development_record_created": True,
                "validated_recommendation_created": False,
                "clinical_recommendation_created": False,
                "guideline_recommendation_created": False,
                "canonical_scientific_synthesis_created": False,
                "meta_analysis_performed": False,
                "prisma_event_emitted": False,
                "source_human_validation_changed": False,
                "source_recommendation_candidate_changed": False,
                "identity_cryptographically_authenticated": False,
            },
        }
        record = {
            **scientific,
            "content_sha256": _digest(scientific),
            "finalized_at": finalized_at,
            "artifact_semantics": (
                "Canonical NutEV record of a human-authored generic recommendation development worksheet. "
                "Canonical means the worksheet/provenance record is authoritative. It is not GRADE EtD, does not "
                "evaluate recommendation strength, and does not create a validated, clinical, or guideline recommendation."
            ),
        }
        record_path = _record_path(root, development_id)
        if record_path.is_file():
            existing = _read_json(record_path, "canonical Recommendation Development")
            if existing.get("content_sha256") != record.get("content_sha256"):
                raise SynthesisGovernanceError("Canonical Recommendation Development id collision")
        else:
            _atomic_json(record_path, record)
        _atomic_json(
            _state_path(root, development_id),
            {
                **state,
                "status": FINALIZED,
                "canonical_recommendation_development_id": development_id,
                "finalized_at": finalized_at,
                "identity_cryptographically_authenticated": False,
            },
        )
    return recommendation_development_status(output_root=output_root)


def recommendation_development_status(
    *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    root = _development_root(output_root)
    counts = {DRAFT: 0, FINALIZED: 0}
    drafts: list[dict[str, Any]] = []
    validation_index: dict[str, dict[str, Any]] = {}

    states_dir = root / "states"
    with _DEVELOPMENT_LOCK:
        state_paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
        for state_path in state_paths:
            try:
                state = _read_json(state_path, state_path.name)
                development_id = str(state.get("development_id") or "")
                draft = _read_json(_draft_path(root, development_id), "Recommendation Development draft")
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            status = str(state.get("status") or DRAFT)
            if status in counts:
                counts[status] += 1
            development = draft.get("development")
            source = draft.get("source_snapshot")
            drafts.append(
                {
                    "development_id": development_id,
                    "status": status,
                    "human_validation_id": draft.get("source_human_validation_id"),
                    "recommendation_candidate_id": draft.get("source_recommendation_candidate_id"),
                    "candidate_statement": source.get("candidate_statement")
                    if isinstance(source, Mapping)
                    else None,
                    "proposed_recommendation_text": development.get("proposed_recommendation_text")
                    if isinstance(development, Mapping)
                    else None,
                    "population_scope": development.get("population_scope")
                    if isinstance(development, Mapping)
                    else None,
                    "recommendation_strength": STRENGTH_NOT_EVALUATED,
                    "prepared_by": development.get("prepared_by")
                    if isinstance(development, Mapping)
                    else None,
                    "staged_at": state.get("staged_at"),
                }
            )
            validation_id = str(draft.get("source_human_validation_id") or "")
            validation_index[validation_id] = {
                "development_id": development_id,
                "status": status,
            }

    finalized: list[dict[str, Any]] = []
    finalized_dir = root / "finalized"
    if finalized_dir.is_dir():
        for path in sorted(finalized_dir.glob("*.json")):
            try:
                record = _read_json(path, path.name)
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            if (
                record.get("recommendation_development_record_type")
                != CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE
            ):
                continue
            development = record.get("development")
            if not isinstance(development, Mapping):
                continue
            finalized.append(
                {
                    "development_id": record.get("development_id"),
                    "human_validation_id": record.get("source_human_validation_id"),
                    "recommendation_candidate_id": record.get(
                        "source_recommendation_candidate_id"
                    ),
                    "proposed_recommendation_text": development.get(
                        "proposed_recommendation_text"
                    ),
                    "population_scope": development.get("population_scope"),
                    "recommendation_strength": development.get("recommendation_strength"),
                    "method": record.get("method"),
                    "finalizer": development.get("finalizer"),
                    "finalized_at": record.get("finalized_at"),
                    "canonical": record.get("canonical"),
                    "validated_recommendation_created": bool(
                        (record.get("guardrails") or {}).get("validated_recommendation_created")
                    ),
                    "clinical_recommendation_created": bool(
                        (record.get("guardrails") or {}).get("clinical_recommendation_created")
                    ),
                    "guideline_recommendation_created": bool(
                        (record.get("guardrails") or {}).get("guideline_recommendation_created")
                    ),
                    "grade_etd_applied": bool(
                        (record.get("guardrails") or {}).get("grade_etd_applied")
                    ),
                }
            )

    drafts.sort(key=lambda item: str(item.get("staged_at") or ""), reverse=True)
    finalized.sort(key=lambda item: str(item.get("finalized_at") or ""), reverse=True)
    return {
        "status": "READY",
        "method": DEVELOPMENT_METHOD,
        "development_draft_type": DEVELOPMENT_DRAFT_TYPE,
        "canonical_recommendation_development_record_type": (
            CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE
        ),
        "recommendation_strength_default": STRENGTH_NOT_EVALUATED,
        "counts": counts,
        "draft_count": len(drafts),
        "drafts": drafts[:STATUS_LIMIT],
        "draft_list_truncated": len(drafts) > STATUS_LIMIT,
        "finalized_development_count": len(finalized),
        "finalized_developments": finalized[:STATUS_LIMIT],
        "finalized_development_list_truncated": len(finalized) > STATUS_LIMIT,
        "human_validation_development_index": validation_index,
        "scientific_boundary": (
            "Recommendation Development requires an ACCEPT HumanValidation and records human-entered considerations "
            "for population, action, alternatives, benefits, harms/burdens, values/preferences, resources, equity, "
            "acceptability, feasibility, implementation and uncertainty. The generic NutEV worksheet is not GRADE EtD, "
            "does not evaluate recommendation strength, and does not create a validated, clinical, or guideline recommendation."
        ),
    }
