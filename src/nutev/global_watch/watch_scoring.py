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


def score_watch_item(item: dict) -> float:
    """Score with current facade extensions synchronized into the preserved core.

    `watch_extensions.py` extends `watch_scoring.BONUS_TERMS` and
    `watch_scoring.NUTMEV_SCOPE_TERMS` at import time. Keep those public extension
    hooks authoritative while delegating the stable scoring algorithm to `_impl`.
    """
    _impl.BONUS_TERMS = BONUS_TERMS
    _impl.NUTMEV_SCOPE_TERMS = NUTMEV_SCOPE_TERMS
    return _impl.score_watch_item(item)


_impl._apply_terms = _apply_terms
_impl._has_nutmev_scope_signal = _has_nutmev_scope_signal
