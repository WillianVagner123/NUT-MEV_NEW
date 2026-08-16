from __future__ import annotations

import argparse
from datetime import date, datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nutev.engine.validators import normalize_doi, normalize_pmid, normalize_url
from nutev.search.brave_optional import search_brave
from nutev.search.crossref import search_crossref
from nutev.search.doaj import search_doaj
from nutev.search.europepmc import search_europepmc
from nutev.search.gf02_pubmed_current import load_candidate_config, resolved_line_expressions
from nutev.search.google_pse import search_google_pse
from nutev.search.official_sources import load_official_manifest, manifest_sources
from nutev.search.openalex import search_openalex
from nutev.search.pubmed import PubMedClient
from nutev.search.semantic_scholar import search_semantic_scholar
from nutev.search.serpapi_optional import search_serpapi

SCHEMA_VERSION = 1
COLLECTION_TYPE = "REAL_DISCOVERY_NONFORMAL"
SUCCESS_STATUSES = {"completed", "empty", "partial"}
OFFICIAL_WORKSTREAMS = ("busca1", "busca2a", "busca2b")
WEB_KEYWORDS = (
    "guideline",
    "guidance",
    "recommendation",
    "consensus",
    "statement",
    "standard",
    "nutrition",
    "diet",
    "dietary",
    "food",
)
_FIELD_TAG_RE = re.compile(r"\[(?:mesh|tiab|ti|pt|la|dp)\]", re.I)
_SPACE_RE = re.compile(r"\s+")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    return cleaned[:160] or "item"


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            handle.write("\n")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


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
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _strip_pubmed_fields(query: str) -> str:
    text = _FIELD_TAG_RE.sub("", query)
    text = re.sub(r"\bhasabstract\b", "", text, flags=re.I)
    text = text.replace("**", "*")
    return _SPACE_RE.sub(" ", text).strip()


def _queries() -> dict[str, str]:
    config_path = REPO_ROOT / "config" / "gf02_pubmed_candidates.json"
    config = load_candidate_config(config_path)
    expressions = resolved_line_expressions(config)
    final_line = str(config.get("final_line") or "#7")
    pubmed = expressions[final_line]
    q1 = _strip_pubmed_fields(str((config.get("lines") or {}).get("#1", {}).get("query") or ""))
    q2 = _strip_pubmed_fields(str((config.get("lines") or {}).get("#2", {}).get("query") or ""))
    q4 = _strip_pubmed_fields(str((config.get("lines") or {}).get("#4", {}).get("query") or ""))
    generic = f"(({q1}) AND ({q2})) OR ({q4})"
    generic = _SPACE_RE.sub(" ", generic).strip()
    web = generic.replace("*", "")
    return {
        "pubmed": pubmed,
        "generic": generic,
        "web": web,
        "candidate": str(config.get("current_candidate") or "UNKNOWN"),
    }


def _artifact_ok(entry: dict[str, Any]) -> bool:
    path = Path(str(entry.get("path") or ""))
    expected = str(entry.get("sha256") or "")
    if not path.is_file() or not expected:
        return False
    return sha256(path.read_bytes()).hexdigest() == expected


