from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
import re

from nutev.global_watch import _watch_scoring_impl as _impl

# Preserve the validated scoring implementation byte-for-byte and replace only
# lexical matching/scope policy. Runtime functions in _impl resolve these hooks
# dynamically, so score_watch_item() receives the hardened behavior below.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

_CKM_SCOPE_TERMS = (
    "cardiovascular-kidney-metabolic",
    "cardiovascular kidney metabolic",
    "cardiovascular-kidney-metabolic syndrome",
    "cardiovascular kidney metabolic syndrome",
    "cardio-kidney-metabolic",
    "cardio kidney metabolic",
    "ckm syndrome",
)

_impl.NUTMEV_SCOPE_TERMS = tuple(dict.fromkeys((*_impl.NUTMEV_SCOPE_TERMS, *_CKM_SCOPE_TERMS)))
NUTMEV_SCOPE_TERMS = _impl.NUTMEV_SCOPE_TERMS

# Implementation-science language is methodologically useful but is not, by
# itself, evidence that a record belongs to NutEV. Keep these records visible and
# apply only a soft operational penalty when no substantive nutrition/NutEV anchor
# is present. This changes prioritization, never raw retrieval or inclusion.
_GENERIC_IMPLEMENTATION_TERMS = (
    "implementation science",
    "implementation research",
    "implementation framework",
    "implementation strategy",
    "implementation outcomes",
    "implementation trial",
    "effectiveness-implementation",
    "effectiveness implementation",
    "hybrid effectiveness-implementation",
    "hybrid effectiveness implementation",
    "quality improvement",
    "service delivery",
    "care delivery",
    "dissemination",
    "scale-up",
    "scale up",
    "adoption",
    "reach",
    "maintenance",
)

_SUBSTANTIVE_NUTEV_ANCHOR_TERMS = (
    "nutrition",
    "diet",
    "dietary",
    "food",
    "meal",
    "culinary",
    "lifestyle medicine",
    "lifestyle nutrition",
    "lifestyle intervention",
    "medical nutrition therapy",
    "obesity",
    "adiposity",
    "weight management",
    "cardiometabolic",
    "cardiovascular-kidney-metabolic",
    "cardio-kidney-metabolic",
    "metabolic syndrome",
    "diabetes",
    "hypertension",
    "blood pressure",
    "dyslipidemia",
    "dyslipidaemia",
    "masld",
    "nafld",
    "mash",
    "nash",
    "fatty liver",
    "steatotic liver disease",
    "produce prescription",
    "medically tailored",
    "food literacy",
    "nutrition literacy",
    "culinary medicine",
)

_GENERIC_IMPLEMENTATION_PENALTY = -30.0

_TERM_SEPARATOR_RE = re.compile(r"[-\s]+")


@lru_cache(maxsize=8192)
def _watch_term_pattern(term: str) -> re.Pattern[str]:
    parts = [part for part in _TERM_SEPARATOR_RE.split(term.strip()) if part]
    if not parts:
        return re.compile(r"(?!)")
    body = r"[-\s]+".join(re.escape(part) for part in parts)
    return re.compile(rf"(?<!\w){body}(?!\w)", flags=re.IGNORECASE)


def _watch_term_present(text: str, term: object) -> bool:
    value = str(term or "").strip()
    if not value:
        return False
    return bool(_watch_term_pattern(value).search(text))


def _apply_terms(score: float, text: str, terms: Iterable[tuple[str, float]]) -> float:
    for key, value in terms:
        if _watch_term_present(text, key):
            score += value
    return score


def _has_nutmev_scope_signal(text: str) -> bool:
    return any(_watch_term_present(text, term) for term in NUTMEV_SCOPE_TERMS)


def _is_generic_implementation_noise(text: str) -> bool:
    has_generic_signal = any(
        _watch_term_present(text, term) for term in _GENERIC_IMPLEMENTATION_TERMS
    )
    if not has_generic_signal:
        return False
    return not any(
        _watch_term_present(text, term) for term in _SUBSTANTIVE_NUTEV_ANCHOR_TERMS
    )


def score_watch_item(item: dict) -> float:
    """Score with current facade extensions synchronized into the preserved core.

    `watch_extensions.py` extends `watch_scoring.BONUS_TERMS` and
    `watch_scoring.NUTMEV_SCOPE_TERMS` at import time. Keep those public extension
    hooks authoritative while delegating the stable scoring algorithm to `_impl`.

    Generic implementation-science language without a substantive NutEV anchor is
    down-ranked operationally but remains in the raw evidence stream for review.
    """
    _impl.BONUS_TERMS = globals()["BONUS_TERMS"]
    _impl.NUTMEV_SCOPE_TERMS = NUTMEV_SCOPE_TERMS
    score = _impl.score_watch_item(item)
    text = _build_scoring_text(item)
    if _is_generic_implementation_noise(text):
        score += _GENERIC_IMPLEMENTATION_PENALTY
    return round(score, 3)


_impl._apply_terms = _apply_terms
_impl._has_nutmev_scope_signal = _has_nutmev_scope_signal
