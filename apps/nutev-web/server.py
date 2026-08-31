from __future__ import annotations

import argparse
import copy
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import sys
import threading
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4
import webbrowser

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import article1_context_index as context_index
import human_review_store as review_store
import review_control
from article_workbench_data import (
    ArticleWorkbenchDataError,
    load_article_detail,
    load_article_page,
    workbench_status,
)
from progress_search import search_evidence_progressive
from query_compiler import compile_query_plan
from radar_data import RadarDataError, load_radar_state
from search_adapter import (
    PROVIDER_LABELS,
    PROVIDER_ORDER,
    list_search_runs,
    load_search_run,
    search_evidence,
)
from validation_adjudication import (
    adjudication_payload,
    finalize_adjudication,
    save_adjudication,
)
from validation_decision import decision_status, lock_validation_decision
from validation_gold import build_and_validate_gold, gold_status
from validation_metrics import metrics_status, run_validation_metrics
from validation_readiness import get_validation_readiness
from validation_server import (
    prepare_round,
    reviewer_payload,
    round_status,
    save_decision,
    submit_reviewer,
)

MAX_BODY_BYTES = 256 * 1024
CONTEXT_UNAVAILABLE_MESSAGE = (
    "Article 1 agent context bundle is not available. Run tools/build_article1_agent_context.py."
)


def _first(query: dict[str, list[str]], key: str, default: str = "") -> str:
    values = query.get(key) or []
    return str(values[0]).strip() if values else default


def _year(query: dict[str, list[str]], key: str) -> int | None:
    raw = _first(query, key)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{key} must be a year") from None


def _context_filters(query: dict[str, list[str]]) -> dict[str, object]:
    return {
        "route": _first(query, "route", "all") or "all",
        "source_provider": _first(query, "source_provider"),
        "full_text_status": _first(query, "full_text_status"),
        "document_class": _first(query, "document_class"),
        "domain": _first(query, "domain"),
        "year_from": _year(query, "year_from"),
        "year_to": _year(query, "year_to"),
    }

MAX_SEARCH_JOBS = 100
_SEARCH_JOBS: dict[str, dict[str, object]] = {}
_SEARCH_JOBS_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _prune_jobs_locked() -> None:
    while len(_SEARCH_JOBS) >= MAX_SEARCH_JOBS:
        removable = next(
            (
                job_id
                for job_id, job in _SEARCH_JOBS.items()
                if job.get("status") in {"completed", "failed"}
            ),
            None,
        )
        if removable is None:
            removable = next(iter(_SEARCH_JOBS))
        _SEARCH_JOBS.pop(removable, None)


def _update_job(job_id: str, event: dict[str, object]) -> None:
    with _SEARCH_JOBS_LOCK:
        job = _SEARCH_JOBS.get(job_id)
        if job is None:
            return
        event_type = str(event.get("type") or "")
        if event_type == "search_started":
            job["status"] = "running"
            job["stage"] = "searching"
            job["search_id"] = event.get("search_id")
        elif event_type == "provider_started":
            job["status"] = "running"
            job["stage"] = "searching"
            provider_id = str(event.get("provider") or "")
            for item in job.get("providers", []):
                if isinstance(item, dict) and item.get("provider") == provider_id:
                    item["status"] = "running"
                    break
        elif event_type == "provider_completed":
            provider = event.get("provider")
            if isinstance(provider, dict):
                provider_id = str(provider.get("provider") or "")
                providers = job.get("providers", [])
                if isinstance(providers, list):
                    for index, item in enumerate(providers):
                        if isinstance(item, dict) and item.get("provider") == provider_id:
                            providers[index] = dict(provider)
                            break
            job["completed_providers"] = int(event.get("completed_providers") or 0)
            job["total_providers"] = int(event.get("total_providers") or 0)
        elif event_type == "finalizing":
            job["stage"] = "finalizing"
            job["records_before_dedup"] = int(event.get("records_before_dedup") or 0)
        elif event_type == "search_completed":
            job["stage"] = "persisting"
        job["updated_at"] = _now()