def _save_provider_snapshot(run_dir: Path, provider: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    path = run_dir / "providers" / f"{_safe(provider)}.jsonl"
    digest = _atomic_jsonl(path, rows)
    return {
        "provider": provider,
        "path": str(path),
        "sha256": digest,
        "records": len(rows),
        "saved_at": _now(),
    }


def _normal_key(row: dict[str, Any]) -> str:
    doi = normalize_doi(str(row.get("doi") or "")) or ""
    if doi:
        return "doi:" + doi.lower()
    pmid = normalize_pmid(row.get("pmid")) or ""
    if pmid:
        return "pmid:" + pmid
    url = normalize_url(str(row.get("url") or "")) or ""
    if url:
        return "url:" + url.lower()
    title = _SPACE_RE.sub(" ", str(row.get("title") or "").strip().lower())
    return "title:" + title if title else ""


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = _normal_key(row)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(row)
    return out


def _date_query(base: str, start: date, end: date) -> str:
    return f'({base}) AND ("{start.isoformat().replace("-", "/")}"[dp] : "{end.isoformat().replace("-", "/")}"[dp])'


def _pubmed_exhaustive(
    project_root: Path,
    run_dir: Path,
    base_query: str,
    progress: Callable[[str], None],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pubmed_dir = run_dir / "pubmed_partitions"
    state_path = run_dir / "pubmed_partition_state.json"
    state = _load_json(state_path)
    if state.get("base_query_sha256") != sha256(base_query.encode("utf-8")).hexdigest():
        state = {
            "schema_version": 1,
            "base_query_sha256": sha256(base_query.encode("utf-8")).hexdigest(),
            "started_at": _now(),
            "counts": {},
            "partitions": {},
            "errors": [],
        }
        _atomic_json(state_path, state)

    client = PubMedClient()
    checkpoint_dir = project_root / "07_logs" / "checkpoints" / "collect_everything_pubmed"
    context_base = {
        "checkpoint_dir": checkpoint_dir,
        "resume": True,
        "workstream": "article1_collect_everything",
    }

    if state.get("base_total_found") is None:
        progress("PubMed: contando o universo completo da query canônica...")
        probe = client.search(base_query, limit=1, context=context_base)
        state["base_total_found"] = int(probe.total_found or probe.total_returned or 0)
        _atomic_json(state_path, state)
    base_total = int(state.get("base_total_found") or 0)
    progress(f"PubMed: total informado pelo provedor = {base_total}.")

    start = date(1800, 1, 1)
    end = date(date.today().year + 1, 12, 31)
    stack: list[tuple[date, date]] = [(start, end)]
    leaf_keys: list[str] = []
    unresolved: list[dict[str, Any]] = []

    while stack:
        lo, hi = stack.pop()
        key = f"{lo.isoformat()}__{hi.isoformat()}"
        entry = dict((state.get("partitions") or {}).get(key) or {})
        if entry.get("status") == "complete" and _artifact_ok(entry):
            leaf_keys.append(key)
            continue

        counts = state.setdefault("counts", {})
        if key not in counts:
            q = _date_query(base_query, lo, hi)
            probe_context = dict(context_base)
            probe_context["workstream"] = f"article1_count_{key}"
            probe = client.search(q, limit=1, context=probe_context)
            counts[key] = int(probe.total_found or probe.total_returned or 0)
            _atomic_json(state_path, state)
        count = int(counts[key])
        if count <= 9999:
            q = _date_query(base_query, lo, hi)
            fetch_context = dict(context_base)
            fetch_context["workstream"] = f"article1_fetch_{key}"
            progress(f"PubMed: {key} → {count} registros; salvando esta partição...")
            if count == 0:
                rows: list[dict[str, Any]] = []
            else:
                result = client.search(q, limit=count, context=fetch_context)
                rows = list(result.rows or [])
            path = pubmed_dir / f"{_safe(key)}.jsonl"
            digest = _atomic_jsonl(path, rows)
            state.setdefault("partitions", {})[key] = {
                "status": "complete",
                "count_reported": count,
                "records_saved": len(rows),
                "path": str(path),
                "sha256": digest,
                "query": q,
                "saved_at": _now(),
            }
            _atomic_json(state_path, state)
            leaf_keys.append(key)
            continue

        if lo >= hi:
            unresolved.append({"range": key, "count": count, "reason": "single_day_over_9999"})
            continue
        span_days = (hi - lo).days
        mid = date.fromordinal(lo.toordinal() + span_days // 2)
        if mid >= hi:
            unresolved.append({"range": key, "count": count, "reason": "cannot_split_further"})
            continue
        stack.append((date.fromordinal(mid.toordinal() + 1), hi))
        stack.append((lo, mid))

    complement_key = "outside_1800_current_plus1"
    complement = f'({base_query}) NOT ("1800/01/01"[dp] : "{end.isoformat().replace("-", "/")}"[dp])'
    counts = state.setdefault("counts", {})
    if complement_key not in counts:
        probe_context = dict(context_base)
        probe_context["workstream"] = "article1_count_undated"
        probe = client.search(complement, limit=1, context=probe_context)
        counts[complement_key] = int(probe.total_found or probe.total_returned or 0)
        _atomic_json(state_path, state)
    complement_count = int(counts[complement_key])
    if complement_count <= 9999:
        entry = dict((state.get("partitions") or {}).get(complement_key) or {})
        if not (entry.get("status") == "complete" and _artifact_ok(entry)):
            fetch_context = dict(context_base)
            fetch_context["workstream"] = "article1_fetch_undated"
            rows = [] if complement_count == 0 else list(client.search(complement, limit=complement_count, context=fetch_context).rows or [])
            path = pubmed_dir / f"{complement_key}.jsonl"
            digest = _atomic_jsonl(path, rows)
            state.setdefault("partitions", {})[complement_key] = {
                "status": "complete",
                "count_reported": complement_count,
                "records_saved": len(rows),
                "path": str(path),
                "sha256": digest,
                "query": complement,
                "saved_at": _now(),
            }
            _atomic_json(state_path, state)
        leaf_keys.append(complement_key)
    else:
        unresolved.append({"range": complement_key, "count": complement_count, "reason": "undated_over_9999"})

    rows_all: list[dict[str, Any]] = []
    for key in leaf_keys:
        entry = dict((state.get("partitions") or {}).get(key) or {})
        if _artifact_ok(entry):
            rows_all.extend(_read_jsonl(Path(str(entry["path"]))))
    rows_all = _dedupe(rows_all)
    state["finished_at"] = _now()
    state["records_unique_saved"] = len(rows_all)
    state["unresolved_partitions"] = unresolved
    state["coverage_complete"] = not unresolved and (len(rows_all) >= base_total or base_total == 0)
    _atomic_json(state_path, state)
    progress(
        f"PubMed: {len(rows_all)} registros únicos salvos em partições; "
        f"coverage_complete={state['coverage_complete']}."
    )
    return rows_all, state


def _run_list_provider(
    run_dir: Path,
    provider: str,
    query: str,
    loader: Callable[[], list[dict[str, Any]]],
    progress: Callable[[str], None],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta_path = run_dir / "providers" / f"{_safe(provider)}.meta.json"
    meta = _load_json(meta_path)
    if meta.get("status") == "complete" and _artifact_ok(meta):
        rows = _read_jsonl(Path(str(meta["path"])))
        progress(f"{provider}: restaurado do autosave ({len(rows)} registros).")
        return rows, meta
    progress(f"{provider}: pesquisando...")
    try:
        rows = list(loader() or [])
        artifact = _save_provider_snapshot(run_dir, provider, rows)
        meta = {
            **artifact,
            "status": "complete",
            "query": query,
            "error": "",
        }
    except Exception as exc:
        rows = []
        meta = {
            "provider": provider,
            "status": "failed",
            "query": query,
            "error": str(exc),
            "saved_at": _now(),
        }
    _atomic_json(meta_path, meta)
    progress(f"{provider}: {meta['status']} ({len(rows)} registros).")
    return rows, meta


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = next((value or "" for key, value in attrs if key.lower() == "href"), "")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = ""
            self._text = []


def _same_domain(a: str, b: str) -> bool:
    try:
        da = urlparse(a).netloc.lower().removeprefix("www.")
        db = urlparse(b).netloc.lower().removeprefix("www.")
    except Exception:
        return False
    return bool(da and db and da == db)


def _ext_for(url: str, content_type: str) -> str:
    path = urlparse(url).path.lower()
    for ext in (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".txt", ".xml", ".json"):
        if path.endswith(ext):
            return ext
    ctype = content_type.lower()
    if "pdf" in ctype:
        return ".pdf"
    if "html" in ctype:
        return ".html"
    if "json" in ctype:
        return ".json"
    if "xml" in ctype:
        return ".xml"
    return ".bin"


def _fetch_web_document(
    session: requests.Session,
    url: str,
    docs_dir: Path,
    *,
    max_bytes: int,
) -> tuple[dict[str, Any], bytes]:
    started = _now()
    response = session.get(url, timeout=(10, 45), allow_redirects=True, stream=True)
    status = int(response.status_code)
    content_type = str(response.headers.get("content-type") or "")
    chunks: list[bytes] = []
    size = 0
    truncated = False
    if status < 400:
        for chunk in response.iter_content(chunk_size=1024 * 128):
            if not chunk:
                continue
            if size + len(chunk) > max_bytes:
                remain = max(0, max_bytes - size)
                if remain:
                    chunks.append(chunk[:remain])
                    size += remain
                truncated = True
                break
            chunks.append(chunk)
            size += len(chunk)
    content = b"".join(chunks)
    digest = sha256(content).hexdigest() if content else ""
    saved_path = ""
    if content:
        ext = _ext_for(str(response.url), content_type)
        path = docs_dir / f"{digest[:24]}{ext}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(content)
        saved_path = str(path)
    row = {
        "source": "official_web_live",
        "source_provider": "official_web_live",
        "title": "",
        "url": str(response.url),
        "original_url": url,
        "http_status": status,
        "content_type": content_type,
        "content_bytes_saved": len(content),
        "content_truncated": truncated,
        "content_sha256": digest,
        "saved_path": saved_path,
        "retrieved_at": started,
        "metadata_status": "official_web_live",
        "article_type": "web_document",
        "doi": "",
        "pmid": "",
        "pmcid": "",
        "abstract": "",
        "summary": "",
        "journal": "",
        "year": "",
        "publication_date": "",
        "authors": "",
    }
    return row, content


def _official_web(
    run_dir: Path,
    progress: Callable[[str], None],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta_path = run_dir / "providers" / "official_web_live.meta.json"
    meta = _load_json(meta_path)
    if meta.get("status") == "complete" and _artifact_ok(meta):
        rows = _read_jsonl(Path(str(meta["path"])))
        progress(f"official_web_live: restaurado do autosave ({len(rows)} documentos).")
        return rows, meta

    manifest = load_official_manifest(REPO_ROOT / "config", include_countries=True)
    seeds: list[dict[str, Any]] = []
    seen_seed: set[str] = set()
    for workstream in OFFICIAL_WORKSTREAMS:
        for row in manifest_sources(manifest, workstream):
            url = str(row.get("url") or "")
            if not url or url in seen_seed:
                continue
            seen_seed.add(url)
            item = dict(row)
            item["workstream"] = workstream
            seeds.append(item)

    max_bytes = int(os.environ.get("NUTEV_WEB_MAX_BYTES", str(25 * 1024 * 1024)))
    links_per_seed = int(os.environ.get("NUTEV_WEB_LINKS_PER_SEED", "5"))
    session = requests.Session()
    session.headers.update({"User-Agent": "NutEV Evidence Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"})
    rows: list[dict[str, Any]] = []
    fetched: set[str] = set()
    docs_dir = run_dir / "web_documents"
    try:
        for index, seed in enumerate(seeds, start=1):
            seed_url = str(seed["url"])
            progress(f"Web oficial {index}/{len(seeds)}: {seed_url}")
            try:
                row, content = _fetch_web_document(session, seed_url, docs_dir, max_bytes=max_bytes)
                row.update(
                    {
                        "title": str(seed.get("title") or seed.get("name") or ""),
                        "authority": seed.get("authority"),
                        "source_institution": seed.get("source_institution") or "",
                        "workstream": seed.get("workstream"),
                        "query": "official_manifest_article1",
                        "provider_query": "official_manifest_article1",
                    }
                )
                rows.append(row)
                fetched.add(str(row.get("url") or seed_url))
                _atomic_jsonl(run_dir / "providers" / "official_web_live.partial.jsonl", rows)

                if row.get("http_status", 999) >= 400 or row.get("content_truncated"):
                    continue
                if "html" not in str(row.get("content_type") or "").lower() or not content:
                    continue
                parser = _LinkParser()
                try:
                    parser.feed(content.decode("utf-8", errors="ignore"))
                except Exception:
                    continue
                candidates: list[str] = []
                for href, text in parser.links:
                    absolute = urljoin(str(row.get("url") or seed_url), href)
                    if absolute in fetched or not _same_domain(seed_url, absolute):
                        continue
                    haystack = (absolute + " " + text).lower()
                    if not any(word in haystack for word in WEB_KEYWORDS):
                        continue
                    if absolute.startswith("mailto:") or absolute.startswith("javascript:"):
                        continue
                    candidates.append(absolute)
                    if len(candidates) >= links_per_seed:
                        break
                for child in candidates:
                    fetched.add(child)
                    try:
                        child_row, _ = _fetch_web_document(session, child, docs_dir, max_bytes=max_bytes)
                        child_row.update(
                            {
                                "title": "",
                                "authority": seed.get("authority"),
                                "source_institution": seed.get("source_institution") or "",
                                "workstream": seed.get("workstream"),
                                "parent_url": seed_url,
                                "query": "official_manifest_article1_discovered_link",
                                "provider_query": "official_manifest_article1_discovered_link",
                            }
                        )
                        rows.append(child_row)
                        _atomic_jsonl(run_dir / "providers" / "official_web_live.partial.jsonl", rows)
                    except Exception as exc:
                        rows.append(
                            {
                                "source": "official_web_live",
                                "source_provider": "official_web_live",
                                "url": child,
                                "parent_url": seed_url,
                                "metadata_status": "fetch_failed",
                                "error": str(exc),
                                "retrieved_at": _now(),
                            }
                        )
            except Exception as exc:
                rows.append(
                    {
                        "source": "official_web_live",
                        "source_provider": "official_web_live",
                        "title": str(seed.get("title") or ""),
                        "url": seed_url,
                        "metadata_status": "fetch_failed",
                        "error": str(exc),
                        "retrieved_at": _now(),
                    }
                )
                _atomic_jsonl(run_dir / "providers" / "official_web_live.partial.jsonl", rows)
    finally:
        session.close()

    artifact = _save_provider_snapshot(run_dir, "official_web_live", rows)
    meta = {**artifact, "status": "complete", "seed_count": len(seeds), "query": "official_manifest_article1"}
    _atomic_json(meta_path, meta)
    progress(f"official_web_live: {len(rows)} páginas/documentos salvos.")
    return rows, meta


def _run_optional_web(
    run_dir: Path,
    web_query: str,
    progress: Callable[[str], None],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    metas: dict[str, dict[str, Any]] = {}
    providers = [
        ("google_pse", bool(os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID")), lambda: search_google_pse(web_query, limit=100)),
        ("brave", bool(os.environ.get("BRAVE_API_KEY")), lambda: search_brave(web_query, limit=20)),
        ("serpapi", bool(os.environ.get("SERPAPI_API_KEY")), lambda: search_serpapi(web_query, limit=100)),
    ]
    for provider, configured, call in providers:
        if not configured:
            external.append({"provider": provider, "reason": "api_credentials_not_configured"})
            continue
        meta_path = run_dir / "providers" / f"{provider}.meta.json"
        meta = _load_json(meta_path)
        if meta.get("status") == "complete" and _artifact_ok(meta):
            existing_rows = _read_jsonl(Path(str(meta["path"])))
            rows.extend(existing_rows)
            metas[provider] = meta
            progress(f"{provider}: restaurado do autosave ({len(existing_rows)} resultados web).")
            continue
        progress(f"{provider}: buscando na web aberta...")
        result = call()
        provider_rows = list(result.rows or [])
        artifact = _save_provider_snapshot(run_dir, provider, provider_rows)
        meta = {
            **artifact,
            "status": "complete" if result.status in SUCCESS_STATUSES else result.status,
            "provider_status": result.status,
            "total_found": result.total_found,
            "error": result.error or "",
            "query": web_query,
        }
        _atomic_json(meta_path, meta)
        metas[provider] = meta
        rows.extend(provider_rows)
    return rows, external, metas


def run(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    state_path = project_root / "07_logs" / "collect_everything" / "latest.json"
    queries = _queries()
    strategy_hash = sha256((queries["pubmed"] + "\n" + queries["generic"]).encode("utf-8")).hexdigest()
    existing = _load_json(state_path)
    reusable = bool(existing and existing.get("strategy_sha256") == strategy_hash and existing.get("run_id"))
    run_id = str(existing["run_id"]) if reusable else "everything_" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z") + "_" + uuid4().hex[:8]
    run_dir = project_root / "13_collect_everything" / _safe(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    def progress(text: str) -> None:
        print(text, flush=True)
        current = _load_json(state_path)
        current.update({
            "schema_version": SCHEMA_VERSION,
            "collection_type": COLLECTION_TYPE,
            "run_id": run_id,
            "strategy_sha256": strategy_hash,
            "status": "RUNNING",
            "last_message": text,
            "updated_at": _now(),
            "run_dir": str(run_dir),
            "prisma_eligible": False,
            "formal_execution_authorized": False,
            "scientific_gate_effect": "NONE",
        })
        _atomic_json(state_path, current)

    progress("NutEV: iniciando/retomando coleta REAL em todas as fontes automatizáveis. PRESS não bloqueia esta coleta.")
    progress("Autosave ativo. O que for salvo permanece no disco mesmo se o terminal fechar.")

    provider_rows: dict[str, list[dict[str, Any]]] = {}
    provider_meta: dict[str, dict[str, Any]] = {}
    external_requirements: list[dict[str, Any]] = []

    pubmed_rows, pubmed_state = _pubmed_exhaustive(project_root, run_dir, queries["pubmed"], progress)
    provider_rows["pubmed"] = pubmed_rows
    provider_meta["pubmed"] = {
        "status": "complete" if pubmed_state.get("coverage_complete") else "partial",
        "records": len(pubmed_rows),
        "provider_total_found": pubmed_state.get("base_total_found"),
        "coverage_complete": bool(pubmed_state.get("coverage_complete")),
        "partition_state_path": str(run_dir / "pubmed_partition_state.json"),
        "unresolved_partitions": pubmed_state.get("unresolved_partitions") or [],
    }

    max_epmc = int(os.environ.get("NUTEV_EVERYTHING_EUROPEPMC_MAX", "50000"))
    max_openalex = int(os.environ.get("NUTEV_EVERYTHING_OPENALEX_MAX", "50000"))
    max_crossref = int(os.environ.get("NUTEV_EVERYTHING_CROSSREF_MAX", "10000"))
    max_doaj = int(os.environ.get("NUTEV_EVERYTHING_DOAJ_MAX", "10000"))
    max_s2 = int(os.environ.get("NUTEV_EVERYTHING_S2_MAX", "10000"))

    loaders: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = [
        ("europepmc", lambda: search_europepmc(queries["generic"], page_size=1000, max_results=max_epmc)),
        ("openalex", lambda: search_openalex(queries["web"], per_page=200, max_results=max_openalex)),
        ("crossref", lambda: search_crossref(queries["web"], rows=1000, max_results=max_crossref)),
        ("doaj", lambda: search_doaj(queries["web"], page_size=100, max_results=max_doaj)),
        ("semantic_scholar", lambda: search_semantic_scholar(queries["web"], page_size=100, max_results=max_s2)),
    ]
    for provider, loader in loaders:
        rows, meta = _run_list_provider(run_dir, provider, queries["generic"], loader, progress)
        provider_rows[provider] = rows
        provider_meta[provider] = meta

    official_rows, official_meta = _official_web(run_dir, progress)
    provider_rows["official_web_live"] = official_rows
    provider_meta["official_web_live"] = official_meta

    web_rows, web_external, web_metas = _run_optional_web(run_dir, queries["web"], progress)
    for provider, meta in web_metas.items():
        provider_meta[provider] = meta
    for row in web_rows:
        provider_rows.setdefault(str(row.get("source_provider") or "web"), []).append(row)
    external_requirements.extend(web_external)

    external_requirements.extend(
        [
            {"provider": "scielo_native", "reason": "official_csv_or_ris_export_required"},
            {"provider": "lilacs_bvs", "reason": "official_csv_or_ris_export_required"},
            {"provider": "scopus", "reason": "licensed_access_or_export_required"},
            {"provider": "web_of_science", "reason": "licensed_access_or_export_required"},
        ]
    )

    combined: list[dict[str, Any]] = []
    for provider, rows in provider_rows.items():
        for row in rows:
            item = dict(row)
            item.setdefault("source_provider", provider)
            item.setdefault("source", provider)
            item["collection_type"] = COLLECTION_TYPE
            item["prisma_eligible"] = False
            item["formal_execution_authorized"] = False
            item["scientific_gate_effect"] = "NONE"
            combined.append(item)
    master = _dedupe(combined)
    master_path = run_dir / "master_records.jsonl"
    master_sha = _atomic_jsonl(master_path, master)

    provider_summary = {}
    for provider, rows in provider_rows.items():
        meta = provider_meta.get(provider) or {}
        provider_summary[provider] = {
            "status": meta.get("status") or "complete",
            "records_saved": len(rows),
            "path": meta.get("path") or "",
            "sha256": meta.get("sha256") or "",
            "error": meta.get("error") or "",
            "coverage_complete": meta.get("coverage_complete"),
            "provider_total_found": meta.get("provider_total_found") or meta.get("total_found"),
        }

    result = {
        "schema_version": SCHEMA_VERSION,
        "collection_type": COLLECTION_TYPE,
        "run_id": run_id,
        "started_at": existing.get("started_at") if reusable else _now(),
        "finished_at": _now(),
        "status": "COMPLETE_WITH_EXTERNAL_REQUIREMENTS" if external_requirements else "COMPLETE",
        "strategy_sha256": strategy_hash,
        "strategy_candidate": queries["candidate"],
        "queries": queries,
        "providers": provider_summary,
        "external_requirements": external_requirements,
        "records_before_cross_source_dedup": len(combined),
        "unique_records_after_cross_source_dedup": len(master),
        "master_records_path": str(master_path),
        "master_records_sha256": master_sha,
        "run_dir": str(run_dir),
        "prisma_eligible": False,
        "formal_execution_authorized": False,
        "scientific_gate_effect": "NONE",
        "human_decision_inferred": False,
        "notes": [
            "This is real pre-review discovery, not FORMAL execution.",
            "PRESS/FREEZE/PRISMA state is not changed by this command.",
            "Missing licensed/export/API sources are reported at the end and never silently substituted.",
        ],
    }
    _atomic_json(run_dir / "manifest.json", result)
    _atomic_json(state_path, result)

    print("", flush=True)
    print("COLETA REAL FINALIZADA", flush=True)
    print(f"Registros antes da deduplicação entre fontes: {len(combined)}", flush=True)
    print(f"Registros únicos organizados: {len(master)}", flush=True)
    print(f"Master: {master_path}", flush=True)
    if external_requirements:
        print("Pendências externas/licenciadas (não bloquearam a coleta automática):", flush=True)
        for item in external_requirements:
            print(f"- {item['provider']}: {item['reason']}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run every real, automatable NutEV discovery source without crossing scientific gates.")
    parser.add_argument("--project-root", default="project_output_scientific")
    args = parser.parse_args()
    try:
        run(Path(args.project_root))
    except KeyboardInterrupt:
        print("Interrompido pelo usuário. Autosaves existentes foram preservados; execute o mesmo comando para retomar.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Falha: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("Os autosaves já gravados foram preservados. Execute o mesmo comando para retomar.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
