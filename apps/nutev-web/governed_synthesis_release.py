from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

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

    root = _registry_root(output_root)
    entry = _read_json(_entry_path(root, artifact_id), "registry entry")
    if entry.get("registry_entry_type") != ENTRY_TYPE:
        raise SynthesisGovernanceError("Registry entry type inválido")
    if entry.get("status") != APPROVED:
        raise SynthesisGovernanceError(
            "Somente APPROVED_FOR_GOVERNED_USE pode gerar release package"
        )
    decision = entry.get("governance_decision")
    if not isinstance(decision, Mapping) or decision.get("action") != "APPROVE":
        raise SynthesisGovernanceError("Registry entry sem aprovação humana válida")
    if decision.get("human_entered") is not True:
        raise SynthesisGovernanceError("Governance decision não está marcada como humana")
    if decision.get("source_revalidated_at_decision") is not True:
        raise SynthesisGovernanceError("Source não foi revalidado na decisão de governance")

    content_sha = str(entry.get("source_content_sha256") or "")
    brief = _read_json(_artifact_path(root, content_sha), "source Brief")
    validated = validate_brief(brief, output_root=output_root)
    if validated["content_sha256"] != content_sha:
        raise SynthesisGovernanceError("Source Brief diverge do registry entry")
    if validated["context_fingerprint"] != entry.get("source_context_fingerprint"):
        raise SynthesisGovernanceError("Context fingerprint diverge do registry entry")

    decisions = brief.get("reviewed_decisions") or []
    relationship_counts = brief.get("relationship_counts") or {}
    domain_counts = brief.get("domain_counts") or {}
    comparability_counts = brief.get("comparability_counts") or {}

    scientific_content = {
        "release_type": RELEASE_TYPE,
        "canonical": False,
        "release_scope": "GOVERNED_DISSEMINATION_PACKAGE",
        "source_registry_artifact_id": artifact_id,
        "source_registry_status": APPROVED,
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
        "relationship_counts": relationship_counts,
        "domain_counts": domain_counts,
        "comparability_counts": comparability_counts,
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
            "It is not a canonical scientific synthesis, certainty assessment, meta-analysis, or PRISMA output."
        ),
    }
