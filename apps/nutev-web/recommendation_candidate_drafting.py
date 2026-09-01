from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Mapping

from evidence_set_construction import (
    CANONICAL_EVIDENCE_SET_RECORD_TYPE,
    _member_snapshot,
    _set_path,
    _set_root,
)
from governed_synthesis_release import DEFAULT_OUTPUT_ROOT, _atomic_json, _digest, _read_json
from synthesis_governance import SynthesisGovernanceError

RECOMMENDATION_DRAFT_TYPE = "NUTEV_RECOMMENDATION_CANDIDATE_DRAFT_V1"
RECOMMENDATION_STATE_TYPE = "NUTEV_RECOMMENDATION_CANDIDATE_STATE_V1"
CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE = (
    "NUTEV_CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_V1"
)
RECOMMENDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_CANDIDATE"
RECOMMENDATION_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_CANDIDATE"
DRAFT = "DRAFT"
FINALIZED = "FINALIZED"
READINESS_NOT_EVALUATED = "not_evaluated"
MAX_EVIDENCE_SETS = 20
STATUS_LIMIT = 200

_RECOMMENDATION_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _recommendation_root(output_root: Path) -> Path:
    return output_root / "scientific" / "recommendation_candidates"


def _draft_path(root: Path, draft_id: str) -> Path:
    return root / "drafts" / f"{draft_id}.json"


def _state_path(root: Path, draft_id: str) -> Path:
    return root / "states" / f"{draft_id}.json"


def _candidate_path(root: Path, candidate_id: str) -> Path:
    return root / "finalized" / f"{candidate_id}.json"


def _record_scientific_content(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in record
        if key not in {"content_sha256", "finalized_at", "artifact_semantics"}
    }


def _draft_scientific_content(draft: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: draft[key]
        for key in draft
        if key not in {"content_sha256", "generated_at", "artifact_semantics"}
    }


