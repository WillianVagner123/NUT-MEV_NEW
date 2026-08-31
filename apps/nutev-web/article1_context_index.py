"""Server-side aggregation over the verified, rank-blind Article 1 context bundle.

The bundle (``agent_context/article1``) is the only input. It is loaded once, hash-verified
against ``CONTEXT_MANIFEST.json`` and cached, so the browser never has to download or aggregate
the corpus itself.

Everything produced here is navigation/context. Counts, matrices, route membership, full-text
status and machine profiles are not eligibility, inclusion/exclusion, quality, risk of bias,
certainty, recommendation or PRISMA decisions.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
DEFAULT_CONTEXT_ROOTS = (
    REPO_ROOT / "project_output_reference" / "agent_context" / "article1",
    APP_ROOT / "agent-context" / "article1",
)

GUARDRAIL = (
    "Rank-blind navigation aggregate over the Tier A profiled set. Document counts, routes, "
    "domains, document classes and full-text status are not eligibility, inclusion/exclusion, "
    "quality, risk of bias, certainty, recommendation or PRISMA decisions."
)
UNIVERSE_LABEL = (
    "Article 1 Tier A profiled documents (deepened + review profile v2). "
    "Not the full Bank and not a PRISMA screening set."
)

#: Rank/relevance fields that must never reach a navigation surface.
FORBIDDEN_FIELDS = frozenset(
    {
        "reference_rank",
        "reference_score",
        "reference_tier",
        "machine_relevance_score",
        "machine_relevance_band",
    }
)

NO_DOMAIN_KEY = "no_operational_domain"
UNCLASSIFIED_KEY = "unclassified"

DOMAIN_ORDER: tuple[str, ...] = (
    "nutrition_assessment",
    "dietary_counseling",
    "nutrition_prescription",
    "monitoring_follow_up",
    "food_skills_competencies",
    "food_literacy",
    "social_context",
    "food_based_guidance",
    "nutrition_care_process",
    "lifestyle_medicine",
    "implementation_practice",
)
DOMAIN_LABELS: dict[str, str] = {
    "nutrition_assessment": "Nutrition assessment",
    "dietary_counseling": "Dietary counseling",
    "nutrition_prescription": "Nutrition prescription",
    "monitoring_follow_up": "Monitoring / follow-up",
    "food_skills_competencies": "Food skills / competencies",
    "food_literacy": "Food literacy",
    "social_context": "Social context",
    "food_based_guidance": "Food-based guidance",
    "nutrition_care_process": "Nutrition Care Process",
    "lifestyle_medicine": "Lifestyle Medicine",
    "implementation_practice": "Implementation / practice",
    NO_DOMAIN_KEY: "No operational domain detected",
}

DOCUMENT_CLASS_ORDER: tuple[str, ...] = (
    "food_based_dietary_guideline",
    "clinical_practice_guideline",
    "consensus_statement",
    "position_statement",
    "framework_model",
    "evidence_synthesis",
    "implementation_evaluation",
    "primary_randomized",
    "primary_observational",
    "primary_qualitative",
)
DOCUMENT_CLASS_LABELS: dict[str, str] = {
    "food_based_dietary_guideline": "Food-based dietary guideline",
    "clinical_practice_guideline": "Clinical practice guideline",
    "consensus_statement": "Consensus statement",
    "position_statement": "Position statement",
    "framework_model": "Framework / model",
    "evidence_synthesis": "Evidence synthesis",
    "implementation_evaluation": "Implementation evaluation",
    "primary_randomized": "Primary randomized",
    "primary_observational": "Primary observational",
    "primary_qualitative": "Primary qualitative",
    "competency_curriculum": "Competency / curriculum",
    "review": "Review",
    "guidance": "Guidance",
    UNCLASSIFIED_KEY: "Unclassified",
}

ROUTE_FILTERS = ("all", "B-NORM", "C-STRUCT", "overlap", "unrouted")
TIMELINE_SERIES: dict[str, dict[str, str]] = {
    "all": {"label": "All documents", "kind": "all"},
    "B-NORM": {"label": "B-NORM", "kind": "route", "value": "B-NORM"},
    "C-STRUCT": {"label": "C-STRUCT", "kind": "route", "value": "C-STRUCT"},
    "food_based_dietary_guideline": {
        "label": "Food-based dietary guideline",
        "kind": "document_class",
        "value": "food_based_dietary_guideline",
    },
    "clinical_practice_guideline": {
        "label": "Clinical practice guideline",
        "kind": "document_class",
        "value": "clinical_practice_guideline",
    },
    "evidence_synthesis": {
        "label": "Evidence synthesis",
        "kind": "document_class",
        "value": "evidence_synthesis",
    },
    "social_context": {"label": "Social context", "kind": "domain", "value": "social_context"},
    "food_literacy": {"label": "Food literacy", "kind": "domain", "value": "food_literacy"},
    "lifestyle_medicine": {
        "label": "Lifestyle Medicine",
        "kind": "domain",
        "value": "lifestyle_medicine",
    },
}
MAX_TIMELINE_SERIES = 6

_CACHE: dict[str, tuple[tuple[Any, ...], "Article1Context"]] = {}


class Article1ContextError(RuntimeError):
    """Raised when the Article 1 context bundle cannot be proven from verified inputs."""


class Article1ContextUnavailable(Article1ContextError):
    """Raised when no bundle has been materialized yet."""


def domain_label(key: str) -> str:
    return DOMAIN_LABELS.get(key, str(key).replace("_", " ").capitalize())


def document_class_label(key: str) -> str:
    return DOCUMENT_CLASS_LABELS.get(key, str(key).replace("_", " ").capitalize())


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Article1ContextError(f"invalid JSON at {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise Article1ContextError(f"expected a JSON object at {path.name}")
    return value


def _int_or_none(value: object) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if 1000 <= number <= 2999 else None


class Article1Context:
    """Immutable, verified view of one Article 1 context bundle."""

    def __init__(
        self,
        *,
        root: Path,
        manifest: Mapping[str, Any],
        search_state: Mapping[str, Any],
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        self.root = root
        self.manifest = dict(manifest)
        self.search_state = dict(search_state)
        self.records = list(records)
        self._by_id = {str(row["document_id"]): row for row in self.records}
        self.document_classes = self._ordered_classes()
        self.domains = self._ordered_domains()

    # -- construction ---------------------------------------------------

    def _ordered_classes(self) -> list[str]:
        present = {str(row["document_class"]) for row in self.records}
        ordered = [key for key in DOCUMENT_CLASS_ORDER if key in present]
        extra = sorted(present - set(DOCUMENT_CLASS_ORDER) - {UNCLASSIFIED_KEY})
        tail = [UNCLASSIFIED_KEY] if UNCLASSIFIED_KEY in present else []
        return [*ordered, *extra, *tail]

    def _ordered_domains(self) -> list[str]:
        present: set[str] = set()
        has_empty = False
        for row in self.records:
            domains = row["domains"]
            if domains:
                present.update(domains)
            else:
                has_empty = True
        ordered = [key for key in DOMAIN_ORDER if key in present]
        extra = sorted(present - set(DOMAIN_ORDER))
        tail = [NO_DOMAIN_KEY] if has_empty else []
        return [*ordered, *extra, *tail]

    # -- selection ------------------------------------------------------

    def get(self, document_id: str) -> Mapping[str, Any] | None:
        return self._by_id.get(str(document_id))

    def select(
        self,
        *,
        route: str = "",
        domain: str = "",
        document_class: str = "",
        source_provider: str = "",
        full_text_status: str = "",
        year_from: int | None = None,
        year_to: int | None = None,
        document_ids: Iterable[str] | None = None,
    ) -> list[Mapping[str, Any]]:
        route = (route or "all").strip()
        if route not in ROUTE_FILTERS:
            raise Article1ContextError(f"unknown route filter: {route}")
        allowed = {str(value) for value in document_ids} if document_ids is not None else None
        selected: list[Mapping[str, Any]] = []
        for row in self.records:
            if allowed is not None and row["document_id"] not in allowed:
                continue
            routes = row["routes"]
            if route == "B-NORM" and "B-NORM" not in routes:
                continue
            if route == "C-STRUCT" and "C-STRUCT" not in routes:
                continue
            if route == "overlap" and not {"B-NORM", "C-STRUCT"} <= set(routes):
                continue
            if route == "unrouted" and routes:
                continue
            if domain:
                if domain == NO_DOMAIN_KEY:
                    if row["domains"]:
                        continue
                elif domain not in row["domains"]:
                    continue
            if document_class and row["document_class"] != document_class:
                continue
            if source_provider and row["source_provider"] != source_provider:
                continue
            if full_text_status and row["full_text_status"] != full_text_status:
                continue
            year = row["year"]
            if year_from is not None and (year is None or year < year_from):
                continue
            if year_to is not None and (year is None or year > year_to):
                continue
            selected.append(row)
        return selected

    # -- provenance -----------------------------------------------------

    def provenance(self) -> dict[str, Any]:
        outputs = self.manifest.get("outputs") or {}
        summaries = outputs.get("article_summaries") or {}
        return {
            "search_id": self.manifest.get("search_id") or self.search_state.get("search_id"),
            "context_version": self.manifest.get("context_version"),
            "context_type": self.manifest.get("context_type"),
            "context_status": self.manifest.get("status"),
            "context_created_at": self.manifest.get("created_at"),
            "article_summaries_sha256": summaries.get("sha256"),
            "workbench_database_sha256": (self.manifest.get("source") or {}).get(
                "workbench_database_sha256"
            ),
            "route_queue_manifest_sha256": (self.manifest.get("source") or {}).get(
                "route_queue_manifest_sha256"
            ),
            "bundle_root": str(self.root),
        }


def _normalize_record(row: Mapping[str, Any], line_number: int) -> dict[str, Any]:
    leaked = FORBIDDEN_FIELDS & set(row)
    if leaked:
        raise Article1ContextError(
            f"context bundle exposes rank/relevance fields at record {line_number}: {sorted(leaked)}"
        )
    document_id = str(row.get("document_id") or "").strip()
    if not document_id:
        raise Article1ContextError(f"context record {line_number} has no document_id")
    profile = row.get("review_profile")
    profile = profile if isinstance(profile, dict) else {}
    domains = [str(value) for value in (profile.get("operational_domains") or []) if value]
    matches = profile.get("operational_domain_matches")
    document_class = str(
        profile.get("primary_document_class") or row.get("document_class") or UNCLASSIFIED_KEY
    )
    routes = sorted({str(value) for value in (row.get("routes") or []) if value})
    return {
        "document_id": document_id,
        "title": row.get("title") or "",
        "year": _int_or_none(row.get("year")),
        "doi": row.get("doi") or "",
        "pmid": row.get("pmid") or "",
        "source_provider": str(row.get("source_provider") or ""),
        "document_class": document_class,
        "declared_document_class": str(row.get("document_class") or ""),
        "full_text_status": str(row.get("full_text_status") or "unknown"),
        "reference_stub": row.get("reference_stub") or "",
        "routes": routes,
        "domains": domains,
        "domain_matches": matches if isinstance(matches, dict) else {},
        "document_class_basis": profile.get("document_classification_basis"),
        "document_class_confidence": profile.get("document_class_confidence"),
        "document_class_warnings": profile.get("document_class_warnings") or [],
        "evidence_excerpt_count": int(row.get("evidence_excerpt_count") or 0),
        "result_bundle_count": int(row.get("result_bundle_count") or 0),
    }


def _resolve_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    for candidate in DEFAULT_CONTEXT_ROOTS:
        if (candidate / "CONTEXT_MANIFEST.json").is_file():
            return candidate
    return DEFAULT_CONTEXT_ROOTS[0]


def load_context(root: Path | None = None) -> Article1Context:
    """Load and hash-verify the Article 1 context bundle, with an mtime/size cache."""
    base = _resolve_root(root)
    manifest_path = base / "CONTEXT_MANIFEST.json"
    summaries_path = base / "ARTICLE_SUMMARIES.jsonl"
    state_path = base / "SEARCH_STATE.json"
    if not manifest_path.is_file() or not summaries_path.is_file():
        raise Article1ContextUnavailable(
            "Article 1 agent context bundle is not available. "
            "Run tools/build_article1_agent_context.py."
        )

    manifest_stat = manifest_path.stat()
    summaries_stat = summaries_path.stat()
    signature = (
        manifest_stat.st_size,
        manifest_stat.st_mtime_ns,
        summaries_stat.st_size,
        summaries_stat.st_mtime_ns,
    )
    cached = _CACHE.get(str(base))
    if cached is not None and cached[0] == signature:
        return cached[1]

    manifest = _read_json(manifest_path)
    if manifest.get("context_type") != "NUTEV_ARTICLE1_AGENT_CONTEXT":
        raise Article1ContextError("unexpected Article 1 context manifest type")
    if manifest.get("status") != "PASS":
        raise Article1ContextError("Article 1 context manifest is not PASS")
    expected = str(
        ((manifest.get("outputs") or {}).get("article_summaries") or {}).get("sha256") or ""
    ).strip().lower()
    if not expected:
        raise Article1ContextError("context manifest has no ARTICLE_SUMMARIES.jsonl SHA-256")
    actual = _sha256_file(summaries_path)
    if actual != expected:
        raise Article1ContextError(
            f"ARTICLE_SUMMARIES.jsonl SHA-256 mismatch: expected {expected}, got {actual}"
        )

    records: list[dict[str, Any]] = []
    with summaries_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Article1ContextError(
                    f"invalid JSONL in ARTICLE_SUMMARIES.jsonl:{line_number}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise Article1ContextError(
                    f"non-object record in ARTICLE_SUMMARIES.jsonl:{line_number}"
                )
            records.append(_normalize_record(row, line_number))

    search_state = _read_json(state_path) if state_path.is_file() else {}
    context = Article1Context(
        root=base,
        manifest=manifest,
        search_state=search_state,
        records=records,
    )
    _CACHE[str(base)] = (signature, context)
    return context


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------


def _route_distribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    b_norm = sum(1 for row in rows if "B-NORM" in row["routes"])
    c_struct = sum(1 for row in rows if "C-STRUCT" in row["routes"])
    overlap = sum(1 for row in rows if {"B-NORM", "C-STRUCT"} <= set(row["routes"]))
    unrouted = sum(1 for row in rows if not row["routes"])
    return {
        "B-NORM": b_norm,
        "C-STRUCT": c_struct,
        "overlap": overlap,
        "only_B-NORM": b_norm - overlap,
        "only_C-STRUCT": c_struct - overlap,
        "union": b_norm + c_struct - overlap,
        "unrouted": unrouted,
    }


def _full_text_distribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row["full_text_status"]) for row in rows)
    counts["available"] = counts.get("retrieved", 0) + counts.get("partial", 0)
    return dict(sorted(counts.items()))


def _year_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row["year"]) for row in rows if row["year"] is not None)
    return {year: counts[year] for year in sorted(counts)}


def _labelled_counts(counts: Mapping[str, int], labeller) -> list[dict[str, Any]]:
    return [
        {"key": key, "label": labeller(key), "documents": value}
        for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _filters_payload(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value not in ("", None)}


def evidence_map(
    *,
    context: Article1Context,
    route: str = "all",
    source_provider: str = "",
    full_text_status: str = "",
    document_class: str = "",
    domain: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
    document_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Domain x document-class matrix. Cell intensity is a document count and nothing else."""
    rows = context.select(
        route=route,
        source_provider=source_provider,
        full_text_status=full_text_status,
        document_class=document_class,
        domain=domain,
        year_from=year_from,
        year_to=year_to,
        document_ids=document_ids,
    )
    domain_keys = [key for key in context.domains if not domain or key == domain]
    class_keys = [key for key in context.document_classes if not document_class or key == document_class]

    buckets: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        keys = row["domains"] or [NO_DOMAIN_KEY]
        for key in keys:
            buckets[(key, row["document_class"])].append(row)

    cells: list[dict[str, Any]] = []
    for domain_key in domain_keys:
        line: list[dict[str, Any]] = []
        for class_key in class_keys:
            bucket = buckets.get((domain_key, class_key), [])
            full_text = _full_text_distribution(bucket)
            line.append(
                {
                    "domain": domain_key,
                    "document_class": class_key,
                    "documents": len(bucket),
                    "routes": _route_distribution(bucket),
                    "full_text": {
                        "available": full_text.get("available", 0),
                        "retrieved": full_text.get("retrieved", 0),
                        "partial": full_text.get("partial", 0),
                    },
                }
            )
        cells.append({"domain": domain_key, "label": domain_label(domain_key), "cells": line})

    # Row totals are distinct documents in that domain (a document appears once per domain row).
    row_totals = {
        domain_key: sum(cell["documents"] for cell in line["cells"])
        for domain_key, line in zip(domain_keys, cells, strict=True)
    }
    # Column totals are distinct documents in that class: a multi-domain document occupies several
    # cells of the same column, so summing the column would double-count it.
    column_totals = {
        class_key: sum(1 for row in rows if row["document_class"] == class_key)
        for class_key in class_keys
    }
    # Each cell counts a document once per domain it carries, so the cells sum above the document
    # count. That sum is reported separately as `cell_assignments`, never as a document total.
    return {
        "status": "ready",
        "universe": {
            "label": UNIVERSE_LABEL,
            "documents": len(context.records),
            "filtered_documents": len(rows),
            "cell_assignments": sum(row_totals.values()),
            "multi_domain_documents": sum(1 for row in rows if len(row["domains"]) > 1),
        },
        "filters": _filters_payload(
            route=route if route != "all" else None,
            source_provider=source_provider,
            full_text_status=full_text_status,
            document_class=document_class,
            domain=domain,
            year_from=year_from,
            year_to=year_to,
        ),
        "domains": [{"key": key, "label": domain_label(key)} for key in domain_keys],
        "document_classes": [
            {"key": key, "label": document_class_label(key)} for key in class_keys
        ],
        "rows": cells,
        "row_totals": row_totals,
        "column_totals": column_totals,
        "intensity_semantics": "document count only; never quality, certainty or effect magnitude",
        "provenance": context.provenance(),
        "guardrail": GUARDRAIL,
    }


