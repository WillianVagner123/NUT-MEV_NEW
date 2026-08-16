from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import logging
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, Iterable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nutev.engine.validators import normalize_doi, normalize_pmid, normalize_url
from nutev.extract.pdf_text import missing_ocr_dependencies
from nutev.extract.smart_extract import extract_document

POSTPROCESS_SCHEMA_VERSION = 1
POSTPROCESS_TYPE = "REAL_DISCOVERY_POSTPROCESS_NONFORMAL"
_SPACE_RE = re.compile(r"\s+")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _atomic_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            handle.write("\n")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
        handle.write("\n")
        handle.flush()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"invalid JSON object at {path}:{line_number}")
            rows.append(value)
    return rows


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip())


def _normalize_pmcid(value: Any) -> str:
    raw = _clean_text(value).upper().replace(" ", "")
    if not raw:
        return ""
    if raw.startswith("PMC"):
        suffix = raw[3:]
        return "PMC" + suffix if suffix.isdigit() else raw
    return "PMC" + raw if raw.isdigit() else raw


def _title_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _clean_text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _stable_document_id(row: dict[str, Any]) -> str:
    doi = str(row.get("doi_normalized") or "")
    pmid = str(row.get("pmid_normalized") or "")
    pmcid = str(row.get("pmcid_normalized") or "")
    url = str(row.get("url_normalized") or "")
    title = str(row.get("title_normalized_key") or "")
    if doi:
        key = "doi:" + doi.casefold()
    elif pmid:
        key = "pmid:" + pmid
    elif pmcid:
        key = "pmcid:" + pmcid
    elif url:
        key = "url:" + url.casefold()
    elif title:
        key = "title:" + title
    else:
        key = "row:" + json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
    return "doc_" + sha256(key.encode("utf-8")).hexdigest()[:24]


def normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    raw_doi = _clean_text(row.get("doi"))
    raw_pmid = _clean_text(row.get("pmid"))
    raw_pmcid = _clean_text(row.get("pmcid"))
    raw_url = _clean_text(row.get("url"))
    title = _clean_text(row.get("title"))
    abstract = _clean_text(row.get("abstract") or row.get("summary") or row.get("snippet"))

    doi = normalize_doi(raw_doi) or ""
    pmid = normalize_pmid(raw_pmid) or ""
    pmcid = _normalize_pmcid(raw_pmcid)
    url = normalize_url(raw_url) or ""
    title_key = _title_key(title)

    out["title"] = title
    out["abstract"] = abstract
    out["doi_normalized"] = doi
    out["pmid_normalized"] = pmid
    out["pmcid_normalized"] = pmcid
    out["url_normalized"] = url
    out["title_normalized_key"] = title_key
    out["raw_identity"] = {
        "doi": raw_doi,
        "pmid": raw_pmid,
        "pmcid": raw_pmcid,
        "url": raw_url,
    }
    out["technical_flags"] = {
        "missing_title": not bool(title),
        "missing_abstract": not bool(abstract),
        "missing_strong_identifier": not bool(doi or pmid or pmcid),
        "missing_any_locator": not bool(doi or pmid or pmcid or url),
    }
    out["document_id"] = _stable_document_id(out)
    out["cleaning_source"] = "SYSTEM_DETERMINISTIC"
    out["human_screening_decision"] = None
    out["prisma_eligible"] = False
    out["formal_execution_authorized"] = False
    out["scientific_gate_effect"] = "NONE"
    return out


def possible_duplicate_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        title_key = str(row.get("title_normalized_key") or "")
        if len(title_key) < 30:
            continue
        buckets.setdefault(title_key, []).append(row)
    groups: list[dict[str, Any]] = []
    for title_key, items in buckets.items():
        if len(items) < 2:
            continue
        strong = {
            (
                str(item.get("doi_normalized") or ""),
                str(item.get("pmid_normalized") or ""),
                str(item.get("pmcid_normalized") or ""),
            )
            for item in items
        }
        if len(strong) <= 1:
            continue
        groups.append(
            {
                "group_id": "dup_" + sha256(title_key.encode("utf-8")).hexdigest()[:20],
                "title_normalized_key": title_key,
                "document_ids": [str(item.get("document_id") or "") for item in items],
                "source_providers": sorted(
                    {str(item.get("source_provider") or item.get("source") or "") for item in items}
                ),
                "status": "POSSIBLE_DUPLICATE_HUMAN_REVIEW",
                "auto_merged": False,
            }
        )
    return groups


