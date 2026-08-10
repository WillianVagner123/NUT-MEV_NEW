from __future__ import annotations

from functools import lru_cache
import re
from typing import Any


_TEXT_FIELDS = (
    "title",
    "abstract",
    "summary",
    "snippet",
    "extracted_text",
    "journal",
    "source_institution",
    "evidence_type",
)


def _text_blob(record: dict[str, Any]) -> str:
    return " ".join(str(record.get(k, "") or "") for k in _TEXT_FIELDS).lower()


@lru_cache(maxsize=4096)
def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", flags=re.IGNORECASE)


def _term_present(blob: str, term: object) -> bool:
    value = str(term or "").strip()
    if not value:
        return False
    return bool(_term_pattern(value).search(blob))


def _match_terms(blob: str, terms: list[str]) -> int:
    return sum(1 for term in terms if _term_present(blob, term))


# Signals that a record is centrally about diet / nutrition / eating (Article 1
# scope). Used to keep clinical/pharmacological documents that only *mention*
# nutrition out of the core corpus unless they are dietary in focus.
_DIETARY_CENTRALITY_TERMS = [
    "diet", "dietary", "nutrition", "nutritional", "food", "eating", "meal",
    "dietary pattern", "dietary guideline", "food-based", "vegetable", "fruit",
    "whole grain", "dieta", "alimenta", "alimentar", "nutri", "padrão alimentar",
]
# Off-scope markers: if present WITHOUT dietary centrality, the record is very
# likely outside the Article 1 dietary-guideline scope.
_OFF_SCOPE_TERMS = {
    "pharmacology": ["pharmacolog", "drug therapy", "glp-1", "glp1", "semaglutide", "metformin", "anticoagul", "statin", "pharmacotherap"],
    "oncology_vte": ["thromboembolism", "venous thrombo", "chemotherap", "oncolog", "cancer treatment", "tumor"],
    "pediatric_only": ["neonat", "infant formula", "preterm", "paediatric intensive", "pediatric intensive"],
    "surgical": ["bariatric surgery", "surgical", "perioperative", "post-operative"],
}


def _scope_signals(blob: str, matched_domains: list[str], record: dict) -> tuple[int, str, list[str]]:
    central = (
        bool(matched_domains)
        or bool(record.get("diet_patterns") or record.get("diet_pattern"))
        or _match_terms(blob, _DIETARY_CENTRALITY_TERMS) >= 2
    )
    flags = sorted(
        {
            label
            for label, terms in _OFF_SCOPE_TERMS.items()
            if any(_term_present(blob, term) for term in terms)
        }
    )
    if central:
        status = "in_scope"
    elif flags:
        status = "off_scope_review"
    else:
        status = "low_dietary_signal"
    return int(central), status, flags


def classify_evidence(
    records: list[dict[str, Any]],
    ontology: dict[str, Any],
    lenses_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    domains = ontology.get("domains", {})
    outcomes = ontology.get("outcomes", {})
    lens_map = lenses_cfg.get("lenses", {})

    for r in records:
        blob = _text_blob(r)
        matched_domains: list[str] = []
        matched_outcomes: list[str] = []
        lens_scores: dict[str, int] = {}

        for domain, terms in domains.items():
            score = _match_terms(blob, terms)
            r[f"domain_{domain}_count"] = score
            r[f"domain_{domain}_present"] = int(score > 0)
            if score > 0:
                matched_domains.append(domain)

        for outcome, terms in outcomes.items():
            score = _match_terms(blob, terms)
            r[f"outcome_{outcome}_count"] = score
            r[f"outcome_{outcome}_present"] = int(score > 0)
            if score > 0:
                matched_outcomes.append(outcome)

        for lens, lens_cfg in lens_map.items():
            lens_domains = lens_cfg.get("domains", [])
            score = sum(int(d in matched_domains) for d in lens_domains)
            lens_scores[lens] = score
            r[f"lens_{lens}_score"] = score
            r[f"lens_{lens}_present"] = int(score > 0)

        r["domains"] = sorted(set(matched_domains))
        r["outcomes"] = sorted(set(matched_outcomes))
        r["evidence_lenses"] = [k for k, v in lens_scores.items() if v > 0]

        # Scope gate for Article 1: flag records that are not centrally about
        # diet/nutrition so reviewers can exclude off-scope material (e.g.
        # pharmacology-only, oncology VTE, pediatric intensive care).
        centrality, scope_status, scope_flags = _scope_signals(blob, matched_domains, r)
        r["dietary_centrality"] = centrality
        r["scope_status"] = scope_status
        r["scope_flags"] = scope_flags

    return records
