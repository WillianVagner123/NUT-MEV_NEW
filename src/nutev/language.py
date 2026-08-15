from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

_LANGUAGE_ALIASES = {
    "pt": "pt", "por": "pt", "pt-br": "pt", "pt_br": "pt", "portuguese": "pt", "portugues": "pt", "português": "pt",
    "es": "es", "spa": "es", "spanish": "es", "espanol": "es", "español": "es",
    "en": "en", "eng": "en", "english": "en",
    "fr": "fr", "fra": "fr", "fre": "fr", "french": "fr", "francais": "fr", "français": "fr",
    "it": "it", "ita": "it", "italian": "it", "italiano": "it",
    "de": "de", "deu": "de", "ger": "de", "german": "de", "deutsch": "de",
}

_STOPWORDS = {
    "pt": {"a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos", "e", "em", "entre", "esta", "este", "foi", "mais", "na", "nas", "no", "nos", "ou", "para", "por", "que", "saude", "saúde", "uma", "um"},
    "es": {"a", "al", "con", "como", "de", "del", "el", "en", "entre", "esta", "este", "fue", "la", "las", "los", "mas", "más", "o", "para", "por", "que", "salud", "una", "un", "y"},
    "en": {"a", "an", "and", "as", "at", "between", "by", "for", "from", "health", "in", "is", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with"},
    "fr": {"a", "avec", "comme", "dans", "de", "des", "du", "et", "est", "la", "le", "les", "ou", "par", "pour", "que", "sante", "santé", "un", "une"},
    "it": {"a", "con", "come", "da", "del", "della", "e", "in", "la", "le", "lo", "o", "per", "salute", "un", "una"},
    "de": {"als", "bei", "das", "der", "die", "ein", "eine", "für", "gesundheit", "im", "in", "ist", "mit", "oder", "und", "von", "zu"},
}

_DIACRITIC_HINTS = {
    "pt": set("ãõçáàâêéíóôú"),
    "es": set("ñ¿¡áéíóúü"),
    "fr": set("àâçéèêëîïôùûüÿœ"),
    "it": set("àèéìíîòóùú"),
    "de": set("äöüß"),
}

_TESSERACT_CODES = {
    "pt": "por",
    "es": "spa",
    "en": "eng",
    "fr": "fra",
    "it": "ita",
    "de": "deu",
}


def normalize_language_code(value: object) -> str:
    raw = str(value or "").strip().lower().replace("_", "-")
    if not raw:
        return ""
    if raw in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[raw]
    short = raw.split("-", 1)[0]
    return _LANGUAGE_ALIASES.get(short, short if len(short) == 2 else "")


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text or "")]


def detect_language(text: str, *, declared: object = None) -> dict[str, Any]:
    """Dependency-light language hinting with auditable provenance.

    A declared language is preserved as the original-language claim. Detection is
    deliberately conservative and intended for routing OCR/translation work, not
    for scientific classification. Low-information text returns ``und``.
    """
    declared_code = normalize_language_code(declared)
    sample = (text or "").strip()
    tokens = _tokens(sample[:12000])
    if not tokens:
        return {
            "declared_language": declared_code or None,
            "detected_language": declared_code or "und",
            "confidence": 1.0 if declared_code else 0.0,
            "method": "declared" if declared_code else "insufficient_text",
        }

    scores: dict[str, float] = {code: 0.0 for code in _STOPWORDS}
    token_set = set(tokens)
    for code, words in _STOPWORDS.items():
        scores[code] += float(sum(token in words for token in tokens))
        scores[code] += 0.25 * len(token_set & words)
    lower = sample.casefold()
    for code, chars in _DIACRITIC_HINTS.items():
        scores[code] += 0.75 * sum(lower.count(char) for char in chars)

    if declared_code in scores:
        # A declaration is a useful prior, but never overwrites the detected result.
        scores[declared_code] += 1.5

    ranked = sorted(scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
    best_code, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    evidence = sum(scores.values())
    if best_score < 2.0:
        return {
            "declared_language": declared_code or None,
            "detected_language": declared_code or "und",
            "confidence": 0.35 if declared_code else 0.0,
            "method": "declared_low_text" if declared_code else "heuristic_low_confidence",
        }
    margin = max(0.0, best_score - second_score)
    confidence = min(0.99, 0.55 + (margin / max(best_score, 1.0)) * 0.4 + min(evidence, 10.0) / 100.0)
    return {
        "declared_language": declared_code or None,
        "detected_language": best_code,
        "confidence": round(confidence, 3),
        "method": "heuristic_stopwords_diacritics",
    }


def detect_language_code(text: str, *, declared: object = None) -> str:
    return str(detect_language(text, declared=declared)["detected_language"])


def tesseract_language_for(code: object, *, available: set[str] | None = None) -> str | None:
    normalized = normalize_language_code(code)
    candidate = _TESSERACT_CODES.get(normalized)
    if not candidate:
        return None
    if available is not None and candidate not in available:
        return None
    return candidate


@dataclass(frozen=True)
class TranslationRecord:
    document_id: str
    source_language: str
    target_language: str
    status: str
    original_text_path: str
    translated_text_path: str = ""
    translator: str = ""
    model_or_version: str = ""
    original_sha256: str = ""
    translated_sha256: str = ""
    created_at: str = ""


def translation_record(**kwargs: Any) -> dict[str, Any]:
    """Build a non-destructive translation provenance record.

    The original is always retained separately. A completed translation must name
    the translator/version and point to a distinct translated artifact.
    """
    record = TranslationRecord(**kwargs)
    status = record.status.strip().upper()
    if status not in {"PENDING", "SKIPPED", "FAILED", "COMPLETED"}:
        raise ValueError("invalid translation status")
    if not record.document_id.strip() or not record.original_text_path.strip():
        raise ValueError("document_id and original_text_path are required")
    if record.source_language == record.target_language and status == "COMPLETED":
        raise ValueError("completed translation must change language")
    if status == "COMPLETED":
        if not record.translated_text_path.strip():
            raise ValueError("completed translation requires translated_text_path")
        if record.translated_text_path == record.original_text_path:
            raise ValueError("translation cannot overwrite original_text_path")
        if not record.translator.strip() or not record.model_or_version.strip():
            raise ValueError("completed translation requires translator and model_or_version")
    payload = asdict(record)
    payload["status"] = status
    payload["source_language"] = normalize_language_code(record.source_language) or record.source_language
    payload["target_language"] = normalize_language_code(record.target_language) or record.target_language
    return payload


__all__ = [
    "TranslationRecord",
    "detect_language",
    "detect_language_code",
    "normalize_language_code",
    "tesseract_language_for",
    "translation_record",
]
