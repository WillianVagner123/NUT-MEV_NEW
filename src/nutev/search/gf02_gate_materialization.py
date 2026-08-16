"""Build the auditable GF-02 pre-PRESS gate from already-persisted PILOT evidence.

This module is deterministic and never chooses a human decision. It exists so a
completed PubMed PILOT + rescue-only review always yields the gate artifact the
UI expects, including after an Engine upgrade/resume.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.review.gf02_noise_review import read_rescue_only_sample, review_progress
from nutev.search.gf02_evidence import validate_sentinel_registry
from nutev.search.gf02_prepress_gate import evaluate_gf02_prepress_gate
from nutev.search.gf02_pubmed_pilot import load_candidate_config, load_sentinel_registry


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink()


def _current_manifest(repo_root: Path, project_root: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    repo = Path(repo_root)
    project = Path(project_root)
    config = load_candidate_config(repo / "config" / "gf02_pubmed_candidates.json")
    candidate = str(config.get("current_candidate") or "").strip()
    if not candidate:
        raise ValueError("GF-02 current_candidate is missing")

    root = project / "07_logs" / "gf02" / "pubmed"
    matches: list[tuple[float, Path, dict[str, Any]]] = []
    if root.is_dir():
        for path in root.glob("*/run_manifest.json"):
            payload = _load_json(path)
            if str(payload.get("candidate_version") or "") != candidate:
                continue
            try:
                stamp = path.stat().st_mtime
            except OSError:
                stamp = 0.0
            matches.append((stamp, path, payload))
    if not matches:
        raise FileNotFoundError(f"GF-02 PILOT manifest not found for candidate {candidate}")

    _, path, manifest = max(matches, key=lambda item: item[0])
    if manifest.get("status") != "SUCCEEDED":
        raise ValueError("GF-02 gate cannot be materialized from a non-successful PILOT manifest")
    if str(manifest.get("search_type") or "").upper() != "PILOT":
        raise ValueError("GF-02 gate requires a PILOT manifest")
    if manifest.get("prisma_eligible") is not False:
        raise ValueError("GF-02 PILOT manifest must remain PRISMA-ineligible")
    return manifest, path, config


def _sentinel_recall(
    repo_root: Path,
    *,
    manifest: dict[str, Any],
    priority_ids: list[str],
) -> dict[str, Any]:
    registry = load_sentinel_registry(Path(repo_root) / "config" / "article1_sentinel_registry.json")
    validate_sentinel_registry(registry)
    by_id = {item.sentinel_id: item for item in registry}
    mechanism = manifest.get("priority_sentinel_mechanism") or {}
    final_line = str(manifest.get("final_line") or "#7")

    recovered: list[str] = []
    missing: list[str] = []
    unresolved: list[str] = []
    for sentinel_id in priority_ids:
        record = by_id.get(sentinel_id)
        if record is None or str(record.identity_status or "").upper() != "RESOLVED":
            unresolved.append(sentinel_id)
            continue
        final_recovered = bool((mechanism.get(sentinel_id) or {}).get(final_line))
        if final_recovered:
            recovered.append(sentinel_id)
        else:
            missing.append(sentinel_id)

    return {
        "recovered_sentinel_ids": recovered,
        "missing_resolved_sentinel_ids": missing,
        "unresolved_sentinel_ids": unresolved,
    }


def materialize_gf02_prepress_gate(repo_root: Path, project_root: Path) -> dict[str, Any]:
    """Create/update ``gate_status.json`` from current real PILOT evidence.

    Existing human decision fields are preserved only when both the PILOT
    manifest and reviewed rescue-only sample hashes are unchanged. A changed
    evidence basis clears the current decision but keeps the historical records.
    """
    repo = Path(repo_root)
    project = Path(project_root)
    manifest, manifest_path, config = _current_manifest(repo, project)

    sample_path = Path(str(manifest.get("rescue_only_sample") or ""))
    if not sample_path.is_file():
        raise FileNotFoundError(f"GF-02 rescue-only sample not found: {sample_path}")
    rows = read_rescue_only_sample(sample_path)
    progress = review_progress(sample_path)

    priority_ids = [str(item) for item in (config.get("priority_expectations") or {}).keys()]
    if not priority_ids:
        raise ValueError("GF-02 priority sentinel set is empty")
    recall = _sentinel_recall(repo, manifest=manifest, priority_ids=priority_ids)

    classification_counts: dict[str, int] = {}
    for row in rows:
        label = str(row.get("classification") or "").strip().upper()
        if label:
            classification_counts[label] = classification_counts.get(label, 0) + 1

    gate_path = project / "07_logs" / "gf02" / "gate_status.json"
    existing = _load_json(gate_path)
    manifest_sha = _sha256(manifest_path)
    sample_sha = _sha256(sample_path)
    same_basis = bool(
        existing
        and existing.get("source_manifest_sha256") == manifest_sha
        and existing.get("source_sample_sha256") == sample_sha
    )

    human_decision = str(existing.get("human_decision") or "") if same_basis else ""
    human_decision_by = str(existing.get("human_decision_by") or "") if same_basis else ""
    missing_explanations = existing.get("missing_explanations") if same_basis else {}
    if not isinstance(missing_explanations, dict):
        missing_explanations = {}

    evaluated = evaluate_gf02_prepress_gate(
        strategy_version=manifest,
        pubmed_recall=recall,
        noise_summary={
            "sample_size": len(rows) if progress.get("complete") else 0,
            "classification_counts": classification_counts,
            "precision_estimated": False,
        },
        priority_sentinels=tuple(priority_ids),
        missing_explanations=missing_explanations,
        human_decision=human_decision or None,
        human_decision_by=human_decision_by,
    )

    history = existing.get("human_decision_history") or []
    if not isinstance(history, list):
        history = []
    payload = {
        **evaluated,
        "candidate_version": manifest.get("candidate_version"),
        "run_id": manifest.get("run_id"),
        "source_manifest_path": str(manifest_path),
        "source_manifest_sha256": manifest_sha,
        "source_sample_path": str(sample_path),
        "source_sample_sha256": sample_sha,
        "sample_review_complete": bool(progress.get("complete")),
        "sample_size": len(rows),
        "sample_classification_counts": classification_counts,
        "precision_estimated": False,
        "pubmed_sentinel_evidence": recall,
        "human_decision_history": history,
        "evidence_basis_changed": bool(existing and not same_basis),
        "press_approval_inferred": False,
        "formal_execution_authorized": False,
        "prisma_eligible": False,
    }
    if same_basis:
        for key in ("human_decision_rationale", "human_decision_at"):
            if key in existing:
                payload[key] = existing[key]
    _atomic_json(gate_path, payload)
    return payload


__all__ = ["materialize_gf02_prepress_gate"]
