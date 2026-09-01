from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any, Mapping

from governed_publication_manifest import (
    MANIFEST_RECORD_TYPE,
    MANIFEST_TYPE,
    STATEMENT_TYPE,
    _manifest_path,
    _manifest_record_path,
    _manifest_root,
    build_publication_manifest,
)
from governed_synthesis_release import DEFAULT_OUTPUT_ROOT, _atomic_json, _digest, _read_json
from synthesis_governance import SynthesisGovernanceError

CLAIM_CANDIDATE_TYPE = "NUTEV_EVIDENCE_CLAIM_CANDIDATE_V1"
CLAIM_STATE_TYPE = "NUTEV_EVIDENCE_CLAIM_REVIEW_STATE_V1"
CLAIM_VALIDATION_TYPE = "NUTEV_EVIDENCE_CLAIM_HUMAN_VALIDATION_V1"
CANONICAL_CLAIM_RECORD_TYPE = "NUTEV_CANONICAL_EVIDENCE_CLAIM_RECORD_V1"
CLAIM_STAGE_OPERATION = "STAGE_EVIDENCE_CLAIM_REVIEW"
CLAIM_DECIDE_OPERATION = "DECIDE_EVIDENCE_CLAIM"
PENDING = "PENDING_HUMAN_REVIEW"
REVISION_REQUIRED = "REVISION_REQUIRED"
ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"
FINAL_STATES = {ACCEPTED, REJECTED}
DECISIONS = {"ACCEPT", "REJECT", "REVISE"}
STATUS_LIMIT = 200
_CLAIM_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claim_root(output_root: Path) -> Path:
    return output_root / "scientific" / "evidence_claims"


def _candidate_path(root: Path, candidate_id: str) -> Path:
    return root / "candidates" / f"{candidate_id}.json"


def _state_path(root: Path, candidate_id: str) -> Path:
    return root / "states" / f"{candidate_id}.json"


def _review_path(root: Path, candidate_id: str, review_id: str) -> Path:
    return root / "reviews" / candidate_id / f"{review_id}.json"


def _claim_path(root: Path, claim_id: str) -> Path:
    return root / "accepted" / f"{claim_id}.json"


def _manifest_scientific_content(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: manifest[key]
        for key in manifest
        if key not in {"content_sha256", "generated_at", "artifact_semantics"}
    }


