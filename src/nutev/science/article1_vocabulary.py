"""Audit Article 1 route vocabulary before formal query freeze.

This module mines deterministic title vocabulary from the rank-blind B-NORM and
C-STRUCT reading queues. It is a strategy-audit aid only. Corpus frequency does
not establish eligibility, validity, completeness, or permission to add a term
to a formal search strategy.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


VOCABULARY_AUDIT_VERSION = "nutev_article1_vocabulary_audit_v1"
REQUIRED_ROUTE_QUEUE_VERSION = "nutev_article1_route_queue_v1"
ROUTES = ("B-NORM", "C-STRUCT")

# B-NORM mirrors the current route architecture already discussed for the
# protocol. C-STRUCT is explicitly a candidate lexicon, not a frozen query.
BASELINE_TERMS: dict[str, tuple[str, ...]] = {
    "B-NORM": (
        "nutrition",
        "diet*",
        "food-based",
        "dietary pattern*",
        "guideline*",
        "guidance",
        "recommendation*",
        "consensus",
        "position statement*",
        "scientific statement*",
        "professional statement*",
        "standard*",
    ),
    "C-STRUCT": (
        "framework",
        "model",
        "competenc*",
        "food literacy",
        "nutrition literacy",
        "food skills",
        "culinary skills",
        "culinary medicine",
        "nutrition care process",
        "implementation",
        "dietary assessment",
        "nutrition assessment",
        "dietary counseling",
        "nutrition counseling",
        "nutrition prescription",
        "monitoring",
        "follow-up",
        "lifestyle medicine",
    ),
}

_FORMAL_STATUS = {
    "B-NORM": "candidate_baseline_from_current_protocol_architecture_not_frozen_here",
    "C-STRUCT": "candidate_lexicon_not_formal_query_and_not_frozen",
}

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "based", "by", "for", "from", "in",
    "into", "is", "of", "on", "or", "the", "to", "using", "with", "among",
    "between", "during", "after", "before", "their", "this", "that", "these",
    "those", "study", "studies", "analysis", "evaluation", "effect", "effects",
    "impact", "association", "associations", "adults", "patients", "people",
}

_FORBIDDEN_REVIEW_FIELDS = {
    "reference_rank",
    "reference_score",
    "reference_tier",
    "machine_relevance_score",
    "machine_relevance_band",
}


class Article1VocabularyAuditError(RuntimeError):
    """Raised when vocabulary audit inputs cannot be verified."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Article1VocabularyAuditError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Article1VocabularyAuditError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise Article1VocabularyAuditError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise Article1VocabularyAuditError(f"missing JSONL file: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Article1VocabularyAuditError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise Article1VocabularyAuditError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    return rows


