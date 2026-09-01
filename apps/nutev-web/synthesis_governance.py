from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import threading
from typing import Any, Mapping
from uuid import uuid4


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "project_output_reference"
REVIEW_TYPE = "NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1"
BRIEF_TYPE = "NUTEV_HUMAN_SYNTHESIS_BRIEF_V1"
ENTRY_TYPE = "NUTEV_SYNTHESIS_GOVERNANCE_ENTRY_V1"
REGISTRY_TYPE = "NUTEV_SYNTHESIS_GOVERNANCE_REGISTRY_V1"
STAGED = "STAGED"
APPROVED = "APPROVED_FOR_GOVERNED_USE"
REJECTED = "REJECTED_BY_GOVERNANCE"
DECISIONS = {"APPROVE": APPROVED, "REJECT": REJECTED}
_LOCK = threading.RLock()


class SynthesisGovernanceError(RuntimeError):
    pass


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


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} não encontrado: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SynthesisGovernanceError(f"{label} inválido") from exc
    if not isinstance(value, dict):
        raise SynthesisGovernanceError(f"{label} precisa ser objeto JSON")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _registry_root(output_root: Path) -> Path:
    return output_root / "scientific" / "synthesis_registry"


def _current_search_state(output_root: Path) -> dict[str, Any]:
    return _read_json(
        output_root / "agent_context" / "article1" / "SEARCH_STATE.json",
        "SEARCH_STATE.json",
    )


def context_fingerprint_source(search: Mapping[str, Any]) -> dict[str, Any]:
    runtime = search.get("runtime") or {}
    if not isinstance(runtime, Mapping):
        runtime = {}
    workbench = runtime.get("workbench") or {}
    routes = runtime.get("article1_routes") or {}
    profiles = runtime.get("review_profiles") or {}
    return {
        "search_id": search.get("search_id"),
        "context_version": search.get("context_version"),
        "question": search.get("question"),
        "workbench_database_sha256": (
            workbench.get("database_sha256") if isinstance(workbench, Mapping) else None
        ),
        "route_manifest_sha256": (
            routes.get("manifest_sha256") if isinstance(routes, Mapping) else None
        ),
        "review_profile_version": (
            profiles.get("profile_version") if isinstance(profiles, Mapping) else None
        ),
        "agent_article_summaries": runtime.get("agent_article_summaries"),
    }


def current_context_fingerprint(output_root: Path) -> tuple[dict[str, Any], str]:
    search = _current_search_state(output_root)
    source = context_fingerprint_source(search)
    return search, _digest(source)


