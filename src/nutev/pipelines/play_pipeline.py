"""One-command computational orchestration for NutEV pilot runs.

`nutev play` is intentionally gate-aware. The first implementation supports
PILOT strategy versions only: it may execute the frozen registered strategy,
build the auditable master corpus, resolve lawful open-access full text,
download accessible artifacts, extract native text and run OCR when required.

It must NOT silently promote a pilot to a formal/PRISMA run. Formal execution
remains blocked here until the scientific gate/freeze model (GF-02/GF-03/GF-06/
GF-07/GF-10) is implemented and authorized.
"""
from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests

from nutev.__version__ import __version__
from nutev.acquire.fulltext_resolver import resolve_many
from nutev.download.downloader import download_records
from nutev.extract.smart_extract import extract_document
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import (
    default_registry_path,
    get_strategy_version,
    list_strategy_versions,
)

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
PLAY_SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _safe_component(value: str) -> str:
    return "".join(
        char if char.isalnum() or char in {"-", "_"} else "_" for char in value
    )


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    tmp.replace(path)
    return _sha256_file(path)


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            handle.write("\n")
    tmp.replace(path)
    return _sha256_file(path)


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    fieldnames = sorted({key for row in rows for key in row})
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        if fieldnames:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    tmp.replace(path)
    return _sha256_file(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"invalid object in {path} at line {line_number}")
            rows.append(value)
    return rows


def _resolve_strategy_version(project_root: Path, version_id: str | None) -> dict[str, Any]:
    db_path = default_registry_path(project_root)
    if version_id:
        version = get_strategy_version(db_path, version_id)
        if version is None:
            raise ValueError(f"unknown strategy version: {version_id}")
        return version
    versions = list_strategy_versions(db_path, limit=1)
    if not versions:
        raise ValueError(
            "no registered search strategy exists; save a PILOT version in "
            "Search Strategy first"
        )
    return versions[0]