def _normalize_evidence_set_ids(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raise SynthesisGovernanceError("RecommendationCandidate evidence_set_ids deve ser lista")
    values = [str(value or "").strip() for value in raw]
    if not values or any(not value for value in values):
        raise SynthesisGovernanceError(
            "RecommendationCandidate exige ao menos um EvidenceSet finalizado"
        )
    if len(values) > MAX_EVIDENCE_SETS:
        raise SynthesisGovernanceError(
            f"RecommendationCandidate suporta no máximo {MAX_EVIDENCE_SETS} EvidenceSets"
        )
    if len(set(values)) != len(values):
        raise SynthesisGovernanceError("RecommendationCandidate não aceita EvidenceSet duplicado")
    return sorted(values)


def _load_finalized_evidence_set(
    evidence_set_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence_set_id = str(evidence_set_id or "").strip()
    if not evidence_set_id:
        raise SynthesisGovernanceError("EvidenceSet id obrigatório")

    root = _set_root(output_root)
    record = _read_json(_set_path(root, evidence_set_id), "canonical EvidenceSet")
    if record.get("evidence_set_record_type") != CANONICAL_EVIDENCE_SET_RECORD_TYPE:
        raise SynthesisGovernanceError("EvidenceSet record type inválido")
    if record.get("canonical") is not True or record.get("human_finalized") is not True:
        raise SynthesisGovernanceError("RecommendationCandidate exige EvidenceSet humano finalizado")

    expected_sha = _digest(_record_scientific_content(record))
    if str(record.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("EvidenceSet content SHA-256 inválido")

    evidence_set = record.get("evidence_set")
    if not isinstance(evidence_set, Mapping):
        raise SynthesisGovernanceError("EvidenceSet payload inválido")
    if str(evidence_set.get("id") or "") != evidence_set_id:
        raise SynthesisGovernanceError("EvidenceSet id diverge do registro canônico")

    claim_ids = [str(value or "").strip() for value in evidence_set.get("claim_ids") or []]
    if not claim_ids or any(not value for value in claim_ids):
        raise SynthesisGovernanceError("EvidenceSet sem claims válidos")

    guardrails = record.get("guardrails")
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("EvidenceSet sem guardrails")
    if guardrails.get("evidence_set_created") is not True:
        raise SynthesisGovernanceError("EvidenceSet não registra criação explícita")
    if guardrails.get("membership_human_curated") is not True:
        raise SynthesisGovernanceError("EvidenceSet não registra membership humana")
    for key in (
        "automatic_claim_grouping_performed",
        "automatic_relation_inference_performed",
        "claim_evaluation_scores_aggregated",
        "consensus_inferred",
        "contradiction_inferred",
        "certainty_assessed",
        "overall_certainty_grade_created",
        "formal_risk_of_bias_assessed",
        "canonical_scientific_synthesis_created",
        "clinical_recommendation_created",
        "meta_analysis_performed",
        "prisma_event_emitted",
        "identity_cryptographically_authenticated",
    ):
        if guardrails.get(key) is not False:
            raise SynthesisGovernanceError(f"EvidenceSet guardrail inválido: {key}")

    stored_members = record.get("member_snapshots")
    if not isinstance(stored_members, list) or len(stored_members) != len(claim_ids):
        raise SynthesisGovernanceError("EvidenceSet member snapshots inválidos")
    stored_by_claim: dict[str, Mapping[str, Any]] = {}
    for raw in stored_members:
        if not isinstance(raw, Mapping):
            raise SynthesisGovernanceError("EvidenceSet member snapshot inválido")
        claim_id = str(raw.get("claim_id") or "").strip()
        if not claim_id or claim_id in stored_by_claim:
            raise SynthesisGovernanceError("EvidenceSet possui member snapshot ausente ou duplicado")
        stored_by_claim[claim_id] = raw
    if set(stored_by_claim) != set(claim_ids):
        raise SynthesisGovernanceError("EvidenceSet member snapshots divergem dos claim ids")

    for claim_id in claim_ids:
        current = _member_snapshot(claim_id, output_root=output_root)
        if _digest(current) != _digest(dict(stored_by_claim[claim_id])):
            raise SynthesisGovernanceError(
                "EvidenceSet não corresponde mais aos EvidenceClaims/ClaimEvaluations/contexto atuais"
            )

    return record, dict(evidence_set)


def _set_snapshot(evidence_set_id: str, *, output_root: Path) -> dict[str, Any]:
    record, evidence_set = _load_finalized_evidence_set(
        evidence_set_id, output_root=output_root
    )
    metadata = evidence_set.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SynthesisGovernanceError("EvidenceSet sem metadata")
    claim_ids = [str(value) for value in evidence_set.get("claim_ids") or []]
    return {
        "evidence_set_id": evidence_set_id,
        "evidence_set_content_sha256": record.get("content_sha256"),
        "name": evidence_set.get("name"),
        "lens": evidence_set.get("lens"),
        "claim_ids": claim_ids,
        "claim_count": len(claim_ids),
        "focus_statement": metadata.get("focus_statement"),
        "scope": metadata.get("scope") or {},
        "curator": metadata.get("curator"),
        "source_context_fingerprint": record.get("source_context_fingerprint"),
        "search_id": record.get("search_id"),
        "context_version": record.get("context_version"),
        "finalized_at": record.get("finalized_at"),
    }


def _build_draft(
    *,
    statement: str,
    rationale: str,
    intended_audience: str,
    intended_context: str,
    evidence_set_ids: list[str],
    output_root: Path,
) -> dict[str, Any]:
    snapshots = [
        _set_snapshot(evidence_set_id, output_root=output_root)
        for evidence_set_id in evidence_set_ids
    ]
    fingerprints = {str(item.get("source_context_fingerprint") or "") for item in snapshots}
    search_ids = {str(item.get("search_id") or "") for item in snapshots}
    context_versions = {str(item.get("context_version") or "") for item in snapshots}
    if "" in fingerprints or len(fingerprints) != 1:
        raise SynthesisGovernanceError(
            "RecommendationCandidate exige EvidenceSets do mesmo context fingerprint"
        )
    if "" in search_ids or len(search_ids) != 1:
        raise SynthesisGovernanceError("RecommendationCandidate exige EvidenceSets do mesmo search id")
    if "" in context_versions or len(context_versions) != 1:
        raise SynthesisGovernanceError(
            "RecommendationCandidate exige EvidenceSets da mesma context version"
        )

    scientific = {
        "draft_type": RECOMMENDATION_DRAFT_TYPE,
        "canonical": False,
        "draft_scope": "HUMAN_AUTHORED_RECOMMENDATION_CANDIDATE_FROM_FINALIZED_EVIDENCE_SETS",
        "statement": statement,
        "rationale": rationale,
        "intended_audience": intended_audience,
        "intended_context": intended_context,
        "evidence_set_ids": evidence_set_ids,
        "evidence_set_snapshots": snapshots,
        "source_context_fingerprint": next(iter(fingerprints)),
        "search_id": next(iter(search_ids)),
        "context_version": next(iter(context_versions)),
        "readiness": READINESS_NOT_EVALUATED,
        "guardrails": {
            "statement_requires_human_authorship": True,
            "automatic_statement_generation_performed": False,
            "automatic_readiness_inference_performed": False,
            "readiness_evaluated": False,
            "evidence_set_agreement_inferred": False,
            "evidence_set_contradiction_inferred": False,
            "evidence_set_scores_aggregated": False,
            "certainty_assessed": False,
            "overall_certainty_grade_created": False,
            "formal_risk_of_bias_assessed": False,
            "recommendation_candidate_created": False,
            "recommendation_validated": False,
            "human_validation_created": False,
            "clinical_recommendation_created": False,
            "canonical_scientific_synthesis_created": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "upstream_evidence_sets_changed": False,
            "single_evidence_set_candidate_is_not_validated_recommendation": True,
            "multiple_evidence_sets_do_not_imply_consensus": True,
            "identity_cryptographically_authenticated": False,
        },
    }
    draft_id = "recommendation_draft_" + _digest(scientific)[:24]
    content = {**scientific, "draft_id": draft_id}
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": _now(),
        "artifact_semantics": (
            "Non-canonical human-authored RecommendationCandidate draft linked to finalized EvidenceSets. "
            "It is not a validated recommendation, certainty assessment, clinical recommendation, or synthesis."
        ),
    }


def stage_recommendation_candidate(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    statement = str(payload.get("statement") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    intended_audience = str(payload.get("intended_audience") or "").strip()
    intended_context = str(payload.get("intended_context") or "").strip()
    staged_by = str(payload.get("staged_by") or "").strip()
    statement_human_authored_confirmed = payload.get("statement_human_authored_confirmed") is True

    if len(statement) < 30:
        raise SynthesisGovernanceError(
            "RecommendationCandidate statement precisa ter pelo menos 30 caracteres"
        )
    if len(rationale) < 30:
        raise SynthesisGovernanceError(
            "RecommendationCandidate rationale precisa ter pelo menos 30 caracteres"
        )
    if len(intended_audience) < 3:
        raise SynthesisGovernanceError("Intended audience precisa ter pelo menos 3 caracteres")
    if len(intended_context) < 10:
        raise SynthesisGovernanceError("Intended context precisa ter pelo menos 10 caracteres")
    if not staged_by:
        raise SynthesisGovernanceError("Identifique quem iniciou o RecommendationCandidate")
    if not statement_human_authored_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que o statement foi escrito por humano e não gerado automaticamente pelo sistema"
        )

    evidence_set_ids = _normalize_evidence_set_ids(payload.get("evidence_set_ids"))
    draft = _build_draft(
        statement=statement,
        rationale=rationale,
        intended_audience=intended_audience,
        intended_context=intended_context,
        evidence_set_ids=evidence_set_ids,
        output_root=output_root,
    )
    draft_id = str(draft.get("draft_id") or "")
    root = _recommendation_root(output_root)
    with _RECOMMENDATION_LOCK:
        draft_path = _draft_path(root, draft_id)
        state_path = _state_path(root, draft_id)
        if draft_path.is_file():
            existing = _read_json(draft_path, "RecommendationCandidate draft")
            if existing.get("content_sha256") != draft.get("content_sha256"):
                raise SynthesisGovernanceError("RecommendationCandidate draft id collision")
        else:
            _atomic_json(draft_path, draft)
        if not state_path.is_file():
            _atomic_json(
                state_path,
                {
                    "state_type": RECOMMENDATION_STATE_TYPE,
                    "draft_id": draft_id,
                    "status": DRAFT,
                    "staged_by": staged_by,
                    "staged_at": _now(),
                    "canonical_recommendation_candidate_id": None,
                    "identity_cryptographically_authenticated": False,
                },
            )
    return recommendation_candidate_status(output_root=output_root)


def _load_draft(
    draft_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    draft_id = str(draft_id or "").strip()
    if not draft_id:
        raise SynthesisGovernanceError("RecommendationCandidate draft id obrigatório")
    root = _recommendation_root(output_root)
    draft = _read_json(_draft_path(root, draft_id), "RecommendationCandidate draft")
    state = _read_json(_state_path(root, draft_id), "RecommendationCandidate state")
    if draft.get("draft_type") != RECOMMENDATION_DRAFT_TYPE or draft.get("canonical") is not False:
        raise SynthesisGovernanceError("RecommendationCandidate draft inválido")
    if state.get("state_type") != RECOMMENDATION_STATE_TYPE or state.get("draft_id") != draft_id:
        raise SynthesisGovernanceError("RecommendationCandidate state inválido")
    expected_sha = _digest(_draft_scientific_content(draft))
    if draft.get("content_sha256") != expected_sha:
        raise SynthesisGovernanceError("RecommendationCandidate draft content SHA-256 inválido")
    return draft, state


def _revalidate_draft(draft: Mapping[str, Any], *, output_root: Path) -> None:
    rebuilt = _build_draft(
        statement=str(draft.get("statement") or ""),
        rationale=str(draft.get("rationale") or ""),
        intended_audience=str(draft.get("intended_audience") or ""),
        intended_context=str(draft.get("intended_context") or ""),
        evidence_set_ids=_normalize_evidence_set_ids(draft.get("evidence_set_ids")),
        output_root=output_root,
    )
    if rebuilt.get("content_sha256") != draft.get("content_sha256"):
        raise SynthesisGovernanceError(
            "RecommendationCandidate draft não corresponde mais aos EvidenceSets/contexto atuais; restage necessário"
        )


def finalize_recommendation_candidate(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    draft_id = str(payload.get("draft_id") or "").strip()
    finalizer = str(payload.get("finalizer") or "").strip()
    finalization_rationale = str(payload.get("finalization_rationale") or "").strip()
    evidence_sets_are_not_certainty_confirmed = (
        payload.get("evidence_sets_are_not_certainty_confirmed") is True
    )
    candidate_is_not_validated_recommendation_confirmed = (
        payload.get("candidate_is_not_validated_recommendation_confirmed") is True
    )
    human_validation_required_confirmed = payload.get("human_validation_required_confirmed") is True

    if not finalizer:
        raise SynthesisGovernanceError("Identifique quem finalizou o RecommendationCandidate")
    if len(finalization_rationale) < 30:
        raise SynthesisGovernanceError(
            "Finalization rationale precisa ter pelo menos 30 caracteres"
        )
    if not evidence_sets_are_not_certainty_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que EvidenceSet membership não equivale a certainty, consensus ou evidence strength"
        )
    if not candidate_is_not_validated_recommendation_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que RecommendationCandidate finalizado ainda não é recomendação validada"
        )
    if not human_validation_required_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que HumanValidation explícita será necessária antes de qualquer recomendação aceita"
        )

    root = _recommendation_root(output_root)
    with _RECOMMENDATION_LOCK:
        draft, state = _load_draft(draft_id, output_root=output_root)
        _revalidate_draft(draft, output_root=output_root)
        if state.get("status") == FINALIZED:
            existing_id = str(state.get("canonical_recommendation_candidate_id") or "")
            if existing_id:
                return recommendation_candidate_status(output_root=output_root)
            raise SynthesisGovernanceError("RecommendationCandidate state final sem candidate id")

        evidence_set_ids = _normalize_evidence_set_ids(draft.get("evidence_set_ids"))
        snapshots = draft.get("evidence_set_snapshots")
        if not isinstance(snapshots, list) or len(snapshots) != len(evidence_set_ids):
            raise SynthesisGovernanceError("RecommendationCandidate EvidenceSet snapshots inválidos")

        scientific = {
            "recommendation_candidate_record_type": CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE,
            "canonical": True,
            "human_finalized": True,
            "source_draft_id": draft_id,
            "source_draft_content_sha256": draft.get("content_sha256"),
            "source_context_fingerprint": draft.get("source_context_fingerprint"),
            "search_id": draft.get("search_id"),
            "context_version": draft.get("context_version"),
            "recommendation_candidate": {
                "id": "pending",
                "statement": draft.get("statement"),
                "evidence_set_ids": evidence_set_ids,
                "readiness": READINESS_NOT_EVALUATED,
                "rationale": draft.get("rationale"),
                "metadata": {
                    "candidate_semantics": "HUMAN_AUTHORED_NOT_YET_VALIDATED_RECOMMENDATION_CANDIDATE",
                    "intended_audience": draft.get("intended_audience"),
                    "intended_context": draft.get("intended_context"),
                    "staged_by": state.get("staged_by"),
                    "finalizer": finalizer,
                    "finalization_rationale": finalization_rationale,
                    "source_evidence_sets": snapshots,
                    "human_entered": True,
                    "identity_cryptographically_authenticated": False,
                },
            },
            "confirmations": {
                "statement_human_authored_confirmed": True,
                "evidence_sets_are_not_certainty_confirmed": True,
                "candidate_is_not_validated_recommendation_confirmed": True,
                "human_validation_required_confirmed": True,
                "human_entered": True,
                "identity_cryptographically_authenticated": False,
            },
            "guardrails": {
                "recommendation_candidate_created": True,
                "automatic_statement_generation_performed": False,
                "automatic_readiness_inference_performed": False,
                "readiness_evaluated": False,
                "recommendation_validated": False,
                "human_validation_created": False,
                "evidence_sets_revalidated_at_finalization": True,
                "evidence_set_agreement_inferred": False,
                "evidence_set_contradiction_inferred": False,
                "evidence_set_scores_aggregated": False,
                "certainty_assessed": False,
                "overall_certainty_grade_created": False,
                "formal_risk_of_bias_assessed": False,
                "clinical_recommendation_created": False,
                "canonical_scientific_synthesis_created": False,
                "meta_analysis_performed": False,
                "prisma_event_emitted": False,
                "upstream_evidence_sets_changed": False,
                "single_evidence_set_candidate_is_not_validated_recommendation": True,
                "multiple_evidence_sets_do_not_imply_consensus": True,
                "identity_cryptographically_authenticated": False,
            },
        }
        candidate_id = "recommendation_candidate_" + _digest(scientific)[:24]
        scientific["recommendation_candidate"]["id"] = candidate_id
        content_sha256 = _digest(scientific)
        record = {
            **scientific,
            "content_sha256": content_sha256,
            "finalized_at": _now(),
            "artifact_semantics": (
                "Canonical NutEV record of a human-authored RecommendationCandidate. Canonical means the "
                "candidate/provenance record is authoritative; it is not a validated or clinical recommendation, "
                "certainty judgment, meta-analysis, or PRISMA output."
            ),
        }
        candidate_path = _candidate_path(root, candidate_id)
        if candidate_path.is_file():
            existing = _read_json(candidate_path, "canonical RecommendationCandidate")
            if existing.get("content_sha256") != content_sha256:
                raise SynthesisGovernanceError("Canonical RecommendationCandidate id collision")
        else:
            _atomic_json(candidate_path, record)
        _atomic_json(
            _state_path(root, draft_id),
            {
                **state,
                "status": FINALIZED,
                "canonical_recommendation_candidate_id": candidate_id,
                "finalized_at": record["finalized_at"],
                "identity_cryptographically_authenticated": False,
            },
        )
    return recommendation_candidate_status(output_root=output_root)


def recommendation_candidate_status(
    *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    root = _recommendation_root(output_root)
    drafts: list[dict[str, Any]] = []
    counts = {DRAFT: 0, FINALIZED: 0}
    states_dir = root / "states"
    with _RECOMMENDATION_LOCK:
        state_paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
        for state_path in state_paths:
            try:
                state = _read_json(state_path, state_path.name)
                draft_id = str(state.get("draft_id") or "")
                draft = _read_json(_draft_path(root, draft_id), "RecommendationCandidate draft")
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            status = str(state.get("status") or DRAFT)
            if status in counts:
                counts[status] += 1
            drafts.append(
                {
                    "draft_id": draft_id,
                    "status": status,
                    "statement": draft.get("statement"),
                    "rationale": draft.get("rationale"),
                    "intended_audience": draft.get("intended_audience"),
                    "intended_context": draft.get("intended_context"),
                    "evidence_set_ids": draft.get("evidence_set_ids") or [],
                    "evidence_set_count": len(draft.get("evidence_set_ids") or []),
                    "readiness": draft.get("readiness"),
                    "source_context_fingerprint": draft.get("source_context_fingerprint"),
                    "search_id": draft.get("search_id"),
                    "context_version": draft.get("context_version"),
                    "staged_by": state.get("staged_by"),
                    "canonical_recommendation_candidate_id": state.get(
                        "canonical_recommendation_candidate_id"
                    ),
                }
            )

    finalized: list[dict[str, Any]] = []
    set_index: dict[str, list[str]] = {}
    finalized_dir = root / "finalized"
    if finalized_dir.is_dir():
        for path in sorted(finalized_dir.glob("*.json")):
            try:
                record = _read_json(path, path.name)
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            if (
                record.get("recommendation_candidate_record_type")
                != CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE
            ):
                continue
            candidate = record.get("recommendation_candidate")
            if not isinstance(candidate, Mapping):
                continue
            candidate_id = str(candidate.get("id") or "")
            evidence_set_ids = [str(value) for value in candidate.get("evidence_set_ids") or []]
            for evidence_set_id in evidence_set_ids:
                set_index.setdefault(evidence_set_id, []).append(candidate_id)
            metadata = candidate.get("metadata")
            finalized.append(
                {
                    "recommendation_candidate_id": candidate_id,
                    "statement": candidate.get("statement"),
                    "evidence_set_ids": evidence_set_ids,
                    "evidence_set_count": len(evidence_set_ids),
                    "readiness": candidate.get("readiness"),
                    "rationale": candidate.get("rationale"),
                    "intended_audience": metadata.get("intended_audience")
                    if isinstance(metadata, Mapping)
                    else None,
                    "intended_context": metadata.get("intended_context")
                    if isinstance(metadata, Mapping)
                    else None,
                    "finalizer": metadata.get("finalizer") if isinstance(metadata, Mapping) else None,
                    "finalized_at": record.get("finalized_at"),
                    "canonical": record.get("canonical"),
                    "recommendation_validated": bool(
                        (record.get("guardrails") or {}).get("recommendation_validated")
                    ),
                    "clinical_recommendation_created": bool(
                        (record.get("guardrails") or {}).get("clinical_recommendation_created")
                    ),
                }
            )
    for values in set_index.values():
        values.sort()
    drafts.sort(key=lambda item: str(item.get("draft_id") or ""))
    finalized.sort(key=lambda item: str(item.get("finalized_at") or ""), reverse=True)
    return {
        "status": "READY",
        "draft_type": RECOMMENDATION_DRAFT_TYPE,
        "canonical_recommendation_candidate_record_type": (
            CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_TYPE
        ),
        "readiness_default": READINESS_NOT_EVALUATED,
        "draft_count": len(drafts),
        "draft_counts": counts,
        "drafts": drafts[:STATUS_LIMIT],
        "draft_list_truncated": len(drafts) > STATUS_LIMIT,
        "finalized_recommendation_candidate_count": len(finalized),
        "finalized_recommendation_candidates": finalized[:STATUS_LIMIT],
        "finalized_recommendation_candidate_list_truncated": len(finalized) > STATUS_LIMIT,
        "evidence_set_candidate_index": set_index,
        "max_evidence_sets": MAX_EVIDENCE_SETS,
        "scientific_boundary": (
            "RecommendationCandidate is a human-authored candidate statement linked to finalized EvidenceSets. "
            "Finalization does not validate the recommendation, assess readiness/certainty, infer consensus, "
            "create a clinical recommendation, perform meta-analysis, or emit PRISMA state."
        ),
    }
