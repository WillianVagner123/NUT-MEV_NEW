"""Automatic final Article 1 outputs after all human scientific decisions close.

This module does not make screening, ABCD, relation, PRESS or FREEZE decisions.
It only serializes already-resolved FORMAL state into reproducible manuscript-
facing artifacts and an integrity-checked completion manifest.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.review.article1_runtime import (
    article1_export_bundle,
    article1_runtime_status,
    create_article1_synthesis_snapshot,
)
from nutev.review.article1_screening_runtime import (
    formal_screening_status,
    full_text_queue,
    title_abstract_queue,
)
from nutev.review.article_screening_ledger import get_screening_session
from nutev.search.corpus_build_ledger import get_corpus_build
from nutev.search.strategy_registry import default_registry_path, get_strategy_version

FINAL_SCHEMA_VERSION = 1


def _sha256_file(path: Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return _sha256_file(path)


def _atomic_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    return _sha256_file(path)


def _formal_lineage(db_path: Path, session_id: str) -> dict[str, Any]:
    session = get_screening_session(db_path, session_id)
    if not session:
        raise ValueError(f"unknown screening session: {session_id}")
    build = get_corpus_build(db_path, str(session["build_id"]))
    if not build or str(build.get("status") or "") != "SUCCEEDED":
        raise ValueError("final outputs require a successful immutable corpus build")
    version = get_strategy_version(db_path, str(build["version_id"]))
    if not version:
        raise ValueError("strategy version for the FORMAL corpus is missing")
    if str(version.get("search_type") or "").upper() != "FORMAL":
        raise ValueError("final Article 1 outputs require a FORMAL strategy version")
    if not bool(version.get("prisma_eligible")):
        raise ValueError("the FORMAL strategy is not PRISMA-eligible")
    return {"session": session, "build": build, "version": version}


def _screening_rows(
    db_path: Path,
    *,
    session_id: str,
    project_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    title = title_abstract_queue(db_path, session_id=session_id)
    full = full_text_queue(db_path, session_id=session_id, project_root=project_root)
    if any(not row.get("final_action") for row in title):
        raise ValueError("title/abstract screening still contains unresolved records")
    if any(not row.get("final_action") for row in full):
        raise ValueError("full-text screening still contains unresolved records")
    return title, full


def _prisma_payload(
    *,
    session_id: str,
    build_id: str,
    version_id: str,
    title_rows: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    title_excluded = sum(row.get("final_action") == "EXCLUDE" for row in title_rows)
    advanced = sum(row.get("final_action") == "ADVANCE" for row in title_rows)
    full_excluded = sum(row.get("final_decision") == "EXCLUDE" for row in full_rows)
    included = sum(row.get("final_decision") == "INCLUDE" for row in full_rows)
    return {
        "schema_version": 1,
        "article_id": "article_1",
        "execution_mode": "FORMAL",
        "prisma_eligible": True,
        "session_id": session_id,
        "build_id": build_id,
        "version_id": version_id,
        "records_after_automatic_deduplication": len(title_rows),
        "records_screened_title_abstract": len(title_rows),
        "records_excluded_title_abstract": title_excluded,
        "reports_sought_for_retrieval_or_full_text_assessment": advanced,
        "reports_assessed_for_eligibility": len(full_rows),
        "reports_excluded_full_text": full_excluded,
        "reports_included_article_1": included,
        "unresolved_title_abstract": 0,
        "unresolved_full_text": 0,
        "human_decision_inferred": False,
        "note": (
            "Counts are derived only from the resolved dual-review FORMAL Article 1 ledger. "
            "PILOT/STAGING/CALIBRATION records contribute zero to these counts."
        ),
    }


def _screening_export_rows(
    title_rows: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    title_by_id = {str(row["document_id"]): row for row in title_rows}
    full_by_id = {str(row["document_id"]): row for row in full_rows}
    output: list[dict[str, Any]] = []
    for document_id, title in sorted(title_by_id.items()):
        full = full_by_id.get(document_id) or {}
        output.append(
            {
                "document_id": document_id,
                "title": title.get("title", ""),
                "doi": title.get("doi", ""),
                "pmid": title.get("pmid", ""),
                "title_abstract_status": title.get("status", ""),
                "title_abstract_final_action": title.get("final_action", ""),
                "full_text_status": full.get("status", "NOT_APPLICABLE"),
                "full_text_final_decision": full.get("final_decision", ""),
                "final_family": full.get("final_family", ""),
                "full_text_path": full.get("full_text_path", ""),
            }
        )
    return output


def build_article1_final_outputs(
    project_root: Path,
    *,
    formal_summary: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    """Generate the terminal audit/manuscript package from resolved FORMAL state."""
    project = Path(project_root)
    scientific = formal_summary.get("scientific_state") or {}
    if str(scientific.get("search_type") or "").upper() != "FORMAL":
        raise ValueError("a FORMAL execution summary is required")
    if not bool(scientific.get("formal_freeze_authorized")):
        raise ValueError("final outputs are blocked without an authorized immutable FREEZE")

    db_path = default_registry_path(project)
    lineage = _formal_lineage(db_path, session_id)
    build = lineage["build"]
    version = lineage["version"]
    screening = formal_screening_status(
        db_path,
        session_id=session_id,
        project_root=project,
    )
    if screening.get("phase") != "SCREENING_COMPLETE":
        raise ValueError("final outputs are blocked until dual-review screening is complete")

    title_rows, full_rows = _screening_rows(
        db_path,
        session_id=session_id,
        project_root=project,
    )
    included = int(screening.get("included_documents") or 0)
    runtime = article1_runtime_status(db_path, session_id=session_id)
    if included and not bool(runtime.get("synthesis_ready")):
        raise ValueError("final outputs are blocked until ABCD and relation review are closed")

    prisma = _prisma_payload(
        session_id=session_id,
        build_id=str(build["build_id"]),
        version_id=str(version["version_id"]),
        title_rows=title_rows,
        full_rows=full_rows,
    )
    if int(prisma["reports_included_article_1"]) != included:
        raise ValueError("screening inclusion count is inconsistent with the final PRISMA payload")

    if included:
        synthesis_snapshot = create_article1_synthesis_snapshot(
            db_path,
            session_id=session_id,
            strict=True,
        )
        export_bundle = article1_export_bundle(db_path, session_id=session_id)
        synthesis = synthesis_snapshot["payload"]
    else:
        synthesis_snapshot = None
        synthesis = {
            "session_id": session_id,
            "execution_mode": "FORMAL",
            "included_documents": 0,
            "closed_documents": 0,
            "ready": True,
            "components": [],
            "cooccurrence": [],
            "explicit_relations": [],
            "method_characterization": [],
            "interpretation": "No documents were finally included after resolved dual review.",
        }
        export_bundle = {
            "status": runtime,
            "codebook": [],
            "final_abcd": [],
            "final_relations": [],
            "synthesis": synthesis,
        }

    output_dir = project / "08_exports" / "article1_final"
    output_dir.mkdir(parents=True, exist_ok=True)
    prisma_path = output_dir / "article1_prisma.json"
    synthesis_path = output_dir / "article1_synthesis.json"
    bundle_path = output_dir / "article1_export_bundle.json"
    screening_path = output_dir / "article1_screening_resolutions.csv"
    manifest_path = output_dir / "manifest.json"

    screening_rows = _screening_export_rows(title_rows, full_rows)
    hashes = {
        "prisma_sha256": _atomic_json(prisma_path, prisma),
        "synthesis_sha256": _atomic_json(synthesis_path, synthesis),
        "export_bundle_sha256": _atomic_json(bundle_path, export_bundle),
        "screening_resolutions_sha256": _atomic_csv(
            screening_path,
            screening_rows,
            [
                "document_id",
                "title",
                "doi",
                "pmid",
                "title_abstract_status",
                "title_abstract_final_action",
                "full_text_status",
                "full_text_final_decision",
                "final_family",
                "full_text_path",
            ],
        ),
    }
    latest_summary_path = project / "12_play" / "latest_summary.json"
    manifest = {
        "schema_version": FINAL_SCHEMA_VERSION,
        "status": "SUCCEEDED",
        "article_id": "article_1",
        "execution_mode": "FORMAL",
        "session_id": session_id,
        "build_id": str(build["build_id"]),
        "version_id": str(version["version_id"]),
        "prisma_eligible": True,
        "included_documents": included,
        "synthesis_ready": bool(synthesis.get("ready")),
        "synthesis_snapshot_id": (
            str(synthesis_snapshot.get("snapshot_id") or "") if synthesis_snapshot else ""
        ),
        "inputs": {
            "formal_summary_path": str(latest_summary_path),
            "formal_summary_sha256": (
                _sha256_file(latest_summary_path) if latest_summary_path.is_file() else ""
            ),
            "corpus_manifest_path": str(build.get("manifest_path") or ""),
            "corpus_manifest_sha256": str(build.get("manifest_sha256") or ""),
        },
        "outputs": {
            "prisma_path": str(prisma_path),
            "synthesis_path": str(synthesis_path),
            "export_bundle_path": str(bundle_path),
            "screening_resolutions_path": str(screening_path),
            **hashes,
        },
        "governance": {
            "human_decision_inferred": False,
            "pilot_counts_included": False,
            "formal_freeze_required": True,
            "dual_review_required": True,
        },
    }
    manifest_sha256 = _atomic_json(manifest_path, manifest)
    return {
        "status": "SUCCEEDED",
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "prisma": prisma,
        "synthesis": synthesis,
        "outputs": manifest["outputs"],
    }


def final_outputs_status(project_root: Path, *, session_id: str) -> dict[str, Any]:
    """Validate an existing final package without creating or authorizing anything."""
    manifest_path = Path(project_root) / "08_exports" / "article1_final" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"complete": False, "manifest_path": str(manifest_path), "blockers": ["manifest_missing_or_invalid"]}
    if not isinstance(manifest, dict):
        return {"complete": False, "manifest_path": str(manifest_path), "blockers": ["manifest_invalid"]}
    blockers: list[str] = []
    if str(manifest.get("status") or "") != "SUCCEEDED":
        blockers.append("manifest_not_succeeded")
    if str(manifest.get("session_id") or "") != str(session_id):
        blockers.append("session_mismatch")
    outputs = manifest.get("outputs") or {}
    for path_key, hash_key in (
        ("prisma_path", "prisma_sha256"),
        ("synthesis_path", "synthesis_sha256"),
        ("export_bundle_path", "export_bundle_sha256"),
        ("screening_resolutions_path", "screening_resolutions_sha256"),
    ):
        path = Path(str(outputs.get(path_key) or ""))
        expected = str(outputs.get(hash_key) or "")
        if not path.is_file():
            blockers.append(f"missing:{path_key}")
        elif not expected or _sha256_file(path) != expected:
            blockers.append(f"hash_mismatch:{path_key}")
    return {
        "complete": not blockers,
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "blockers": blockers,
    }


__all__ = ["build_article1_final_outputs", "final_outputs_status"]