def _query_strings(query_plan: dict[str, object]) -> dict[str, str]:
    raw = query_plan.get("provider_queries")
    if not isinstance(raw, dict):
        return {}
    output: dict[str, str] = {}
    for provider, value in raw.items():
        if isinstance(value, dict):
            query = str(value.get("query") or "").strip()
        else:
            query = str(value or "").strip()
        if query:
            output[str(provider)] = query
    return output


def _run_search_job(
    job_id: str,
    *,
    query: object,
    providers: list[str],
    per_provider: int,
    max_results: int,
    query_plan: dict[str, object],
) -> None:
    try:
        result = search_evidence_progressive(
            query,
            providers=providers,
            per_provider=per_provider,
            max_results=max_results,
            provider_queries=_query_strings(query_plan),
            query_plan=query_plan,
            on_progress=lambda event: _update_job(job_id, event),
        )
    except Exception as exc:
        with _SEARCH_JOBS_LOCK:
            job = _SEARCH_JOBS.get(job_id)
            if job is not None:
                job["status"] = "failed"
                job["stage"] = "failed"
                job["error"] = f"{type(exc).__name__}: {exc}"
                job["updated_at"] = _now()
        return

    with _SEARCH_JOBS_LOCK:
        job = _SEARCH_JOBS.get(job_id)
        if job is not None:
            job["status"] = "completed"
            job["stage"] = "completed"
            job["search_id"] = result.get("search_id")
            job["result"] = result
            job["completed_providers"] = len(providers)
            job["updated_at"] = _now()


def _selected_providers(payload: dict[str, object]) -> list[str]:
    raw_providers = payload.get("providers")
    providers = (
        [str(value) for value in raw_providers]
        if isinstance(raw_providers, list)
        else list(PROVIDER_ORDER)
    )
    providers = list(dict.fromkeys(providers))
    invalid = [provider for provider in providers if provider not in PROVIDER_ORDER]
    if invalid:
        raise ValueError("Providers inválidos: " + ", ".join(invalid))
    if not providers:
        raise ValueError("Selecione pelo menos um provider.")
    return providers


def _create_search_job(payload: dict[str, object]) -> dict[str, object]:
    providers = _selected_providers(payload)
    query = str(payload.get("query") or "").strip()
    if not query:
        raise ValueError("A pergunta de busca não pode ficar vazia.")
    per_provider = int(payload.get("per_provider", 25))
    max_results = int(payload.get("max_results", 100))
    query_plan = compile_query_plan(query, providers, payload.get("strategy"))

    job_id = "job_" + uuid4().hex
    job: dict[str, object] = {
        "job_id": job_id,
        "search_id": None,
        "status": "queued",
        "stage": "queued",
        "query": query,
        "query_plan": query_plan,
        "created_at": _now(),
        "updated_at": _now(),
        "completed_providers": 0,
        "total_providers": len(providers),
        "providers": [
            {
                "provider": provider,
                "label": PROVIDER_LABELS[provider],
                "status": "queued",
                "returned": 0,
                "total_found": None,
                "error": "",
            }
            for provider in providers
        ],
        "result": None,
        "error": None,
    }
    with _SEARCH_JOBS_LOCK:
        _prune_jobs_locked()
        _SEARCH_JOBS[job_id] = job

    thread = threading.Thread(
        target=_run_search_job,
        kwargs={
            "job_id": job_id,
            "query": query,
            "providers": providers,
            "per_provider": per_provider,
            "max_results": max_results,
            "query_plan": query_plan,
        },
        name=f"nutev-search-{job_id[-8:]}",
        daemon=True,
    )
    thread.start()
    return copy.deepcopy(job)


def _load_search_job(job_id: str) -> dict[str, object]:
    with _SEARCH_JOBS_LOCK:
        job = _SEARCH_JOBS.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return copy.deepcopy(job)


