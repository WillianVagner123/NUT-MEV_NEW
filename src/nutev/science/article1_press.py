from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


FORMAL_PROVIDERS = (
    "pubmed",
    "lilacs_bvs",
    "scielo",
    "scopus",
    "web_of_science",
)
ROUTE_ORDER = (
    "B-NORM",
    "C1-CARE-PROCESS",
    "C2-COMPETENCY-LITERACY",
    "C3-IMPLEMENTATION",
    "C4-SOCIAL-CONTEXT",
)


class Article1PressError(ValueError):
    """Raised when the pre-freeze Article 1 PRESS contract is inconsistent."""


@dataclass(frozen=True)
class RouteSpec:
    route_id: str
    blocks: tuple[tuple[str, tuple[str, ...]], ...]
    status: str


def _terms(values: Iterable[object]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return tuple(out)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Article1PressError(f"Expected JSON object: {path}")
    return payload


def route_specs(draft: dict[str, Any]) -> dict[str, RouteSpec]:
    routes = draft.get("routes") or {}
    b_norm = routes.get("B-NORM") or {}
    c_struct = routes.get("C-STRUCT") or {}
    subs = c_struct.get("subroutes") or {}

    specs: dict[str, RouteSpec] = {}
    b_blocks = b_norm.get("blocks") or {}
    specs["B-NORM"] = RouteSpec(
        route_id="B-NORM",
        blocks=tuple(
            (str(name), _terms(values or [])) for name, values in b_blocks.items()
        ),
        status=str(b_norm.get("status") or "CANDIDATE_FOR_PRESS"),
    )

    for route_id in ROUTE_ORDER[1:]:
        raw = subs.get(route_id) or {}
        blocks: list[tuple[str, tuple[str, ...]]] = []
        if raw.get("anchor"):
            blocks.append(("anchor", _terms(raw.get("anchor") or [])))
        if raw.get("terms"):
            blocks.append(("terms", _terms(raw.get("terms") or [])))
        if raw.get("social_context_terms"):
            blocks.append(
                ("social_context_terms", _terms(raw.get("social_context_terms") or []))
            )
        if raw.get("operational_marker"):
            blocks.append(
                ("operational_marker", _terms(raw.get("operational_marker") or []))
            )
        specs[route_id] = RouteSpec(
            route_id=route_id,
            blocks=tuple(blocks),
            status=str(raw.get("status") or "CANDIDATE_FOR_PRESS"),
        )

    for route_id in ROUTE_ORDER:
        spec = specs.get(route_id)
        if spec is None or not spec.blocks or any(not values for _, values in spec.blocks):
            raise Article1PressError(f"Route {route_id} is missing explicit query blocks")
    return specs


def _escape(text: str) -> str:
    return text.replace('"', " ").strip()


def _plain_term(text: str) -> str:
    clean = _escape(text)
    if " " in clean:
        return f'"{clean}"'
    return clean


def _pubmed_term(text: str) -> str:
    clean = _escape(text)
    if " " in clean:
        return f'"{clean}"[Title/Abstract]'
    return f"{clean}[Title/Abstract]"


def _bvs_term(text: str) -> str:
    return f'tw:{_plain_term(text)}'


def _format_block(provider: str, terms: tuple[str, ...]) -> str:
    if provider == "pubmed":
        rendered = [_pubmed_term(term) for term in terms]
        return "(" + " OR ".join(rendered) + ")"
    if provider == "lilacs_bvs":
        rendered = [_bvs_term(term) for term in terms]
        return "(" + " OR ".join(rendered) + ")"
    rendered = [_plain_term(term) for term in terms]
    inner = " OR ".join(rendered)
    if provider == "scopus":
        return f"TITLE-ABS-KEY({inner})"
    if provider == "web_of_science":
        return f"TS=({inner})"
    if provider == "scielo":
        return f"({inner})"
    raise Article1PressError(f"Unsupported formal provider: {provider}")


def compile_route_query(provider: str, spec: RouteSpec) -> str:
    if provider not in FORMAL_PROVIDERS:
        raise Article1PressError(f"Unsupported formal provider: {provider}")
    return " AND ".join(_format_block(provider, values) for _, values in spec.blocks)


def _with_extra_term(spec: RouteSpec, block_name: str, term: str) -> RouteSpec:
    blocks: list[tuple[str, tuple[str, ...]]] = []
    found = False
    for name, values in spec.blocks:
        if name == block_name:
            found = True
            blocks.append((name, _terms((*values, term))))
        else:
            blocks.append((name, values))
    if not found:
        raise Article1PressError(f"Route {spec.route_id} has no block {block_name}")
    return RouteSpec(spec.route_id, tuple(blocks), spec.status)


def _union(queries: Iterable[str]) -> str:
    values = [query for query in queries if query]
    return "(" + ") OR (".join(values) + ")"


def build_delta_tests(provider: str, specs: dict[str, RouteSpec]) -> list[dict[str, Any]]:
    b_norm = specs["B-NORM"]
    c1 = specs["C1-CARE-PROCESS"]
    c3 = specs["C3-IMPLEMENTATION"]
    c4 = specs["C4-SOCIAL-CONTEXT"]

    b_base = compile_route_query(provider, b_norm)
    b_food_based = compile_route_query(
        provider, _with_extra_term(b_norm, "nutrition_anchor", "food based")
    )
    b_healthy = compile_route_query(
        provider, _with_extra_term(b_norm, "nutrition_anchor", "healthy eating")
    )
    c1_base = compile_route_query(provider, c1)
    c1_meal = compile_route_query(provider, _with_extra_term(c1, "terms", "meal plan*"))
    c3_query = compile_route_query(provider, c3)
    c4_query = compile_route_query(provider, c4)

    non_c4_union = _union(
        compile_route_query(provider, specs[route_id]) for route_id in ROUTE_ORDER[:-1]
    )

    return [
        {
            "id": "D01",
            "route": "B-NORM",
            "comparison": "baseline vs + food based orthographic variant",
            "baseline_query": b_base,
            "variant_query": b_food_based,
            "incremental_query": f"({b_food_based}) NOT ({b_base})",
            "human_interpretation_required": True,
        },
        {
            "id": "D02",
            "route": "B-NORM",
            "comparison": "baseline vs + healthy eating",
            "baseline_query": b_base,
            "variant_query": b_healthy,
            "incremental_query": f"({b_healthy}) NOT ({b_base})",
            "human_interpretation_required": True,
        },
        {
            "id": "D03",
            "route": "C1-CARE-PROCESS",
            "comparison": "with vs without meal plan*",
            "baseline_query": c1_base,
            "variant_query": c1_meal,
            "incremental_query": f"({c1_meal}) NOT ({c1_base})",
            "human_interpretation_required": True,
        },
        {
            "id": "D04",
            "route": "C3-IMPLEMENTATION",
            "comparison": "standalone yield and precision sample",
            "baseline_query": None,
            "variant_query": c3_query,
            "incremental_query": c3_query,
            "human_interpretation_required": True,
        },
        {
            "id": "D05",
            "route": "C4-SOCIAL-CONTEXT",
            "comparison": "incremental yield and precision sample",
            "baseline_query": non_c4_union,
            "variant_query": _union((non_c4_union, c4_query)),
            "incremental_query": f"({c4_query}) NOT ({non_c4_union})",
            "human_interpretation_required": True,
        },
    ]


def build_press_package(draft: dict[str, Any]) -> dict[str, Any]:
    specs = route_specs(draft)
    provider_packages: dict[str, Any] = {}
    for provider in FORMAL_PROVIDERS:
        route_queries = {
            route_id: compile_route_query(provider, specs[route_id])
            for route_id in ROUTE_ORDER
        }
        provider_packages[provider] = {
            "status": "CANDIDATE_NOT_NATIVE_VALIDATED",
            "simulation_forbidden": provider in {"scopus", "web_of_science"},
            "routes": route_queries,
            "delta_tests": build_delta_tests(provider, specs),
        }

    canonical = {
        "schema_version": 1,
        "package_type": "NUTEV_ARTICLE1_PRESS_QUERY_CANDIDATES",
        "draft_version": draft.get("draft_version"),
        "question": draft.get("question"),
        "status": "PREFREEZE_CANDIDATE_ONLY",
        "formal_execution_authorized": False,
        "provider_packages": provider_packages,
        "guardrails": {
            "candidate_is_not_native_validation": True,
            "candidate_is_not_press_pass": True,
            "candidate_is_not_query_freeze": True,
            "candidate_is_not_formal_search": True,
            "candidate_is_not_prisma_event": True,
            "scopus_web_of_science_must_not_be_simulated": True,
            "delta_test_results_require_human_interpretation": True,
        },
    }
    canonical_json = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    canonical["package_sha256"] = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return canonical