def _screening_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for row in rows:
        queue.append(
            {
                "document_id": row.get("document_id"),
                "title": row.get("title") or "",
                "abstract": row.get("abstract") or "",
                "year": row.get("year") or row.get("publication_date") or "",
                "source_provider": row.get("source_provider") or row.get("source") or "",
                "doi": row.get("doi_normalized") or "",
                "pmid": row.get("pmid_normalized") or "",
                "pmcid": row.get("pmcid_normalized") or "",
                "url": row.get("url_normalized") or row.get("url") or "",
                "screening_stage": "TITLE_ABSTRACT",
                "human_decision": None,
                "reviewer": None,
                "reviewed_at": None,
                "machine_decision": None,
                "prisma_eligible": False,
            }
        )
    return queue


def _fulltext_after_screening_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": row.get("document_id"),
            "doi": row.get("doi_normalized") or "",
            "pmid": row.get("pmid_normalized") or "",
            "pmcid": row.get("pmcid_normalized") or "",
            "url": row.get("url_normalized") or row.get("url") or "",
            "status": "AWAITING_HUMAN_TITLE_ABSTRACT_INCLUDE",
            "download_authorized_by_screening": False,
            "human_decision_inferred": False,
        }
        for row in rows
        if str(row.get("source_provider") or "") != "official_web_live"
    ]


