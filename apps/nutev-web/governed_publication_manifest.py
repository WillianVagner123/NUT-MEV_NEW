from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Mapping

from governed_synthesis_release import (
    DEFAULT_OUTPUT_ROOT,
    RELEASE_RECORD_TYPE,
    RELEASE_TYPE,
    _atomic_json,
    _digest,
    _package_path,
    _read_json,
    _record_path,
    _release_root,
    build_governed_release,
)
from synthesis_governance import SynthesisGovernanceError

MANIFEST_TYPE = "NUTEV_GOVERNED_PUBLICATION_MANIFEST_V1"
MANIFEST_RECORD_TYPE = "NUTEV_GOVERNED_PUBLICATION_MANIFEST_RECORD_V1"
STATEMENT_TYPE = "NUTEV_PUBLICATION_STATEMENT_CANDIDATE_V1"
_MANIFEST_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_root(output_root: Path) -> Path:
    return output_root / "scientific" / "publication_manifests"


def _manifest_path(root: Path, manifest_id: str) -> Path:
    return root / "manifests" / f"{manifest_id}.json"


def _manifest_record_path(root: Path, manifest_id: str) -> Path:
    return root / "records" / f"{manifest_id}.json"


def _release_scientific_content(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: package[key]
        for key in package
        if key not in {"content_sha256", "generated_at", "artifact_semantics"}
    }


def _source_identifiers(document_id: str) -> dict[str, str]:
    raw = str(document_id or "").strip()
    lowered = raw.casefold()
    if lowered.startswith("doi:"):
        return {"doi": raw[4:]}
    if lowered.startswith("pmid:"):
        return {"pmid": raw[5:]}
    if lowered.startswith("pmcid:"):
        return {"pmcid": raw[6:]}
    return {"document_id": raw} if raw else {}


def _citation_entry(
    snapshot: Mapping[str, Any], *, decision_id: str, role: str, citation_id: str
) -> dict[str, Any]:
    document_id = str(snapshot.get("document_id") or "").strip()
    title = str(snapshot.get("title") or "").strip()
    bundle_id = str(snapshot.get("bundle_id") or "").strip()
    result_text = str(snapshot.get("result_text") or "").strip()
    if not document_id or not title or not bundle_id or not result_text:
        raise SynthesisGovernanceError(
            f"Publication citation incompleta em {decision_id}:{role}"
        )
    return {
        "citation_id": citation_id,
        "decision_id": decision_id,
        "role": role,
        "document_id": document_id,
        "title": title,
        "identifiers": _source_identifiers(document_id),
        "bundle_id": bundle_id,
        "source_sentence_sha256": str(snapshot.get("source_sentence_sha256") or ""),
        "result_text": result_text,
        "outcomes": snapshot.get("outcomes") or [],
        "effect_measures": snapshot.get("effect_measures") or [],
        "confidence_intervals": snapshot.get("confidence_intervals") or [],
        "p_values": snapshot.get("p_values") or [],
        "routes": snapshot.get("routes") or [],
        "source_reference": snapshot.get("source_reference"),
        "citation_semantics": (
            "Source-linked snapshot used in a human synthesis decision. This citation entry does "
            "not establish study validity, eligibility, certainty, causality, or an accepted EvidenceClaim."
        ),
    }


def _statement_candidate(
    decision: Mapping[str, Any], *, decision_id: str, citation_ids: list[str]
) -> dict[str, Any]:
    relation = str(decision.get("relation") or "").strip()
    domain_label = str(decision.get("domain_label") or decision.get("domain") or "").strip()
    reviewer = str(decision.get("reviewer") or "").strip()
    rationale = str(decision.get("rationale") or "").strip()
    if not relation or not reviewer or len(rationale) < 20:
        raise SynthesisGovernanceError(f"Human decision inválida em {decision_id}")
    statement = (
        f"In the governed human synthesis review, the source-linked pair in {domain_label or 'this domain'} "
        f"was classified by the reviewer as {relation}."
    )
    return {
        "statement_type": STATEMENT_TYPE,
        "statement_id": f"statement_{_digest({'decision_id': decision_id, 'relation': relation})[:24]}",
        "decision_id": decision_id,
        "statement_text": statement,
        "relation": relation,
        "domain": decision.get("domain"),
        "domain_label": domain_label,
        "reviewer": reviewer,
        "human_rationale": rationale,
        "citation_ids": citation_ids,
        "publication_status": "CANDIDATE_ONLY",
        "accepted_evidence_claim": False,
        "machine_inferred_scientific_claim": False,
        "requires_human_author_editing": True,
        "statement_semantics": (
            "Describes a recorded human synthesis judgement only. It must not be rewritten as "
            "evidence certainty, causal proof, clinical recommendation, or scientific consensus."
        ),
    }


