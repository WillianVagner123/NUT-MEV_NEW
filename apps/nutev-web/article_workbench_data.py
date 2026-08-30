from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
DEFAULT_WORKBENCH_ROOT = REPO_ROOT / "project_output_reference" / "scientific" / "workbench"
_VERIFIED_DB: dict[str, tuple[int, int, str]] = {}
_SORT_MODES = {"relevance", "newest", "oldest"}
_TIERS = {"A", "B", "C", "D"}


class ArticleWorkbenchDataError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(root: Path) -> dict[str, Any]:
    path = root / "WORKBENCH_MANIFEST.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArticleWorkbenchDataError(f"invalid Workbench manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise ArticleWorkbenchDataError("Workbench manifest must be an object")
    if value.get("workbench_type") != "NUTEV_ARTICLE_WORKBENCH_V1":
        raise ArticleWorkbenchDataError("unexpected Workbench manifest type")
    if value.get("status") != "PASS":
        raise ArticleWorkbenchDataError("Workbench manifest is not PASS")
    return value


def _verified_database(root: Path) -> tuple[Path, dict[str, Any]]:
    manifest = _read_manifest(root)
    output = (manifest.get("outputs") or {}).get("database") or {}
    database = Path(str(output.get("path") or ""))
    if not database.is_absolute():
        database = (REPO_ROOT / database).resolve()
    expected = str(output.get("sha256") or "").strip().lower()
    if not database.is_file() or not expected:
        raise ArticleWorkbenchDataError("Workbench database or SHA-256 is missing")
    stat = database.stat()
    key = str(database)
    cached = _VERIFIED_DB.get(key)
    signature = (stat.st_size, stat.st_mtime_ns, expected)
    if cached != signature:
        actual = _sha256_file(database)
        if actual != expected:
            raise ArticleWorkbenchDataError(
                f"Workbench database SHA-256 mismatch: expected {expected}, got {actual}"
            )
        _VERIFIED_DB[key] = signature
    return database, manifest


def _connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _article_columns(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(article_cards)").fetchall()
    }


