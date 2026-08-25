from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


SUPPORTED_FRAMEWORKS = {
    "PCC": ("Population", "Concept", "Context"),
    "PICO": ("Population", "Intervention", "Comparator", "Outcome"),
    "PECO": ("Population", "Exposure", "Comparator", "Outcome"),
}
SUPPORTED_TERM_KINDS = {"free", "mesh", "decs"}
MAX_CONCEPTS = 8
MAX_TERMS_PER_CONCEPT = 80
MAX_TERM_LENGTH = 180
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ReviewTerm:
    text: str
    kind: str = "free"


@dataclass(frozen=True)
class ReviewConcept:
    label: str
    terms: tuple[ReviewTerm, ...]


def _clean_text(value: object, *, max_length: int = MAX_TERM_LENGTH) -> str:
    text = _SPACE_RE.sub(" ", str(value or "")).strip()
    if len(text) > max_length:
        raise ValueError(f"Texto excede o limite de {max_length} caracteres")
    return text


def _normalize_term(value: object) -> ReviewTerm | None:
    if isinstance(value, dict):
        text = _clean_text(value.get("text"))
        kind = str(value.get("kind") or "free").strip().lower()
    else:
        raw = _clean_text(value)
        kind = "free"
        text = raw
        lowered = raw.lower()
        for prefix in ("mesh:", "decs:", "free:"):
            if lowered.startswith(prefix):
                kind = prefix[:-1]
                text = _clean_text(raw[len(prefix) :])
                break
    if not text:
        return None
    if kind not in SUPPORTED_TERM_KINDS:
        raise ValueError(f"Tipo de termo não suportado: {kind}")
    return ReviewTerm(text=text, kind=kind)


def normalize_strategy(strategy: object) -> dict[str, Any] | None:
    if not isinstance(strategy, dict):
        return None
    framework = str(strategy.get("framework") or "PCC").strip().upper()
    if framework not in SUPPORTED_FRAMEWORKS:
        raise ValueError("Framework deve ser PCC, PICO ou PECO")
    raw_concepts = strategy.get("concepts")
    if not isinstance(raw_concepts, list) or not raw_concepts:
        return None
    if len(raw_concepts) > MAX_CONCEPTS:
        raise ValueError(f"Estratégia aceita no máximo {MAX_CONCEPTS} blocos conceituais")

    concepts: list[ReviewConcept] = []
    for index, raw_concept in enumerate(raw_concepts, start=1):
        if not isinstance(raw_concept, dict):
            raise ValueError("Cada bloco conceitual deve ser um objeto")
        label = _clean_text(raw_concept.get("label") or f"Concept {index}", max_length=80)
        raw_terms = raw_concept.get("terms")
        if not isinstance(raw_terms, list):
            raise ValueError(f"Bloco {label} precisa de uma lista de termos")
        if len(raw_terms) > MAX_TERMS_PER_CONCEPT:
            raise ValueError(
                f"Bloco {label} aceita no máximo {MAX_TERMS_PER_CONCEPT} termos"
            )
        terms: list[ReviewTerm] = []
        seen: set[tuple[str, str]] = set()
        for value in raw_terms:
            term = _normalize_term(value)
            if term is None:
                continue
            key = (term.kind, term.text.casefold())
            if key in seen:
                continue
            seen.add(key)
            terms.append(term)
        if terms:
            concepts.append(ReviewConcept(label=label, terms=tuple(terms)))

    if not concepts:
        return None
    return {"framework": framework, "concepts": concepts}


def _escape_phrase(text: str) -> str:
    return text.replace('"', " ").strip()


def _quote_plain(text: str) -> str:
    cleaned = _escape_phrase(text)
    if not cleaned:
        return ""
    if "*" in cleaned and " " not in cleaned:
        return cleaned
    return f'"{cleaned}"' if " " in cleaned else cleaned


def _pubmed_term(term: ReviewTerm) -> str:
    cleaned = _escape_phrase(term.text)
    if term.kind == "mesh":
        return f'"{cleaned}"[Mesh]'
    free = cleaned if ("*" in cleaned and " " not in cleaned) else f'"{cleaned}"'
    return f"{free}[Title/Abstract]"


