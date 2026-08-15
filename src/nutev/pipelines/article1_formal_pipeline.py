"""Resumable FORMAL computational chain for the one-button Article 1 engine.

Only computational stages run here. The existing formal execution guard remains
the authority for strategy/FREEZE/Git/config authorization; human screening and
scientific decisions are deliberately outside this module.
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
from nutev.search.strategy_execution_ledger import get_search_run, list_execution_artifacts
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import default_registry_path, list_strategy_versions

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
ProgressFn = Callable[[str], None]


def _now() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _emit(callback: ProgressFn | None, text: str) -> None:
    if callback:
        callback(text)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    tmp.replace(path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _file_sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_formal_strategy(project_root: Path) -> dict[str, Any] | None:
    versions = list_strategy_versions(default_registry_path(project_root), limit=100)
    return next(
        (
            row
            for row in versions
            if str(row.get("search_type") or "").upper() == "FORMAL"
            and bool(row.get("prisma_eligible"))
        ),
        None,
    )


def _search_from_checkpoint(root: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    stage = (state.get("stages") or {}).get("search") or {}
    run_id = str(stage.get("run_id") or "")
    if not run_id:
        return None
    run = get_search_run(default_registry_path(root), run_id)
    if not run or str(run.get("status") or "") not in {"SUCCEEDED", "PARTIAL"}:
        return None
    manifest = _load_json(Path(str(run.get("manifest_path") or "")))
    if not manifest:
        return None
    return {**run, "formal_authorization": manifest.get("formal_authorization") or {}}


def _provider_rows(root: Path, run_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in list_execution_artifacts(default_registry_path(root), run_id=run_id):
        total = item.get("total_found")
        returned = int(item.get("records_returned") or 0)
        out.append(
            {
                "provider": str(item.get("provider") or ""),
                "status": str(item.get("provider_status") or ""),
                "records_returned": returned,
                "total_found": int(total) if total is not None else None,
                "truncated": total is not None and returned < int(total),
                "snapshot_path": str(item.get("snapshot_path") or ""),
                "snapshot_sha256": str(item.get("snapshot_sha256") or ""),
                "exact_expression": str(item.get("exact_expression") or ""),
            }
        )
    return out


def _language_fields(extracted: dict[str, Any], declared: object) -> dict[str, Any]:
    row = dict(extracted)
    text_path = Path(str(row.get("text_path") or ""))
    text = text_path.read_text(encoding="utf-8", errors="ignore") if text_path.is_file() else ""
    detection = detect_language(text, declared=declared)
    row.update(
        {
            "language_original": normalize_language_code(declared) or None,
            "language_detected": detection.get("detected_language"),
            "language_detection_confidence": detection.get("confidence"),
            "language_detection_method": detection.get("method"),
        }
    )
    return row


def _save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    _write_json(path, state)


def run_or_resume_formal_chain(
    project_root: Path,
    *,
    progress_fn: ProgressFn | None = None,
    logger: logging.Logger | None = None,
    provider_limit: int = 10000,
) -> dict[str, Any]:
    root = Path(project_root)
    log = logger or logging.getLogger("nutev.article1.formal")
    version = latest_formal_strategy(root)
    if version is None:
        raise RuntimeError(
            "Nenhuma estratégia FORMAL/PRISMA-eligible está registrada. "
            "O Engine não cria uma estratégia formal por adivinhação."
        )

    state_path = root / "12_play" / "formal_chain_state.json"
    state = _load_json(state_path)
    if str(state.get("version_id") or "") != str(version["version_id"]):
        state = {
            "schema_version": 1,
            "version_id": str(version["version_id"]),
            "strategy_id": str(version["strategy_id"]),
            "created_at": _now(),
            "status": "READY",
            "stages": {},
        }
    state["status"] = "RUNNING"
    _save_state(state_path, state)

    try:
        search = _search_from_checkpoint(root, state)
        if search is None:
            _emit(progress_fn, "FORMAL 1/6 — busca congelada...")
            search = execute_strategy_version(
                root,
                version_id=str(version["version_id"]),
                breadth="specific",
                limit=provider_limit,
                resume=True,
            )
            if str(search.get("status") or "") not in {"SUCCEEDED", "PARTIAL"}:
                raise RuntimeError("A busca FORMAL não terminou em estado auditável.")
            state["stages"]["search"] = {
                "run_id": str(search["run_id"]),
                "status": str(search.get("status") or ""),
                "completed_at": _now(),
            }
            _save_state(state_path, state)
        else:
            _emit(progress_fn, "FORMAL 1/6 — checkpoint da busca reutilizado.")
        run_id = str(search["run_id"])

        corpus_stage = (state["stages"].get("corpus") or {})
        master_path = Path(str(corpus_stage.get("master_path") or ""))
        if not master_path.is_file():
            _emit(progress_fn, "FORMAL 2/6 — corpus e deduplicação...")
            corpus = build_corpus_from_search_run(root, run_id=run_id)
            master_path = Path(str(corpus["master_jsonl_path"]))
            state["stages"]["corpus"] = {
                "build_id": str(corpus.get("build_id") or ""),
                "master_path": str(master_path),
                "completed_at": _now(),
            }
            _save_state(state_path, state)
        else:
            corpus = {"build_id": corpus_stage.get("build_id"), "master_jsonl_path": str(master_path)}
            _emit(progress_fn, "FORMAL 2/6 — checkpoint do corpus reutilizado.")
        master_rows = _read_jsonl(master_path)
        master_by_id = {str(row.get("document_id") or ""): row for row in master_rows}

        formal_dir = root / "12_play" / "formal"
        fulltext_path = formal_dir / "fulltext_ledger.jsonl"
        fulltext_rows = _read_jsonl(fulltext_path)
        if not fulltext_rows and master_rows:
            _emit(progress_fn, f"FORMAL 3/6 — resolvendo texto completo de {len(master_rows)} documentos...")
            session = requests.Session()
            session.headers.update({"User-Agent": "NutEV Article1 FORMAL"})
            email = (
                os.environ.get("UNPAYWALL_EMAIL")
                or os.environ.get("CROSSREF_MAILTO")
                or os.environ.get("NCBI_EMAIL")
                or os.environ.get("ENTREZ_EMAIL")
            )
            fulltext_rows = resolve_many(master_rows, email=email, session=session)
            _write_jsonl(fulltext_path, fulltext_rows)
            state["stages"]["fulltext"] = {"ledger": str(fulltext_path), "completed_at": _now()}
            _save_state(state_path, state)
        else:
            _emit(progress_fn, "FORMAL 3/6 — checkpoint de texto completo reutilizado.")

        download_path = formal_dir / "download_manifest.jsonl"
        failure_path = formal_dir / "download_failures.jsonl"
        download_rows = _read_jsonl(download_path)
        failures = _read_jsonl(failure_path)
        if not (state["stages"].get("download") or {}).get("completed_at"):
            downloadable: list[dict[str, Any]] = []
            for row in fulltext_rows:
                url = str(row.get("fulltext_url") or "").strip()
                if row.get("fulltext_status") == "fulltext_oa" and url:
                    item = dict(row)
                    item.update({"metadata_url": row.get("url", ""), "oa_url": url, "url": url})
                    downloadable.append(item)
            _emit(progress_fn, f"FORMAL 4/6 — download lícito de {len(downloadable)} documentos...")
            download_rows, failures = download_records(
                downloadable,
                root / "03_corpus" / "03B_public_downloads",
                root / "03_corpus" / "03C_official_docs",
                log,
            )
            by_url = {str(row.get("url") or ""): str(row.get("document_id") or "") for row in downloadable}
            for item in download_rows:
                item["document_id"] = by_url.get(str(item.get("url") or ""), "")
                path = Path(str(item.get("path") or ""))
                item["sha256"] = _file_sha(path) if path.is_file() else ""
            for item in failures:
                item["document_id"] = by_url.get(str(item.get("url") or ""), "")
            _write_jsonl(download_path, download_rows)
            _write_jsonl(failure_path, failures)
            state["stages"]["download"] = {
                "downloaded": len(download_rows),
                "failed": len(failures),
                "completed_at": _now(),
            }
            _save_state(state_path, state)
        else:
            _emit(progress_fn, "FORMAL 4/6 — checkpoint de downloads reutilizado.")

        extraction_path = formal_dir / "extraction_manifest.jsonl"
        extraction_rows = _read_jsonl(extraction_path)
        done = {
            (str(row.get("document_id") or ""), str(row.get("source_artifact_sha256") or ""))
            for row in extraction_rows
        }
        pending = [
            item
            for item in download_rows
            if (str(item.get("document_id") or ""), str(item.get("sha256") or "")) not in done
        ]
        _emit(progress_fn, f"FORMAL 5/6 — OCR/extração: {len(pending)} pendente(s).")
        for index, item in enumerate(pending, start=1):
            path = Path(str(item.get("path") or ""))
            document_id = str(item.get("document_id") or "")
            _emit(progress_fn, f"FORMAL 5/6 — {index}/{len(pending)} {path.name}")
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
                    "used_ocr": False,
                    "text_path": "",
                    "chars": 0,
                    "extraction_status": "failed",
                    "reason": str(exc),
                }
            extracted["document_id"] = document_id
            extracted["source_artifact_sha256"] = str(item.get("sha256") or "")
            master = master_by_id.get(document_id) or {}
            extracted = _language_fields(
                extracted,
                master.get("language_original") or master.get("language"),
            )
            extraction_rows.append(extracted)
            _write_jsonl(extraction_path, extraction_rows)
            state["stages"]["extraction"] = {
                "processed": len(extraction_rows),
                "last_document_id": document_id,
                "status": "RUNNING",
            }
            _save_state(state_path, state)
        state["stages"]["extraction"] = {
            "processed": len(extraction_rows),
            "status": "SUCCEEDED",
            "completed_at": _now(),
        }
        _save_state(state_path, state)

        _emit(progress_fn, "FORMAL 6/6 — consolidando document_id e artefatos...")
        bundle = build_document_bundle_index(
            root,
            master_rows=master_rows,
            fulltext_rows=fulltext_rows,
            download_manifest=download_rows,
            extraction_manifest=extraction_rows,
        )
        state["stages"]["bundle"] = {"path": bundle["bundle_path"], "completed_at": _now()}

        providers = _provider_rows(root, run_id)
        authorization = search.get("formal_authorization") or {}
        warnings = bool(
            failures
            or any(row["truncated"] for row in providers)
            or any(str(row["status"]).lower() not in {"completed", "empty"} for row in providers)
            or any(not str(row.get("text_path") or "") for row in extraction_rows)
        )
        execution_status = "COMPLETE_WITH_WARNINGS" if warnings else "COMPLETE"
        summary = {
            "schema_version": 2,
            "play_id": "article1_formal",
            "finished_at": _now(),
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
            "search": {"run_id": run_id, "providers": providers},
            "corpus": {
                "build_id": corpus.get("build_id"),
                "master_jsonl_path": str(master_path),
                "unique_records": len(master_rows),
            },
            "fulltext": {
                "resolved_rows": len(fulltext_rows),
                "downloaded": len(download_rows),
                "download_failed": len(failures),
            },
            "extraction": {
                "processed": len(extraction_rows),
                "usable_text": sum(bool(str(row.get("text_path") or "")) for row in extraction_rows),
                "ocr_used": sum(bool(row.get("used_ocr")) for row in extraction_rows),
            },
            "document_bundle": bundle,
            "human_review": {"required": True, "automatic_include_exclude_decisions": 0},
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
        _write_json(summary_path, summary)
        _write_json(root / "12_play" / "latest_summary.json", summary)
        state["status"] = execution_status
        state["finished_at"] = summary["finished_at"]
        _save_state(state_path, state)
        return summary
    except BaseException as exc:
        state["status"] = "FAILED"
        state["last_error"] = str(exc) or type(exc).__name__
        _save_state(state_path, state)
        raise


__all__ = ["latest_formal_strategy", "run_or_resume_formal_chain"]
