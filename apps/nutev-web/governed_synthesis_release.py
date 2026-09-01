from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import threading
from typing import Any, Mapping
from uuid import uuid4

from synthesis_governance import (
    APPROVED,
    DEFAULT_OUTPUT_ROOT,
    ENTRY_TYPE,
    SynthesisGovernanceError,
    _artifact_path,
    _entry_path,
    _read_json,
    _registry_root,
    validate_brief,
)

RELEASE_TYPE = "NUTEV_GOVERNED_SYNTHESIS_RELEASE_V1"
RELEASE_RECORD_TYPE = "NUTEV_GOVERNED_SYNTHESIS_RELEASE_RECORD_V1"
PUBLICATION_OPERATION = "PREPARE_PUBLICATION_MANIFEST"
CLAIM_STAGE_OPERATION = "STAGE_EVIDENCE_CLAIM_REVIEW"
CLAIM_DECIDE_OPERATION = "DECIDE_EVIDENCE_CLAIM"
EVALUATION_STAGE_OPERATION = "STAGE_CLAIM_EVALUATION"
EVALUATION_FINALIZE_OPERATION = "FINALIZE_CLAIM_EVALUATION"
_RELEASE_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable(value: Any) -> Any:
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    return value


def _digest(value: Any) -> str:
    raw = json.dumps(
        _stable(value), ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _release_root(output_root: Path) -> Path:
    return output_root / "scientific" / "synthesis_releases"


def _package_path(root: Path, package_id: str) -> Path:
    return root / "packages" / f"{package_id}.json"


def _record_path(root: Path, package_id: str) -> Path:
    return root / "records" / f"{package_id}.json"


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _approved_source(
    artifact_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = _registry_root(output_root)
    entry = _read_json(_entry_path(root, artifact_id), "registry entry")
    if entry.get("registry_entry_type") != ENTRY_TYPE:
        raise SynthesisGovernanceError("Registry entry type inválido")
    if entry.get("status") != APPROVED:
        raise SynthesisGovernanceError(
            "Somente APPROVED_FOR_GOVERNED_USE pode gerar release package"
        )
    if entry.get("canonical_registry_record") is not True:
        raise SynthesisGovernanceError("Registry entry não é registro canônico de governance")
    if entry.get("canonical_scientific_synthesis_created") is not False:
        raise SynthesisGovernanceError("Registry entry declara canonização científica indevida")

    decision = entry.get("governance_decision")
    if not isinstance(decision, Mapping) or decision.get("action") != "APPROVE":
        raise SynthesisGovernanceError("Registry entry sem aprovação humana válida")
    if decision.get("human_entered") is not True:
        raise SynthesisGovernanceError("Governance decision não está marcada como humana")
    if decision.get("source_revalidated_at_decision") is not True:
        raise SynthesisGovernanceError("Source não foi revalidado na decisão de governance")
    if decision.get("identity_cryptographically_authenticated") is not False:
        raise SynthesisGovernanceError("Registry entry faz claim de identidade não suportado")

    content_sha = str(entry.get("source_content_sha256") or "")
    brief = _read_json(_artifact_path(root, content_sha), "source Brief")
    validated = validate_brief(brief, output_root=output_root)
    if validated["content_sha256"] != content_sha:
        raise SynthesisGovernanceError("Source Brief diverge do registry entry")
    if validated["context_fingerprint"] != entry.get("source_context_fingerprint"):
        raise SynthesisGovernanceError("Context fingerprint diverge do registry entry")
    return entry, dict(decision), brief


def build_governed_release(
    artifact_id: str,
    *,
    prepared_by: str,
    purpose: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    artifact_id = str(artifact_id or "").strip()
    prepared_by = str(prepared_by or "").strip()
    purpose = str(purpose or "").strip()
    if not artifact_id:
        raise SynthesisGovernanceError("Artifact id obrigatório")
    if not prepared_by:
        raise SynthesisGovernanceError("Identifique quem preparou o release package")
    if len(purpose) < 20:
        raise SynthesisGovernanceError("Purpose precisa ter pelo menos 20 caracteres")

    entry, decision, brief = _approved_source(artifact_id, output_root=output_root)
    content_sha = str(entry.get("source_content_sha256") or "")
    validated = validate_brief(brief, output_root=output_root)
    decisions = brief.get("reviewed_decisions") or []

    scientific_content = {
        "release_type": RELEASE_TYPE,
        "canonical": False,
        "release_scope": "GOVERNED_DISSEMINATION_PACKAGE",
        "source_registry_artifact_id": artifact_id,
        "source_registry_status": APPROVED,
        "source_registry_decided_at": decision.get("decided_at"),
        "source_brief_content_sha256": content_sha,
        "source_context_fingerprint": validated["context_fingerprint"],
        "search_id": validated["search_id"],
        "context_version": validated["context_version"],
        "question": validated["question"],
        "reviewer": validated["reviewer"],
        "governance": {
            "governor": decision.get("governor"),
            "rationale": decision.get("rationale"),
            "decided_at": decision.get("decided_at"),
            "human_entered": True,
            "identity_cryptographically_authenticated": False,
        },
        "prepared_by": prepared_by,
        "purpose": purpose,
        "relationship_counts": brief.get("relationship_counts") or {},
        "domain_counts": brief.get("domain_counts") or {},
        "comparability_counts": brief.get("comparability_counts") or {},
        "reviewed_decisions": decisions,
        "guardrails": {
            "source_registry_approval_revalidated": True,
            "source_brief_revalidated_against_current_context": True,
            "canonical_scientific_synthesis_created": False,
            "accepted_evidence_claims_created": False,
            "risk_of_bias_assessed": False,
            "certainty_assessed": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "formal_search_state_changed": False,
            "relationship_counts_are_not_evidence_strength": True,
            "governed_release_is_not_scientific_validation": True,
            "identity_cryptographically_authenticated": False,
        },
    }
    content_sha256 = _digest(scientific_content)
    return {
        **scientific_content,
        "content_sha256": content_sha256,
        "generated_at": _now(),
        "artifact_semantics": (
            "Governed dissemination package derived from an approved registry entry. "
            "It is not a canonical scientific synthesis, certainty assessment, meta-analysis, "
            "accepted EvidenceClaim, or PRISMA output."
        ),
    }


def prepare_governed_release(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    operation = str(payload.get("operation") or "").strip()
    if operation == PUBLICATION_OPERATION:
        from governed_publication_manifest import prepare_publication_manifest

        return prepare_publication_manifest(payload, output_root=output_root)
    if operation == CLAIM_STAGE_OPERATION:
        from evidence_claim_review import stage_claim_candidates

        return stage_claim_candidates(payload, output_root=output_root)
    if operation == CLAIM_DECIDE_OPERATION:
        from evidence_claim_review_gate import decide_claim_candidate

        return decide_claim_candidate(payload, output_root=output_root)
    if operation == EVALUATION_STAGE_OPERATION:
        from claim_evaluation_appraisal import stage_claim_evaluation

        return stage_claim_evaluation(payload, output_root=output_root)
    if operation == EVALUATION_FINALIZE_OPERATION:
        from claim_evaluation_appraisal import finalize_claim_evaluation

        return finalize_claim_evaluation(payload, output_root=output_root)

    package = build_governed_release(
        str(payload.get("artifact_id") or ""),
        prepared_by=str(payload.get("prepared_by") or ""),
        purpose=str(payload.get("purpose") or ""),
        output_root=output_root,
    )
    package_id = f"release_{str(package['content_sha256'])[:24]}"
    root = _release_root(output_root)
    package_path = _package_path(root, package_id)
    record_path = _record_path(root, package_id)

    with _RELEASE_LOCK:
        if package_path.is_file() and record_path.is_file():
            existing = _read_json(package_path, "release package")
            record = _read_json(record_path, "release record")
            return {"record": record, "package": existing}

        record = {
            "release_record_type": RELEASE_RECORD_TYPE,
            "package_id": package_id,
            "release_type": RELEASE_TYPE,
            "package_content_sha256": package["content_sha256"],
            "source_registry_artifact_id": package["source_registry_artifact_id"],
            "source_registry_status": package["source_registry_status"],
            "source_context_fingerprint": package["source_context_fingerprint"],
            "search_id": package["search_id"],
            "context_version": package["context_version"],
            "prepared_by": package["prepared_by"],
            "purpose": package["purpose"],
            "generated_at": package["generated_at"],
            "canonical_release_record": True,
            "release_package_canonical": False,
            "canonical_scientific_synthesis_created": False,
            "scientific_boundary": (
                "This record proves that a governed dissemination package was prepared from an "
                "approved registry entry after revalidation. It does not validate the science."
            ),
        }
        _atomic_json(package_path, package)
        _atomic_json(record_path, record)
    return {"record": record, "package": package}


def release_status(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    root = _release_root(output_root)
    records: list[dict[str, Any]] = []
    directory = root / "records"
    with _RELEASE_LOCK:
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                try:
                    records.append(_read_json(path, path.name))
                except (FileNotFoundError, SynthesisGovernanceError):
                    continue
    records.sort(key=lambda item: str(item.get("generated_at") or ""), reverse=True)

    from claim_evaluation_appraisal import claim_evaluation_status
    from evidence_claim_review import claim_review_status
    from governed_publication_manifest import publication_status

    publication = publication_status(output_root=output_root)
    claims = claim_review_status(output_root=output_root)
    evaluations = claim_evaluation_status(output_root=output_root)
    return {
        "status": "READY",
        "release_type": RELEASE_TYPE,
        "count": len(records),
        "records": records,
        "publication_manifest_type": publication["manifest_type"],
        "publication_count": publication["count"],
        "publication_records": publication["records"],
        "evidence_claim_candidate_type": claims["candidate_type"],
        "evidence_claim_record_type": claims["canonical_claim_record_type"],
        "evidence_claim_candidate_count": claims["candidate_count"],
        "evidence_claim_candidate_counts": claims["candidate_counts"],
        "evidence_claim_candidates": claims["candidates"],
        "evidence_claim_candidate_list_truncated": claims["candidate_list_truncated"],
        "accepted_evidence_claim_count": claims["accepted_claim_count"],
        "accepted_evidence_claims": claims["accepted_claims"],
        "accepted_evidence_claim_list_truncated": claims["accepted_claim_list_truncated"],
        "claim_evaluation_method": evaluations["appraisal_method"],
        "claim_evaluation_candidate_type": evaluations["evaluation_candidate_type"],
        "claim_evaluation_record_type": evaluations["canonical_evaluation_record_type"],
        "claim_evaluation_dimensions": evaluations["dimensions"],
        "claim_evaluation_judgment_scale": evaluations["judgment_scale"],
        "claim_evaluation_assessment_basis_options": evaluations["assessment_basis_options"],
        "claim_evaluation_candidate_count": evaluations["candidate_count"],
        "claim_evaluation_candidate_counts": evaluations["candidate_counts"],
        "claim_evaluation_candidates": evaluations["candidates"],
        "claim_evaluation_candidate_list_truncated": evaluations["candidate_list_truncated"],
        "finalized_claim_evaluation_count": evaluations["finalized_evaluation_count"],
        "finalized_claim_evaluations": evaluations["finalized_evaluations"],
        "finalized_claim_evaluation_list_truncated": evaluations[
            "finalized_evaluation_list_truncated"
        ],
        "scientific_boundary": (
            "Release/publication remain preparation artifacts; accepted EvidenceClaims are source-level "
            "propositions; ClaimEvaluation records explicit human appraisal dimensions only. The generic "
            "appraisal is not formal risk of bias, certainty/GRADE, EvidenceSet synthesis, recommendation, "
            "meta-analysis, PRISMA, or canonical scientific synthesis."
        ),
    }
