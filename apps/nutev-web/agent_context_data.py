from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
DEFAULT_CONTEXT_ROOT = REPO_ROOT / "project_output_reference" / "agent_context" / "article1"
MAX_PAGE_SIZE = 100


class AgentContextDataError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentContextDataError(f"invalid agent context JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AgentContextDataError(f"agent context JSON must be an object: {path}")
    return value


def _resolved_output(root: Path, item: dict[str, Any]) -> tuple[Path, str]:
    raw = str(item.get("path") or "").strip()
    expected = str(item.get("sha256") or "").strip().lower()
    if not raw or not expected:
        raise AgentContextDataError("agent context output path/hash missing")
    path = Path(raw)
    if not path.is_absolute():
        path = root / path.name
    if not path.is_file():
        raise AgentContextDataError(f"agent context output missing: {path}")
    actual = _sha256_file(path)
    if actual != expected:
        raise AgentContextDataError(
            f"agent context output SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return path, actual


def _verified_context(root: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    manifest = _read_json(root / "CONTEXT_MANIFEST.json")
    if manifest.get("context_type") != "NUTEV_ARTICLE1_AGENT_CONTEXT":
        raise AgentContextDataError("unexpected agent context manifest type")
    if manifest.get("status") != "PASS":
        raise AgentContextDataError("agent context manifest is not PASS")
    safety = manifest.get("safety") or {}
    if safety.get("rank_blind") is not True or safety.get("full_text_included") is not False:
        raise AgentContextDataError("agent context safety contract is not rank-blind/full-text-free")
    outputs = manifest.get("outputs") or {}
    state_path, _ = _resolved_output(root, outputs.get("search_state") or {})
    summaries_path, _ = _resolved_output(root, outputs.get("article_summaries") or {})
    state = _read_json(state_path)
    return manifest, state, summaries_path


def agent_context_status(root: Path | None = None) -> dict[str, Any]:
    base = root or DEFAULT_CONTEXT_ROOT
    try:
        manifest, state, _summaries = _verified_context(base)
    except FileNotFoundError:
        return {
            "status": "not_ready",
            "message": "Article 1 agent context not built. Run tools/build_article1_agent_context.py.",
            "full_text_exposed": False,
        }
    return {
        "status": "ready",
        "context_version": manifest.get("context_version"),
        "search_id": manifest.get("search_id"),
        "question": state.get("question"),
        "master_status": state.get("master_status"),
        "formal_search": state.get("formal_search") or {},
        "runtime": state.get("runtime") or {},
        "counts": manifest.get("counts") or {},
        "articles_endpoint": "/api/agent-context/article1/articles",
        "article_detail_endpoint_template": "/api/articles/{document_id}",
        "rank_blind": True,
        "full_text_exposed": False,
        "semantics": "agent navigation/context only; not screening, evidence acceptance or PRISMA",
    }


def _read_summary_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AgentContextDataError(
                    f"invalid article summary JSONL at line {line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise AgentContextDataError(
                    f"article summary JSONL row {line_number} is not an object"
                )
            forbidden = {
                "reference_rank",
                "reference_score",
                "reference_tier",
                "machine_relevance_score",
                "machine_relevance_band",
            }
            leaked = forbidden & set(value)
            if leaked:
                raise AgentContextDataError(
                    "agent article summary exposes forbidden fields: " + ", ".join(sorted(leaked))
                )
            rows.append(value)
    return rows


def load_agent_article_page(
    *,
    root: Path | None = None,
    limit: int = 50,
    offset: int = 0,
    route: str = "",
    document_class: str = "",
    q: str = "",
) -> dict[str, Any]:
    base = root or DEFAULT_CONTEXT_ROOT
    _manifest, _state, summaries_path = _verified_context(base)
    page_limit = max(1, min(int(limit), MAX_PAGE_SIZE))
    page_offset = max(0, int(offset))
    route = str(route or "").strip().upper()
    document_class = str(document_class or "").strip()
    query = " ".join(str(q or "").casefold().split())[:300]

    rows = _read_summary_rows(summaries_path)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if route and route not in {str(value).upper() for value in row.get("routes") or []}:
            continue
        if document_class and str(row.get("document_class") or "") != document_class:
            continue
        if query:
            haystack = " ".join(
                str(value or "")
                for value in (
                    row.get("title"),
                    row.get("reference_stub"),
                    row.get("doi"),
                    row.get("pmid"),
                )
            ).casefold()
            if query not in haystack:
                continue
        filtered.append(row)

    visible = filtered[page_offset: page_offset + page_limit]
    next_offset = page_offset + len(visible)
    if next_offset >= len(filtered):
        next_offset = None
    return {
        "status": "ready",
        "total_filtered": len(filtered),
        "page_size": len(visible),
        "offset": page_offset,
        "next_offset": next_offset,
        "filters": {
            "route": route,
            "document_class": document_class,
            "q": q,
        },
        "articles": visible,
        "rank_blind": True,
        "full_text_exposed": False,
        "max_page_size": MAX_PAGE_SIZE,
    }