def _load_ocr_history(events_path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(events_path):
        digest = str(row.get("source_artifact_sha256") or "")
        if digest:
            latest[digest] = row
    return latest


def _ocr_downloaded_official_documents(
    collection_run_dir: Path,
    post_dir: Path,
    project_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    provider_path = collection_run_dir / "providers" / "official_web_live.jsonl"
    official_rows = _read_jsonl(provider_path)
    events_path = post_dir / "official_extraction_events.jsonl"
    history = _load_ocr_history(events_path)
    logger = logging.getLogger("nutev.process_everything")
    ocr_dir = project_root / "04_ocr_text" / "collect_everything" / collection_run_dir.name
    text_dir = project_root / "05_extraction" / "collect_everything" / collection_run_dir.name

    candidates: list[tuple[dict[str, Any], Path, str]] = []
    seen_sha: set[str] = set()
    for row in official_rows:
        path_value = str(row.get("saved_path") or "")
        if not path_value:
            continue
        path = Path(path_value)
        if not path.is_file():
            continue
        digest = str(row.get("content_sha256") or "") or _file_sha256(path)
        if not digest or digest in seen_sha:
            continue
        seen_sha.add(digest)
        candidates.append((row, path, digest))

    processed = 0
    skipped = 0
    for index, (source_row, path, digest) in enumerate(candidates, start=1):
        previous = history.get(digest) or {}
        previous_status = str(previous.get("extraction_status") or "")
        previous_text_path = str(previous.get("text_path") or "")
        retryable_setup_gap = previous_status == "pdf_needs_ocr_setup"
        already_good = previous_status in {"ok", "ok_ocr", "fake_pdf_html", "fake_pdf_text"}
        if already_good and previous_text_path and Path(previous_text_path).is_file():
            skipped += 1
            continue
        if previous and not retryable_setup_gap and previous_status in {
            "junk_or_blocked",
            "too_short",
            "pdf_no_text",
            "empty",
            "ocr_fail",
        }:
            skipped += 1
            continue

        print(f"Extração/OCR oficial {index}/{len(candidates)}: {path.name}", flush=True)
        try:
            result = extract_document(path, ocr_dir, text_dir, logger, capture_pages=False)
        except Exception as exc:
            result = {
                "file": str(path),
                "ext": path.suffix.lower().lstrip("."),
                "used_ocr": False,
                "ocr_failed_pages": "",
                "text_path": "",
                "chars": 0,
                "extraction_status": "failed",
                "reason": str(exc),
            }
        result.update(
            {
                "source_artifact_sha256": digest,
                "source_url": source_row.get("url") or "",
                "original_url": source_row.get("original_url") or "",
                "source_provider": "official_web_live",
                "processed_at": _now(),
                "prisma_eligible": False,
                "formal_execution_authorized": False,
                "scientific_gate_effect": "NONE",
            }
        )
        _append_jsonl(events_path, result)
        history[digest] = result
        processed += 1
        _atomic_json(
            post_dir / "ocr_state.json",
            {
                "schema_version": POSTPROCESS_SCHEMA_VERSION,
                "status": "RUNNING",
                "candidates": len(candidates),
                "processed_this_run": processed,
                "resumed_or_skipped": skipped,
                "last_source_artifact_sha256": digest,
                "updated_at": _now(),
            },
        )

    final_rows = list(history.values())
    _atomic_jsonl(post_dir / "official_extraction_manifest.jsonl", final_rows)
    summary = {
        "downloaded_official_artifacts": len(candidates),
        "manifest_entries": len(final_rows),
        "processed_this_run": processed,
        "resumed_or_skipped": skipped,
        "usable_text": sum(bool(str(row.get("text_path") or "")) for row in final_rows),
        "ocr_used": sum(bool(row.get("used_ocr")) for row in final_rows),
        "needs_ocr_setup": sum(
            str(row.get("extraction_status") or "") == "pdf_needs_ocr_setup" for row in final_rows
        ),
        "junk_or_blocked": sum(
            str(row.get("extraction_status") or "") == "junk_or_blocked" for row in final_rows
        ),
        "failed_or_unusable": sum(
            not bool(str(row.get("text_path") or "")) for row in final_rows
        ),
        "ocr_dependencies_missing": missing_ocr_dependencies(),
        "events_path": str(events_path),
        "manifest_path": str(post_dir / "official_extraction_manifest.jsonl"),
    }
    _atomic_json(post_dir / "ocr_state.json", {**summary, "status": "COMPLETE", "updated_at": _now()})
    return final_rows, summary


def run(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    collection_state_path = root / "07_logs" / "collect_everything" / "latest.json"
    collection = _load_json(collection_state_path)
    if collection.get("collection_type") != "REAL_DISCOVERY_NONFORMAL":
        raise RuntimeError("No completed run_everything_now collection was found.")

    master_path = Path(str(collection.get("master_records_path") or ""))
    expected_master_sha = str(collection.get("master_records_sha256") or "")
    if not master_path.is_file():
        raise RuntimeError(f"Collection master not found: {master_path}")
    actual_master_sha = _file_sha256(master_path)
    if not expected_master_sha or actual_master_sha != expected_master_sha:
        raise RuntimeError("Collection master SHA-256 mismatch; refusing to postprocess altered input.")

    collection_run_id = str(collection.get("run_id") or "unknown")
    collection_run_dir = Path(str(collection.get("run_dir") or master_path.parent))
    post_dir = root / "14_postprocess_everything" / collection_run_id
    post_dir.mkdir(parents=True, exist_ok=True)
    state_path = root / "07_logs" / "postprocess_everything" / "latest.json"

    print("NutEV: pós-processamento técnico da coleta ampla.", flush=True)
    print("RAW será preservado. Nenhuma decisão INCLUDE/EXCLUDE será inventada.", flush=True)

    clean_path = post_dir / "clean_records.jsonl"
    clean_meta_path = post_dir / "clean_records.meta.json"
    clean_meta = _load_json(clean_meta_path)
    if (
        clean_path.is_file()
        and clean_meta.get("source_master_sha256") == actual_master_sha
        and clean_meta.get("clean_records_sha256") == _file_sha256(clean_path)
    ):
        clean_rows = _read_jsonl(clean_path)
        print(f"Limpeza técnica: restaurada do autosave ({len(clean_rows)} registros).", flush=True)
    else:
        raw_rows = _read_jsonl(master_path)
        print(f"Limpeza técnica: normalizando {len(raw_rows)} registros sem alterar o RAW...", flush=True)
        clean_rows = [normalize_record(row) for row in raw_rows]
        clean_sha = _atomic_jsonl(clean_path, clean_rows)
        _atomic_json(
            clean_meta_path,
            {
                "schema_version": POSTPROCESS_SCHEMA_VERSION,
                "source_master_path": str(master_path),
                "source_master_sha256": actual_master_sha,
                "clean_records_path": str(clean_path),
                "clean_records_sha256": clean_sha,
                "records": len(clean_rows),
                "created_at": _now(),
            },
        )

    duplicate_groups = possible_duplicate_groups(clean_rows)
    duplicate_path = post_dir / "possible_duplicate_groups.jsonl"
    _atomic_jsonl(duplicate_path, duplicate_groups)

    screening_path = post_dir / "title_abstract_screening_queue.jsonl"
    _atomic_jsonl(screening_path, _screening_queue(clean_rows))
    fulltext_queue_path = post_dir / "fulltext_after_screening_queue.jsonl"
    _atomic_jsonl(fulltext_queue_path, _fulltext_after_screening_queue(clean_rows))

    print("Documentos oficiais já baixados: iniciando extração nativa / OCR quando necessário...", flush=True)
    _, ocr_summary = _ocr_downloaded_official_documents(collection_run_dir, post_dir, root)

    missing_title = sum(bool(row.get("technical_flags", {}).get("missing_title")) for row in clean_rows)
    missing_abstract = sum(bool(row.get("technical_flags", {}).get("missing_abstract")) for row in clean_rows)
    summary = {
        "schema_version": POSTPROCESS_SCHEMA_VERSION,
        "postprocess_type": POSTPROCESS_TYPE,
        "source_collection_run_id": collection_run_id,
        "source_master_path": str(master_path),
        "source_master_sha256": actual_master_sha,
        "status": "COMPLETE_WITH_OCR_SETUP_GAP" if ocr_summary["ocr_dependencies_missing"] else "COMPLETE",
        "finished_at": _now(),
        "technical_cleaning": {
            "records": len(clean_rows),
            "missing_title": missing_title,
            "missing_abstract": missing_abstract,
            "possible_duplicate_groups": len(duplicate_groups),
            "clean_records_path": str(clean_path),
            "possible_duplicate_groups_path": str(duplicate_path),
        },
        "screening": {
            "queue_path": str(screening_path),
            "records_waiting_human_title_abstract_review": len(clean_rows),
            "automatic_include_exclude_decisions": 0,
        },
        "fulltext": {
            "queue_path": str(fulltext_queue_path),
            "network_resolution_deferred_until_human_include": True,
        },
        "official_document_extraction": ocr_summary,
        "raw_preserved": True,
        "human_decision_inferred": False,
        "prisma_eligible": False,
        "formal_execution_authorized": False,
        "scientific_gate_effect": "NONE",
        "post_dir": str(post_dir),
    }
    _atomic_json(post_dir / "manifest.json", summary)
    _atomic_json(state_path, summary)

    print("", flush=True)
    print("PÓS-PROCESSAMENTO FINALIZADO", flush=True)
    print(f"Registros técnicos limpos: {len(clean_rows)}", flush=True)
    print(f"Grupos de possíveis duplicatas para revisão: {len(duplicate_groups)}", flush=True)
    print(f"Fila título/resumo: {screening_path}", flush=True)
    print(f"Textos/OCR oficiais utilizáveis: {ocr_summary['usable_text']}", flush=True)
    print(f"OCR realmente usado: {ocr_summary['ocr_used']}", flush=True)
    if ocr_summary["ocr_dependencies_missing"]:
        print("OCR de scans ainda depende de instalação local:", flush=True)
        for item in ocr_summary["ocr_dependencies_missing"]:
            print(f"- {item}", flush=True)
        print("Depois de instalar, rode este mesmo comando novamente; os autosaves serão reutilizados.", flush=True)
    print(f"Manifest: {post_dir / 'manifest.json'}", flush=True)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Clean the latest run_everything_now master deterministically, prepare human screening, "
            "and extract/OCR already-downloaded official documents without crossing scientific gates."
        )
    )
    parser.add_argument("--project-root", default="project_output_scientific")
    args = parser.parse_args()
    try:
        run(Path(args.project_root))
    except KeyboardInterrupt:
        print("Interrompido. O RAW e os eventos de OCR já gravados foram preservados.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Falha: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