class NutEVHandler(SimpleHTTPRequestHandler):
    server_version = "NutEVWeb/1.0"

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def _json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, object]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Content-Length inválido") from exc
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("Payload inválido ou grande demais")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("JSON inválido") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON precisa ser um objeto")
        return value

    def _is_loopback(self) -> bool:
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    def _require_loopback(self) -> bool:
        if self._is_loopback():
            return True
        self._json(
            {
                "error": "coordinator_local_only",
                "message": "A coordenação, adjudicação, gold, métricas e lock de decisão só podem ser executados no navegador local do servidor.",
            },
            HTTPStatus.FORBIDDEN,
        )
        return False

    def _bearer(self) -> str:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        return header[len(prefix):].strip() if header.startswith(prefix) else ""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._json(
                {
                    "status": "ok",
                    "service": "nutev-web",
                    "validation_available": VALIDATION_ROOT.is_dir(),
                    "progressive_search": True,
                    "structured_review_query_builder": True,
                    "provider_specific_queries": True,
                    "radar_dashboard": True,
                    "article_workbench": True,
                    "server_backed_blind_review": True,
                    "human_adjudication": True,
                    "canonical_gold_validation": True,
                    "validation_metrics_gate": True,
                    "validation_decision_lock": True,
                    "scientific_intelligence_workspace_v2": True,
                    "evidence_map": True,
                    "dashboard_drill_down": True,
                    "review_control_center": True,
                    "human_review_event_log": True,
                    "frontend_can_change_formal_search_gate": False,
                    "frontend_can_emit_prisma_event": False,
                }
            )
            return
        if path == "/api/validation/readiness":
            self._json(get_validation_readiness())
            return
        if path == "/api/validation/round":
            if not self._require_loopback():
                return
            try:
                self._json(round_status())
            except FileNotFoundError:
                self._json({"error": "validation_round_not_prepared"}, HTTPStatus.NOT_FOUND)
            return
        if path == "/api/validation/adjudication":
            if not self._require_loopback():
                return
            try:
                self._json(adjudication_payload())
            except FileNotFoundError as exc:
                self._json({"error": "validation_round_not_prepared", "message": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._json({"error": "adjudication_not_ready", "message": str(exc)}, HTTPStatus.CONFLICT)
            return
        if path == "/api/validation/gold":
            if not self._require_loopback():
                return
            try:
                self._json(gold_status())
            except FileNotFoundError as exc:
                self._json({"error": "validation_round_not_prepared", "message": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._json({"error": "gold_status_invalid", "message": str(exc)}, HTTPStatus.CONFLICT)
            return
        if path == "/api/validation/metrics":
            if not self._require_loopback():
                return
            try:
                self._json(metrics_status())
            except FileNotFoundError as exc:
                self._json({"error": "validation_round_not_prepared", "message": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._json({"error": "metrics_status_invalid", "message": str(exc)}, HTTPStatus.CONFLICT)
            return
        if path == "/api/validation/decision":
            if not self._require_loopback():
                return
            try:
                self._json(decision_status())
            except FileNotFoundError as exc:
                self._json({"error": "validation_round_not_prepared", "message": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._json({"error": "decision_status_invalid", "message": str(exc)}, HTTPStatus.CONFLICT)
            return
        if path == "/api/validation/reviewer":
            try:
                self._json(reviewer_payload(self._bearer()))
            except PermissionError as exc:
                self._json({"error": "invalid_private_link", "message": str(exc)}, HTTPStatus.UNAUTHORIZED)
            return
        if path == "/api/providers":
            self._json(
                {
                    "providers": [
                        {"id": provider, "label": PROVIDER_LABELS[provider]}
                        for provider in PROVIDER_ORDER
                    ]
                }
            )
            return
        if path == "/api/radar":
            try:
                self._json(load_radar_state())
            except RadarDataError as exc:
                self._json(
                    {
                        "status": "invalid",
                        "error": "radar_data_invalid",
                        "message": str(exc),
                    },
                    HTTPStatus.CONFLICT,
                )
            return
        if path.startswith("/api/dashboard/") or path.startswith("/api/evidence-map") \
                or path in {"/api/timeline", "/api/routes/compare"} \
                or path.startswith("/api/review/"):
            self._handle_intelligence_get(path, parse_qs(parsed.query))
            return
        if path == "/api/articles/status":
            try:
                self._json(workbench_status())
            except ArticleWorkbenchDataError as exc:
                self._json(
                    {
                        "status": "invalid",
                        "error": "article_workbench_invalid",
                        "message": str(exc),
                    },
                    HTTPStatus.CONFLICT,
                )
            return
        if path == "/api/articles":
            query = parse_qs(parsed.query)
            try:
                limit = int((query.get("limit") or ["50"])[0])
            except ValueError:
                limit = 50
            try:
                restriction = self._corpus_restriction(query)
            except context_index.Article1ContextUnavailable as exc:
                self._json(
                    {
                        "status": "not_ready",
                        "error": "article1_context_unavailable",
                        "message": str(exc) or CONTEXT_UNAVAILABLE_MESSAGE,
                    },
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return
            except context_index.Article1ContextError as exc:
                self._json(
                    {
                        "status": "invalid",
                        "error": "article1_context_invalid",
                        "message": str(exc),
                    },
                    HTTPStatus.CONFLICT,
                )
                return
            except ValueError as exc:
                self._json(
                    {"error": "invalid_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST
                )
                return
            document_ids, context_filters = restriction
            try:
                self._json(
                    load_article_page(
                        q=(query.get("q") or [""])[0],
                        limit=limit,
                        cursor=(query.get("cursor") or [None])[0],
                        source_provider=(query.get("source_provider") or [""])[0],
                        document_class=(
                            "" if context_filters else (query.get("document_class") or [""])[0]
                        ),
                        full_text_status=(query.get("full_text_status") or [""])[0],
                        document_ids=document_ids,
                        context_filters=context_filters,
                    )
                )
            except FileNotFoundError:
                self._json(workbench_status())
            except ArticleWorkbenchDataError as exc:
                status = (
                    HTTPStatus.BAD_REQUEST
                    if "cursor" in str(exc).casefold()
                    else HTTPStatus.CONFLICT
                )
                self._json(
                    {
                        "status": "invalid",
                        "error": "article_workbench_query_invalid",
                        "message": str(exc),
                    },
                    status,
                )
            return
        if path.startswith("/api/articles/"):
            document_id = unquote(path[len("/api/articles/"):]).strip()
            if not document_id:
                self._json({"error": "article_not_found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                self._json(load_article_detail(document_id))
            except KeyError:
                self._json({"error": "article_not_found"}, HTTPStatus.NOT_FOUND)
            except FileNotFoundError:
                self._json(workbench_status())
            except ArticleWorkbenchDataError as exc:
                self._json(
                    {
                        "status": "invalid",
                        "error": "article_workbench_invalid",
                        "message": str(exc),
                    },
                    HTTPStatus.CONFLICT,
                )
            return
        if path.startswith("/api/search/jobs/"):
            job_id = unquote(path[len("/api/search/jobs/"):]).strip()
            try:
                self._json(_load_search_job(job_id))
            except KeyError:
                self._json({"error": "search_job_not_found"}, HTTPStatus.NOT_FOUND)
            return
        if path == "/api/searches":
            query = parse_qs(parsed.query)
            try:
                limit = int((query.get("limit") or ["30"])[0])
            except ValueError:
                limit = 30
            self._json({"searches": list_search_runs(limit=limit)})
            return
        if path.startswith("/api/searches/"):
            search_id = unquote(path[len("/api/searches/"):]).strip()
            try:
                self._json(load_search_run(search_id))
            except (FileNotFoundError, ValueError):
                self._json({"error": "search_not_found"}, HTTPStatus.NOT_FOUND)
            return
        return super().do_GET()

    def _corpus_restriction(
        self,
        query: dict[str, list[str]],
    ) -> tuple[list[str] | None, dict[str, object]]:
        """Resolve Evidence Map / review filters to a document-id restriction.

        Domain, route and human review status only exist for the Tier A profiled set, so a
        drill-down using them narrows the corpus page to those documents instead of silently
        widening it. Without those parameters the corpus keeps its plain server-side filters.
        """
        route = _first(query, "route", "all") or "all"
        domain = _first(query, "domain")
        review_status_filter = _first(query, "review_status")
        year_from = _year(query, "year_from")
        year_to = _year(query, "year_to")
        document_class = _first(query, "document_class")
        needs_context = bool(
            domain
            or review_status_filter
            or year_from is not None
            or year_to is not None
            or route != "all"
        )
        if not needs_context:
            return None, {}
        context = context_index.load_context()
        rows = context.select(
            route=route,
            domain=domain,
            document_class=document_class,
            year_from=year_from,
            year_to=year_to,
        )
        if review_status_filter:
            wanted = review_status_filter.strip().upper()
            if wanted not in review_store.REVIEW_STATUSES:
                raise ValueError(f"unknown review status filter: {review_status_filter!r}")
            states = review_store.document_states(row["document_id"] for row in rows)
            rows = [
                row
                for row in rows
                if str((states.get(row["document_id"]) or {}).get("status") or "NOT_STARTED")
                == wanted
            ]
        filters = {
            key: value
            for key, value in {
                "route": route if route != "all" else "",
                "domain": domain,
                "document_class": document_class,
                "review_status": review_status_filter,
                "year_from": year_from,
                "year_to": year_to,
            }.items()
            if value not in ("", None)
        }
        filters["universe"] = context_index.UNIVERSE_LABEL
        return [row["document_id"] for row in rows], filters

    def _context(self) -> object | None:
        """Return the verified Article 1 context bundle, or answer with an explicit state."""
        try:
            return context_index.load_context()
        except context_index.Article1ContextUnavailable as exc:
            self._json(
                {
                    "status": "not_ready",
                    "error": "article1_context_unavailable",
                    "message": str(exc) or CONTEXT_UNAVAILABLE_MESSAGE,
                },
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return None
        except context_index.Article1ContextError as exc:
            self._json(
                {
                    "status": "invalid",
                    "error": "article1_context_invalid",
                    "message": str(exc),
                },
                HTTPStatus.CONFLICT,
            )
            return None

    def _handle_intelligence_get(self, path: str, query: dict[str, list[str]]) -> None:
        """Read-only scientific intelligence aggregates. None of these changes any gate."""
        if path == "/api/review/status" or path == "/api/review/queue" or path == "/api/review/conflicts":
            self._handle_review_get(path, query)
            return
        if path.startswith("/api/review/document/"):
            document_id = unquote(path[len("/api/review/document/"):]).strip()
            if not document_id:
                self._json({"error": "document_id_required"}, HTTPStatus.BAD_REQUEST)
                return
            events = review_store.document_events(document_id)
            self._json(
                {
                    "status": "ready",
                    "document_id": document_id,
                    "review": review_store.derive_document_state(events),
                    "events": events,
                    "vocabulary": {
                        "statuses": list(review_store.REVIEW_STATUSES),
                        "decisions": list(review_store.REVIEW_DECISIONS),
                        "stages": list(review_store.REVIEW_STAGES),
                    },
                    "append_only": True,
                    "guardrail": review_store.GUARDRAIL,
                }
            )
            return
        if path == "/api/review/store":
            self._json(review_store.store_status())
            return
        context = self._context()
        if context is None:
            return
        try:
            filters = _context_filters(query)
            if path == "/api/dashboard/overview":
                self._json(context_index.dashboard_overview(context=context, **filters))
                return
            if path == "/api/evidence-map":
                self._json(context_index.evidence_map(context=context, **filters))
                return
            if path == "/api/evidence-map/cell":
                cell_filters = dict(filters)
                domain = cell_filters.pop("domain")
                document_class = cell_filters.pop("document_class")
                self._json(
                    context_index.evidence_map_cell(
                        context=context,
                        domain=domain,
                        document_class=document_class,
                        limit=int(_first(query, "limit", "50") or 50),
                        offset=int(_first(query, "offset", "0") or 0),
                        **cell_filters,
                    )
                )
                return
            if path == "/api/timeline":
                series = [
                    value
                    for raw in (query.get("series") or [])
                    for value in str(raw).split(",")
                    if value.strip()
                ]
                self._json(
                    context_index.timeline(
                        context=context,
                        series=[value.strip() for value in series] or None,
                        **filters,
                    )
                )
                return
            if path == "/api/routes/compare":
                self._json(
                    context_index.routes_compare(
                        context=context,
                        source_provider=filters["source_provider"],
                        full_text_status=filters["full_text_status"],
                        year_from=filters["year_from"],
                        year_to=filters["year_to"],
                    )
                )
                return
        except (context_index.Article1ContextError, ValueError) as exc:
            self._json(
                {"error": "invalid_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST
            )
            return
        self._json({"error": "not_found", "message": path}, HTTPStatus.NOT_FOUND)

    def _handle_review_get(self, path: str, query: dict[str, list[str]]) -> None:
        context = self._context()
        if context is None:
            return
        states = review_store.document_states()
        try:
            if path == "/api/review/status":
                self._json(
                    review_control.review_status(
                        context=context,
                        states=states,
                        route=_first(query, "route", "all") or "all",
                        document_class=_first(query, "document_class"),
                        domain=_first(query, "domain"),
                    )
                )
                return
            if path == "/api/review/conflicts":
                self._json(
                    {
                        "status": "ready",
                        "conflicts": review_control.conflicts(context=context, states=states),
                        "guardrail": review_control.GUARDRAIL,
                    }
                )
                return
            self._json(
                review_control.review_queue(
                    context=context,
                    states=states,
                    route=_first(query, "route", "all") or "all",
                    document_class=_first(query, "document_class"),
                    domain=_first(query, "domain"),
                    full_text_status=_first(query, "full_text_status"),
                    review_status_filter=_first(query, "review_status"),
                    reviewer_id=_first(query, "reviewer_id"),
                    limit=int(_first(query, "limit", "50") or 50),
                    offset=int(_first(query, "offset", "0") or 0),
                )
            )
        except (context_index.Article1ContextError, ValueError) as exc:
            self._json({"error": "invalid_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/review/event":
            # Human operational review state only. The web tier cannot approve PRESS, authorize
            # GF-10, freeze a query, execute a formal search or emit a PRISMA event.
            if not self._require_loopback():
                return
            try:
                payload = self._read_json()
                result = review_store.append_event(
                    document_id=str(payload.get("document_id") or ""),
                    reviewer_id=str(payload.get("reviewer_id") or ""),
                    status=str(payload.get("status") or ""),
                    stage=str(payload.get("stage") or "route_reading"),
                    route=str(payload.get("route") or ""),
                    decision=str(payload.get("decision") or ""),
                    reason_code=str(payload.get("reason_code") or ""),
                    reason_text=str(payload.get("reason_text") or ""),
                    supersedes=str(payload.get("supersedes") or ""),
                )
                self._json(result, HTTPStatus.CREATED)
            except review_store.HumanReviewError as exc:
                self._json(
                    {"error": "invalid_review_event", "message": str(exc)},
                    HTTPStatus.BAD_REQUEST,
                )
            except ValueError as exc:
                self._json({"error": "invalid_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/query/compile":
            try:
                payload = self._read_json()
                providers = _selected_providers(payload)
                query = str(payload.get("query") or "").strip()
                if not query:
                    raise ValueError("A pergunta de busca não pode ficar vazia.")
                self._json(
                    compile_query_plan(query, providers, payload.get("strategy")),
                    HTTPStatus.OK,
                )
            except ValueError as exc:
                self._json({"error": "invalid_query_strategy", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/validation/round/prepare":
            if not self._require_loopback():
                return
            try:
                self._read_json()
                self._json(prepare_round(), HTTPStatus.CREATED)
            except ValueError as exc:
                self._json({"error": "validation_round_not_ready", "message": str(exc)}, HTTPStatus.CONFLICT)
            except Exception as exc:
                self._json({"error": "validation_round_prepare_failed", "message": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if path in {"/api/validation/adjudication/save", "/api/validation/adjudication/finalize"}:
            if not self._require_loopback():
                return
            try:
                payload = self._read_json()
                result = save_adjudication(payload) if path.endswith("/save") else finalize_adjudication()
                self._json(result)
            except ValueError as exc:
                self._json({"error": "invalid_adjudication", "message": str(exc)}, HTTPStatus.CONFLICT)
            return
        if path == "/api/validation/gold/build":
            if not self._require_loopback():
                return
            try:
                self._read_json()
                self._json(build_and_validate_gold(), HTTPStatus.CREATED)
            except FileNotFoundError as exc:
                self._json({"error": "validation_round_not_prepared", "message": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._json({"error": "gold_validation_blocked", "message": str(exc)}, HTTPStatus.CONFLICT)
            except Exception as exc:
                self._json({"error": "gold_validation_failed", "message": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if path == "/api/validation/metrics/run":
            if not self._require_loopback():
                return
            try:
                self._read_json()
                self._json(run_validation_metrics(), HTTPStatus.CREATED)
            except FileNotFoundError as exc:
                self._json({"error": "validation_metrics_source_missing", "message": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._json({"error": "validation_metrics_blocked", "message": str(exc)}, HTTPStatus.CONFLICT)
            except Exception as exc:
                self._json({"error": "validation_metrics_failed", "message": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if path == "/api/validation/decision/lock":
            if not self._require_loopback():
                return
            try:
                self._read_json()
                self._json(lock_validation_decision(), HTTPStatus.CREATED)
            except FileNotFoundError as exc:
                self._json({"error": "validation_decision_source_missing", "message": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._json({"error": "validation_decision_blocked", "message": str(exc)}, HTTPStatus.CONFLICT)
            except Exception as exc:
                self._json({"error": "validation_decision_failed", "message": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if path in {"/api/validation/reviewer/save", "/api/validation/reviewer/submit"}:
            try:
                payload = self._read_json()
                token = self._bearer()
                result = save_decision(token, payload) if path.endswith("/save") else submit_reviewer(token)
                self._json(result)
            except PermissionError as exc:
                self._json({"error": "invalid_private_link", "message": str(exc)}, HTTPStatus.UNAUTHORIZED)
            except ValueError as exc:
                self._json({"error": "invalid_assessment", "message": str(exc)}, HTTPStatus.CONFLICT)
            return
        if path not in {"/api/search", "/api/search/jobs"}:
            self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            if path == "/api/search/jobs":
                self._json(_create_search_job(payload), HTTPStatus.ACCEPTED)
                return
            result = search_evidence(
                payload.get("query"),
                providers=(
                    [str(value) for value in payload.get("providers", [])]
                    if isinstance(payload.get("providers"), list)
                    else None
                ),
                per_provider=int(payload.get("per_provider", 25)),
                max_results=int(payload.get("max_results", 100)),
            )
        except ValueError as exc:
            self._json({"error": "invalid_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:
            self._json({"error": "search_failed", "message": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._json(result)

    def translate_path(self, path: str) -> str:
        clean = urlparse(path).path
        if clean.startswith("/validation"):
            suffix = clean[len("/validation"):].lstrip("/")
            target = VALIDATION_ROOT / (suffix or "index.html")
            if target.is_dir():
                target = target / "index.html"
            return str(target)
        suffix = clean.lstrip("/")
        target = APP_ROOT / (suffix or "index.html")
        if target.is_dir():
            target = target / "index.html"
        return str(target)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("[nutev-web] " + (fmt % args) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the unified NutEV search + validation web interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), NutEVHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"NutEV web disponível em {url}")
    print("Ctrl+C para encerrar.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
