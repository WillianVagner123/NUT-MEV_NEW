"""OCR for images and rendered PDF pages with adaptive multilingual routing.

When ``NUTEV_OCR_LANG`` is unset, NutEV inspects the Tesseract language packs
actually installed and uses the supported multilingual set available on that
machine. Users may still pin an exact language expression for reproducibility.
The resolved default expression is exported as ``_DEFAULT_LANG`` so the existing
OCR cache signature changes when installed language capability changes.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nutev.language import detect_language

_SUPPORTED_PACKS = ("por", "eng", "spa", "fra", "ita", "deu")
_MIN_LONG_SIDE = 1800
_DEFAULT_CONFIG = os.environ.get(
    "NUTEV_OCR_CONFIG",
    "--oem 1 --psm 3 -c preserve_interword_spaces=1",
)


def installed_tesseract_languages() -> tuple[str, ...]:
    """Return installed Tesseract languages without turning setup failure into evidence."""
    try:
        import pytesseract

        return tuple(sorted(str(item) for item in pytesseract.get_languages(config="") if str(item).strip()))
    except Exception:
        return ()


def _automatic_language_expression() -> str:
    available = installed_tesseract_languages()
    chosen = [code for code in _SUPPORTED_PACKS if code in available]
    if not chosen:
        if "eng" in available:
            chosen = ["eng"]
        elif available:
            chosen = [available[0]]
        else:
            chosen = ["eng"]
    return "+".join(chosen)


# Keep this as the *resolved* expression because pdf_text.ocr_cache_signature()
# includes it. Installing/removing a language pack therefore changes the cache key.
_DEFAULT_LANG = os.environ.get("NUTEV_OCR_LANG") or _automatic_language_expression()


def _preprocess(image):
    """Grayscale + autocontrast + upscale a PIL image for cleaner OCR."""
    from PIL import Image, ImageOps

    img = image.convert("L")
    img = ImageOps.autocontrast(img)
    w, h = img.size
    longest = max(w, h)
    if longest and longest < _MIN_LONG_SIDE:
        scale = _MIN_LONG_SIDE / longest
        img = img.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))),
            Image.LANCZOS,
        )
    return img


def resolve_ocr_language(lang: str | None = None) -> tuple[str, tuple[str, ...]]:
    """Resolve the requested Tesseract expression and preserve the available set."""
    available = installed_tesseract_languages()
    requested = str(lang or _DEFAULT_LANG or "eng").strip()
    if requested.lower() == "auto":
        requested = _automatic_language_expression()
    return requested, available


def _quality(text: str) -> dict[str, Any]:
    clean = (text or "").strip()
    alpha = sum(char.isalpha() for char in clean)
    alpha_ratio = (alpha / len(clean)) if clean else 0.0
    return {
        "chars": len(clean),
        "alpha_ratio": round(alpha_ratio, 4),
        "usable": len(clean) >= 40 and alpha_ratio >= 0.35,
    }


def ocr_pil_image_with_meta(
    image,
    *,
    lang: str | None = None,
    config: str | None = None,
) -> dict[str, Any]:
    """OCR one image and return text plus language/quality diagnostics."""
    import pytesseract

    resolved_lang, available = resolve_ocr_language(lang)
    resolved_config = _DEFAULT_CONFIG if config is None else config
    prepared = _preprocess(image)
    fallback_used = False
    try:
        text = pytesseract.image_to_string(
            prepared,
            lang=resolved_lang,
            config=resolved_config,
        )
    except pytesseract.TesseractError:
        if resolved_lang == "eng":
            raise
        fallback_used = True
        text = pytesseract.image_to_string(prepared, lang="eng", config=resolved_config)
        resolved_lang = "eng"

    detection = detect_language(text)
    return {
        "text": text,
        "tesseract_language": resolved_lang,
        "tesseract_languages_available": list(available),
        "fallback_to_english": fallback_used,
        "detected_language": detection.get("detected_language"),
        "language_detection_confidence": detection.get("confidence"),
        "language_detection_method": detection.get("method"),
        "quality": _quality(text),
    }


def ocr_pil_image(image, *, lang: str | None = None, config: str | None = None) -> str:
    """Compatibility text-only OCR API using the adaptive multilingual path."""
    return str(ocr_pil_image_with_meta(image, lang=lang, config=config)["text"])


def ocr_image(path: Path, *, lang: str | None = None, config: str | None = None) -> str:
    """OCR a standalone image file through the same adaptive path."""
    from PIL import Image

    with Image.open(path) as img:
        return ocr_pil_image(img, lang=lang, config=config)


__all__ = [
    "installed_tesseract_languages",
    "ocr_image",
    "ocr_pil_image",
    "ocr_pil_image_with_meta",
    "resolve_ocr_language",
]
