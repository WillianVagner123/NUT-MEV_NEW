"""Resumable FORMAL computational chain for the one-button Article 1 engine.

This module runs only a strategy that passes the existing execution-edge formal
authorization guard. It does not perform human screening, PRESS, FREEZE, or
adjudication. Those states must already exist as real evidence before this chain
can start.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests

from nutev.__version__ import __version__
from nutev.acquire.fulltext_resolver import resolve_many
from nutev.download.downloader import download_records
from nutev.extract.smart_extract import extract_document
from nutev.language import detect_language, normalize_language_code
from nutev.pipelines.document_bundle import build_document_bundle_index
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_execution_ledger import (
    get_search_run,
    list_execution_artifacts,
)
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import (
    default_registry_path,
    get_strategy_version,
    list_strategy_versions,
)

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
FORMAL_CHAIN_SCHEMA_VERSION = 1
ProgressFn = Callable[[str], None]


def _now_iso() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            handle.write("\n")
    tmp.replace(path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not Path(path).is_file():
        return rows
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _emit(progress_fn: ProgressFn | None, message: str) -> None:
    if progress_fn is not None:
        progress_fn(message)


def latest_formal_strategy(project_root: Path) -> dict[str, Any] | None:
    db_path = default_registry_path(project_root)
    versions = list_strategy_versions(db_path, limit=100)
    return next(
        (
            version
            for version in versions
            if str(version.get("search_type") or "").upper() == "FORMAL"
            and bool(version.get("prisma_eligible"))
        ),
        None,
    )


def _provider_rows(project_root: Path, run_id: str) -> list[dict[str, Any]]:
    artifacts = list_execution_artifacts(default_registry_path(project_root), run_id=run_id)
    rows: list[dict[str, Any]] = []
    for item in artifacts:
        total = item.get("total_found")
        returned = int(item.get("records_returned") or 0)
        rows.append(
            {
                "provider": str(item.get("provider") or ""),
                "status": str(item.get("provider_status") or ""),
                "total_found": int(total) if total is not None else None,
                "records_returned": returned,
                "truncated": total is not None and returned < int(total),
                "snapshot_path": str(item.get("snapshot_path") or ""),
                "snapshot_sha256": str(item.get("snapshot_sha256") or ""),
                "exact_expression": str(item.get("exact_expression") or ""),
            }
        )
    return rows


def _existing_search_summary(project_root: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    stage = (state.get("stages") or {}).get("search") or {}
    run_id = str(stage.get("run_id") or "")
    if not run_id:
        return None
    run = get_search_run(default_registry_path(project_root), run_id)
    if not run or str(run.get("status") or "") not in {"SUCCEEDED", "PARTIAL"}:
        return None
    manifest = _load_json(Path(str(run.get("manifest_path") or "")))
    if not manifest:
        return None
    return {
        **run,
        "formal_authorization": manifest.get("formal_authorization") or {},
        "records_identified_before_deduplication": int(run.get("records_identified") or 0),
        "provider_reported_total_found": int(run.get("provider_reported_total_found") or 0),
        "providers": manifest.get("providers") or [],
    }


def _annotate_extraction_language(
    extracted: dict[str, Any],
    *,
    declared_language: object,
) -> dict[str, Any]:
    row = dict(extracted)
    text_path = Path(str(row.get("text_path") or ""))
    text = ""
    if text_path.is_file():
        try:
            text = text_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
    detection = detect_language(text, declared=declared_language)
    row["language_original"] = normalize_language_code(declared_language) or None
    row["language_detected"] = detection.get("detected_language")
    row["language_detection_confidence"] = detection.get("confidence")
    row["language_detection_method"] = detection.get("method")
    return row


def run_or_resume_formal_chain(
    project_root: Path,
    *,
    progress_fn: ProgressFn | None = None,
    logger: logging.Logger | None = None,
    provider_limit: int = 10000,
) -> dict[str, Any]:
    """Run the authorized FORMAL computational chain with stage checkpoints."""
    root = Path(project_root)
    log = logger or logging.getLogger("nutev.article1.formal")
    version = latest_formal_strategy(root)
    if version is None:
        raise RuntimeError(
            "Nenhuma estratégia FORMAL/PRISMA-eligible está registrada no Search Registry. "
            "O Engine não cria uma estratégia formal por adivinhação."
        )

    state_path = root / "12_play" / "formal_chain_state.json"
    state = _load_json(state_path)
    if str(state.get("version_id") or "") != str(version["version_id"]):
        state = {
            "schema_version": FORMAL_CHAIN_SCHEMA_VERSION,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "version_id": str(version["version_id"]),
            "strategy_id": str(version["strategy_id"]),
            "status": "READY",
            "stages": {},
        }
        _atomic_json(state_path, state)

    state["status"] = "RUNNING"
    state["updated_at"] = _now_iso()
    _atomic_json(state_path, state)

    try:
        search_summary = _existing_search_summary(root, state)
        if search_summary is None:
            _emit(progress_fn, "FORMAL 1/6 — executando a estratégia congelada nos provedores autorizados...")
            search_summary = execute_strategy_version(
                root,
                version_id=str(version["version_id"]),
                breadth="specific",
                limit=provider_limit,
                resume=True,
            )
            if str(search_summary.get("status") or "") not in {"SUCCEEDED", "PARTIAL"}:
                raise RuntimeError(
                    "Execução FORMAL da busca não concluiu: "
                    + "; ".join(str(item) for item in (search_summary.get("errors") or []))
                )
            state["stages"]["search"] = {
                "status": str(search_summary.get("status") or ""),
                "run_id": str(search_summary["run_id"]),
                "manifest_path": str(search_summary.get("manifest_path") or ""),
                "completed_at": _now_iso(),
            }
            _atomic_json(state_path, state)
        else:
            _emit(progress_fn, "FORMAL 1/6 — busca já concluída; checkpoint reutilizado.")

        run_id = str(search_summary["run_id"])
        corpus_stage = (state.get("stages") or {}).get("corpus") or {}
        master_path = Path(str(corpus_stage.get("master_jsonl_path") or ""))
        if not master_path.is_file():
            _emit(progress_fn, "FORMAL 2/6 — normalizando e deduplicando o corpus master...")
            corpus = build_corpus_from_search_run(root, run_id=run_id)
            master_path = Path(str(corpus["master_jsonl_path"]))
            state["stages"]["corpus"] = {
                "status": str(corpus.get("status") or ""),
                "build_id": str(corpus.get("build_id") or ""),
                "master_jsonl_path": str(master_path),
                "manifest_path": str(corpus.get("manifest_path") or ""),
                "completed_at": _now_iso(),
            }
            _atomic_json(state_path, state)
        else:
            _emit(progress_fn, "FORMAL 2/6 — corpus master já existe; checkpoint reutilizado.")
            corpus = {
                "build_id": str(corpus_stage.get("build_id") or ""),
                "status": str(corpus_stage.get("status") or "SUCCEEDED"),
                "master_jsonl_path": str(master_path),
            }
        master_rows = _read_jsonl(master_path)

        formal_dir = root / "12_play" / "formal"
        fulltext_path = formal_dir / "fulltext_ledger.jsonl"
        fulltext_rows = _read_jsonl(fulltext_path)
        if not fulltext_rows and master_rows:
            _emit(progress_fn, f"FORMAL 3/6 — resolvendo texto completo lícito para {len(master_rows)} documentos...")
            session = requests.Session()
            session.headers.update(
                {"User-Agent": "NutEV Article1 FORMAL (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"}
            )
            email = (
                os.environ.get("UNPAYWALL_EMAIL")
                or os.environ.get("CROSSREF_MAILTO")
                or os.environ.get("NCBI_EMAIL")
                or os.environ.get("ENTREZ_EMAIL")
            )
            fulltext_rows = resolve_many([dict(row) for row in master_rows], email=email, session=session)
            _atomic_jsonl(fulltext_path, fulltext_rows)
            state["stages"]["fulltext_resolution"] = {
                "status": "SUCCEEDED",
                "ledger_path": str(fulltext_path),
                "completed_at": _now_iso(),
            }
            _atomic_json(state_path, state)
        else:
            _emit(progress_fn, "FORMAL 3/6 — resolução de texto completo já salva; checkpoint reutilizado.")

        download_path = formal_dir / "download_manifest.jsonl"
        failure_path = formal_dir / "download_failures.jsonl"
        download_manifest = _read_jsonl(download_path)
        download_failed = _read_jsonl(failure_path)
        download_stage_done = bool(((state.get("stages") or {}).get("download") or {}).get("completed_at"))
        if not download_stage_done:
            downloadable: list[dict[str, Any]] = []
            for row in fulltext_rows:
                fulltext_url = str(row.get("fulltext_url") or "").strip()
                if row.get("fulltext_status") != "fulltext_oa" or not fulltext_url:
                    continue
                enriched = dict(row)
                enriched["metadata_url"] = str(row.get("url") or "")
                enriched["oa_url"] = fulltext_url
                enriched["url"] = fulltext_url
                downloadable.append(enriched)
            _emit(progress_fn, f"FORMAL 4/6 — baixando {len(downloadable)} textos completos autorizados...")
            download_manifest, download_failed = download_records(
                downloadable,
                root / "03_corpus" / "03B_public_downloads",
                root / "03_corpus" / "03C_official_docs",
                log,
            )
            by_url = {
                str(row.get("url") or ""): str(row.get("document_id") or "")
                for row in downloadable
            }
            for item in download_manifest:
                item["document_id"] = by_url.get(str(item.get("url") or ""), "")
                path = Path(str(item.get("path") or ""))
                item["sha256"] = _sha256_file(path) if path.is_file() else ""
            for item in download_failed:
                item["document_id"] = by_url.get(str(item.get("url") or ""), "")
            _atomic_jsonl(download_path, download_manifest)
            _atomic_jsonl(failure_path, download_failed)
            state["stages"]["download"] = {
                "status": "SUCCEEDED" if not download_failed else "COMPLETE_WITH_WARNINGS",
                "downloaded": len(download_manifest),
                "failed": len(download_failed),
                "completed_at": _now_iso(),
            }
            _atomic_json(state_path, state)
        else:
            _emit(progress_fn, "FORMAL 4/6 — downloads já registrados; checkpoint reutilizado.")

        extraction_path = formal_dir / "extraction_manifest.jsonl"
        extraction_manifest = _read_jsonl(extraction_path)
        extracted_keys = {
            (str(row.get("document_id") or ""), str(row.get("source_artifact_sha256") or ""))
            for row in extraction_manifest
        }
        master_by_id = {str(row.get("document_id") or ""): row for row in master_rows}
        pending = [
            item for item in download_manifest
            if (
                str(item.get("document_id") or ""),
                str(item.get("sha256") or ""),
            ) not in extracted_keys
        ]
        if pending:
            _emit(progress_fn, f"FORMAL 5/6 — extraindo/OCR: {len(pending)} artefatos ainda pendentes...")
        else:
            _emit(progress_fn, "FORMAL 5/6 — extração/OCR já concluída para os artefatos conhecidos.")
        for index, item in enumerate(pending, start=1):
            path = Path(str(item.get("path") or ""))
            document_id = str(item.get("document_id") or "")
            _emit(progress_fn, f"FORMAL 5/6 — OCR/extração {index}/{len(pending)}: {path.name}")
            try:
                extracted = extract_document(
                    path,
                    root / "04_ocr_text",
                    root / "05_extraction",
                    log,
                    capture_pages=True,
                )
            except Exception as exc:
                extracted = {
                    "file": str(path),
                    "ext": path.suffix.lower().lstrip("."),
                    "used_ocr": False,
                    "ocr_failed_pages": "",
                    "text_path": "",
                    "chars": 0,
                    "extraction_status": "failed",
                    "reason": str(exc),
                }
            extracted["document_id"] = document_id
            extracted["source_artifact_sha256"] = str(item.get("sha256") or "")
            declared = (master_by_id.get(document_id) or {}).get("language") or (master_by_id.get(document_id) or {}).get("language_original")
            extracted = _annotate_extraction_language(extracted, declared_language=declared)
            extraction_manifest.append(extracted)
            # Persist after every document so Ctrl+C/power loss resumes at the next artifact.
            _atomic_jsonl(extraction_path, extraction_manifest)
            state["stages"]["extraction"] = {
                "status": "RUNNING",
                "processed": len(extraction_manifest),
                "last_document_id": document_id,
                "updated_at": _now_iso(),
            }
            _atomic_json(state_path, state)
        state["stages"]["extraction"] = {
            "status": "SUCCEEDED",
            "processed": len(extraction_manifest),
            "completed_at": _now_iso(),
        }
        _atomic_json(state_path, state)

        _emit(progress_fn, "FORMAL 6/6 — consolidando original, OCR e versões sob o document_id...")
        bundle = build_document_bundle_index(
            root,
            master_rows=master_rows,
            fulltext_rows=fulltext_rows,
            download_manifest=download_manifest,
            extraction_manifest=extraction_manifest,
        )
        state["stages"]["document_bundle"] = {
            "status": "SUCCEEDED",
            "bundle_path": bundle["bundle_path"],
            "completed_at": _now_iso(),
        }

        provider_rows = _provider_rows(root, run_id)
        authorization = search_summary.get("formal_authorization") or {}
        any_truncated = any(bool(row.get("truncated")) for row in provider_rows)
        provider_failures = any(str(row.get("status") or "").lower() not in {"completed", "empty"} for row in provider_rows)
        usable_text = sum(bool(str(row.get("text_path") or "")) for row in extraction_manifest)
        failed_extraction = len(extraction_manifest) - usable_text
        execution_status = (
            "COMPLETE_WITH_WARNINGS"
            if any_truncated or provider_failures or download_failed or failed_extraction
            else "COMPLETE"
        )
        total_found = sum(
            int(row["total_found"]) if row.get("total_found") is not None else int(row.get("records_returned") or 0)
            for row in provider_rows
        )
        records_returned = sum(int(row.get("records_returned") or 0) for row in provider_rows)
        summary = {
            "schema_version": 2,
            "play_id": "article1_formal",
            "created_at": state.get("created_at"),
            "finished_at": _now_iso(),
            "project_root": str(root),
            "software": {"version": __version__},
            "scientific_state": {
                "strategy_id": version["strategy_id"],
                "version_id": version["version_id"],
                "version": version["version"],
                "search_type": "FORMAL",
                "prisma_eligible": True,
                "strategy_checksum_sha256": version["checksum_sha256"],
                "formal_freeze_authorized": bool(authorization.get("authorized")),
                "freeze_id": authorization.get("freeze_id"),
            },
            "search": {
                "run_id": run_id,
                "status": search_summary.get("status"),
                "records_returned": records_returned,
                "provider_reported_total_found": total_found,
                "providers": provider_rows,
                "any_truncated": any_truncated,
            },
            "corpus": {
                "build_id": corpus.get("build_id"),
                "master_jsonl_path": str(master_path),
                "unique_records": len(master_rows),
            },
            "fulltext": {
                "resolved_rows": len(fulltext_rows),
                "downloaded": len(download_manifest),
                "download_failed": len(download_failed),
            },
            "extraction": {
                "processed": len(extraction_manifest),
                "usable_text": usable_text,
                "ocr_used": sum(bool(row.get("used_ocr")) for row in extraction_manifest),
                "failed_or_unusable": failed_extraction,
            },
            "document_bundle": bundle,
            "human_review": {
                "required": True,
                "automatic_include_exclude_decisions": 0,
            },
            "status": {
                "execution_status": execution_status,
                "scientific_readiness": "FORMAL_CORPUS_READY_FOR_HUMAN_SCREENING",
                "manuscript_ready": False,
                "prisma_eligible": True,
                "formal_freeze_authorized": bool(authorization.get("authorized")),
            },
            "artifacts": {
                "formal_chain_state_path": str(state_path),
                "fulltext_ledger_path": str(fulltext_path),
                "download_manifest_path": str(download_path),
                "download_failures_path": str(failure_path),
                "extraction_manifest_path": str(extraction_path),
                "document_bundle_path": bundle["bundle_path"],
            },
        }
        summary_path = formal_dir / "play_summary.json"
        _atomic_json(summary_path, summary)
        _atomic_json(root / "12_play" / "latest_summary.json", summary)
        state["stages"]["finalize"] = {
            "status": execution_status,
            "summary_path": str(summary_path),
            "completed_at": _now_iso(),
        }
        state["status"] = execution_status
        state["finished_at"] = summary["finished_at"]
        state["updated_at"] = _now_iso()
        _atomic_json(state_path, state)
        return summary
    except BaseException as exc:
        state["status"] = "FAILED"
        state["last_error"] = str(exc) or type(exc).__name__
        state["updated_at"] = _now_iso()
        _atomic_json(state_path, state)
        raise


__all__ = ["latest_formal_strategy", "run_or_resume_formal_chain"]