def _validated_release(
    package_id: str, *, output_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    package_id = str(package_id or "").strip()
    if not package_id:
        raise SynthesisGovernanceError("Release package id obrigatório")
    root = _release_root(output_root)
    record = _read_json(_record_path(root, package_id), "release record")
    package = _read_json(_package_path(root, package_id), "release package")
    if record.get("release_record_type") != RELEASE_RECORD_TYPE:
        raise SynthesisGovernanceError("Release record type inválido")
    if package.get("release_type") != RELEASE_TYPE or package.get("canonical") is not False:
        raise SynthesisGovernanceError("Release package inválido ou indevidamente canônico")
    if record.get("canonical_release_record") is not True:
        raise SynthesisGovernanceError("Release record não é trilha operacional canônica")
    if record.get("release_package_canonical") is not False:
        raise SynthesisGovernanceError("Release record declara package canônico indevidamente")
    if record.get("canonical_scientific_synthesis_created") is not False:
        raise SynthesisGovernanceError("Release record declara síntese científica canônica")

    expected_sha = _digest(_release_scientific_content(package))
    if str(package.get("content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("Release package content SHA-256 inválido")
    if str(record.get("package_content_sha256") or "") != expected_sha:
        raise SynthesisGovernanceError("Release record diverge do package SHA-256")

    rebuilt = build_governed_release(
        str(package.get("source_registry_artifact_id") or ""),
        prepared_by=str(package.get("prepared_by") or ""),
        purpose=str(package.get("purpose") or ""),
        output_root=output_root,
    )
    if rebuilt.get("content_sha256") != expected_sha:
        raise SynthesisGovernanceError(
            "Release package não corresponde mais ao contexto científico atual; prepare novo release"
        )
    return record, package


def build_publication_manifest(
    package_id: str,
    *,
    publication_owner: str,
    intended_use: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    publication_owner = str(publication_owner or "").strip()
    intended_use = str(intended_use or "").strip()
    if not publication_owner:
        raise SynthesisGovernanceError("Identifique o responsável pelo publication manifest")
    if len(intended_use) < 20:
        raise SynthesisGovernanceError("Intended use precisa ter pelo menos 20 caracteres")

    record, release = _validated_release(package_id, output_root=output_root)
    decisions = release.get("reviewed_decisions")
    if not isinstance(decisions, list) or not decisions:
        raise SynthesisGovernanceError("Release sem decisões humanas source-linked")

    citations: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    seen_decisions: set[str] = set()
    for index, raw_decision in enumerate(decisions, start=1):
        if not isinstance(raw_decision, Mapping):
            raise SynthesisGovernanceError("Decision inválida no release")
        decision = dict(raw_decision)
        decision_id = str(decision.get("decision_id") or "").strip()
        if not decision_id or decision_id in seen_decisions:
            raise SynthesisGovernanceError("Decision id ausente ou duplicado no release")
        seen_decisions.add(decision_id)
        anchor = decision.get("anchor")
        candidate = decision.get("candidate")
        if not isinstance(anchor, Mapping) or not isinstance(candidate, Mapping):
            raise SynthesisGovernanceError(f"Snapshots ausentes em {decision_id}")
        anchor_id = f"CIT-{index:04d}-A"
        candidate_id = f"CIT-{index:04d}-B"
        citations.append(
            _citation_entry(anchor, decision_id=decision_id, role="anchor", citation_id=anchor_id)
        )
        citations.append(
            _citation_entry(
                candidate,
                decision_id=decision_id,
                role="candidate",
                citation_id=candidate_id,
            )
        )
        statements.append(
            _statement_candidate(
                decision,
                decision_id=decision_id,
                citation_ids=[anchor_id, candidate_id],
            )
        )

    content = {
        "manifest_type": MANIFEST_TYPE,
        "canonical": False,
        "publication_scope": "GOVERNED_PUBLICATION_PREPARATION",
        "source_release_package_id": package_id,
        "source_release_content_sha256": release["content_sha256"],
        "source_release_record_canonical": record["canonical_release_record"],
        "source_context_fingerprint": release["source_context_fingerprint"],
        "search_id": release["search_id"],
        "context_version": release["context_version"],
        "question": release["question"],
        "publication_owner": publication_owner,
        "intended_use": intended_use,
        "citation_bundle": citations,
        "statement_candidates": statements,
        "guardrails": {
            "source_release_revalidated_against_current_context": True,
            "publication_statements_are_candidate_only": True,
            "citations_are_source_linked_snapshots_not_validity_endorsements": True,
            "accepted_evidence_claims_created": False,
            "canonical_scientific_synthesis_created": False,
            "risk_of_bias_assessed": False,
            "certainty_assessed": False,
            "meta_analysis_performed": False,
            "prisma_event_emitted": False,
            "formal_search_state_changed": False,
            "clinical_recommendation_created": False,
            "relationship_counts_are_not_evidence_strength": True,
            "identity_cryptographically_authenticated": False,
            "external_llm_generated_scientific_claims": False,
        },
    }
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": _now(),
        "artifact_semantics": (
            "Governed publication-preparation manifest with source-linked citations and candidate "
            "statements describing recorded human judgements. It is not a canonical synthesis, "
            "accepted EvidenceClaim, certainty assessment, meta-analysis, or PRISMA output."
        ),
    }


def prepare_publication_manifest(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    manifest = build_publication_manifest(
        str(payload.get("package_id") or ""),
        publication_owner=str(payload.get("publication_owner") or ""),
        intended_use=str(payload.get("intended_use") or ""),
        output_root=output_root,
    )
    manifest_id = f"publication_{str(manifest['content_sha256'])[:24]}"
    root = _manifest_root(output_root)
    manifest_path = _manifest_path(root, manifest_id)
    record_path = _manifest_record_path(root, manifest_id)
    with _MANIFEST_LOCK:
        if manifest_path.is_file() and record_path.is_file():
            return {
                "record": _read_json(record_path, "publication manifest record"),
                "manifest": _read_json(manifest_path, "publication manifest"),
            }
        record = {
            "manifest_record_type": MANIFEST_RECORD_TYPE,
            "manifest_id": manifest_id,
            "manifest_type": MANIFEST_TYPE,
            "manifest_content_sha256": manifest["content_sha256"],
            "source_release_package_id": manifest["source_release_package_id"],
            "source_release_content_sha256": manifest["source_release_content_sha256"],
            "source_context_fingerprint": manifest["source_context_fingerprint"],
            "search_id": manifest["search_id"],
            "context_version": manifest["context_version"],
            "publication_owner": manifest["publication_owner"],
            "intended_use": manifest["intended_use"],
            "citation_count": len(manifest["citation_bundle"]),
            "statement_candidate_count": len(manifest["statement_candidates"]),
            "generated_at": manifest["generated_at"],
            "canonical_manifest_record": True,
            "publication_manifest_canonical": False,
            "accepted_evidence_claims_created": False,
            "canonical_scientific_synthesis_created": False,
            "scientific_boundary": (
                "This record proves that a publication-preparation manifest was produced from a "
                "revalidated governed release. It does not validate or accept scientific claims."
            ),
        }
        _atomic_json(manifest_path, manifest)
        _atomic_json(record_path, record)
    return {"record": record, "manifest": manifest}


def publication_status(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    directory = _manifest_root(output_root) / "records"
    records: list[dict[str, Any]] = []
    with _MANIFEST_LOCK:
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                try:
                    records.append(_read_json(path, path.name))
                except (FileNotFoundError, SynthesisGovernanceError):
                    continue
    records.sort(key=lambda item: str(item.get("generated_at") or ""), reverse=True)
    return {
        "status": "READY",
        "manifest_type": MANIFEST_TYPE,
        "count": len(records),
        "records": records,
        "scientific_boundary": (
            "Publication manifests contain citation bundles and candidate statements about recorded "
            "human judgements only. They do not create accepted EvidenceClaims, certainty, RoB, "
            "meta-analysis, PRISMA state, recommendations, or canonical scientific synthesis."
        ),
    }