def evidence_map_cell(
    *,
    context: Article1Context,
    domain: str,
    document_class: str,
    route: str = "all",
    source_provider: str = "",
    full_text_status: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 50,
    offset: int = 0,
    document_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Exact document list behind one Evidence Map cell."""
    if not domain or not document_class:
        raise Article1ContextError("domain and document_class are required for a cell drill-down")
    rows = context.select(
        route=route,
        domain=domain,
        document_class=document_class,
        source_provider=source_provider,
        full_text_status=full_text_status,
        year_from=year_from,
        year_to=year_to,
        document_ids=document_ids,
    )
    rows = sorted(rows, key=lambda row: (-(row["year"] or 0), row["document_id"]))
    page_limit = max(1, min(int(limit), 100))
    page_offset = max(0, int(offset))
    page = rows[page_offset : page_offset + page_limit]
    return {
        "status": "ready",
        "domain": {"key": domain, "label": domain_label(domain)},
        "document_class": {"key": document_class, "label": document_class_label(document_class)},
        "total_filtered": len(rows),
        "page_size": len(page),
        "offset": page_offset,
        "next_offset": page_offset + page_limit if page_offset + page_limit < len(rows) else None,
        "routes": _route_distribution(rows),
        "full_text": _full_text_distribution(rows),
        "documents": [
            {
                "document_id": row["document_id"],
                "title": row["title"],
                "year": row["year"],
                "doi": row["doi"],
                "pmid": row["pmid"],
                "source_provider": row["source_provider"],
                "document_class": row["document_class"],
                "full_text_status": row["full_text_status"],
                "routes": row["routes"],
                "domains": row["domains"],
            }
            for row in page
        ],
        "provenance": context.provenance(),
        "guardrail": GUARDRAIL,
    }


def timeline(
    *,
    context: Article1Context,
    series: Sequence[str] | None = None,
    route: str = "all",
    source_provider: str = "",
    full_text_status: str = "",
    document_class: str = "",
    domain: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """Per-year counts for a small, explicitly chosen set of series."""
    requested = [key for key in (series or ["all"]) if key in TIMELINE_SERIES]
    if not requested:
        requested = ["all"]
    if len(requested) > MAX_TIMELINE_SERIES:
        raise Article1ContextError(
            f"at most {MAX_TIMELINE_SERIES} timeline series can be plotted at once"
        )
    base = context.select(
        route=route,
        source_provider=source_provider,
        full_text_status=full_text_status,
        document_class=document_class,
        domain=domain,
        year_from=year_from,
        year_to=year_to,
    )
    years = sorted({row["year"] for row in base if row["year"] is not None})
    payload: list[dict[str, Any]] = []
    for key in requested:
        definition = TIMELINE_SERIES[key]
        kind = definition["kind"]
        value = definition.get("value", "")
        if kind == "all":
            rows = base
        elif kind == "route":
            rows = [row for row in base if value in row["routes"]]
        elif kind == "domain":
            rows = [row for row in base if value in row["domains"]]
        else:
            rows = [row for row in base if row["document_class"] == value]
        counts = _year_counts(rows)
        payload.append(
            {
                "key": key,
                "label": definition["label"],
                "documents": len(rows),
                "points": [
                    {"year": year, "documents": counts.get(str(year), 0)} for year in years
                ],
            }
        )
    return {
        "status": "ready",
        "years": years,
        "series": payload,
        "available_series": [
            {"key": key, "label": value["label"]} for key, value in TIMELINE_SERIES.items()
        ],
        "max_series": MAX_TIMELINE_SERIES,
        "undated_documents": sum(1 for row in base if row["year"] is None),
        "provenance": context.provenance(),
        "guardrail": (
            "Publication-year distribution of a navigation set. It is not a trend, a causal signal "
            "or evidence strength."
        ),
    }


def routes_compare(
    *,
    context: Article1Context,
    source_provider: str = "",
    full_text_status: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """B-NORM x C-STRUCT comparison: overlap, exclusives and unrouted."""
    base = context.select(
        source_provider=source_provider,
        full_text_status=full_text_status,
        year_from=year_from,
        year_to=year_to,
    )
    groups = {
        "B-NORM": [row for row in base if "B-NORM" in row["routes"]],
        "C-STRUCT": [row for row in base if "C-STRUCT" in row["routes"]],
        "overlap": [row for row in base if {"B-NORM", "C-STRUCT"} <= set(row["routes"])],
        "only_B-NORM": [
            row for row in base if "B-NORM" in row["routes"] and "C-STRUCT" not in row["routes"]
        ],
        "only_C-STRUCT": [
            row for row in base if "C-STRUCT" in row["routes"] and "B-NORM" not in row["routes"]
        ],
        "unrouted": [row for row in base if not row["routes"]],
    }
    breakdown: dict[str, Any] = {}
    for key, rows in groups.items():
        domain_counts: Counter[str] = Counter()
        for row in rows:
            for value in row["domains"] or [NO_DOMAIN_KEY]:
                domain_counts[value] += 1
        breakdown[key] = {
            "documents": len(rows),
            "years": _year_counts(rows),
            "document_classes": _labelled_counts(
                Counter(row["document_class"] for row in rows), document_class_label
            ),
            "domains": _labelled_counts(domain_counts, domain_label),
            "providers": _labelled_counts(
                Counter(row["source_provider"] or "unknown" for row in rows), lambda key: key
            ),
            "full_text": _full_text_distribution(rows),
        }
    return {
        "status": "ready",
        "universe": {"label": UNIVERSE_LABEL, "documents": len(base)},
        "counts": {key: len(rows) for key, rows in groups.items()},
        "breakdown": breakdown,
        "provenance": context.provenance(),
        "guardrail": (
            "Route membership is a reading queue. Being on a route is not inclusion and being off "
            "every route is not exclusion."
        ),
    }


def dashboard_overview(
    *,
    context: Article1Context,
    route: str = "all",
    source_provider: str = "",
    full_text_status: str = "",
    document_class: str = "",
    domain: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """One aggregate for the Scientific Overview, so the browser never recomputes the corpus."""
    rows = context.select(
        route=route,
        source_provider=source_provider,
        full_text_status=full_text_status,
        document_class=document_class,
        domain=domain,
        year_from=year_from,
        year_to=year_to,
    )
    state = context.search_state
    runtime = state.get("runtime") or {}
    domain_counts: Counter[str] = Counter()
    for row in rows:
        for value in row["domains"] or [NO_DOMAIN_KEY]:
            domain_counts[value] += 1
    full_text = _full_text_distribution(rows)
    return {
        "status": "ready",
        "question": state.get("question"),
        "master_status": state.get("master_status"),
        "formal_search": state.get("formal_search") or {},
        "runtime": runtime,
        "universe": {
            "label": UNIVERSE_LABEL,
            "documents": len(context.records),
            "filtered_documents": len(rows),
        },
        "filters": _filters_payload(
            route=route if route != "all" else None,
            source_provider=source_provider,
            full_text_status=full_text_status,
            document_class=document_class,
            domain=domain,
            year_from=year_from,
            year_to=year_to,
        ),
        "document_classes": _labelled_counts(
            Counter(row["document_class"] for row in rows), document_class_label
        ),
        "domains": _labelled_counts(domain_counts, domain_label),
        "providers": _labelled_counts(
            Counter(row["source_provider"] or "unknown" for row in rows), lambda key: key
        ),
        "full_text": full_text,
        "routes": _route_distribution(rows),
        "years": _year_counts(rows),
        "undated_documents": sum(1 for row in rows if row["year"] is None),
        "provenance": context.provenance(),
        "guardrail": GUARDRAIL,
    }
