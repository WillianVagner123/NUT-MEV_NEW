"""Validation and normalization for the global NutEV search field.

The global field accepts plain alternatives only. Provider-specific Boolean syntax
is rendered by :mod:`nutev.search.strategy_builder`, so raw field tags/operators
must not be allowed to silently change the meaning of the registered strategy.

This module intentionally validates only input shape and provider-rendering safety.
It does not decide scientific eligibility, GF-02 completion, PRESS approval, or
formal/PRISMA status.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

SUPPORTED_LANGUAGES = ("eng", "por", "spa")

LANGUAGE_ALIASES = {
    "en": "eng",
    "eng": "eng",
    "english": "eng",
    "pt": "por",
    "por": "por",
    "portuguese": "por",
    "portugues": "por",
    "es": "spa",
    "spa": "spa",
    "spanish": "spa",
    "espanol": "spa",
}

PUBMED_LANGUAGE_NAMES = {
    "eng": "english",
    "por": "portuguese",
    "spa": "spanish",
}

OPENALEX_LANGUAGE_CODES = {
    "eng": "en",
    "por": "pt",
    "spa": "es",
}

# Deliberately small current allow-list: labels already useful to the Article 1
# workflow and represented by PubMed Publication Type [pt] syntax. Extend only
# with an explicit, tested provider mapping rather than silently accepting typos.
PUBLICATION_TYPE_ALIASES = {
    "guideline": "Guideline",
    "practice guideline": "Practice Guideline",
    "systematic review": "Systematic Review",
    "meta analysis": "Meta-Analysis",
    "meta-analysis": "Meta-Analysis",
    "review": "Review",
    "clinical trial": "Clinical Trial",
    "randomized controlled trial": "Randomized Controlled Trial",
    "randomised controlled trial": "Randomized Controlled Trial",
    "controlled clinical trial": "Controlled Clinical Trial",
    "observational study": "Observational Study",
    "government publication": "Government Publication",
    "comparative study": "Comparative Study",
}

# Explicit rendering support in the current builder. A False value means the
# selected filter must not be implied to have been applied for that provider.
FILTER_SUPPORT = {
    "pubmed": {"year": True, "language": True, "publication_type": True},
    "europepmc": {"year": True, "language": True, "publication_type": False},
    "crossref": {"year": True, "language": False, "publication_type": False},
    "openalex": {"year": True, "language": True, "publication_type": False},
}

_BOOLEAN_TOKEN = re.compile(r"(?<!\w)(AND|OR|NOT)(?!\w)")
_PROVIDER_SYNTAX = (
    re.compile(r"\[[^\]]+\]"),
    re.compile(r"\bTITLE-ABS-KEY\s*\(", re.IGNORECASE),
    re.compile(r"\bTS\s*=", re.IGNORECASE),
    re.compile(r"\bPUB_YEAR\s*:", re.IGNORECASE),
    re.compile(r"\bFIRST_PDATE\s*:", re.IGNORECASE),
    re.compile(r"\bLANG\s*:", re.IGNORECASE),
    re.compile(r"\bquery\s*=", re.IGNORECASE),
    re.compile(r"\bfilter\s*=", re.IGNORECASE),
)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(ascii_value.casefold().replace("_", " ").split())


def _iter_values(value: object, *, split_commas: bool = True) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_values: Iterable[object] = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = [value]

    out: list[str] = []
    for raw in raw_values:
        text = str(raw).replace(";", "\n")
        if split_commas:
            text = text.replace(",", "\n")
        for chunk in text.split("\n"):
            cleaned = " ".join(chunk.strip().split())
            if cleaned:
                out.append(cleaned)
    return out


def _clean_query_term(term: str) -> str:
    term = " ".join(term.strip().split())
    if len(term) >= 2 and term[0] == term[-1] and term[0] in {'"', "'"}:
        term = term[1:-1].strip()
    if not term:
        raise ValueError("A alternativa de pesquisa não pode ficar vazia.")
    if '"' in term:
        raise ValueError(
            "Aspas internas não são aceitas no campo global; informe a frase sem sintaxe manual."
        )
    if _BOOLEAN_TOKEN.search(term):
        raise ValueError(
            "O campo global aceita alternativas simples; não use AND/OR/NOT manualmente."
        )
    if any(pattern.search(term) for pattern in _PROVIDER_SYNTAX):
        raise ValueError(
            "Não use tags ou sintaxe específica de base no campo global; o NutEV renderiza isso por provedor."
        )
    return term


def normalize_query_terms(value: object) -> list[str]:
    """Return deduplicated plain alternatives for the unified global field."""
    values = _iter_values(value, split_commas=isinstance(value, str))
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        term = _clean_query_term(raw)
        key = term.casefold()
        if key not in seen:
            out.append(term)
            seen.add(key)
    return out


def normalize_year(value: object, *, label: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        year = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} deve ser um ano inteiro ou 0 para sem filtro.") from exc
    if year == 0:
        return None
    if year < 1000 or year > 3000:
        raise ValueError(f"{label} deve estar entre 1000 e 3000, ou 0 para sem filtro.")
    return year


def normalize_year_range(year_from: object, year_to: object) -> tuple[int | None, int | None]:
    lo = normalize_year(year_from, label="Ano inicial")
    hi = normalize_year(year_to, label="Ano final")
    if lo is not None and hi is not None and lo > hi:
        raise ValueError("Ano inicial não pode ser maior que o ano final.")
    return lo, hi


def normalize_languages(value: object) -> list[str]:
    values = _iter_values(value)
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        key = _fold(raw)
        canonical = LANGUAGE_ALIASES.get(key)
        if canonical is None:
            allowed = ", ".join(SUPPORTED_LANGUAGES)
            raise ValueError(
                f"Idioma não reconhecido: {raw!r}. Use um dos códigos validados: {allowed}."
            )
        if canonical not in seen:
            out.append(canonical)
            seen.add(canonical)
    return out


def normalize_publication_types(value: object) -> list[str]:
    values = _iter_values(value)
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        key = _fold(raw).replace(" - ", "-")
        canonical = PUBLICATION_TYPE_ALIASES.get(key)
        if canonical is None:
            allowed = ", ".join(sorted(set(PUBLICATION_TYPE_ALIASES.values())))
            raise ValueError(
                f"Tipo de publicação não reconhecido: {raw!r}. Valores atuais: {allowed}."
            )
        folded = canonical.casefold()
        if folded not in seen:
            out.append(canonical)
            seen.add(folded)
    return out


def pubmed_language_name(code: str) -> str:
    return PUBMED_LANGUAGE_NAMES[code]


def openalex_language_code(code: str) -> str:
    return OPENALEX_LANGUAGE_CODES[code]
