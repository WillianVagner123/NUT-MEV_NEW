from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Mapping

from governed_synthesis_release import DEFAULT_OUTPUT_ROOT, _atomic_json, _digest, _read_json
from recommendation_development import (
    CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE,
    DEVELOPMENT_METHOD,
    STRENGTH_NOT_EVALUATED,
    _development_root,
    _draft_path as _development_draft_path,
    _record_path as _development_record_path,
    _revalidate_draft,
    _scientific_content as _development_scientific_content,
)
from synthesis_governance import SynthesisGovernanceError

ADOPTION_CASE_TYPE = "NUTEV_RECOMMENDATION_ADOPTION_CASE_V1"
ADOPTION_STATE_TYPE = "NUTEV_RECOMMENDATION_ADOPTION_STATE_V1"
CANONICAL_RECOMMENDATION_ADOPTION_RECORD_TYPE = "NUTEV_CANONICAL_RECOMMENDATION_ADOPTION_RECORD_V1"
ADOPTION_STAGE_OPERATION = "STAGE_RECOMMENDATION_ADOPTION"
ADOPTION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_ADOPTION"
PENDING = "PENDING"
ADOPT_FOR_DEFINED_SCOPE = "ADOPT_FOR_DEFINED_SCOPE"
REJECT = "REJECT"
RETURN_FOR_REVISION = "RETURN_FOR_REVISION"
DECISIONS = {ADOPT_FOR_DEFINED_SCOPE, REJECT, RETURN_FOR_REVISION}
MODEL_DECISIONS = {
    ADOPT_FOR_DEFINED_SCOPE: "adopt_for_defined_scope",
    REJECT: "reject",
    RETURN_FOR_REVISION: "return_for_revision",
}
STATUS_LIMIT = 200

_ADOPTION_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _adoption_root(output_root: Path) -> Path:
    return output_root / "scientific" / "recommendation_adoptions"


def _case_path(root: Path, adoption_id: str) -> Path:
    return root / "cases" / f"{adoption_id}.json"


def _state_path(root: Path, adoption_id: str) -> Path:
    return root / "states" / f"{adoption_id}.json"


def _record_path(root: Path, adoption_id: str) -> Path:
    return root / "finalized" / f"{adoption_id}.json"


def _scientific_content(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in record
        if key not in {"content_sha256", "generated_at", "decided_at", "artifact_semantics"}
    }