def _encode_cursor(sort_mode: str, primary: int, document_id: str) -> str:
    raw = json.dumps([sort_mode, primary, document_id], separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(value: str | None) -> tuple[str, int, str] | None:
    if not value:
        return None
    try:
        padded = value + ("=" * (-len(value) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        if isinstance(payload, list) and len(payload) == 2:
            year, document_id = payload
            return "newest", int(year), str(document_id)
        if isinstance(payload, list) and len(payload) == 3:
            sort_mode, primary, document_id = payload
            sort_mode = str(sort_mode)
            if sort_mode not in _SORT_MODES:
                raise ValueError(sort_mode)
            return sort_mode, int(primary), str(document_id)
        raise ValueError("cursor shape")
    except Exception as exc:
        raise ArticleWorkbenchDataError("invalid article cursor") from exc


def _query_directives(q: str) -> tuple[str, str, str]:
    tier = ""
    sort_mode = "newest"
    visible: list[str] = []
    for token in str(q or "").split():
        lower = token.casefold()
        if lower.startswith("__nutev_tier:"):
            candidate = token.split(":", 1)[1].strip().upper()
            if candidate in _TIERS:
                tier = candidate
            continue
        if lower.startswith("__nutev_sort:"):
            candidate = token.split(":", 1)[1].strip().casefold()
            if candidate in _SORT_MODES:
                sort_mode = candidate
            continue
        visible.append(token)
    return " ".join(visible).strip(), tier, sort_mode


def workbench_status(root: Path | None = None) -> dict[str, Any]:
    base = root or DEFAULT_WORKBENCH_ROOT
    try:
        database, manifest = _verified_database(base)
    except FileNotFoundError:
        return {
            "status": "not_ready",
            "message": "Article Workbench ainda sem índice. Rode `nutev science-workbench-index`.",
        }
    counts = manifest.get("counts") or {}
    extension = ((manifest.get("extensions") or {}).get("bank_priority") or {})
    priority_ready = isinstance(extension, dict) and extension.get("status") == "PASS"
    return {
        "status": "ready",
        "database": str(database),
        "articles": int(counts.get("articles") or 0),
        "evidence_excerpts": int(counts.get("evidence_excerpts") or 0),
        "result_bundles": int(counts.get("result_bundles") or 0),
        "priority_index": priority_ready,
        "priority_search_id": extension.get("search_id") if priority_ready else None,
        "page_limit_max": 100,
        "full_corpus_sent_to_browser": False,
    }


def load_article_page(
    *,
    root: Path | None = None,
    q: str = "",
    limit: int = 50,
    cursor: str | None = None,
    source_provider: str = "",
    document_class: str = "",
    full_text_status: str = "",
) -> dict[str, Any]:
    base = root or DEFAULT_WORKBENCH_ROOT
    database, _manifest = _verified_database(base)
    page_limit = max(1, min(int(limit), 100))
    query_text, tier, sort_mode = _query_directives(q)

    with _connect(database) as connection:
        columns = _article_columns(connection)
        priority_ready = {
            "reference_rank",
            "reference_score",
            "reference_tier",
        }.issubset(columns)
        if (tier or sort_mode == "relevance") and not priority_ready:
            raise ArticleWorkbenchDataError(
                "Bank priority index is not ready. Run tools/augment_workbench_priority.py."
            )

        conditions: list[str] = []
        parameters: list[Any] = []
        normalized_query = " ".join(query_text.casefold().split())[:300]
        if normalized_query:
            conditions.append("search_text LIKE ?")
            parameters.append(f"%{normalized_query}%")
        if source_provider:
            conditions.append("source_provider = ?")
            parameters.append(source_provider)
        if document_class:
            conditions.append("document_class = ?")
            parameters.append(document_class)
        if full_text_status:
            conditions.append("full_text_status = ?")
            parameters.append(full_text_status)
        if tier:
            conditions.append("reference_tier = ?")
            parameters.append(f"BANK_{tier}_PROCESSING_PRIORITY")
        base_where = " WHERE " + " AND ".join(conditions) if conditions else ""

        decoded_cursor = _decode_cursor(cursor)
        page_conditions = list(conditions)
        page_parameters = list(parameters)
        if sort_mode == "relevance":
            primary_expr = "COALESCE(reference_rank, 2147483647)"
            order_by = primary_expr + " ASC, document_id ASC"
            if decoded_cursor is not None:
                cursor_sort, cursor_primary, cursor_document = decoded_cursor
                if cursor_sort != sort_mode:
                    raise ArticleWorkbenchDataError("article cursor sort does not match current sort")
                page_conditions.append(
                    f"({primary_expr} > ? OR ({primary_expr} = ? AND document_id > ?))"
                )
                page_parameters.extend([cursor_primary, cursor_primary, cursor_document])
        elif sort_mode == "oldest":
            primary_expr = "COALESCE(year, 9999)"
            order_by = primary_expr + " ASC, document_id ASC"
            if decoded_cursor is not None:
                cursor_sort, cursor_primary, cursor_document = decoded_cursor
                if cursor_sort != sort_mode:
                    raise ArticleWorkbenchDataError("article cursor sort does not match current sort")
                page_conditions.append(
                    f"({primary_expr} > ? OR ({primary_expr} = ? AND document_id > ?))"
                )
                page_parameters.extend([cursor_primary, cursor_primary, cursor_document])
        else:
            sort_mode = "newest"
            primary_expr = "COALESCE(year, 0)"
            order_by = primary_expr + " DESC, document_id ASC"
            if decoded_cursor is not None:
                cursor_sort, cursor_primary, cursor_document = decoded_cursor
                if cursor_sort != sort_mode:
                    raise ArticleWorkbenchDataError("article cursor sort does not match current sort")
                page_conditions.append(
                    f"({primary_expr} < ? OR ({primary_expr} = ? AND document_id > ?))"
                )
                page_parameters.extend([cursor_primary, cursor_primary, cursor_document])

        page_where = " WHERE " + " AND ".join(page_conditions) if page_conditions else ""
        total = int(
            connection.execute(
                "SELECT COUNT(*) FROM article_cards" + base_where,
                parameters,
            ).fetchone()[0]
        )
        priority_select = (
            "reference_rank, reference_score, reference_tier"
            if priority_ready
            else "NULL AS reference_rank, NULL AS reference_score, NULL AS reference_tier"
        )
        rows = connection.execute(
            f"""
            SELECT document_id, title, year, doi, pmid, source_provider,
                   document_class, full_text_status, reference_stub, llm_context_chars,
                   {priority_select}
            FROM article_cards
            """
            + page_where
            + f" ORDER BY {order_by} LIMIT ?",
            [*page_parameters, page_limit + 1],
        ).fetchall()

    has_more = len(rows) > page_limit
    visible = rows[:page_limit]
    next_cursor = None
    if has_more and visible:
        last = visible[-1]
        if sort_mode == "relevance":
            primary = int(last["reference_rank"] or 2147483647)
        elif sort_mode == "oldest":
            primary = int(last["year"] if last["year"] is not None else 9999)
        else:
            primary = int(last["year"] or 0)
        next_cursor = _encode_cursor(sort_mode, primary, str(last["document_id"]))
    return {
        "status": "ready",
        "total_filtered": total,
        "page_size": len(visible),
        "next_cursor": next_cursor,
        "filters": {
            "q": query_text,
            "source_provider": source_provider,
            "document_class": document_class,
            "full_text_status": full_text_status,
            "tier": tier,
            "sort": sort_mode,
        },
        "articles": [dict(row) for row in visible],
        "performance": {
            "server_side_filtering": True,
            "server_side_priority_sort": priority_ready,
            "full_corpus_sent_to_browser": False,
            "max_page_size": 100,
        },
    }


def load_article_detail(
    document_id: str,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or DEFAULT_WORKBENCH_ROOT
    database, _manifest = _verified_database(base)
    with _connect(database) as connection:
        columns = _article_columns(connection)
        priority_ready = {
            "reference_rank",
            "reference_score",
            "reference_tier",
        }.issubset(columns)
        priority_select = (
            ", reference_rank, reference_score, reference_tier"
            if priority_ready
            else ", NULL AS reference_rank, NULL AS reference_score, NULL AS reference_tier"
        )
        card_row = connection.execute(
            "SELECT card_json" + priority_select + " FROM article_cards WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        if card_row is None:
            raise KeyError(document_id)
        excerpts = connection.execute(
            """
            SELECT excerpt_json FROM evidence_excerpts
            WHERE document_id = ?
            ORDER BY priority_score DESC, excerpt_id ASC
            """,
            (document_id,),
        ).fetchall()
        results = connection.execute(
            """
            SELECT result_json FROM result_bundles
            WHERE document_id = ?
            ORDER BY priority_score DESC, result_id ASC
            """,
            (document_id,),
        ).fetchall()
    return {
        "status": "ready",
        "card": json.loads(card_row["card_json"]),
        "bank_priority": {
            "reference_rank": card_row["reference_rank"],
            "reference_score": card_row["reference_score"],
            "reference_tier": card_row["reference_tier"],
            "semantics": "operational reading/processing priority; not scientific inclusion or quality",
        },
        "evidence_excerpts": [json.loads(row["excerpt_json"]) for row in excerpts],
        "result_bundles": [json.loads(row["result_json"]) for row in results],
        "full_text_in_response": False,
    }