def _europepmc_term(term: ReviewTerm) -> str:
    cleaned = _escape_phrase(term.text)
    if term.kind == "mesh":
        return f'MESH:"{cleaned}"'
    return f'TITLE_ABS:"{cleaned}"'


def _bvs_term(term: ReviewTerm) -> str:
    cleaned = _escape_phrase(term.text)
    if term.kind in {"mesh", "decs"}:
        return f'mh:"{cleaned}"'
    return f'tw:"{cleaned}"'


def _compile_boolean(concepts: list[ReviewConcept], formatter) -> str:
    blocks: list[str] = []
    for concept in concepts:
        formatted = [formatter(term) for term in concept.terms]
        formatted = [item for item in formatted if item]
        if not formatted:
            continue
        blocks.append("(" + " OR ".join(formatted) + ")")
    return " AND ".join(blocks)


def _compile_plain_boolean(concepts: list[ReviewConcept]) -> str:
    return _compile_boolean(concepts, lambda term: _quote_plain(term.text))


def compile_provider_query(provider: str, concepts: list[ReviewConcept]) -> tuple[str, str]:
    """Return (query, dialect).

    Controlled-vocabulary tags are used only where NutEV has an explicit provider dialect.
    Elsewhere their labels are projected as free text rather than pretending that the
    provider supports MeSH/DeCS semantics.
    """

    if provider == "pubmed":
        return _compile_boolean(concepts, _pubmed_term), "pubmed_mesh_title_abstract"
    if provider == "europepmc":
        return _compile_boolean(concepts, _europepmc_term), "europepmc_mesh_title_abstract"
    if provider == "lilacs_bvs_native":
        return _compile_boolean(concepts, _bvs_term), "bvs_decs_mesh_tw"
    if provider == "scielo_native":
        return _compile_plain_boolean(concepts), "scielo_boolean_free_text"
    if provider == "doaj":
        return _compile_plain_boolean(concepts), "doaj_boolean_free_text"
    if provider in {"openalex", "crossref", "semantic_scholar"}:
        return _compile_plain_boolean(concepts), "generic_boolean_free_text"
    return _compile_plain_boolean(concepts), "generic_boolean_free_text"


def compile_query_plan(
    question: object,
    providers: list[str],
    strategy: object = None,
) -> dict[str, Any]:
    question_text = _clean_text(question, max_length=500)
    normalized = normalize_strategy(strategy)
    if normalized is None:
        return {
            "schema_version": 1,
            "mode": "natural_language",
            "question": question_text,
            "framework": None,
            "concepts": [],
            "provider_queries": {
                provider: {
                    "query": question_text,
                    "dialect": "natural_language_passthrough",
                }
                for provider in providers
            },
            "controlled_vocabulary_terms": 0,
            "warnings": [
                "Sem estratégia estruturada: a pergunta é enviada como texto aos providers.",
                "NutEV não inventa MeSH/DeCS automaticamente neste modo.",
            ],
        }

    concepts: list[ReviewConcept] = list(normalized["concepts"])
    provider_queries: dict[str, dict[str, str]] = {}
    for provider in providers:
        query, dialect = compile_provider_query(provider, concepts)
        provider_queries[provider] = {"query": query, "dialect": dialect}

    controlled_count = sum(
        1
        for concept in concepts
        for term in concept.terms
        if term.kind in {"mesh", "decs"}
    )
    return {
        "schema_version": 1,
        "mode": "structured_review",
        "question": question_text,
        "framework": normalized["framework"],
        "concepts": [
            {
                "label": concept.label,
                "terms": [
                    {"text": term.text, "kind": term.kind} for term in concept.terms
                ],
            }
            for concept in concepts
        ],
        "provider_queries": provider_queries,
        "controlled_vocabulary_terms": controlled_count,
        "warnings": [
            "A estratégia é compilada somente a partir dos termos explicitamente aprovados pelo usuário.",
            "MeSH/DeCS não são inventados por heurística: devem ser inseridos ou aprovados antes da execução.",
            "Providers sem dialeto controlado explícito recebem projeção booleana em texto livre, registrada no audit trail.",
        ],
    }
