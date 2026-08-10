from __future__ import annotations

from functools import lru_cache
import re

from nutev.export import _curation_impl as _impl

# Preserve the historical curation module API while keeping the large, already
# validated implementation byte-for-byte in _curation_impl.py. The policy below
# replaces only operational priority classification and is injected into the
# implementation before curate_outputs() is called.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

_CURATED_ANCHOR_TERMS = [
    "nutrition",
    "nutritional",
    "diet",
    "dietary",
    "food",
    "eating",
    "meal",
    "obesity",
    "obesidade",
    "overweight",
    "cardiometabolic",
    "diabetes",
    "prediabetes",
    "hypertension",
    "dyslipidemia",
    "dyslipidaemia",
    "hyperlipidemia",
    "hyperlipidaemia",
    "metabolic syndrome",
    "insulin resistance",
    "masld",
    "nafld",
    "mafld",
    "mash",
    "nash",
    "fatty liver",
    "steatotic liver disease",
    "mediterranean",
    "dash",
    "mind diet",
    "plant-based",
    "plant based",
    "eat-lancet",
    "diet quality",
    "healthy eating index",
    "dietary inflammatory index",
    "ultra-processed food",
    "ultra processed food",
    "ultra-processed foods",
    "ultra processed foods",
    "upf",
    "nova classification",
    "nova food classification",
    "lifestyle medicine",
    "culinary medicine",
    "food literacy",
    "food and nutrition literacy",
    "nutrition literacy",
    "food agency",
    "food is medicine",
    "food as medicine",
    "produce prescription",
    "produce rx",
    "medically tailored meal",
    "medically tailored meals",
    "food pharmacy",
    "food farmacy",
    "nutrition security",
    "food insecurity",
    "food environment",
    "healthy food access",
    "teaching kitchen",
    "teaching kitchens",
    "dietary adherence",
    "dietary self-monitoring",
    "eating behavior",
    "eating behaviour",
]

_CURATED_EVIDENCE_SIGNALS = [
    "guideline",
    "guidelines",
    "clinical practice guideline",
    "practice advisory",
    "practice guidance",
    "guidance statement",
    "consensus",
    "consensus statement",
    "scientific statement",
    "position statement",
    "position paper",
    "systematic review",
    "meta-analysis",
    "meta analysis",
    "umbrella review",
    "randomized controlled trial",
    "randomised controlled trial",
    "controlled trial",
    "pragmatic trial",
    "implementation trial",
    "implementation evaluation",
    "quality improvement study",
]

_TERM_SEPARATOR_RE = re.compile(r"[-\s]+")


@lru_cache(maxsize=4096)
def _priority_term_pattern(term: str) -> re.Pattern[str]:
    parts = [part for part in _TERM_SEPARATOR_RE.split(term.strip()) if part]
    if not parts:
        return re.compile(r"(?!)")
    body = r"[-\s]+".join(re.escape(part) for part in parts)
    return re.compile(rf"(?<!\w){body}(?!\w)", flags=re.IGNORECASE)


def _priority_term_present(text: str, term: object) -> bool:
    value = str(term or "").strip()
    if not value:
        return False
    return bool(_priority_term_pattern(value).search(text))


def _priority_text(row: dict) -> str:
    return " ".join(_impl._as_text(row.get(field)) for field in _impl._PRIORITY_TEXT_FIELDS)


def _curated_priority_signals(row: dict) -> dict[str, object]:
    try:
        score = float(row.get("relevance_score") or row.get("score") or 0)
    except Exception:
        score = 0.0
    text = _priority_text(row)
    anchor = any(_priority_term_present(text, term) for term in _CURATED_ANCHOR_TERMS)
    evidence_signal = any(
        _priority_term_present(text, term) for term in _CURATED_EVIDENCE_SIGNALS
    )
    editorial_tier = _impl._as_text(row.get("editorial_priority_tier")).lower()
    return {
        "score": score,
        "anchor": anchor,
        "evidence_signal": evidence_signal,
        "high_value_editorial": editorial_tier in _impl._A1_PROXY_TIERS,
    }


def _is_prioritized(row: dict) -> bool:
    """Operational priority requires a NutEV thematic anchor.

    Evidence type/editorial authority can strengthen priority but cannot make an
    unrelated clinical document a NutEV-priority record. This remains an
    operational flag; it is not a scientific inclusion decision.
    """
    signals = _curated_priority_signals(row)
    if not signals["anchor"]:
        return False
    score = float(signals["score"])
    if score >= 8:
        return True
    return score >= 7 and bool(signals["high_value_editorial"])


# curate_outputs() and _curate_row() are implemented in _curation_impl and look
# up _is_prioritized in that module at runtime. Replace that single policy hook
# while preserving all other curation code byte-for-byte.
_impl._is_prioritized = _is_prioritized
curate_outputs = _impl.curate_outputs