def _load_finalized_development(
    development_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    development_id = str(development_id or "").strip()
    if not development_id:
        raise SynthesisGovernanceError("Recommendation Development id obrigatório")

    root = _development_root(output_root)
    record = _read_json(
        _development_record_path(root, development_id), "canonical Recommendation Development"
    )
    if (
        record.get("recommendation_development_record_type")
        != CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_TYPE
    ):
        raise SynthesisGovernanceError("Recommendation Development record type inválido")
    if record.get("canonical") is not True or record.get("human_finalized") is not True:
        raise SynthesisGovernanceError(
            "Recommendation Adoption exige Recommendation Development canônico e finalizado"
        )
    if record.get("method") != DEVELOPMENT_METHOD:
        raise SynthesisGovernanceError("Recommendation Development method inválido")

    expected_sha = _digest(_development_scientific_content(record))
    if str(record.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("Recommendation Development content SHA-256 inválido")

    development = record.get("development")
    if not isinstance(development, Mapping):
        raise SynthesisGovernanceError("Recommendation Development payload inválido")
    if str(development.get("recommendation_strength") or "") != STRENGTH_NOT_EVALUATED:
        raise SynthesisGovernanceError(
            "Recommendation Development strength foi alterado fora do contrato da Fase 21"
        )

    guardrails = record.get("guardrails")
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("Recommendation Development sem guardrails")
    for key in (
        "source_human_validation_accept_revalidated",
        "source_candidate_revalidated",
        "recommendation_development_record_created",
    ):
        if guardrails.get(key) is not True:
            raise SynthesisGovernanceError(f"Recommendation Development guardrail inválido: {key}")
    for key in (
        "automatic_recommendation_generation_performed",
        "candidate_statement_auto_promoted",
        "recommendation_strength_evaluated",
        "formal_etd_framework_applied",
        "grade_etd_applied",
        "certainty_assessed",
        "grade_assessed",
        "formal_risk_of_bias_assessed",
        "formal_benefit_harm_balance_determined",
        "values_preferences_formally_assessed",
        "resource_use_formally_assessed",
        "equity_formally_assessed",
        "acceptability_formally_assessed",
        "feasibility_formally_assessed",
        "validated_recommendation_created",
        "clinical_recommendation_created",
        "guideline_recommendation_created",
        "canonical_scientific_synthesis_created",
        "meta_analysis_performed",
        "prisma_event_emitted",
        "source_human_validation_changed",
        "source_recommendation_candidate_changed",
        "identity_cryptographically_authenticated",
    ):
        if guardrails.get(key) is not False:
            raise SynthesisGovernanceError(f"Recommendation Development guardrail inválido: {key}")

    draft = _read_json(
        _development_draft_path(root, development_id), "Recommendation Development source draft"
    )
    if str(record.get("source_draft_content_sha256") or "") != str(
        draft.get("content_sha256") or ""
    ):
        raise SynthesisGovernanceError("Recommendation Development source draft SHA divergiu")
    _revalidate_draft(draft, output_root=output_root)

    for key in (
        "source_human_validation_id",
        "source_human_validation_content_sha256",
        "source_recommendation_candidate_id",
        "source_recommendation_candidate_content_sha256",
        "source_context_fingerprint",
        "search_id",
        "context_version",
    ):
        if record.get(key) != draft.get(key):
            raise SynthesisGovernanceError(
                f"Recommendation Development diverge do source draft em {key}"
            )
    if _digest(record.get("source_snapshot")) != _digest(draft.get("source_snapshot")):
        raise SynthesisGovernanceError("Recommendation Development source snapshot divergiu")

    return record, dict(development)


def _development_snapshot(development_id: str, *, output_root: Path) -> dict[str, Any]:
    record, development = _load_finalized_development(development_id, output_root=output_root)
    return {
        "recommendation_development_id": development_id,
        "recommendation_development_content_sha256": record.get("content_sha256"),
        "method": record.get("method"),
        "proposed_recommendation_text": development.get("proposed_recommendation_text"),
        "population_scope": development.get("population_scope"),
        "intervention_or_action": development.get("intervention_or_action"),
        "comparator_or_alternative": development.get("comparator_or_alternative"),
        "recommendation_strength": development.get("recommendation_strength"),
        "source_human_validation_id": record.get("source_human_validation_id"),
        "source_recommendation_candidate_id": record.get("source_recommendation_candidate_id"),
        "source_context_fingerprint": record.get("source_context_fingerprint"),
        "search_id": record.get("search_id"),
        "context_version": record.get("context_version"),
        "finalized_at": record.get("finalized_at"),
    }


def _adoption_id(development_id: str) -> str:
    return "recommendation_adoption_" + _digest(
        {"target_type": "RecommendationDevelopment", "target_id": development_id}
    )[:24]


def stage_recommendation_adoption(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    development_id = str(payload.get("recommendation_development_id") or "").strip()
    staged_by = str(payload.get("staged_by") or "").strip()
    adoption_scope = str(payload.get("adoption_scope") or "").strip()
    governance_purpose = str(payload.get("governance_purpose") or "").strip()

    if not development_id:
        raise SynthesisGovernanceError("Recommendation Development id obrigatório")
    if not staged_by:
        raise SynthesisGovernanceError("Identifique quem abriu o Recommendation Adoption case")
    if len(adoption_scope) < 30:
        raise SynthesisGovernanceError("Adoption scope precisa ter pelo menos 30 caracteres")
    if len(governance_purpose) < 30:
        raise SynthesisGovernanceError("Governance purpose precisa ter pelo menos 30 caracteres")

    snapshot = _development_snapshot(development_id, output_root=output_root)
    adoption_id = _adoption_id(development_id)
    scientific = {
        "adoption_case_type": ADOPTION_CASE_TYPE,
        "canonical": False,
        "adoption_id": adoption_id,
        "target_type": "RecommendationDevelopment",
        "target_id": development_id,
        "decision": "pending",
        "adoption_scope": adoption_scope,
        "governance_purpose": governance_purpose,
        "source_development": snapshot,
        "source_development_content_sha256": snapshot[
            "recommendation_development_content_sha256"
        ],
        "source_context_fingerprint": snapshot["source_context_fingerprint"],
        "search_id": snapshot["search_id"],
        "context_version": snapshot["context_version"],
        "guardrails": {
            "human_adoption_pending": True,
            "automatic_adoption_decision_performed": False,
            "recommendation_strength_evaluated": False,
            "certainty_assessed": False,
            "grade_assessed": False,
            "formal_etd_framework_applied": False,
            "grade_etd_applied": False,
            "validated_recommendation_created": False,
            "clinical_recommendation_created": False,
            "guideline_recommendation_created": False,
            "universal_recommendation_created": False,
            "canonical_scientific_synthesis_created": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "source_recommendation_development_changed": False,
            "identity_cryptographically_authenticated": False,
        },
    }
    case = {
        **scientific,
        "content_sha256": _digest(scientific),
        "generated_at": _now(),
        "artifact_semantics": (
            "Pending human governance case for one finalized Recommendation Development record. "
            "PENDING is not adoption, recommendation strength, certainty, guideline status, or clinical recommendation."
        ),
    }

    root = _adoption_root(output_root)
    with _ADOPTION_LOCK:
        case_path = _case_path(root, adoption_id)
        state_path = _state_path(root, adoption_id)
        if case_path.is_file():
            existing = _read_json(case_path, "Recommendation Adoption case")
            if existing.get("content_sha256") != case.get("content_sha256"):
                raise SynthesisGovernanceError(
                    "Recommendation Adoption deste development já existe com scope/purpose diferente"
                )
        else:
            _atomic_json(case_path, case)
        if not state_path.is_file():
            _atomic_json(
                state_path,
                {
                    "state_type": ADOPTION_STATE_TYPE,
                    "adoption_id": adoption_id,
                    "target_id": development_id,
                    "status": PENDING,
                    "staged_by": staged_by,
                    "staged_at": _now(),
                    "canonical_recommendation_adoption_id": None,
                    "identity_cryptographically_authenticated": False,
                },
            )
    return recommendation_adoption_status(output_root=output_root)


def _load_case(
    adoption_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    adoption_id = str(adoption_id or "").strip()
    if not adoption_id:
        raise SynthesisGovernanceError("Recommendation Adoption id obrigatório")
    root = _adoption_root(output_root)
    case = _read_json(_case_path(root, adoption_id), "Recommendation Adoption case")
    state = _read_json(_state_path(root, adoption_id), "Recommendation Adoption state")
    if case.get("adoption_case_type") != ADOPTION_CASE_TYPE or case.get("canonical") is not False:
        raise SynthesisGovernanceError("Recommendation Adoption case inválido")
    if state.get("state_type") != ADOPTION_STATE_TYPE or state.get("adoption_id") != adoption_id:
        raise SynthesisGovernanceError("Recommendation Adoption state inválido")
    if case.get("content_sha256") != _digest(_scientific_content(case)):
        raise SynthesisGovernanceError("Recommendation Adoption case content SHA-256 inválido")
    return case, state


def _revalidate_case(case: Mapping[str, Any], *, output_root: Path) -> None:
    development_id = str(case.get("target_id") or "")
    current = _development_snapshot(development_id, output_root=output_root)
    stored = case.get("source_development")
    if not isinstance(stored, Mapping):
        raise SynthesisGovernanceError("Recommendation Adoption sem source development snapshot")
    if _digest(current) != _digest(dict(stored)):
        raise SynthesisGovernanceError(
            "Recommendation Adoption não corresponde mais ao development/upstream/contexto atuais; restage necessário"
        )
    if str(case.get("source_development_content_sha256") or "") != str(
        current.get("recommendation_development_content_sha256") or ""
    ):
        raise SynthesisGovernanceError("Recommendation Adoption source development SHA divergiu")


def _normalize_decision(raw: Any) -> str:
    decision = str(raw or "").strip().upper()
    if decision not in DECISIONS:
        raise SynthesisGovernanceError(
            "Recommendation Adoption decision deve ser ADOPT_FOR_DEFINED_SCOPE, REJECT ou RETURN_FOR_REVISION"
        )
    return decision


def decide_recommendation_adoption(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    adoption_id = str(payload.get("adoption_id") or "").strip()
    decision = _normalize_decision(payload.get("decision"))
    governor = str(payload.get("governor") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    revision_instructions = str(payload.get("revision_instructions") or "").strip()

    if not governor:
        raise SynthesisGovernanceError("Identifique o governor responsável pela decisão")
    if len(rationale) < 50:
        raise SynthesisGovernanceError("Recommendation Adoption rationale precisa ter pelo menos 50 caracteres")
    if decision == RETURN_FOR_REVISION and len(revision_instructions) < 25:
        raise SynthesisGovernanceError(
            "RETURN_FOR_REVISION exige revision instructions com pelo menos 25 caracteres"
        )
    if decision != RETURN_FOR_REVISION and revision_instructions:
        raise SynthesisGovernanceError(
            "Revision instructions só são permitidas para RETURN_FOR_REVISION"
        )

    confirmations = {
        "decision_human_entered_confirmed": payload.get("decision_human_entered_confirmed") is True,
        "defined_scope_only_confirmed": payload.get("defined_scope_only_confirmed") is True,
        "no_strength_or_certainty_inference_confirmed": (
            payload.get("no_strength_or_certainty_inference_confirmed") is True
        ),
        "not_clinical_or_guideline_recommendation_confirmed": (
            payload.get("not_clinical_or_guideline_recommendation_confirmed") is True
        ),
        "upstream_immutable_confirmed": payload.get("upstream_immutable_confirmed") is True,
    }
    if not confirmations["decision_human_entered_confirmed"]:
        raise SynthesisGovernanceError("Confirme que a decisão foi inserida explicitamente por humano")
    if not confirmations["defined_scope_only_confirmed"]:
        raise SynthesisGovernanceError(
            "Confirme que eventual ADOPT vale apenas para o adoption scope declarado"
        )
    if not confirmations["no_strength_or_certainty_inference_confirmed"]:
        raise SynthesisGovernanceError(
            "Confirme que a decisão não infere recommendation strength, certainty ou GRADE"
        )
    if not confirmations["not_clinical_or_guideline_recommendation_confirmed"]:
        raise SynthesisGovernanceError(
            "Confirme que a decisão não cria clinical/guideline recommendation automaticamente"
        )
    if not confirmations["upstream_immutable_confirmed"]:
        raise SynthesisGovernanceError(
            "Confirme que Recommendation Development e upstream permanecem imutáveis"
        )

    root = _adoption_root(output_root)
    with _ADOPTION_LOCK:
        case, state = _load_case(adoption_id, output_root=output_root)
        _revalidate_case(case, output_root=output_root)

        if state.get("status") != PENDING:
            record = _read_json(_record_path(root, adoption_id), "canonical Recommendation Adoption")
            adoption = record.get("recommendation_adoption")
            if isinstance(adoption, Mapping):
                metadata = adoption.get("metadata")
                same = (
                    str(adoption.get("decision") or "") == MODEL_DECISIONS[decision]
                    and str(adoption.get("governor") or "") == governor
                    and str(adoption.get("rationale") or "") == rationale
                    and str(metadata.get("revision_instructions") or "")
                    == revision_instructions
                    if isinstance(metadata, Mapping)
                    else False
                )
                if same:
                    return recommendation_adoption_status(output_root=output_root)
            raise SynthesisGovernanceError(
                "Recommendation Adoption já possui decisão canônica; decisão conflitante não pode sobrescrevê-la"
            )

        current = _development_snapshot(str(case.get("target_id") or ""), output_root=output_root)
        decided_at = _now()
        model_decision = MODEL_DECISIONS[decision]
        adopted = decision == ADOPT_FOR_DEFINED_SCOPE
        scientific = {
            "recommendation_adoption_record_type": CANONICAL_RECOMMENDATION_ADOPTION_RECORD_TYPE,
            "canonical": True,
            "human_finalized": True,
            "adoption_id": adoption_id,
            "target_type": "RecommendationDevelopment",
            "target_id": case.get("target_id"),
            "source_case_content_sha256": case.get("content_sha256"),
            "source_development_content_sha256": current.get(
                "recommendation_development_content_sha256"
            ),
            "source_context_fingerprint": current.get("source_context_fingerprint"),
            "search_id": current.get("search_id"),
            "context_version": current.get("context_version"),
            "recommendation_adoption": {
                "id": adoption_id,
                "decision": model_decision,
                "governor": governor,
                "rationale": rationale,
                "adoption_scope": case.get("adoption_scope"),
                "governance_purpose": case.get("governance_purpose"),
                "recommendation_strength": STRENGTH_NOT_EVALUATED,
                "decided_at": decided_at,
                "metadata": {
                    "revision_instructions": revision_instructions or None,
                    "adopted_for_defined_scope": adopted,
                    "human_entered": True,
                    "identity_cryptographically_authenticated": False,
                },
            },
            "source_development": current,
            "confirmations": {
                **confirmations,
                "human_entered": True,
                "identity_cryptographically_authenticated": False,
            },
            "guardrails": {
                "recommendation_adoption_record_created": True,
                "source_recommendation_development_revalidated": True,
                "adopted_for_defined_scope": adopted,
                "automatic_adoption_decision_performed": False,
                "automatic_revision_applied": False,
                "recommendation_strength_evaluated": False,
                "certainty_assessed": False,
                "grade_assessed": False,
                "formal_etd_framework_applied": False,
                "grade_etd_applied": False,
                "formal_risk_of_bias_assessed": False,
                "validated_recommendation_created": False,
                "clinical_recommendation_created": False,
                "guideline_recommendation_created": False,
                "universal_recommendation_created": False,
                "canonical_scientific_synthesis_created": False,
                "meta_analysis_performed": False,
                "prisma_event_emitted": False,
                "source_recommendation_development_changed": False,
                "identity_cryptographically_authenticated": False,
            },
        }
        record = {
            **scientific,
            "content_sha256": _digest(scientific),
            "decided_at": decided_at,
            "artifact_semantics": (
                "Canonical NutEV governance record of one explicit human adoption decision about a finalized "
                "Recommendation Development worksheet. ADOPT_FOR_DEFINED_SCOPE means adoption only for the declared "
                "scope; it does not evaluate recommendation strength/certainty and does not create a universal, "
                "clinical, or guideline recommendation."
            ),
        }
        record_path = _record_path(root, adoption_id)
        if record_path.is_file():
            existing = _read_json(record_path, "canonical Recommendation Adoption")
            if existing.get("content_sha256") != record.get("content_sha256"):
                raise SynthesisGovernanceError("Canonical Recommendation Adoption id collision")
        else:
            _atomic_json(record_path, record)
        _atomic_json(
            _state_path(root, adoption_id),
            {
                **state,
                "status": decision,
                "decision": model_decision,
                "canonical_recommendation_adoption_id": adoption_id,
                "decided_at": decided_at,
                "identity_cryptographically_authenticated": False,
            },
        )
    return recommendation_adoption_status(output_root=output_root)


def recommendation_adoption_status(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    root = _adoption_root(output_root)
    counts = {
        PENDING: 0,
        ADOPT_FOR_DEFINED_SCOPE: 0,
        REJECT: 0,
        RETURN_FOR_REVISION: 0,
    }
    cases: list[dict[str, Any]] = []
    development_index: dict[str, dict[str, Any]] = {}

    states_dir = root / "states"
    with _ADOPTION_LOCK:
        state_paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
        for state_path in state_paths:
            try:
                state = _read_json(state_path, state_path.name)
                adoption_id = str(state.get("adoption_id") or "")
                case = _read_json(_case_path(root, adoption_id), "Recommendation Adoption case")
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            status = str(state.get("status") or PENDING)
            if status in counts:
                counts[status] += 1
            source = case.get("source_development")
            development_id = str(case.get("target_id") or "")
            cases.append(
                {
                    "adoption_id": adoption_id,
                    "status": status,
                    "decision": state.get("decision") or "pending",
                    "recommendation_development_id": development_id,
                    "proposed_recommendation_text": source.get("proposed_recommendation_text")
                    if isinstance(source, Mapping)
                    else None,
                    "population_scope": source.get("population_scope")
                    if isinstance(source, Mapping)
                    else None,
                    "recommendation_strength": STRENGTH_NOT_EVALUATED,
                    "adoption_scope": case.get("adoption_scope"),
                    "governance_purpose": case.get("governance_purpose"),
                    "staged_by": state.get("staged_by"),
                    "staged_at": state.get("staged_at"),
                    "decided_at": state.get("decided_at"),
                }
            )
            development_index[development_id] = {
                "adoption_id": adoption_id,
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
            if (
                record.get("recommendation_adoption_record_type")
                != CANONICAL_RECOMMENDATION_ADOPTION_RECORD_TYPE
            ):
                continue
            adoption = record.get("recommendation_adoption")
            if not isinstance(adoption, Mapping):
                continue
            metadata = adoption.get("metadata")
            finalized.append(
                {
                    "adoption_id": adoption.get("id"),
                    "recommendation_development_id": record.get("target_id"),
                    "decision": adoption.get("decision"),
                    "governor": adoption.get("governor"),
                    "rationale": adoption.get("rationale"),
                    "adoption_scope": adoption.get("adoption_scope"),
                    "recommendation_strength": adoption.get("recommendation_strength"),
                    "revision_instructions": metadata.get("revision_instructions")
                    if isinstance(metadata, Mapping)
                    else None,
                    "adopted_for_defined_scope": bool(
                        (record.get("guardrails") or {}).get("adopted_for_defined_scope")
                    ),
                    "clinical_recommendation_created": bool(
                        (record.get("guardrails") or {}).get("clinical_recommendation_created")
                    ),
                    "guideline_recommendation_created": bool(
                        (record.get("guardrails") or {}).get("guideline_recommendation_created")
                    ),
                    "certainty_assessed": bool(
                        (record.get("guardrails") or {}).get("certainty_assessed")
                    ),
                    "decided_at": record.get("decided_at"),
                    "canonical": record.get("canonical"),
                }
            )

    cases.sort(key=lambda item: str(item.get("staged_at") or ""), reverse=True)
    finalized.sort(key=lambda item: str(item.get("decided_at") or ""), reverse=True)
    return {
        "status": "READY",
        "adoption_case_type": ADOPTION_CASE_TYPE,
        "canonical_recommendation_adoption_record_type": (
            CANONICAL_RECOMMENDATION_ADOPTION_RECORD_TYPE
        ),
        "decision_options": [ADOPT_FOR_DEFINED_SCOPE, REJECT, RETURN_FOR_REVISION],
        "recommendation_strength_default": STRENGTH_NOT_EVALUATED,
        "counts": counts,
        "case_count": len(cases),
        "cases": cases[:STATUS_LIMIT],
        "case_list_truncated": len(cases) > STATUS_LIMIT,
        "finalized_adoption_count": len(finalized),
        "finalized_adoptions": finalized[:STATUS_LIMIT],
        "finalized_adoption_list_truncated": len(finalized) > STATUS_LIMIT,
        "development_adoption_index": development_index,
        "scientific_boundary": (
            "Recommendation Adoption is a human governance decision over a finalized Recommendation Development "
            "record. ADOPT_FOR_DEFINED_SCOPE means adopted only for the declared scope. It does not evaluate or "
            "assign recommendation strength/certainty, does not apply GRADE EtD, and does not create a universal, "
            "clinical, or guideline recommendation, canonical scientific synthesis, meta-analysis, or PRISMA event."
        ),
    }
