from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Mapping

from claim_evaluation_appraisal import (
    CANONICAL_EVALUATION_RECORD_TYPE,
    _evaluation_root,
    _load_accepted_claim,
)
from governed_synthesis_release import DEFAULT_OUTPUT_ROOT, _atomic_json, _digest, _read_json
from synthesis_governance import SynthesisGovernanceError

EVIDENCE_SET_DRAFT_TYPE = "NUTEV_EVIDENCE_SET_CONSTRUCTION_DRAFT_V1"
EVIDENCE_SET_STATE_TYPE = "NUTEV_EVIDENCE_SET_CONSTRUCTION_STATE_V1"
CANONICAL_EVIDENCE_SET_RECORD_TYPE = "NUTEV_CANONICAL_EVIDENCE_SET_RECORD_V1"
EVIDENCE_SET_STAGE_OPERATION = "STAGE_EVIDENCE_SET"
EVIDENCE_SET_FINALIZE_OPERATION = "FINALIZE_EVIDENCE_SET"
DRAFT = "DRAFT"
FINALIZED = "FINALIZED"
STATUS_LIMIT = 200
MAX_MEMBERS = 100

SCOPE_FIELDS = (
    "domain",
    "population",
    "intervention_or_exposure",
    "comparator",
    "outcome",
    "timeframe",
    "context",
)

_SET_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_root(output_root: Path) -> Path:
    return output_root / "scientific" / "evidence_sets"


def _draft_path(root: Path, draft_id: str) -> Path:
    return root / "drafts" / f"{draft_id}.json"


def _state_path(root: Path, draft_id: str) -> Path:
    return root / "states" / f"{draft_id}.json"


def _set_path(root: Path, evidence_set_id: str) -> Path:
    return root / "finalized" / f"{evidence_set_id}.json"


def _evaluation_scientific_content(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in record
        if key not in {"content_sha256", "evaluated_at", "artifact_semantics"}
    }


def _draft_scientific_content(draft: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: draft[key]
        for key in draft
        if key not in {"content_sha256", "generated_at", "artifact_semantics"}
    }


def _normalize_scope(raw: Any) -> dict[str, str]:
    if raw in (None, ""):
        return {key: "" for key in SCOPE_FIELDS}
    if not isinstance(raw, Mapping):
        raise SynthesisGovernanceError("EvidenceSet scope deve ser objeto")
    extra = sorted({str(key) for key in raw} - set(SCOPE_FIELDS))
    if extra:
        raise SynthesisGovernanceError(f"EvidenceSet scope contém campos não suportados: {extra}")
    scope: dict[str, str] = {}
    for key in SCOPE_FIELDS:
        value = str(raw.get(key) or "").strip()
        if len(value) > 500:
            raise SynthesisGovernanceError(f"EvidenceSet scope {key} excede 500 caracteres")
        scope[key] = value
    return scope