def _validated_manifest(
    manifest_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_id = str(manifest_id or "").strip()
    if not manifest_id:
        raise SynthesisGovernanceError("Publication manifest id obrigatório")
    root = _manifest_root(output_root)
    record = _read_json(_manifest_record_path(root, manifest_id), "publication manifest record")
    manifest = _read_json(_manifest_path(root, manifest_id), "publication manifest")
    if record.get("manifest_record_type") != MANIFEST_RECORD_TYPE:
        raise SynthesisGovernanceError("Publication manifest record type inválido")
    if manifest.get("manifest_type") != MANIFEST_TYPE or manifest.get("canonical") is not False:
        raise SynthesisGovernanceError("Publication manifest inválido ou indevidamente canônico")
    if record.get("canonical_manifest_record") is not True:
        raise SynthesisGovernanceError("Publication manifest record não é trilha operacional canônica")
    if record.get("publication_manifest_canonical") is not False:
        raise SynthesisGovernanceError("Publication manifest record declara manifest canônico")
    if record.get("accepted_evidence_claims_created") is not False:
        raise SynthesisGovernanceError("Publication manifest record já declara EvidenceClaim aceito")

    expected_sha = _digest(_manifest_scientific_content(manifest))
    if str(manifest.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("Publication manifest content SHA-256 inválido")
    if str(record.get("manifest_content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("Publication manifest record diverge do manifest SHA-256")

    guardrails = manifest.get("guardrails")
    required_false = {
        "accepted_evidence_claims_created",
        "canonical_scientific_synthesis_created",
        "risk_of_bias_assessed",
        "certainty_assessed",
        "meta_analysis_performed",
        "prisma_event_emitted",
        "formal_search_state_changed",
        "clinical_recommendation_created",
        "identity_cryptographically_authenticated",
        "external_llm_generated_scientific_claims",
    }
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("Publication manifest sem guardrails")
    for key in required_false:
        if guardrails.get(key) is not False:
            raise SynthesisGovernanceError(f"Publication manifest guardrail inválido: {key}")
    if guardrails.get("publication_statements_are_candidate_only") is not True:
        raise SynthesisGovernanceError("Publication statements perderam status candidate-only")
    if guardrails.get("source_release_revalidated_against_current_context") is not True:
        raise SynthesisGovernanceError("Publication manifest sem revalidação de source release")

    rebuilt = build_publication_manifest(
        str(manifest.get("source_release_package_id") or ""),
        publication_owner=str(manifest.get("publication_owner") or ""),
        intended_use=str(manifest.get("intended_use") or ""),
        output_root=output_root,
    )
    if rebuilt.get("content_sha256") != expected_sha:
        raise SynthesisGovernanceError(
            "Publication manifest não corresponde mais ao contexto científico atual; prepare novo manifest"
        )
    return record, manifest


def _evidence_record_id(document_id: str) -> str:
    document_id = str(document_id or "").strip()
    if not document_id:
        raise SynthesisGovernanceError("Citation sem document id")
    if not document_id.casefold().startswith(("doi:", "pmid:", "url:", "title:")):
        raise SynthesisGovernanceError(
            "Document id não segue a identidade canônica do EvidenceRecord"
        )
    suffix = document_id.split(":", 1)[1].strip() if ":" in document_id else ""
    if not suffix:
        raise SynthesisGovernanceError("Document id canônico vazio")
    return f"evidence:{document_id}"


def _evidence_record_index(output_root: Path) -> dict[str, dict[str, Any]]:
    path = output_root / "scientific" / "evidence_records.jsonl"
    if not path.is_file():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SynthesisGovernanceError(
                f"evidence_records.jsonl inválido na linha {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise SynthesisGovernanceError(
                f"evidence_records.jsonl contém valor não-objeto na linha {line_number}"
            )
        record_id = str(value.get("id") or "").strip()
        if record_id:
            records[record_id] = value
    return records


def _statement_context(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    statements = manifest.get("statement_candidates")
    if not isinstance(statements, list):
        raise SynthesisGovernanceError("Publication manifest sem statement candidates")
    for raw in statements:
        if not isinstance(raw, Mapping):
            raise SynthesisGovernanceError("Statement candidate inválido")
        if raw.get("statement_type") != STATEMENT_TYPE:
            raise SynthesisGovernanceError("Statement candidate type inválido")
        if raw.get("publication_status") != "CANDIDATE_ONLY":
            raise SynthesisGovernanceError("Statement candidate foi promovido antes do claim review")
        if raw.get("accepted_evidence_claim") is not False:
            raise SynthesisGovernanceError("Statement candidate já declara EvidenceClaim aceito")
        citation_ids = raw.get("citation_ids")
        if not isinstance(citation_ids, list) or not citation_ids:
            raise SynthesisGovernanceError("Statement candidate sem citation ids")
        context = {
            "statement_id": raw.get("statement_id"),
            "relation": raw.get("relation"),
            "statement_text": raw.get("statement_text"),
            "directly_promotable_to_evidence_claim": False,
            "context_semantics": (
                "Pairwise synthesis context only. It cannot be directly promoted into an atomic "
                "EvidenceClaim because EvidenceClaim belongs to one EvidenceRecord."
            ),
        }
        for citation_id in citation_ids:
            key = str(citation_id or "").strip()
            if not key or key in mapping:
                raise SynthesisGovernanceError("Citation id ausente ou duplicado em statement context")
            mapping[key] = context
    return mapping


def _candidate_from_citation(
    citation: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    manifest_id: str,
    synthesis_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    citation_id = str(citation.get("citation_id") or "").strip()
    decision_id = str(citation.get("decision_id") or "").strip()
    document_id = str(citation.get("document_id") or "").strip()
    title = str(citation.get("title") or "").strip()
    bundle_id = str(citation.get("bundle_id") or "").strip()
    result_text = str(citation.get("result_text") or "").strip()
    if not citation_id or not decision_id or not title or not bundle_id or not result_text:
        raise SynthesisGovernanceError("Citation incompleta para EvidenceClaim review")
    evidence_record_id = _evidence_record_id(document_id)
    source_snapshot = {
        "citation_id": citation_id,
        "decision_id": decision_id,
        "role": citation.get("role"),
        "document_id": document_id,
        "title": title,
        "identifiers": citation.get("identifiers") or {},
        "bundle_id": bundle_id,
        "source_sentence_sha256": str(citation.get("source_sentence_sha256") or ""),
        "result_text": result_text,
        "outcomes": citation.get("outcomes") or [],
        "effect_measures": citation.get("effect_measures") or [],
        "confidence_intervals": citation.get("confidence_intervals") or [],
        "p_values": citation.get("p_values") or [],
        "routes": citation.get("routes") or [],
        "source_reference": citation.get("source_reference"),
    }
    candidate_id = "claim_candidate_" + _digest(
        {
            "manifest_content_sha256": manifest.get("content_sha256"),
            "citation_id": citation_id,
            "source_snapshot_sha256": _digest(source_snapshot),
        }
    )[:24]
    content = {
        "candidate_type": CLAIM_CANDIDATE_TYPE,
        "candidate_id": candidate_id,
        "canonical": False,
        "candidate_scope": "ATOMIC_SOURCE_SNAPSHOT_FOR_HUMAN_CLAIM_REVIEW",
        "source_manifest_id": manifest_id,
        "source_manifest_content_sha256": manifest.get("content_sha256"),
        "source_release_package_id": manifest.get("source_release_package_id"),
        "source_context_fingerprint": manifest.get("source_context_fingerprint"),
        "search_id": manifest.get("search_id"),
        "context_version": manifest.get("context_version"),
        "evidence_record_id": evidence_record_id,
        "source_snapshot": source_snapshot,
        "synthesis_context": dict(synthesis_context or {}),
        "guardrails": {
            "accepted_evidence_claim_created": False,
            "pairwise_statement_directly_promotable": False,
            "screening_eligibility_verified": False,
            "claim_evaluation_created": False,
            "risk_of_bias_assessed": False,
            "certainty_assessed": False,
            "evidence_set_created": False,
            "clinical_recommendation_created": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "identity_cryptographically_authenticated": False,
        },
    }
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": _now(),
        "artifact_semantics": (
            "Source-linked atomic candidate for explicit human EvidenceClaim review. It is not an "
            "accepted claim, screening inclusion, certainty assessment, or recommendation."
        ),
    }


def _load_candidate(candidate_id: str, *, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_id = str(candidate_id or "").strip()
    if not candidate_id:
        raise SynthesisGovernanceError("Claim candidate id obrigatório")
    root = _claim_root(output_root)
    candidate = _read_json(_candidate_path(root, candidate_id), "claim candidate")
    state = _read_json(_state_path(root, candidate_id), "claim review state")
    if candidate.get("candidate_type") != CLAIM_CANDIDATE_TYPE or candidate.get("canonical") is not False:
        raise SynthesisGovernanceError("Claim candidate inválido")
    if state.get("state_type") != CLAIM_STATE_TYPE or state.get("candidate_id") != candidate_id:
        raise SynthesisGovernanceError("Claim review state inválido")
    content_sha = _digest(
        {
            key: candidate[key]
            for key in candidate
            if key not in {"content_sha256", "generated_at", "artifact_semantics"}
        }
    )
    if content_sha != candidate.get("content_sha256"):
        raise SynthesisGovernanceError("Claim candidate content SHA-256 inválido")
    return candidate, state


def _validate_candidate_current(
    candidate: Mapping[str, Any], *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_id = str(candidate.get("source_manifest_id") or "")
    _, manifest = _validated_manifest(manifest_id, output_root=output_root)
    contexts = _statement_context(manifest)
    citation_id = str((candidate.get("source_snapshot") or {}).get("citation_id") or "")
    citations = manifest.get("citation_bundle")
    if not isinstance(citations, list):
        raise SynthesisGovernanceError("Publication manifest sem citation bundle")
    matches = [
        item
        for item in citations
        if isinstance(item, Mapping) and str(item.get("citation_id") or "") == citation_id
    ]
    if len(matches) != 1:
        raise SynthesisGovernanceError("Source citation não é mais única no publication manifest")
    rebuilt = _candidate_from_citation(
        matches[0],
        manifest=manifest,
        manifest_id=manifest_id,
        synthesis_context=contexts.get(citation_id),
    )
    if rebuilt.get("content_sha256") != candidate.get("content_sha256"):
        raise SynthesisGovernanceError(
            "Claim candidate não corresponde mais ao publication manifest atual; restage necessário"
        )
    return manifest, matches[0]


def stage_claim_candidates(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    manifest_id = str(payload.get("manifest_id") or "").strip()
    staged_by = str(payload.get("staged_by") or "").strip()
    if not manifest_id:
        raise SynthesisGovernanceError("Publication manifest id obrigatório")
    if not staged_by:
        raise SynthesisGovernanceError("Identifique quem iniciou o EvidenceClaim review")

    _, manifest = _validated_manifest(manifest_id, output_root=output_root)
    citations = manifest.get("citation_bundle")
    if not isinstance(citations, list) or not citations:
        raise SynthesisGovernanceError("Publication manifest sem citations para claim review")
    contexts = _statement_context(manifest)
    root = _claim_root(output_root)
    seen: set[str] = set()

    with _CLAIM_LOCK:
        for raw in citations:
            if not isinstance(raw, Mapping):
                raise SynthesisGovernanceError("Citation inválida no publication manifest")
            citation_id = str(raw.get("citation_id") or "").strip()
            if not citation_id or citation_id in seen:
                raise SynthesisGovernanceError("Citation id ausente ou duplicado")
            seen.add(citation_id)
            candidate = _candidate_from_citation(
                raw,
                manifest=manifest,
                manifest_id=manifest_id,
                synthesis_context=contexts.get(citation_id),
            )
            candidate_id = str(candidate["candidate_id"])
            candidate_path = _candidate_path(root, candidate_id)
            state_path = _state_path(root, candidate_id)
            if candidate_path.is_file():
                existing = _read_json(candidate_path, "claim candidate")
                if existing.get("content_sha256") != candidate.get("content_sha256"):
                    raise SynthesisGovernanceError("Claim candidate id collision ou source alterado")
            else:
                _atomic_json(candidate_path, candidate)
            if not state_path.is_file():
                _atomic_json(
                    state_path,
                    {
                        "state_type": CLAIM_STATE_TYPE,
                        "candidate_id": candidate_id,
                        "status": PENDING,
                        "staged_by": staged_by,
                        "staged_at": _now(),
                        "latest_review_id": None,
                        "canonical_evidence_claim_id": None,
                        "final_decision": None,
                        "identity_cryptographically_authenticated": False,
                    },
                )
    return claim_review_status(output_root=output_root)


def _canonical_claim_record(
    candidate: Mapping[str, Any],
    *,
    reviewer: str,
    rationale: str,
    claim_statement: str,
    structured: Mapping[str, Any],
    evidence_record: Mapping[str, Any],
    review_id: str,
) -> dict[str, Any]:
    snapshot = candidate.get("source_snapshot")
    if not isinstance(snapshot, Mapping):
        raise SynthesisGovernanceError("Claim candidate sem source snapshot")
    claim_id = "claim_" + _digest(
        {
            "evidence_record_id": candidate.get("evidence_record_id"),
            "statement": claim_statement,
            "source_snapshot_sha256": _digest(dict(snapshot)),
        }
    )[:24]
    evidence_claim = {
        "id": claim_id,
        "evidence_record_id": candidate.get("evidence_record_id"),
        "statement": claim_statement,
        "locator": snapshot.get("bundle_id"),
        "quote": None,
        "population": structured.get("population") or None,
        "intervention_or_exposure": structured.get("intervention_or_exposure") or None,
        "comparator": structured.get("comparator") or None,
        "outcome": structured.get("outcome") or None,
        "evidence_type": structured.get("evidence_type") or None,
        "metadata": {
            "claim_semantics": "SOURCE_REPORTED_PROPOSITION",
            "source_manifest_id": candidate.get("source_manifest_id"),
            "source_manifest_content_sha256": candidate.get("source_manifest_content_sha256"),
            "source_citation_id": snapshot.get("citation_id"),
            "source_decision_id": snapshot.get("decision_id"),
            "source_document_id": snapshot.get("document_id"),
            "source_bundle_id": snapshot.get("bundle_id"),
            "source_sentence_sha256": snapshot.get("source_sentence_sha256"),
            "source_snapshot_sha256": _digest(dict(snapshot)),
            "source_provider": evidence_record.get("source_provider"),
            "human_validation_id": review_id,
            "reviewer": reviewer,
            "review_rationale": rationale,
            "human_entered": True,
            "identity_cryptographically_authenticated": False,
        },
    }
    content = {
        "claim_record_type": CANONICAL_CLAIM_RECORD_TYPE,
        "canonical": True,
        "evidence_claim": evidence_claim,
        "accepted_from_candidate_id": candidate.get("candidate_id"),
        "source_evidence_record_verified": True,
        "guardrails": {
            "accepted_evidence_claim_created": True,
            "claim_acceptance_scope": "SOURCE_REPORTED_PROPOSITION_ONLY",
            "claim_acceptance_is_not_screening_inclusion": True,
            "screening_eligibility_verified": False,
            "claim_evaluation_created": False,
            "risk_of_bias_assessed": False,
            "certainty_assessed": False,
            "evidence_set_created": False,
            "canonical_scientific_synthesis_created": False,
            "clinical_recommendation_created": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "pairwise_synthesis_statement_promoted": False,
            "identity_cryptographically_authenticated": False,
        },
    }
    return {
        **content,
        "content_sha256": _digest(content),
        "accepted_at": _now(),
        "artifact_semantics": (
            "Canonical source-level EvidenceClaim accepted by explicit human review and linked to an "
            "existing EvidenceRecord. Acceptance does not establish screening inclusion, RoB, certainty, "
            "synthesis, causality, or recommendation."
        ),
    }


def _review_record(
    *,
    candidate: Mapping[str, Any],
    decision: str,
    reviewer: str,
    rationale: str,
    claim_statement: str,
    structured: Mapping[str, Any],
    source_attribution_confirmed: bool,
    scientific_boundary_confirmed: bool,
) -> dict[str, Any]:
    scientific = {
        "candidate_id": candidate.get("candidate_id"),
        "candidate_content_sha256": candidate.get("content_sha256"),
        "source_manifest_id": candidate.get("source_manifest_id"),
        "source_manifest_content_sha256": candidate.get("source_manifest_content_sha256"),
        "decision": decision.casefold(),
        "reviewer": reviewer,
        "rationale": rationale,
        "claim_statement": claim_statement or None,
        "structured_fields": dict(structured),
        "source_attribution_confirmed": source_attribution_confirmed,
        "scientific_boundary_confirmed": scientific_boundary_confirmed,
        "human_entered": True,
        "identity_cryptographically_authenticated": False,
    }
    review_id = "claim_review_" + _digest(scientific)[:24]
    return {
        "validation_type": CLAIM_VALIDATION_TYPE,
        "id": review_id,
        "target_type": CLAIM_CANDIDATE_TYPE,
        "target_id": candidate.get("candidate_id"),
        **scientific,
        "reviewed_at": _now(),
    }


def decide_claim_candidate(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    candidate_id = str(payload.get("candidate_id") or "").strip()
    decision = str(payload.get("decision") or "").strip().upper()
    reviewer = str(payload.get("reviewer") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    claim_statement = str(payload.get("claim_statement") or "").strip()
    source_attribution_confirmed = payload.get("source_attribution_confirmed") is True
    scientific_boundary_confirmed = payload.get("scientific_boundary_confirmed") is True
    if decision not in DECISIONS:
        raise SynthesisGovernanceError("Decision deve ser ACCEPT, REJECT ou REVISE")
    if not reviewer:
        raise SynthesisGovernanceError("Identifique o revisor do EvidenceClaim")
    if len(rationale) < 20:
        raise SynthesisGovernanceError("Rationale precisa ter pelo menos 20 caracteres")
    if decision == "ACCEPT":
        if len(claim_statement) < 20:
            raise SynthesisGovernanceError("Claim statement precisa ter pelo menos 20 caracteres")
        if not source_attribution_confirmed:
            raise SynthesisGovernanceError(
                "Confirme que o claim descreve uma proposição reportada pela fonte"
            )
        if not scientific_boundary_confirmed:
            raise SynthesisGovernanceError(
                "Confirme que claim acceptance não equivale a certainty, RoB, inclusão ou recomendação"
            )

    structured = {
        "population": str(payload.get("population") or "").strip(),
        "intervention_or_exposure": str(payload.get("intervention_or_exposure") or "").strip(),
        "comparator": str(payload.get("comparator") or "").strip(),
        "outcome": str(payload.get("outcome") or "").strip(),
        "evidence_type": str(payload.get("evidence_type") or "").strip(),
    }
    root = _claim_root(output_root)
    with _CLAIM_LOCK:
        candidate, state = _load_candidate(candidate_id, output_root=output_root)
        _validate_candidate_current(candidate, output_root=output_root)
        review = _review_record(
            candidate=candidate,
            decision=decision,
            reviewer=reviewer,
            rationale=rationale,
            claim_statement=claim_statement,
            structured=structured,
            source_attribution_confirmed=source_attribution_confirmed,
            scientific_boundary_confirmed=scientific_boundary_confirmed,
        )
        review_id = str(review["id"])

        if state.get("status") in FINAL_STATES:
            latest_review_id = str(state.get("latest_review_id") or "")
            if latest_review_id == review_id and state.get("final_decision") == decision:
                return claim_review_status(output_root=output_root)
            raise SynthesisGovernanceError("Claim candidate já possui decisão final")

        review_path = _review_path(root, candidate_id, review_id)
        if not review_path.is_file():
            _atomic_json(review_path, review)

        if decision == "REVISE":
            next_state = {
                **state,
                "status": REVISION_REQUIRED,
                "latest_review_id": review_id,
                "final_decision": None,
                "canonical_evidence_claim_id": None,
                "updated_at": _now(),
            }
            _atomic_json(_state_path(root, candidate_id), next_state)
            return claim_review_status(output_root=output_root)

        if decision == "REJECT":
            next_state = {
                **state,
                "status": REJECTED,
                "latest_review_id": review_id,
                "final_decision": "REJECT",
                "canonical_evidence_claim_id": None,
                "updated_at": _now(),
            }
            _atomic_json(_state_path(root, candidate_id), next_state)
            return claim_review_status(output_root=output_root)

        evidence_records = _evidence_record_index(output_root)
        evidence_record_id = str(candidate.get("evidence_record_id") or "")
        evidence_record = evidence_records.get(evidence_record_id)
        snapshot = candidate.get("source_snapshot")
        document_id = (
            str(snapshot.get("document_id") or "").strip()
            if isinstance(snapshot, Mapping)
            else ""
        )
        if not evidence_record or str(evidence_record.get("document_id") or "") != document_id:
            raise SynthesisGovernanceError(
                "EvidenceRecord correspondente não foi localizado; materialize/atualize evidence_records.jsonl antes de ACCEPT"
            )

        claim = _canonical_claim_record(
            candidate,
            reviewer=reviewer,
            rationale=rationale,
            claim_statement=claim_statement,
            structured=structured,
            evidence_record=evidence_record,
            review_id=review_id,
        )
        claim_id = str((claim.get("evidence_claim") or {}).get("id") or "")
        claim_path = _claim_path(root, claim_id)
        if claim_path.is_file():
            existing = _read_json(claim_path, "canonical EvidenceClaim")
            if existing.get("content_sha256") != claim.get("content_sha256"):
                raise SynthesisGovernanceError("Canonical EvidenceClaim id collision")
        else:
            _atomic_json(claim_path, claim)
        next_state = {
            **state,
            "status": ACCEPTED,
            "latest_review_id": review_id,
            "final_decision": "ACCEPT",
            "canonical_evidence_claim_id": claim_id,
            "updated_at": _now(),
        }
        _atomic_json(_state_path(root, candidate_id), next_state)
    return claim_review_status(output_root=output_root)


def claim_review_status(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    root = _claim_root(output_root)
    states_dir = root / "states"
    evidence_records = _evidence_record_index(output_root)
    candidates: list[dict[str, Any]] = []
    counts = {
        PENDING: 0,
        REVISION_REQUIRED: 0,
        ACCEPTED: 0,
        REJECTED: 0,
    }
    with _CLAIM_LOCK:
        state_paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
        for state_path in state_paths:
            try:
                state = _read_json(state_path, state_path.name)
                candidate_id = str(state.get("candidate_id") or "")
                candidate = _read_json(_candidate_path(root, candidate_id), "claim candidate")
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            status = str(state.get("status") or PENDING)
            if status in counts:
                counts[status] += 1
            snapshot = candidate.get("source_snapshot")
            snapshot = dict(snapshot) if isinstance(snapshot, Mapping) else {}
            evidence_record_id = str(candidate.get("evidence_record_id") or "")
            evidence_record = evidence_records.get(evidence_record_id)
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "status": status,
                    "source_manifest_id": candidate.get("source_manifest_id"),
                    "source_manifest_content_sha256": candidate.get("source_manifest_content_sha256"),
                    "source_context_fingerprint": candidate.get("source_context_fingerprint"),
                    "citation_id": snapshot.get("citation_id"),
                    "decision_id": snapshot.get("decision_id"),
                    "role": snapshot.get("role"),
                    "document_id": snapshot.get("document_id"),
                    "title": snapshot.get("title"),
                    "bundle_id": snapshot.get("bundle_id"),
                    "source_sentence_sha256": snapshot.get("source_sentence_sha256"),
                    "result_text": snapshot.get("result_text"),
                    "outcomes": snapshot.get("outcomes") or [],
                    "effect_measures": snapshot.get("effect_measures") or [],
                    "confidence_intervals": snapshot.get("confidence_intervals") or [],
                    "p_values": snapshot.get("p_values") or [],
                    "evidence_record_id": evidence_record_id,
                    "evidence_record_resolved": bool(
                        evidence_record
                        and str(evidence_record.get("document_id") or "")
                        == str(snapshot.get("document_id") or "")
                    ),
                    "synthesis_context": candidate.get("synthesis_context") or {},
                    "latest_review_id": state.get("latest_review_id"),
                    "canonical_evidence_claim_id": state.get("canonical_evidence_claim_id"),
                    "final_decision": state.get("final_decision"),
                }
            )
    candidates.sort(key=lambda item: str(item.get("candidate_id") or ""))

    claims: list[dict[str, Any]] = []
    accepted_dir = root / "accepted"
    if accepted_dir.is_dir():
        for path in sorted(accepted_dir.glob("*.json")):
            try:
                record = _read_json(path, path.name)
            except (FileNotFoundError, SynthesisGovernanceError):
                continue
            if record.get("claim_record_type") != CANONICAL_CLAIM_RECORD_TYPE:
                continue
            evidence_claim = record.get("evidence_claim")
            if not isinstance(evidence_claim, Mapping):
                continue
            metadata = evidence_claim.get("metadata")
            metadata = dict(metadata) if isinstance(metadata, Mapping) else {}
            claims.append(
                {
                    "claim_id": evidence_claim.get("id"),
                    "evidence_record_id": evidence_claim.get("evidence_record_id"),
                    "statement": evidence_claim.get("statement"),
                    "outcome": evidence_claim.get("outcome"),
                    "evidence_type": evidence_claim.get("evidence_type"),
                    "source_citation_id": metadata.get("source_citation_id"),
                    "reviewer": metadata.get("reviewer"),
                    "accepted_at": record.get("accepted_at"),
                    "canonical": record.get("canonical"),
                    "claim_evaluation_created": bool(
                        (record.get("guardrails") or {}).get("claim_evaluation_created")
                    ),
                }
            )
    claims.sort(key=lambda item: str(item.get("accepted_at") or ""), reverse=True)
    return {
        "status": "READY",
        "candidate_type": CLAIM_CANDIDATE_TYPE,
        "canonical_claim_record_type": CANONICAL_CLAIM_RECORD_TYPE,
        "candidate_count": len(candidates),
        "candidate_counts": counts,
        "candidates": candidates[:STATUS_LIMIT],
        "candidate_list_truncated": len(candidates) > STATUS_LIMIT,
        "accepted_claim_count": len(claims),
        "accepted_claims": claims[:STATUS_LIMIT],
        "accepted_claim_list_truncated": len(claims) > STATUS_LIMIT,
        "scientific_boundary": (
            "Only explicit ACCEPT after source revalidation and EvidenceRecord resolution creates a "
            "canonical source-level EvidenceClaim. Claim acceptance is not screening inclusion, RoB, "
            "certainty, EvidenceSet synthesis, recommendation, meta-analysis, or PRISMA state."
        ),
    }