def _provider_report(search_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for provider in search_summary.get("providers") or []:
        returned = int(provider.get("records_returned") or 0)
        raw_total = provider.get("total_found")
        total = int(raw_total) if raw_total is not None else None
        truncated = total is not None and returned < total
        coverage_pct: float | None
        if total is None:
            coverage_pct = None
        elif total == 0:
            coverage_pct = 100.0
        else:
            coverage_pct = round((returned / total) * 100, 2)
        rows.append(
            {
                "provider": str(provider.get("provider") or ""),
                "status": str(provider.get("provider_status") or ""),
                "total_found": total,
                "records_returned": returned,
                "coverage_pct": coverage_pct,
                "truncated": truncated,
                "snapshot_path": str(provider.get("snapshot_path") or ""),
                "snapshot_sha256": str(provider.get("snapshot_sha256") or ""),
            }
        )
    return rows


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    search = summary["search"]
    corpus = summary["corpus"]
    fulltext = summary["fulltext"]
    extraction = summary["extraction"]
    providers = "\n".join(
        f"- {row['provider']}: {row['status']} | "
        f"returned={row['records_returned']} | total={row['total_found']} | "
        f"truncated={row['truncated']}"
        for row in search["providers"]
    ) or "- none"
    text = f"""# NutEV PLAY summary

- play_id: `{summary['play_id']}`
- created_at: `{summary['created_at']}`
- software_version: `{summary['software']['version']}`
- strategy_version_id: `{summary['scientific_state']['version_id']}`
- search_type: `{summary['scientific_state']['search_type']}`
- PRISMA eligible: `{summary['scientific_state']['prisma_eligible']}`
- execution_status: `{summary['status']['execution_status']}`
- scientific_readiness: `{summary['status']['scientific_readiness']}`

## Search

{providers}

Records returned: **{search['records_returned']}**  
Provider-reported total: **{search['provider_reported_total_found']}**  
Any provider truncated: **{search['any_truncated']}**

## Master corpus

Input records: **{corpus['input_records']}**  
Unique documents: **{corpus['unique_records']}**  
Automatic duplicates removed: **{corpus['duplicates_removed']}**  
Possible duplicates pending human review: **{corpus['possible_duplicates']}**

## Full text

Open-access location resolved: **{fulltext['fulltext_oa']}**  
Paywall/no OA location: **{fulltext['paywall']}**  
Needs network: **{fulltext['needs_network']}**  
Downloaded artifacts: **{fulltext['downloaded']}**  
Download failures/metadata-only: **{fulltext['download_failed']}**

## Extraction / OCR

Artifacts processed: **{extraction['processed']}**  
Usable text: **{extraction['usable_text']}**  
OCR used: **{extraction['ocr_used']}**  
OCR/setup/extraction failures: **{extraction['failed_or_unusable']}**

## Scientific boundary

This PLAY implementation is **PILOT-only**. It does not create human INCLUDE/
EXCLUDE decisions, does not approve PRESS, does not authorize GF-10 freeze and
does not feed PRISMA. Institutional/guideline-repository tracks are not yet
merged into this one-command orchestrator and remain an explicit implementation
gap rather than being silently described as executed.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_play(
    project_root: Path,
    *,
    version_id: str | None = None,
    breadth: str = "specific",
    providers: list[str] | tuple[str, ...] | None = None,
    limit: int = 10000,
    resume: bool = True,
    metadata_only: bool = False,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Run the current one-command PILOT workflow and write a complete audit summary.

    Formal or otherwise PRISMA-eligible strategy versions are deliberately
    rejected until the scientific gate/freeze registry can prove authorization.
    """
    root = Path(project_root)
    log = logger or logging.getLogger("nutev.play")
    version = _resolve_strategy_version(root, version_id)

    if bool(version.get("prisma_eligible")):
        raise RuntimeError(
            "nutev play currently refuses PRISMA-eligible/FORMAL execution. "
            "Complete and implement the scientific gate/freeze authorization "
            "(GF-02, GF-03, GF-06, GF-07 and GF-10) before formal PLAY."
        )

    play_id = (
        "play_"
        + datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
        + "_"
        + uuid4().hex[:10]
    )
    play_dir = root / "12_play" / _safe_component(play_id)
    play_dir.mkdir(parents=True, exist_ok=True)
    state_path = play_dir / "play_state.json"

    state: dict[str, Any] = {
        "schema_version": PLAY_SCHEMA_VERSION,
        "play_id": play_id,
        "created_at": _now_iso(),
        "project_root": str(root),
        "strategy": {
            "strategy_id": version["strategy_id"],
            "version_id": version["version_id"],
            "version": version["version"],
            "search_type": version["search_type"],
            "prisma_eligible": bool(version["prisma_eligible"]),
            "checksum_sha256": version["checksum_sha256"],
        },
        "stages": {},
    }
    _atomic_json(state_path, state)

    log.info(
        "PLAY %s: executing strategy version %s",
        play_id,
        version["version_id"],
    )
    search_summary = execute_strategy_version(
        root,
        version_id=str(version["version_id"]),
        breadth=breadth,
        providers=providers,
        limit=limit,
        resume=resume,
    )
    provider_rows = _provider_report(search_summary)
    provider_report_path = play_dir / "search_providers.csv"
    _atomic_csv(provider_report_path, provider_rows)
    state["stages"]["search"] = {
        "status": search_summary.get("status"),
        "run_id": search_summary.get("run_id"),
        "manifest_path": search_summary.get("manifest_path"),
        "provider_report_path": str(provider_report_path),
    }
    _atomic_json(state_path, state)

    log.info("PLAY %s: building master corpus", play_id)
    corpus_summary = build_corpus_from_search_run(
        root,
        run_id=str(search_summary["run_id"]),
    )
    master_path = Path(str(corpus_summary["master_jsonl_path"]))
    master_rows = _read_jsonl(master_path)
    state["stages"]["corpus"] = {
        "status": corpus_summary.get("status"),
        "build_id": corpus_summary.get("build_id"),
        "master_jsonl_path": str(master_path),
        "manifest_path": corpus_summary.get("manifest_path"),
    }
    _atomic_json(state_path, state)

    fulltext_rows: list[dict[str, Any]] = []
    download_manifest: list[dict[str, Any]] = []
    download_failed: list[dict[str, Any]] = []
    extraction_manifest: list[dict[str, Any]] = []

    if not metadata_only:
        log.info(
            "PLAY %s: resolving lawful open-access full text for %d documents",
            play_id,
            len(master_rows),
        )
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "NutEV PLAY/0.3 "
                    "(+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"
                )
            }
        )
        email = (
            os.environ.get("UNPAYWALL_EMAIL")
            or os.environ.get("CROSSREF_MAILTO")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL")
        )
        fulltext_rows = resolve_many(
            [dict(row) for row in master_rows],
            email=email,
            session=session,
        )
        fulltext_ledger_path = play_dir / "fulltext_ledger.jsonl"
        _atomic_jsonl(fulltext_ledger_path, fulltext_rows)

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

        log.info(
            "PLAY %s: downloading %d open-access candidates",
            play_id,
            len(downloadable),
        )
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
            path_value = str(item.get("path") or "")
            path = Path(path_value) if path_value else None
            item["sha256"] = _sha256_file(path) if path and path.is_file() else ""
        for item in download_failed:
            item["document_id"] = by_url.get(str(item.get("url") or ""), "")

        _atomic_jsonl(play_dir / "download_manifest.jsonl", download_manifest)
        _atomic_jsonl(play_dir / "download_failures.jsonl", download_failed)

        log.info(
            "PLAY %s: extracting text / OCR from %d artifacts",
            play_id,
            len(download_manifest),
        )
        for item in download_manifest:
            path_value = str(item.get("path") or "")
            if not path_value:
                continue
            path = Path(path_value)
            try:
                extracted = extract_document(
                    path,
                    root / "04_ocr_text",
                    root / "05_extraction",
                    log,
                )
            except Exception as exc:  # keep failures visible in the ledger
                extracted = {
                    "file": path_value,
                    "ext": path.suffix.lower().lstrip("."),
                    "used_ocr": False,
                    "ocr_failed_pages": "",
                    "text_path": "",
                    "chars": 0,
                    "extraction_status": "failed",
                    "reason": str(exc),
                }
            extracted["document_id"] = str(item.get("document_id") or "")
            extracted["source_artifact_sha256"] = str(item.get("sha256") or "")
            extraction_manifest.append(extracted)
        _atomic_jsonl(play_dir / "extraction_manifest.jsonl", extraction_manifest)
        state["stages"]["fulltext"] = {
            "status": "SUCCEEDED",
            "ledger_path": str(fulltext_ledger_path),
            "downloaded": len(download_manifest),
            "download_failed": len(download_failed),
            "extracted": len(extraction_manifest),
        }
        _atomic_json(state_path, state)
    else:
        state["stages"]["fulltext"] = {
            "status": "SKIPPED_METADATA_ONLY",
        }
        _atomic_json(state_path, state)

    fulltext_counts = {
        "fulltext_oa": sum(
            row.get("fulltext_status") == "fulltext_oa" for row in fulltext_rows
        ),
        "paywall": sum(
            row.get("fulltext_status") == "paywall" for row in fulltext_rows
        ),
        "needs_network": sum(
            row.get("fulltext_status") == "needs_network" for row in fulltext_rows
        ),
    }
    usable_text = sum(
        bool(str(row.get("text_path") or "")) for row in extraction_manifest
    )
    ocr_used = sum(bool(row.get("used_ocr")) for row in extraction_manifest)
    failed_or_unusable = len(extraction_manifest) - usable_text
    any_truncated = any(bool(row.get("truncated")) for row in provider_rows)
    provider_failures = any(
        str(row.get("status") or "").lower() not in {"completed", "empty"}
        for row in provider_rows
    )
    execution_status = (
        "COMPLETE_WITH_WARNINGS"
        if any_truncated or provider_failures or download_failed or failed_or_unusable
        else "COMPLETE"
    )

    summary: dict[str, Any] = {
        "schema_version": PLAY_SCHEMA_VERSION,
        "play_id": play_id,
        "created_at": state["created_at"],
        "finished_at": _now_iso(),
        "project_root": str(root),
        "software": {
            "version": __version__,
        },
        "scientific_state": {
            "strategy_id": version["strategy_id"],
            "version_id": version["version_id"],
            "version": version["version"],
            "search_type": version["search_type"],
            "prisma_eligible": bool(version["prisma_eligible"]),
            "strategy_checksum_sha256": version["checksum_sha256"],
            "formal_freeze_authorized": False,
        },
        "search": {
            "run_id": search_summary["run_id"],
            "status": search_summary["status"],
            "records_returned": int(
                search_summary.get("records_identified_before_deduplication") or 0
            ),
            "provider_reported_total_found": int(
                search_summary.get("provider_reported_total_found") or 0
            ),
            "providers": provider_rows,
            "any_truncated": any_truncated,
        },
        "corpus": {
            "build_id": corpus_summary["build_id"],
            "input_records": int(corpus_summary.get("input_records") or 0),
            "unique_records": int(corpus_summary.get("unique_records") or 0),
            "duplicates_removed": int(
                corpus_summary.get("duplicates_removed") or 0
            ),
            "possible_duplicates": int(
                corpus_summary.get("possible_duplicates") or 0
            ),
            "master_jsonl_path": str(master_path),
        },
        "fulltext": {
            **fulltext_counts,
            "downloaded": len(download_manifest),
            "download_failed": len(download_failed),
            "metadata_only_mode": bool(metadata_only),
        },
        "extraction": {
            "processed": len(extraction_manifest),
            "usable_text": usable_text,
            "ocr_used": ocr_used,
            "failed_or_unusable": failed_or_unusable,
        },
        "tracks": {
            "indexed_database": "EXECUTED",
            "institutional_official": "NOT_YET_INTEGRATED_IN_PLAY",
            "guideline_repositories": "NOT_YET_INTEGRATED_IN_PLAY",
            "scopus": "MANUAL_EXECUTION_REQUIRED_UNTIL_LICENSED_INTEGRATION",
            "web_of_science": "MANUAL_EXECUTION_REQUIRED_UNTIL_LICENSED_INTEGRATION",
        },
        "human_review": {
            "required": True,
            "automatic_include_exclude_decisions": 0,
        },
        "status": {
            "execution_status": execution_status,
            "scientific_readiness": "PILOT_OUTPUT_READY_FOR_HUMAN_REVIEW",
            "manuscript_ready": False,
            "prisma_eligible": False,
            "formal_freeze_authorized": False,
        },
        "artifacts": {
            "play_state_path": str(state_path),
            "provider_report_path": str(provider_report_path),
            "play_dir": str(play_dir),
        },
    }

    summary_path = play_dir / "play_summary.json"
    summary_hash_path = play_dir / "play_summary.sha256"
    summary["artifacts"]["summary_path"] = str(summary_path)
    summary["artifacts"]["summary_sha256_path"] = str(summary_hash_path)

    # Write the summary exactly once, then hash the immutable bytes. The checksum
    # is stored beside the summary rather than embedded into the file it hashes;
    # embedding a self-checksum would necessarily change the bytes after hashing.
    summary_sha256 = _atomic_json(summary_path, summary)
    summary_hash_path.write_text(
        f"{summary_sha256}  {summary_path.name}\n",
        encoding="utf-8",
    )
    _write_summary_markdown(play_dir / "play_summary.md", summary)
    _atomic_json(root / "12_play" / "latest_summary.json", summary)

    state["stages"]["finalize"] = {
        "status": execution_status,
        "summary_path": str(summary_path),
        "summary_sha256": summary_sha256,
        "summary_sha256_path": str(summary_hash_path),
    }
    state["finished_at"] = summary["finished_at"]
    _atomic_json(state_path, state)

    # Returning the checksum is useful to callers, but it is intentionally not
    # inserted into the persisted summary after hashing.
    summary["artifacts"]["summary_sha256"] = summary_sha256
    return summary