def _evaluation_for_claim(
    claim_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = _evaluation_root(output_root)
    finalized_dir = root / "finalized"
    matches: list[dict[str, Any]] = []
    if finalized_dir.is_dir():
        for path in sorted(finalized_dir.glob("*.json")):
            try:
                record = _read_json(path, path.name)
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            if record.get("evaluation_record_type") != CANONICAL_EVALUATION_RECORD_TYPE:
                continue
            evaluation = record.get("claim_evaluation")
            if isinstance(evaluation, Mapping) and str(evaluation.get("claim_id") or "") == claim_id:
                matches.append(record)
    if not matches:
        raise SynthesisGovernanceError(
            f"EvidenceClaim {claim_id} não possui ClaimEvaluation finalizada"
        )
    if len(matches) != 1:
        raise SynthesisGovernanceError(
            f"EvidenceClaim {claim_id} possui múltiplas ClaimEvaluations canônicas; resolução explícita necessária"
        )

    record = matches[0]
    if record.get("canonical") is not True or record.get("human_finalized") is not True:
        raise SynthesisGovernanceError("ClaimEvaluation não está finalizada como registro canônico")
    expected_sha = _digest(_evaluation_scientific_content(record))
    if str(record.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("ClaimEvaluation content SHA-256 inválido")

    evaluation = record.get("claim_evaluation")
    if not isinstance(evaluation, Mapping):
        raise SynthesisGovernanceError("ClaimEvaluation payload inválido")
    evaluation_id = str(evaluation.get("id") or "").strip()
    if not evaluation_id:
        raise SynthesisGovernanceError("ClaimEvaluation sem id")

    guardrails = record.get("guardrails")
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("ClaimEvaluation sem guardrails")
    if guardrails.get("claim_evaluation_created") is not True:
        raise SynthesisGovernanceError("ClaimEvaluation não registra criação explícita")
    for key in (
        "formal_risk_of_bias_assessed",
        "risk_of_bias_assessed",
        "study_validity_determined",
        "certainty_assessed",
        "overall_certainty_grade_created",
        "numeric_appraisal_score_created",
        "automatic_dimension_aggregation_performed",
        "formal_external_instrument_applied",
        "evidence_set_created",
        "canonical_scientific_synthesis_created",
        "clinical_recommendation_created",
        "screening_eligibility_changed",
        "accepted_claim_statement_changed",
        "accepted_claim_status_changed",
        "meta_analysis_performed",
        "prisma_event_emitted",
        "identity_cryptographically_authenticated",
    ):
        if guardrails.get(key) is not False:
            raise SynthesisGovernanceError(f"ClaimEvaluation guardrail inválido: {key}")
    return record, dict(evaluation)


def _member_snapshot(claim_id: str, *, output_root: Path) -> dict[str, Any]:
    claim_record, claim, source_candidate, evidence_record = _load_accepted_claim(
        claim_id, output_root=output_root
    )
    evaluation_record, evaluation = _evaluation_for_claim(claim_id, output_root=output_root)

    if str(evaluation_record.get("source_claim_content_sha256") or "") != str(
        claim_record.get("content_sha256") or ""
    ):
        raise SynthesisGovernanceError("ClaimEvaluation diverge do EvidenceClaim content SHA-256")
    if str(evaluation_record.get("source_context_fingerprint") or "") != str(
        source_candidate.get("source_context_fingerprint") or ""
    ):
        raise SynthesisGovernanceError("ClaimEvaluation diverge do contexto do EvidenceClaim")

    metadata = claim.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SynthesisGovernanceError("EvidenceClaim sem metadata")
    source_snapshot = source_candidate.get("source_snapshot")
    if not isinstance(source_snapshot, Mapping):
        raise SynthesisGovernanceError("EvidenceClaim source candidate sem snapshot")
    dimensions = evaluation.get("dimensions")
    if not isinstance(dimensions, Mapping) or not dimensions:
        raise SynthesisGovernanceError("ClaimEvaluation sem dimensions")

    return {
        "claim_id": claim_id,
        "claim_content_sha256": claim_record.get("content_sha256"),
        "evaluation_id": evaluation.get("id"),
        "evaluation_content_sha256": evaluation_record.get("content_sha256"),
        "evidence_record_id": claim.get("evidence_record_id"),
        "document_id": evidence_record.get("document_id"),
        "source_context_fingerprint": source_candidate.get("source_context_fingerprint"),
        "search_id": source_candidate.get("search_id"),
        "context_version": source_candidate.get("context_version"),
        "statement": claim.get("statement"),
        "population": claim.get("population"),
        "intervention_or_exposure": claim.get("intervention_or_exposure"),
        "comparator": claim.get("comparator"),
        "outcome": claim.get("outcome"),
        "evidence_type": claim.get("evidence_type"),
        "source": {
            "title": source_snapshot.get("title"),
            "citation_id": source_snapshot.get("citation_id"),
            "bundle_id": source_snapshot.get("bundle_id"),
            "source_sentence_sha256": source_snapshot.get("source_sentence_sha256"),
            "source_reference": source_snapshot.get("source_reference"),
        },
        "claim_evaluation": {
            "assessor": evaluation.get("assessor"),
            "rationale": evaluation.get("rationale"),
            "dimensions": dict(dimensions),
            "assessment_basis": evaluation_record.get("assessment_basis"),
            "evaluated_at": evaluation_record.get("evaluated_at"),
        },
    }


def _normalize_claim_ids(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raise SynthesisGovernanceError("EvidenceSet claim_ids deve ser lista")
    claim_ids = [str(value or "").strip() for value in raw]
    if not claim_ids or any(not value for value in claim_ids):
        raise SynthesisGovernanceError("EvidenceSet exige ao menos um EvidenceClaim válido")
    if len(claim_ids) > MAX_MEMBERS:
        raise SynthesisGovernanceError(f"EvidenceSet suporta no máximo {MAX_MEMBERS} claims por set")
    if len(set(claim_ids)) != len(claim_ids):
        raise SynthesisGovernanceError("EvidenceSet não aceita claim duplicado no mesmo set")
    return sorted(claim_ids)


def _build_draft(
    *,
    name: str,
    lens: str,
    focus_statement: str,
    scope: Mapping[str, str],
    claim_ids: list[str],
    output_root: Path,
) -> dict[str, Any]:
    members = [_member_snapshot(claim_id, output_root=output_root) for claim_id in claim_ids]
    fingerprints = {str(item.get("source_context_fingerprint") or "") for item in members}
    search_ids = {str(item.get("search_id") or "") for item in members}
    context_versions = {str(item.get("context_version") or "") for item in members}
    if "" in fingerprints or len(fingerprints) != 1:
        raise SynthesisGovernanceError(
            "EvidenceSet exige claims do mesmo context fingerprint atual"
        )
    if "" in search_ids or len(search_ids) != 1:
        raise SynthesisGovernanceError("EvidenceSet exige claims do mesmo search id")
    if "" in context_versions or len(context_versions) != 1:
        raise SynthesisGovernanceError("EvidenceSet exige claims da mesma context version")

    scientific = {
        "draft_type": EVIDENCE_SET_DRAFT_TYPE,
        "canonical": False,
        "draft_scope": "HUMAN_PROPOSED_GROUPING_OF_ACCEPTED_AND_EVALUATED_CLAIMS",
        "name": name,
        "lens": lens,
        "focus_statement": focus_statement,
        "scope": dict(scope),
        "claim_ids": claim_ids,
        "member_snapshots": members,
        "source_context_fingerprint": next(iter(fingerprints)),
        "search_id": next(iter(search_ids)),
        "context_version": next(iter(context_versions)),
        "guardrails": {
            "membership_is_proposed_only": True,
            "accepted_claims_required": True,
            "finalized_claim_evaluations_required": True,
            "automatic_claim_grouping_performed": False,
            "automatic_relation_inference_performed": False,
            "claim_evaluation_scores_aggregated": False,
            "consensus_inferred": False,
            "contradiction_inferred": False,
            "certainty_assessed": False,
            "overall_certainty_grade_created": False,
            "formal_risk_of_bias_assessed": False,
            "evidence_set_created": False,
            "canonical_scientific_synthesis_created": False,
            "clinical_recommendation_created": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "screening_eligibility_changed": False,
            "accepted_claim_status_changed": False,
            "claim_evaluation_changed": False,
            "overlapping_evidence_sets_allowed": True,
            "single_claim_set_is_not_synthesis": True,
            "identity_cryptographically_authenticated": False,
        },
    }
    draft_id = "evidence_set_draft_" + _digest(scientific)[:24]
    content = {**scientific, "draft_id": draft_id}
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": _now(),
        "artifact_semantics": (
            "Non-canonical proposed EvidenceSet membership. It records a human grouping proposal only and "
            "does not establish agreement, contradiction, certainty, synthesis, or recommendation."
        ),
    }


def stage_evidence_set(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    lens = str(payload.get("lens") or "").strip()
    focus_statement = str(payload.get("focus_statement") or "").strip()
    staged_by = str(payload.get("staged_by") or "").strip()
    if len(name) < 3:
        raise SynthesisGovernanceError("EvidenceSet name precisa ter pelo menos 3 caracteres")
    if not lens:
        raise SynthesisGovernanceError("EvidenceSet lens é obrigatória")
    if len(lens) > 160:
        raise SynthesisGovernanceError("EvidenceSet lens excede 160 caracteres")
    if len(focus_statement) < 20:
        raise SynthesisGovernanceError("EvidenceSet focus statement precisa ter pelo menos 20 caracteres")
    if not staged_by:
        raise SynthesisGovernanceError("Identifique quem iniciou o EvidenceSet")
    claim_ids = _normalize_claim_ids(payload.get("claim_ids"))
    scope = _normalize_scope(payload.get("scope"))

    draft = _build_draft(
        name=name,
        lens=lens,
        focus_statement=focus_statement,
        scope=scope,
        claim_ids=claim_ids,
        output_root=output_root,
    )
    draft_id = str(draft.get("draft_id") or "")
    root = _set_root(output_root)
    with _SET_LOCK:
        draft_path = _draft_path(root, draft_id)
        state_path = _state_path(root, draft_id)
        if draft_path.is_file():
            existing = _read_json(draft_path, "EvidenceSet draft")
            if existing.get("content_sha256") != draft.get("content_sha256"):
                raise SynthesisGovernanceError("EvidenceSet draft id collision")
        else:
            _atomic_json(draft_path, draft)
        if not state_path.is_file():
            _atomic_json(
                state_path,
                {
                    "state_type": EVIDENCE_SET_STATE_TYPE,
                    "draft_id": draft_id,
                    "status": DRAFT,
                    "staged_by": staged_by,
                    "staged_at": _now(),
                    "canonical_evidence_set_id": None,
                    "identity_cryptographically_authenticated": False,
                },
            )
    return evidence_set_status(output_root=output_root)


def _load_draft(
    draft_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    draft_id = str(draft_id or "").strip()
    if not draft_id:
        raise SynthesisGovernanceError("EvidenceSet draft id obrigatório")
    root = _set_root(output_root)
    draft = _read_json(_draft_path(root, draft_id), "EvidenceSet draft")
    state = _read_json(_state_path(root, draft_id), "EvidenceSet state")
    if draft.get("draft_type") != EVIDENCE_SET_DRAFT_TYPE or draft.get("canonical") is not False:
        raise SynthesisGovernanceError("EvidenceSet draft inválido")
    if state.get("state_type") != EVIDENCE_SET_STATE_TYPE or state.get("draft_id") != draft_id:
        raise SynthesisGovernanceError("EvidenceSet state inválido")
    expected_sha = _digest(_draft_scientific_content(draft))
    if draft.get("content_sha256") != expected_sha:
        raise SynthesisGovernanceError("EvidenceSet draft content SHA-256 inválido")
    return draft, state


def _revalidate_draft(draft: Mapping[str, Any], *, output_root: Path) -> None:
    rebuilt = _build_draft(
        name=str(draft.get("name") or ""),
        lens=str(draft.get("lens") or ""),
        focus_statement=str(draft.get("focus_statement") or ""),
        scope=_normalize_scope(draft.get("scope")),
        claim_ids=_normalize_claim_ids(draft.get("claim_ids")),
        output_root=output_root,
    )
    if rebuilt.get("content_sha256") != draft.get("content_sha256"):
        raise SynthesisGovernanceError(
            "EvidenceSet draft não corresponde mais aos claims/evaluations/contexto atuais; restage necessário"
        )


def _normalize_membership_rationales(raw: Any, claim_ids: list[str]) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise SynthesisGovernanceError("Membership rationales obrigatórias")
    supplied = {str(key) for key in raw}
    expected = set(claim_ids)
    if supplied != expected:
        missing = sorted(expected - supplied)
        extra = sorted(supplied - expected)
        raise SynthesisGovernanceError(
            f"Membership rationales inválidas; missing={missing or []}; extra={extra or []}"
        )
    normalized: dict[str, str] = {}
    for claim_id in claim_ids:
        rationale = str(raw.get(claim_id) or "").strip()
        if len(rationale) < 15:
            raise SynthesisGovernanceError(
                f"Membership rationale de {claim_id} precisa ter pelo menos 15 caracteres"
            )
        normalized[claim_id] = rationale
    return normalized


def finalize_evidence_set(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    draft_id = str(payload.get("draft_id") or "").strip()
    curator = str(payload.get("curator") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    membership_human_curated_confirmed = payload.get("membership_human_curated_confirmed") is True
    grouping_is_not_consensus_confirmed = payload.get("grouping_is_not_consensus_confirmed") is True
    scientific_boundary_confirmed = payload.get("scientific_boundary_confirmed") is True
    if not curator:
        raise SynthesisGovernanceError("Identifique o curator do EvidenceSet")
    if len(rationale) < 30:
        raise SynthesisGovernanceError("EvidenceSet rationale precisa ter pelo menos 30 caracteres")
    if not membership_human_curated_confirmed:
        raise SynthesisGovernanceError("Confirme que a membership foi selecionada e justificada por humano")
    if not grouping_is_not_consensus_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que agrupar claims não implica agreement, consensus ou contradiction"
        )
    if not scientific_boundary_confirmed:
        raise SynthesisGovernanceError(
            "Confirme que EvidenceSet não equivale a certainty, síntese canônica ou recomendação"
        )

    root = _set_root(output_root)
    with _SET_LOCK:
        draft, state = _load_draft(draft_id, output_root=output_root)
        _revalidate_draft(draft, output_root=output_root)
        if state.get("status") == FINALIZED:
            existing_id = str(state.get("canonical_evidence_set_id") or "")
            if existing_id:
                return evidence_set_status(output_root=output_root)
            raise SynthesisGovernanceError("EvidenceSet state final sem evidence set id")

        claim_ids = _normalize_claim_ids(draft.get("claim_ids"))
        membership_rationales = _normalize_membership_rationales(
            payload.get("membership_rationales"), claim_ids
        )
        members = draft.get("member_snapshots")
        if not isinstance(members, list) or len(members) != len(claim_ids):
            raise SynthesisGovernanceError("EvidenceSet draft member snapshots inválidos")

        memberships: list[dict[str, Any]] = []
        for member in members:
            if not isinstance(member, Mapping):
                raise SynthesisGovernanceError("EvidenceSet member snapshot inválido")
            claim_id = str(member.get("claim_id") or "")
            if claim_id not in membership_rationales:
                raise SynthesisGovernanceError("EvidenceSet member não corresponde aos claim ids")
            memberships.append(
                {
                    "claim_id": claim_id,
                    "membership_rationale": membership_rationales[claim_id],
                    "claim_content_sha256": member.get("claim_content_sha256"),
                    "evaluation_id": member.get("evaluation_id"),
                    "evaluation_content_sha256": member.get("evaluation_content_sha256"),
                    "evidence_record_id": member.get("evidence_record_id"),
                    "document_id": member.get("document_id"),
                }
            )
        memberships.sort(key=lambda item: str(item.get("claim_id") or ""))

        scientific = {
            "evidence_set_record_type": CANONICAL_EVIDENCE_SET_RECORD_TYPE,
            "canonical": True,
            "human_finalized": True,
            "source_draft_id": draft_id,
            "source_draft_content_sha256": draft.get("content_sha256"),
            "source_context_fingerprint": draft.get("source_context_fingerprint"),
            "search_id": draft.get("search_id"),
            "context_version": draft.get("context_version"),
            "evidence_set": {
                "id": "pending",
                "name": draft.get("name"),
                "claim_ids": claim_ids,
                "lens": draft.get("lens"),
                "metadata": {
                    "construction_semantics": "HUMAN_GROUPING_OF_ACCEPTED_AND_EVALUATED_SOURCE_LEVEL_CLAIMS",
                    "focus_statement": draft.get("focus_statement"),
                    "scope": draft.get("scope") or {},
                    "curator": curator,
                    "rationale": rationale,
                    "memberships": memberships,
                    "human_entered": True,
                    "identity_cryptographically_authenticated": False,
                },
            },
            "member_snapshots": members,
            "confirmations": {
                "membership_human_curated_confirmed": True,
                "grouping_is_not_consensus_confirmed": True,
                "scientific_boundary_confirmed": True,
                "human_entered": True,
                "identity_cryptographically_authenticated": False,
            },
            "guardrails": {
                "evidence_set_created": True,
                "membership_human_curated": True,
                "claims_revalidated_at_finalization": True,
                "claim_evaluations_revalidated_at_finalization": True,
                "automatic_claim_grouping_performed": False,
                "automatic_relation_inference_performed": False,
                "claim_evaluation_scores_aggregated": False,
                "consensus_inferred": False,
                "contradiction_inferred": False,
                "certainty_assessed": False,
                "overall_certainty_grade_created": False,
                "formal_risk_of_bias_assessed": False,
                "canonical_scientific_synthesis_created": False,
                "clinical_recommendation_created": False,
                "meta_analysis_performed": False,
                "prisma_event_emitted": False,
                "screening_eligibility_changed": False,
                "accepted_claim_status_changed": False,
                "claim_evaluation_changed": False,
                "overlapping_evidence_sets_allowed": True,
                "single_claim_set_is_not_synthesis": True,
                "identity_cryptographically_authenticated": False,
            },
        }
        evidence_set_id = "evidence_set_" + _digest(scientific)[:24]
        scientific["evidence_set"]["id"] = evidence_set_id
        content_sha256 = _digest(scientific)
        record = {
            **scientific,
            "content_sha256": content_sha256,
            "finalized_at": _now(),
            "artifact_semantics": (
                "Canonical record of a human-curated grouping of accepted and evaluated source-level claims. "
                "Canonical means authoritative membership/provenance in NutEV; it does not establish consensus, "
                "certainty, synthesis, meta-analysis, or recommendation."
            ),
        }
        set_path = _set_path(root, evidence_set_id)
        if set_path.is_file():
            existing = _read_json(set_path, "canonical EvidenceSet")
            if existing.get("content_sha256") != content_sha256:
                raise SynthesisGovernanceError("Canonical EvidenceSet id collision")
        else:
            _atomic_json(set_path, record)
        _atomic_json(
            _state_path(root, draft_id),
            {
                **state,
                "status": FINALIZED,
                "canonical_evidence_set_id": evidence_set_id,
                "finalized_at": record["finalized_at"],
                "identity_cryptographically_authenticated": False,
            },
        )
    return evidence_set_status(output_root=output_root)


def evidence_set_status(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    root = _set_root(output_root)
    drafts: list[dict[str, Any]] = []
    counts = {DRAFT: 0, FINALIZED: 0}
    states_dir = root / "states"
    with _SET_LOCK:
        state_paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
        for state_path in state_paths:
            try:
                state = _read_json(state_path, state_path.name)
                draft_id = str(state.get("draft_id") or "")
                draft = _read_json(_draft_path(root, draft_id), "EvidenceSet draft")
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            status = str(state.get("status") or DRAFT)
            if status in counts:
                counts[status] += 1
            members = draft.get("member_snapshots")
            member_rows = []
            if isinstance(members, list):
                for raw in members:
                    if isinstance(raw, Mapping):
                        member_rows.append(
                            {
                                "claim_id": raw.get("claim_id"),
                                "statement": raw.get("statement"),
                                "evaluation_id": raw.get("evaluation_id"),
                                "document_id": raw.get("document_id"),
                                "outcome": raw.get("outcome"),
                            }
                        )
            drafts.append(
                {
                    "draft_id": draft_id,
                    "status": status,
                    "name": draft.get("name"),
                    "lens": draft.get("lens"),
                    "focus_statement": draft.get("focus_statement"),
                    "scope": draft.get("scope") or {},
                    "claim_ids": draft.get("claim_ids") or [],
                    "claim_count": len(draft.get("claim_ids") or []),
                    "members": member_rows,
                    "source_context_fingerprint": draft.get("source_context_fingerprint"),
                    "search_id": draft.get("search_id"),
                    "context_version": draft.get("context_version"),
                    "staged_by": state.get("staged_by"),
                    "canonical_evidence_set_id": state.get("canonical_evidence_set_id"),
                }
            )

    finalized: list[dict[str, Any]] = []
    membership_index: dict[str, list[str]] = {}
    finalized_dir = root / "finalized"
    if finalized_dir.is_dir():
        for path in sorted(finalized_dir.glob("*.json")):
            try:
                record = _read_json(path, path.name)
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            if record.get("evidence_set_record_type") != CANONICAL_EVIDENCE_SET_RECORD_TYPE:
                continue
            evidence_set = record.get("evidence_set")
            if not isinstance(evidence_set, Mapping):
                continue
            evidence_set_id = str(evidence_set.get("id") or "")
            claim_ids = [str(value) for value in evidence_set.get("claim_ids") or []]
            for claim_id in claim_ids:
                membership_index.setdefault(claim_id, []).append(evidence_set_id)
            metadata = evidence_set.get("metadata")
            finalized.append(
                {
                    "evidence_set_id": evidence_set_id,
                    "name": evidence_set.get("name"),
                    "lens": evidence_set.get("lens"),
                    "claim_ids": claim_ids,
                    "claim_count": len(claim_ids),
                    "focus_statement": metadata.get("focus_statement") if isinstance(metadata, Mapping) else None,
                    "scope": metadata.get("scope") if isinstance(metadata, Mapping) else {},
                    "curator": metadata.get("curator") if isinstance(metadata, Mapping) else None,
                    "rationale": metadata.get("rationale") if isinstance(metadata, Mapping) else None,
                    "finalized_at": record.get("finalized_at"),
                    "canonical": record.get("canonical"),
                    "certainty_assessed": bool((record.get("guardrails") or {}).get("certainty_assessed")),
                    "canonical_scientific_synthesis_created": bool(
                        (record.get("guardrails") or {}).get("canonical_scientific_synthesis_created")
                    ),
                }
            )
    for values in membership_index.values():
        values.sort()
    finalized.sort(key=lambda item: str(item.get("finalized_at") or ""), reverse=True)
    drafts.sort(key=lambda item: str(item.get("draft_id") or ""))
    return {
        "status": "READY",
        "draft_type": EVIDENCE_SET_DRAFT_TYPE,
        "canonical_evidence_set_record_type": CANONICAL_EVIDENCE_SET_RECORD_TYPE,
        "draft_count": len(drafts),
        "draft_counts": counts,
        "drafts": drafts[:STATUS_LIMIT],
        "draft_list_truncated": len(drafts) > STATUS_LIMIT,
        "finalized_evidence_set_count": len(finalized),
        "finalized_evidence_sets": finalized[:STATUS_LIMIT],
        "finalized_evidence_set_list_truncated": len(finalized) > STATUS_LIMIT,
        "claim_membership_index": membership_index,
        "scope_fields": list(SCOPE_FIELDS),
        "max_members": MAX_MEMBERS,
        "scientific_boundary": (
            "EvidenceSet is a human-curated grouping of accepted, evaluated source-level claims. Membership "
            "does not imply agreement, contradiction, certainty, study inclusion, pooled effect, canonical "
            "scientific synthesis, meta-analysis, recommendation, or PRISMA state."
        ),
    }