def _atomic_json(path: Path, value: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return sha256_file(path)


def _normalize(value: object) -> str:
    text = str(value or "").lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(title: object) -> list[str]:
    return [token for token in _normalize(title).split() if len(token) > 1]


def _title_phrases(title: object) -> set[str]:
    tokens = _tokens(title)
    phrases: set[str] = set()
    for size in (2, 3, 4):
        for index in range(0, len(tokens) - size + 1):
            window = tokens[index:index + size]
            if window[0] in _STOPWORDS or window[-1] in _STOPWORDS:
                continue
            if sum(token not in _STOPWORDS for token in window) < 2:
                continue
            phrase = " ".join(window)
            if len(phrase) >= 7:
                phrases.add(phrase)
    return phrases


def _baseline_stem(term: str) -> str:
    return _normalize(term.replace("*", "")).strip("-")


def _term_present(title: object, term: str) -> bool:
    normalized = _normalize(title)
    stem = _baseline_stem(term)
    return bool(stem) and stem in normalized


def _phrase_represented_by_baseline(phrase: str, terms: Iterable[str]) -> bool:
    normalized = _normalize(phrase)
    for term in terms:
        stem = _baseline_stem(term)
        if stem and (stem in normalized or normalized in stem):
            return True
    return False


def _verified_routes(
    output_root: Path,
    search_id: str,
) -> tuple[dict[str, list[dict[str, Any]]], Path, str, dict[str, Any]]:
    route_root = output_root / "scientific" / "review_routes" / search_id / "article1"
    manifest_path = route_root / "ROUTE_QUEUE_MANIFEST.json"
    manifest = _read_json(manifest_path)
    if manifest.get("queue_type") != "NUTEV_ARTICLE1_ROUTE_REVIEW_QUEUE":
        raise Article1VocabularyAuditError("unexpected route queue manifest type")
    if manifest.get("status") != "PASS":
        raise Article1VocabularyAuditError("route queue manifest is not PASS")
    if str(manifest.get("queue_version") or "") != REQUIRED_ROUTE_QUEUE_VERSION:
        raise Article1VocabularyAuditError("Article 1 vocabulary audit requires route queue v1")

    outputs = manifest.get("outputs") or {}
    route_rows: dict[str, list[dict[str, Any]]] = {}
    for route in ROUTES:
        item = outputs.get(route) or {}
        path = Path(str(item.get("path") or ""))
        if not path.is_absolute():
            path = route_root / path.name
        expected = str(item.get("sha256") or "").strip().lower()
        if not path.is_file() or not expected:
            raise Article1VocabularyAuditError(f"missing route output/hash: {route}")
        actual = sha256_file(path)
        if actual != expected:
            raise Article1VocabularyAuditError(
                f"{route} SHA-256 mismatch: expected {expected}, got {actual}"
            )
        rows = _read_jsonl(path)
        for line_number, row in enumerate(rows, start=1):
            leaked = sorted(_FORBIDDEN_REVIEW_FIELDS & set(row))
            if leaked:
                raise Article1VocabularyAuditError(
                    f"{route} row {line_number} exposes blinded fields: {', '.join(leaked)}"
                )
            if str(row.get("route") or "") != route:
                raise Article1VocabularyAuditError(f"{route} row {line_number} has wrong route")
        route_rows[route] = rows

    return route_rows, manifest_path, sha256_file(manifest_path), manifest


def _route_vocabulary(
    route: str,
    rows: list[dict[str, Any]],
    all_phrase_counts: Mapping[str, Counter[str]],
) -> dict[str, Any]:
    baseline = BASELINE_TERMS[route]
    phrase_counts: Counter[str] = Counter()
    for row in rows:
        phrase_counts.update(_title_phrases(row.get("title")))

    min_review_df = max(3, math.ceil(len(rows) * 0.015))
    top_phrases: list[dict[str, Any]] = []
    for phrase, count in sorted(phrase_counts.items(), key=lambda item: (-item[1], item[0]))[:100]:
        other_count = sum(
            counter.get(phrase, 0)
            for other_route, counter in all_phrase_counts.items()
            if other_route != route
        )
        represented = _phrase_represented_by_baseline(phrase, baseline)
        top_phrases.append(
            {
                "phrase": phrase,
                "document_frequency": count,
                "document_frequency_pct": round(100 * count / max(len(rows), 1), 2),
                "other_route_document_frequency": other_count,
                "represented_by_baseline": represented,
                "manual_query_review_candidate": bool(not represented and count >= min_review_df),
            }
        )

    baseline_coverage = []
    for term in baseline:
        count = sum(1 for row in rows if _term_present(row.get("title"), term))
        baseline_coverage.append(
            {
                "term": term,
                "title_document_frequency": count,
                "title_document_frequency_pct": round(100 * count / max(len(rows), 1), 2),
            }
        )

    return {
        "route": route,
        "documents": len(rows),
        "formal_status": _FORMAL_STATUS[route],
        "baseline_terms": list(baseline),
        "baseline_title_coverage": baseline_coverage,
        "manual_review_min_document_frequency": min_review_df,
        "top_title_phrases": top_phrases,
        "machine_routing_class_counts": dict(
            sorted(Counter(str(row.get("document_class") or "unclassified") for row in rows).items())
        ),
        "machine_routing_domain_counts": dict(
            sorted(
                Counter(
                    str(domain)
                    for row in rows
                    for domain in (row.get("operational_domains") or [])
                ).items()
            )
        ),
    }


def audit_article1_route_vocabulary(
    search_id: str,
    *,
    output_root: Path = Path("project_output_reference"),
) -> dict[str, Any]:
    """Build a deterministic vocabulary audit for B-NORM and C-STRUCT queues."""
    output_root = output_root.resolve()
    route_rows, manifest_path, manifest_sha, route_manifest = _verified_routes(
        output_root, search_id
    )

    phrase_counts: dict[str, Counter[str]] = {}
    for route, rows in route_rows.items():
        counter: Counter[str] = Counter()
        for row in rows:
            counter.update(_title_phrases(row.get("title")))
        phrase_counts[route] = counter

    route_reports = {
        route: _route_vocabulary(route, route_rows[route], phrase_counts)
        for route in ROUTES
    }

    report = {
        "schema_version": 1,
        "audit_type": "NUTEV_ARTICLE1_ROUTE_VOCABULARY_AUDIT",
        "audit_version": VOCABULARY_AUDIT_VERSION,
        "status": "PASS",
        "created_at": _now(),
        "search_id": search_id,
        "source": {
            "route_queue_manifest": str(manifest_path),
            "route_queue_manifest_sha256": manifest_sha,
            "route_queue_version": route_manifest.get("queue_version"),
        },
        "routes": route_reports,
        "guardrails": {
            "corpus_frequency_is_not_eligibility": True,
            "corpus_frequency_is_not_search_validation": True,
            "candidate_terms_require_human_review": True,
            "formal_query_not_auto_modified": True,
            "discovery_corpus_does_not_retroactively_validate_formal_search": True,
            "no_prisma_event_emitted": True,
            "no_screening_decision_emitted": True,
            "external_llm_calls": 0,
        },
    }

    output_dir = output_root / "scientific" / "review_routes" / search_id / "article1"
    report_path = output_dir / "VOCABULARY_AUDIT.json"
    report_sha = _atomic_json(report_path, report)

    summary = {
        "mode": "NUTEV_ARTICLE1_ROUTE_VOCABULARY_AUDIT",
        "status": "COMPLETE",
        "audit_version": VOCABULARY_AUDIT_VERSION,
        "search_id": search_id,
        "B-NORM_documents": len(route_rows["B-NORM"]),
        "C-STRUCT_documents": len(route_rows["C-STRUCT"]),
        "B-NORM_manual_query_review_candidates": sum(
            1 for row in route_reports["B-NORM"]["top_title_phrases"]
            if row["manual_query_review_candidate"]
        ),
        "C-STRUCT_manual_query_review_candidates": sum(
            1 for row in route_reports["C-STRUCT"]["top_title_phrases"]
            if row["manual_query_review_candidate"]
        ),
        "report": str(report_path),
        "report_sha256": report_sha,
        "external_llm_calls": 0,
        "guardrail": (
            "Vocabulary audit only; candidate terms require human review and do not modify "
            "formal searches, eligibility, screening, or PRISMA."
        ),
    }
    return summary