def _brief_scientific_content(artifact: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {"content_sha256", "generated_at", "artifact_semantics"}
    return {key: artifact[key] for key in artifact if key not in excluded}


def _required_guardrails(artifact: Mapping[str, Any]) -> None:
    guardrails = artifact.get("guardrails")
    if not isinstance(guardrails, Mapping):
        raise SynthesisGovernanceError("Brief sem guardrails estruturados")
    required_true = {
        "source_review_is_noncanonical",
        "integrity_verification_is_not_scientific_validation",
        "integrity_verification_does_not_prove_authorship_or_authenticity",
        "relationship_counts_are_not_evidence_strength",
        "convergent_is_not_certainty",
        "divergent_is_not_proven_contradiction",
        "brief_is_not_meta_analysis",
        "brief_is_not_prisma",
    }
    required_false = {
        "accepted_evidence_claims_created",
        "risk_of_bias_assessed",
        "certainty_assessed",
        "formal_search_state_changed",
    }
    if any(guardrails.get(key) is not True for key in required_true):
        raise SynthesisGovernanceError("Brief perdeu guardrail científico obrigatório")
    if any(guardrails.get(key) is not False for key in required_false):
        raise SynthesisGovernanceError("Brief declara criação indevida de estado científico")


def _validate_decisions(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    decisions = artifact.get("reviewed_decisions")
    if not isinstance(decisions, list) or not decisions:
        raise SynthesisGovernanceError("Brief sem decisões humanas")
    seen: set[str] = set()
    valid_relations = {
        "CONVERGENT",
        "DIVERGENT",
        "COMPLEMENTARY",
        "NOT_COMPARABLE",
        "UNCLEAR",
    }
    valid_dimensions = {"SIMILAR", "DIFFERENT", "UNCLEAR", "NOT_AVAILABLE"}
    for item in decisions:
        if not isinstance(item, dict):
            raise SynthesisGovernanceError("Decisão humana inválida")
        decision_id = str(item.get("decision_id") or "")
        if not decision_id or decision_id in seen:
            raise SynthesisGovernanceError("Decision id ausente ou duplicado")
        seen.add(decision_id)
        if item.get("human_entered") is not True or item.get("canonical") is not False:
            raise SynthesisGovernanceError("Decisão não preserva semântica humana não canônica")
        if item.get("relation") not in valid_relations:
            raise SynthesisGovernanceError("Relação humana desconhecida")
        if not str(item.get("reviewer") or "").strip():
            raise SynthesisGovernanceError("Decisão sem revisor")
        if len(str(item.get("rationale") or "").strip()) < 20:
            raise SynthesisGovernanceError("Decisão sem justificativa suficiente")
        anchor = item.get("anchor") or {}
        candidate = item.get("candidate") or {}
        if not isinstance(anchor, Mapping) or not isinstance(candidate, Mapping):
            raise SynthesisGovernanceError("Snapshot de decisão inválido")
        anchor_id = str(anchor.get("document_id") or "")
        candidate_id = str(candidate.get("document_id") or "")
        if not anchor_id or not candidate_id or anchor_id == candidate_id:
            raise SynthesisGovernanceError("Par documental inválido")
        expected = "::".join(sorted((anchor_id, candidate_id)))
        if decision_id != expected:
            raise SynthesisGovernanceError("Decision id não corresponde ao par documental")
        comparability = item.get("comparability") or {}
        if not isinstance(comparability, Mapping):
            raise SynthesisGovernanceError("Comparabilidade inválida")
        for key in ("population", "construct_intervention", "outcome", "timeframe"):
            if comparability.get(key) not in valid_dimensions:
                raise SynthesisGovernanceError(f"Comparabilidade inválida em {key}")
    return decisions


def validate_brief(
    artifact: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    if artifact.get("export_type") != BRIEF_TYPE:
        raise SynthesisGovernanceError("Artifact type não é Human Synthesis Brief V1")
    if artifact.get("canonical") is not False:
        raise SynthesisGovernanceError("Somente Brief não canônico pode entrar no registry")
    if artifact.get("integrity_verified") is not True:
        raise SynthesisGovernanceError("Brief não declara integridade verificada")
    if artifact.get("current_context_match") is not True:
        raise SynthesisGovernanceError("Brief não declara vínculo com contexto atual")
    if artifact.get("source_review_type") != REVIEW_TYPE:
        raise SynthesisGovernanceError("Brief não deriva do Human Synthesis Review V1")
    _required_guardrails(artifact)
    decisions = _validate_decisions(artifact)

    expected_content_sha = str(artifact.get("content_sha256") or "").strip().lower()
    actual_content_sha = _digest(_brief_scientific_content(artifact))
    if not expected_content_sha or expected_content_sha != actual_content_sha:
        raise SynthesisGovernanceError("Content SHA-256 do Brief diverge")

    search, current_fingerprint = current_context_fingerprint(output_root)
    source_fingerprint = str(artifact.get("source_context_fingerprint") or "").strip()
    if not source_fingerprint or source_fingerprint != current_fingerprint:
        raise SynthesisGovernanceError("Context fingerprint do Brief não corresponde ao runtime atual")
    if artifact.get("search_id") != search.get("search_id"):
        raise SynthesisGovernanceError("Search id do Brief diverge do runtime atual")
    if artifact.get("context_version") != search.get("context_version"):
        raise SynthesisGovernanceError("Context version do Brief diverge do runtime atual")
    if search.get("question") and artifact.get("question") != search.get("question"):
        raise SynthesisGovernanceError("Pergunta do Brief diverge do runtime atual")

    return {
        "content_sha256": actual_content_sha,
        "context_fingerprint": current_fingerprint,
        "search_id": search.get("search_id"),
        "context_version": search.get("context_version"),
        "question": search.get("question"),
        "reviewer": artifact.get("reviewer"),
        "decision_count": len(decisions),
    }


def _entry_path(root: Path, artifact_id: str) -> Path:
    return root / "entries" / f"{artifact_id}.json"


def _artifact_path(root: Path, content_sha: str) -> Path:
    return root / "artifacts" / f"{content_sha}.json"


def _load_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    directory = root / "entries"
    if not directory.is_dir():
        return entries
    for path in sorted(directory.glob("*.json")):
        try:
            entries.append(_read_json(path, path.name))
        except (FileNotFoundError, SynthesisGovernanceError):
            continue
    return entries


def registry_status(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    root = _registry_root(output_root)
    with _LOCK:
        entries = _load_entries(root)
    counts = {STAGED: 0, APPROVED: 0, REJECTED: 0}
    for entry in entries:
        status = str(entry.get("status") or "")
        counts[status] = counts.get(status, 0) + 1
    entries.sort(key=lambda item: str(item.get("staged_at") or ""), reverse=True)
    return {
        "registry_type": REGISTRY_TYPE,
        "status": "READY",
        "counts": counts,
        "entries": entries,
        "scientific_boundary": (
            "Registry status records governance workflow only. STAGED is not approved; "
            "APPROVED_FOR_GOVERNED_USE is not evidence certainty, RoB, meta-analysis, PRISMA, "
            "or a claim that reviewer identity was cryptographically authenticated."
        ),
    }


def stage_brief(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    actor = str(payload.get("actor") or "").strip()
    artifact = payload.get("artifact")
    if not actor:
        raise SynthesisGovernanceError("Identifique quem está registrando o artefato")
    if not isinstance(artifact, Mapping):
        raise SynthesisGovernanceError("Payload sem artifact JSON")
    validated = validate_brief(artifact, output_root=output_root)
    content_sha = str(validated["content_sha256"])
    artifact_id = f"brief_{content_sha[:24]}"
    root = _registry_root(output_root)
    entry_path = _entry_path(root, artifact_id)
    artifact_path = _artifact_path(root, content_sha)
    with _LOCK:
        if entry_path.is_file():
            return _read_json(entry_path, entry_path.name)
        _atomic_json(artifact_path, artifact)
        entry = {
            "registry_entry_type": ENTRY_TYPE,
            "artifact_id": artifact_id,
            "source_artifact_type": BRIEF_TYPE,
            "source_artifact_canonical": False,
            "source_content_sha256": content_sha,
            "source_context_fingerprint": validated["context_fingerprint"],
            "search_id": validated["search_id"],
            "context_version": validated["context_version"],
            "question": validated["question"],
            "reviewer": validated["reviewer"],
            "decision_count": validated["decision_count"],
            "status": STAGED,
            "staged_by": actor,
            "staged_at": _now(),
            "governance_decision": None,
            "canonical_registry_record": True,
            "canonical_scientific_synthesis_created": False,
            "reviewer_identity_cryptographically_authenticated": False,
            "scientific_boundary": (
                "This entry is an authoritative record of registry/governance state only. "
                "Staging does not approve the science and does not make the source Brief canonical."
            ),
        }
        _atomic_json(entry_path, entry)
    return entry


def decide_entry(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    artifact_id = str(payload.get("artifact_id") or "").strip()
    action = str(payload.get("action") or "").strip().upper()
    governor = str(payload.get("governor") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    if not artifact_id:
        raise SynthesisGovernanceError("Artifact id obrigatório")
    if action not in DECISIONS:
        raise SynthesisGovernanceError("Ação precisa ser APPROVE ou REJECT")
    if not governor:
        raise SynthesisGovernanceError("Identifique o responsável pela decisão de governance")
    if len(rationale) < 20:
        raise SynthesisGovernanceError("Justificativa de governance precisa ter pelo menos 20 caracteres")

    root = _registry_root(output_root)
    entry_path = _entry_path(root, artifact_id)
    with _LOCK:
        entry = _read_json(entry_path, "registry entry")
        if entry.get("status") != STAGED:
            return entry
        content_sha = str(entry.get("source_content_sha256") or "")
        artifact = _read_json(_artifact_path(root, content_sha), "source Brief")
        validated = validate_brief(artifact, output_root=output_root)
        if validated["content_sha256"] != content_sha:
            raise SynthesisGovernanceError("Source Brief diverge do registry entry")
        decided_at = _now()
        entry["status"] = DECISIONS[action]
        entry["governance_decision"] = {
            "action": action,
            "governor": governor,
            "rationale": rationale,
            "decided_at": decided_at,
            "human_entered": True,
            "identity_cryptographically_authenticated": False,
            "source_revalidated_at_decision": True,
        }
        entry["updated_at"] = decided_at
        entry["canonical_scientific_synthesis_created"] = False
        _atomic_json(entry_path, entry)
    return entry
