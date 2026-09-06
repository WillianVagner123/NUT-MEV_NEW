from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

_CLASS_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "evidence_synthesis",
        (
            "systematic review",
            "meta-analysis",
            "meta analysis",
            "systematic literature review",
        ),
    ),
    (
        "guidance",
        (
            "clinical practice guideline",
            "practice guideline",
            "guideline",
            "consensus statement",
            "position statement",
            "scientific statement",
            "standards of care",
        ),
    ),
    (
        "primary_randomized",
        (
            "randomized controlled trial",
            "randomised controlled trial",
            "randomized trial",
            "randomised trial",
            "controlled clinical trial",
            "randomized",
            "randomised",
        ),
    ),
    (
        "primary_observational",
        (
            "cohort study",
            "prospective cohort",
            "retrospective cohort",
            "cross-sectional",
            "cross sectional",
            "case-control",
            "case control",
            "observational study",
        ),
    ),
    (
        "primary_qualitative",
        (
            "qualitative study",
            "qualitative research",
            "focus group",
            "semi-structured interview",
            "semistructured interview",
        ),
    ),
    (
        "review",
        (
            "scoping review",
            "narrative review",
            "integrative review",
            "literature review",
            "review article",
            "review",
        ),
    ),
)

_QUERY_STOPWORDS = {
    "about",
    "after",
    "among",
    "and",
    "artigo",
    "artigos",
    "com",
    "como",
    "das",
    "dos",
    "effect",
    "effects",
    "em",
    "entre",
    "evidence",
    "for",
    "from",
    "impact",
    "melhora",
    "melhorar",
    "nos",
    "nas",
    "para",
    "por",
    "sobre",
    "the",
    "uma",
    "um",
    "with",
    "what",
    "which",
}
_QUERY_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.I)


def _normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


def _query_terms(query: str | None) -> list[str]:
    if not query:
        return []
    terms: list[str] = []
    for token in _QUERY_TOKEN_RE.findall(_normalized(query)):
        if token in _QUERY_STOPWORDS or token.isdigit():
            continue
        if token not in terms:
            terms.append(token)
        if len(terms) >= 20:
            break
    return terms


def _classification_source(record: Mapping[str, Any]) -> tuple[str, str, list[dict[str, str]]]:
    article_type = _normalized(
        record.get("article_type")
        or record.get("publication_type")
        or record.get("type")
    )
    title = _normalized(record.get("title"))
    abstract = _normalized(
        record.get("abstract") or record.get("summary") or record.get("snippet")
    )

    for document_class, patterns in _CLASS_PATTERNS:
        for pattern in patterns:
            if pattern in article_type:
                return document_class, "high", [{"field": "article_type", "value": pattern}]

    for document_class, patterns in _CLASS_PATTERNS:
        signals: list[dict[str, str]] = []
        for pattern in patterns:
            if pattern in title:
                signals.append({"field": "title", "value": pattern})
            elif pattern in abstract:
                signals.append({"field": "abstract", "value": pattern})
        if signals:
            return document_class, "medium", signals[:3]

    return "unclassified", "low", []


def classify_search_record(
    record: Mapping[str, Any],
    *,
    query: str | None = None,
) -> dict[str, Any]:
    """Build a conservative, explainable search-time article classification.

    The output is an indexing aid. It never emits eligibility, risk-of-bias,
    certainty, causal, or recommendation judgments.
    """

    document_class, confidence, signals = _classification_source(record)
    terms = _query_terms(query)
    title = _normalized(record.get("title"))
    abstract = _normalized(
        record.get("abstract") or record.get("summary") or record.get("snippet")
    )
    title_hits = [term for term in terms if term in title]
    abstract_hits = [term for term in terms if term in abstract and term not in title_hits]
    taxonomy_primary = str(record.get("taxonomy_primary") or "").strip()
    taxonomy_secondary = [
        str(value).strip()
        for value in (record.get("taxonomy_secondary") or [])
        if str(value).strip()
    ][:8]
    matched_terms = [
        str(value).strip()
        for value in (record.get("matched_terms") or [])
        if str(value).strip()
    ][:12]

    retrieval_reasons: list[dict[str, Any]] = []
    if title_hits:
        retrieval_reasons.append({"kind": "query_terms_in_title", "terms": title_hits[:8]})
    if abstract_hits:
        retrieval_reasons.append({"kind": "query_terms_in_abstract", "terms": abstract_hits[:8]})
    if taxonomy_primary:
        retrieval_reasons.append({"kind": "taxonomy_primary", "value": taxonomy_primary})
    if matched_terms:
        retrieval_reasons.append({"kind": "taxonomy_terms", "terms": matched_terms[:8]})
    if record.get("document_type_applied"):
        retrieval_reasons.append(
            {"kind": "document_type_signal", "value": str(record["document_type_applied"])}
        )

    return {
        "document_class": document_class,
        "confidence": confidence,
        "classification_basis": (
            "provider_article_type"
            if confidence == "high"
            else "title_abstract_text_signals"
            if confidence == "medium"
            else "insufficient_signal"
        ),
        "signals": signals,
        "taxonomy_primary": taxonomy_primary or None,
        "taxonomy_secondary": taxonomy_secondary,
        "query_match": {
            "terms_considered": terms,
            "title_hits": title_hits[:8],
            "abstract_hits": abstract_hits[:8],
        },
        "retrieval_reasons": retrieval_reasons,
        "guardrail": (
            "Search classification is a machine indexing aid derived from bibliographic metadata, "
            "text signals, taxonomy and query overlap. It is not eligibility, quality, risk of bias, "
            "certainty, causal inference or recommendation strength."
        ),
    }
