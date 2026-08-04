"""Unified research field -> auditable per-provider search expressions.

The public interface uses one article-independent research field. Researchers
enter terms or phrases once; the same input is rendered for every supported
provider. Article assignment happens after retrieval, so the search form never
requires choosing Article 1, 2, 3, 4, or 5.

The builder keeps three breadth levels for compatibility with existing exports:

- ``broad``     - the global research concept, without filters;
- ``balanced``  - the same global concept, without filters;
- ``specific``  - the global concept plus date/language/publication filters.

Within the unified field, alternatives separated by a new line, semicolon, or
comma form one global concept. Boolean-capable providers OR those alternatives;
Crossref and OpenAlex receive the equivalent combined free-text query.
Provider-specific syntax remains explicit and auditable.
Legacy PICOS/PECO parsing is preserved for existing integrations, but the unified
``query`` key takes precedence whenever it is present.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PROVIDERS = ("pubmed", "europepmc", "crossref", "openalex")
BREADTHS = ("broad", "balanced", "specific")
ARTICLE_SCOPE_ALL = "all_articles"

CORE_ROLES = ("query", "population", "intervention", "exposure")


@dataclass
class Concept:
    """One concept block: a set of synonyms (OR-ed), plus optional MeSH terms."""

    name: str
    terms: list[str]
    role: str = "context"
    mesh: list[str] = field(default_factory=list)


@dataclass
class StrategySpec:
    concepts: list[Concept]
    year_from: int | None = None
    year_to: int | None = None
    languages: list[str] = field(default_factory=list)
    publication_types: list[str] = field(default_factory=list)


_PICOS_ROLE_KEYS = {
    "population": "population",
    "patient": "population",
    "intervention": "intervention",
    "exposure": "exposure",
    "comparison": "comparison",
    "comparator": "comparison",
    "outcome": "outcome",
    "context": "context",
    "setting": "context",
}


def _as_terms(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def _filters_from_spec(spec: dict) -> dict:
    return {
        "year_from": spec.get("year_from"),
        "year_to": spec.get("year_to"),
        "languages": _as_terms(spec.get("languages")),
        "publication_types": _as_terms(spec.get("publication_types")),
    }


def parse_strategy(spec: dict) -> StrategySpec:
    """Build a strategy from the unified field, with PICOS compatibility.

    When ``query`` has content, it becomes the sole research concept and applies
    to every article. Any legacy PICOS/PECO blocks in the same payload are ignored.
    """
    filters = _filters_from_spec(spec)
    raw_query = spec.get("query")
    query_mesh: list[str] = []
    if isinstance(raw_query, dict):
        query_terms = _as_terms(raw_query.get("terms"))
        query_mesh = _as_terms(raw_query.get("mesh"))
    elif isinstance(raw_query, str):
        query_terms = _split_unified_terms(raw_query)
    else:
        query_terms = _as_terms(raw_query)

    if query_terms:
        return StrategySpec(
            concepts=[Concept("global_query", query_terms, role="query", mesh=query_mesh)],
            **filters,
        )

    concepts: list[Concept] = []
    for key, role in _PICOS_ROLE_KEYS.items():
        if key not in spec:
            continue
        raw = spec[key]
        mesh: list[str] = []
        if isinstance(raw, dict):
            terms = _as_terms(raw.get("terms"))
            mesh = _as_terms(raw.get("mesh"))
        else:
            terms = _as_terms(raw)
        if terms:
            concepts.append(Concept(name=key, terms=terms, role=role, mesh=mesh))
    return StrategySpec(concepts=concepts, **filters)


def parse_picos(spec: dict) -> StrategySpec:
    """Backward-compatible alias for historical PICOS/PECO integrations."""
    return parse_strategy(spec)


def _split_terms(text: object) -> list[str]:
    if text is None:
        return []
    out: list[str] = []
    for chunk in str(text).replace(";", "\n").split("\n"):
        term = chunk.strip()
        if term:
            out.append(term)
    return out


def _split_unified_terms(text: object) -> list[str]:
    """Split the single research field into deduplicated OR alternatives."""
    if text is None:
        return []
    out: list[str] = []
    seen: set[str] = set()
    normalized = str(text).replace(";", "\n").replace(",", "\n")
    for chunk in normalized.split("\n"):
        term = chunk.strip()
        key = term.casefold()
        if term and key not in seen:
            out.append(term)
            seen.add(key)
    return out


def _year(value: object) -> int | None:
    try:
        year = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return year or None


def unified_from_text(
    query: object = "",
    *,
    year_from: object = None,
    year_to: object = None,
    languages: object = "",
    publication_types: object = "",
) -> dict:
    """Assemble the article-independent strategy payload used by the dashboard."""
    terms = _split_unified_terms(query)
    if not terms:
        return {}

    spec: dict = {"query": terms, "article_scope": ARTICLE_SCOPE_ALL}
    year_lo = _year(year_from)
    year_hi = _year(year_to)
    if year_lo is not None:
        spec["year_from"] = year_lo
    if year_hi is not None:
        spec["year_to"] = year_hi
    langs = _split_terms(str(languages).replace(",", "\n"))
    if langs:
        spec["languages"] = langs
    pts = _split_terms(publication_types)
    if pts:
        spec["publication_types"] = pts
    return spec


def picos_from_text(
    population: object = "",
    intervention: object = "",
    exposure: object = "",
    comparison: object = "",
    outcome: object = "",
    context: object = "",
    *,
    year_from: object = None,
    year_to: object = None,
    languages: object = "",
    publication_types: object = "",
) -> dict:
    """Legacy six-field assembler retained for external compatibility."""
    spec: dict = {}
    for key, value in (
        ("population", population),
        ("intervention", intervention),
        ("exposure", exposure),
        ("comparison", comparison),
        ("outcome", outcome),
        ("context", context),
    ):
        terms = _split_terms(value)
        if terms:
            spec[key] = terms
    year_lo = _year(year_from)
    year_hi = _year(year_to)
    if year_lo is not None:
        spec["year_from"] = year_lo
    if year_hi is not None:
        spec["year_to"] = year_hi
    langs = _split_terms(str(languages).replace(",", "\n"))
    if langs:
        spec["languages"] = langs
    pts = _split_terms(publication_types)
    if pts:
        spec["publication_types"] = pts
    return spec


def parse_concepts(blocks: list) -> StrategySpec:
    concepts: list[Concept] = []
    for i, block in enumerate(blocks):
        if isinstance(block, dict):
            terms = _as_terms(block.get("terms"))
            if terms:
                concepts.append(
                    Concept(
                        name=str(block.get("name") or f"block{i + 1}"),
                        terms=terms,
                        role=str(block.get("role") or "intervention"),
                        mesh=_as_terms(block.get("mesh")),
                    )
                )
        else:
            terms = _as_terms(block)
            if terms:
                concepts.append(Concept(name=f"block{i + 1}", terms=terms, role="intervention"))
    return StrategySpec(concepts=concepts)


def _blocks_for_breadth(spec: StrategySpec, breadth: str) -> list[Concept]:
    if breadth == "broad":
        core = [c for c in spec.concepts if c.role in CORE_ROLES]
        return core or spec.concepts[:1]
    return list(spec.concepts)


def _quote(term: str, provider: str) -> str:
    term = term.strip()
    if " " not in term:
        return term
    return f'"{term}"'


def _pubmed_block(concept: Concept) -> str:
    parts = [f'{_quote(t, "pubmed")}[tiab]' for t in concept.terms]
    parts += [f"{m}[Mesh]" for m in concept.mesh]
    return "(" + " OR ".join(parts) + ")"


def _plain_block(concept: Concept, provider: str) -> str:
    parts = [_quote(t, provider) for t in concept.terms]
    return "(" + " OR ".join(parts) + ")"


def _pubmed_filters(spec: StrategySpec, breadth: str) -> list[str]:
    if breadth != "specific":
        return []
    out: list[str] = []
    if spec.year_from or spec.year_to:
        lo = spec.year_from or 1900
        hi = spec.year_to or 3000
        out.append(f'("{lo}"[dp] : "{hi}"[dp])')
    language_names = {"eng": "english", "por": "portuguese", "spa": "spanish"}
    langs = [f"{language_names.get(x, x)}[lang]" for x in spec.languages]
    if langs:
        out.append("(" + " OR ".join(langs) + ")")
    pts = [f'{_quote(pt, "pubmed")}[pt]' for pt in spec.publication_types]
    if pts:
        out.append("(" + " OR ".join(pts) + ")")
    return out


def _europepmc_filters(spec: StrategySpec, breadth: str) -> list[str]:
    if breadth != "specific":
        return []
    out: list[str] = []
    if spec.year_from or spec.year_to:
        lo = spec.year_from or 1900
        hi = spec.year_to or 3000
        out.append(f"(PUB_YEAR:[{lo} TO {hi}])")
    if spec.languages:
        out.append("(" + " OR ".join(f"LANG:{x}" for x in spec.languages) + ")")
    return out


def _crossref_filter_param(spec: StrategySpec, breadth: str) -> str:
    if breadth != "specific":
        return ""
    parts: list[str] = []
    if spec.year_from:
        parts.append(f"from-pub-date:{spec.year_from}-01-01")
    if spec.year_to:
        parts.append(f"until-pub-date:{spec.year_to}-12-31")
    return ",".join(parts)


def _openalex_filter_param(spec: StrategySpec, breadth: str) -> str:
    if breadth != "specific":
        return ""
    parts: list[str] = []
    if spec.year_from:
        parts.append(f"from_publication_date:{spec.year_from}-01-01")
    if spec.year_to:
        parts.append(f"to_publication_date:{spec.year_to}-12-31")
    if spec.languages:
        parts.append("language:" + "|".join(spec.languages))
    return ",".join(parts)


def build_query(spec: StrategySpec, provider: str, breadth: str = "balanced") -> str:
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider!r}")
    if breadth not in BREADTHS:
        raise ValueError(f"unknown breadth: {breadth!r}")
    blocks = _blocks_for_breadth(spec, breadth)
    if not blocks:
        return ""

    if provider == "pubmed":
        expr = " AND ".join(_pubmed_block(c) for c in blocks)
        for item in _pubmed_filters(spec, breadth):
            expr += f" AND {item}"
        return expr

    if provider == "europepmc":
        expr = " AND ".join(_plain_block(c, provider) for c in blocks)
        for item in _europepmc_filters(spec, breadth):
            expr += f" AND {item}"
        return expr

    terms = " ".join(_quote(t, provider) for c in blocks for t in c.terms)
    filt = _crossref_filter_param(spec, breadth) if provider == "crossref" else _openalex_filter_param(spec, breadth)
    return f"query={terms} | filter={filt}" if filt else f"query={terms}"


def build_all(spec: StrategySpec) -> dict[str, dict[str, str]]:
    return {
        provider: {breadth: build_query(spec, provider, breadth) for breadth in BREADTHS}
        for provider in PROVIDERS
    }
