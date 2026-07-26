from __future__ import annotations

import hashlib
import json
from pathlib import Path
from nutev.extract.pdf_text import (
    extract_pdf_text_pages,
    ocr_cache_signature,
    ocr_scanned_pdf_pages,
    is_probably_pdf_file,
    missing_ocr_dependencies,
)
from nutev.extract.olmocr_backend import ocr_pdf_olmocr


def _ocr_pdf_pages_backend(path: Path, logger) -> tuple[list[str], list[int]]:
    """Dispatch scanned-PDF OCR to the selected backend, always with a safe
    fallback. When NUTEV_OCR_BACKEND=olmocr and a user-provided olmOCR install
    yields text, use it; otherwise fall back to the deterministic Tesseract path.
    """
    olm = ocr_pdf_olmocr(path, logger)
    if olm:
        return olm, []
    return ocr_scanned_pdf_pages(path, logger)


def _sha256_file(path: Path) -> str | None:
    """SHA-256 of a file's bytes, or None if unreadable (for the OCR cache key)."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _ocr_pdf_with_cache(path: Path, ocr_dir: Path, logger) -> tuple[list[str], list[int]]:
    """OCR a scanned PDF, reusing a content-addressed cache when possible.

    The cache is keyed by the file's SHA-256 **and** the OCR settings signature,
    so identical file content OCR'd with the same settings is never re-run (a big
    win when the same guide is mirrored under different names) — and a settings
    change invalidates it, preserving reproducibility. Tesseract is deterministic,
    so a cache hit returns exactly what a fresh run would.
    """
    sha = _sha256_file(path)
    cache_file = None
    if sha:
        cache_file = Path(ocr_dir) / "_ocrcache" / f"{sha}.{ocr_cache_signature()}.pages.json"
        if cache_file.is_file():
            try:
                pages = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(pages, list):
                    logger.info("OCR cache hit path=%s (sha=%s)", path, sha[:12])
                    return [str(p) for p in pages], []
            except Exception:
                logger.debug("cache de OCR corrompido em %s — refazendo OCR", cache_file, exc_info=True)
    pages, failed = _ocr_pdf_pages_backend(path, logger)
    if cache_file is not None and any(p.strip() for p in pages):
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:  # cache write is best-effort
            logger.warning("não consegui gravar cache de OCR %s: %s", cache_file, exc)
    return pages, failed

# Emit the "install OCR prerequisites" guidance at most once per process so a
# corpus of scanned PDFs does not flood the log with the same instruction.
_OCR_DEPS_WARNED = False


def _warn_ocr_setup_once(logger) -> bool:
    """Warn (once) if scanned-PDF OCR prerequisites are missing. Returns True if missing."""
    global _OCR_DEPS_WARNED
    missing = missing_ocr_dependencies()
    if missing and not _OCR_DEPS_WARNED:
        _OCR_DEPS_WARNED = True
        logger.warning(
            "PDF sem texto nativo encontrado, mas o OCR nao esta configurado. "
            "Instale os pre-requisitos para ler PDFs escaneados: %s",
            "; ".join(missing),
        )
    return bool(missing)
from nutev.extract.docx_text import extract_docx_text
from nutev.extract.spreadsheet_text import extract_csv_text, extract_sheet_text
from nutev.extract.html_text import extract_html_text
from nutev.extract.image_ocr import ocr_image


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


# Anti-bot / interstitial / redirect pages that publishers return with HTTP 200
# but which contain no real document. These must NOT be counted as extracted text.
_JUNK_MARKERS = (
    "checking your browser",
    "just a moment",
    "enable javascript",
    "please enable javascript",
    "recaptcha",
    "captcha",
    "verify you are human",
    "are you a robot",
    "attention required",
    "cloudflare",
    "access denied",
    "request has been blocked",
    "ddos protection",
    "security check to access",
    "why have i been blocked",
)

# Minimum characters below which an HTML/text "document" is treated as too thin
# to be a real full text (metadata/landing/redirect stubs).
MIN_MEANINGFUL_CHARS = 400


def looks_like_junk_text(text: str) -> bool:
    """Return True when extracted text is an anti-bot/redirect page or too thin
    to be a real document (e.g. 'Redirecting', 'Checking your browser')."""
    t = (text or "").strip()
    low = t.lower()
    if not t:
        return True
    # Bare redirect/loading stubs.
    if len(t) < 200 and ("redirect" in low or low in {"redirecting", "loading", "loading..."}):
        return True
    # Interstitial/anti-bot pages: a known marker on a short page.
    if len(t) < 3000 and any(marker in low for marker in _JUNK_MARKERS):
        return True
    return False


# Extraction statuses that are only "successful" if the text is real content.
_QUALITY_CHECKED_STATUSES = {"ok", "ok_ocr", "fake_pdf_html", "fake_pdf_text"}


def _raw_contains_junk_markers(path: Path) -> bool:
    """Anti-bot/interstitial pages often carry the marker in raw HTML even when
    readability extracts little visible text."""
    raw = _read_text_safe(path)[:20000].lower()
    return any(marker in raw for marker in _JUNK_MARKERS)


def _extract_html_file(path: Path) -> str:
    raw = _read_text_safe(path)
    payload = extract_html_text(raw)
    return "\n".join(
        [
            payload.get("title", ""),
            *payload.get("headings", []),
            payload.get("body", ""),
        ]
    ).strip()


def _looks_like_html_bytes(path: Path) -> bool:
    try:
        head = path.read_bytes()[:4096].lower()
        return b"<html" in head or b"<!doctype html" in head or b"<body" in head
    except Exception:
        return False


def extract_document(path: Path, ocr_dir: Path, out_dir: Path, logger, *, capture_pages: bool = False) -> dict:
    ext = path.suffix.lower().lstrip(".")
    text = ""
    used_ocr = False
    ocr_failed_pages = []
    extraction_status = "empty"
    pages: list[str] = []

    if ext == "pdf":
        if is_probably_pdf_file(path):
            native_pages = extract_pdf_text_pages(path)
            if "\n".join(native_pages).strip():
                pages = native_pages
                text = "\n".join(native_pages).strip()
                extraction_status = "ok"
            else:
                ocr_pages, ocr_failed_pages = _ocr_pdf_with_cache(path, ocr_dir, logger)
                pages = ocr_pages
                ocr_text = "\n".join(ocr_pages)
                if ocr_text.strip():
                    text = ocr_text
                    used_ocr = True
                    extraction_status = "ok_ocr"
                elif _warn_ocr_setup_once(logger):
                    # Scanned/image-only PDF that could not be OCR'd because the
                    # OCR prerequisites are not installed — flag distinctly so
                    # the user knows this is a setup gap, not an empty document.
                    extraction_status = "pdf_needs_ocr_setup"
                else:
                    extraction_status = "pdf_no_text"
        elif _looks_like_html_bytes(path):
            text = _extract_html_file(path)
            extraction_status = "fake_pdf_html"
        else:
            text = _read_text_safe(path)
            extraction_status = "fake_pdf_text"

    elif ext == "docx":
        text = extract_docx_text(path)
        extraction_status = "ok" if text else "empty"

    elif ext in {"xlsx", "xls"}:
        text, _ = extract_sheet_text(path)
        extraction_status = "ok" if text else "empty"

    elif ext == "csv":
        text, _ = extract_csv_text(path)
        extraction_status = "ok" if text else "empty"

    elif ext in {"html", "htm"}:
        text = _extract_html_file(path)
        extraction_status = "ok" if text else "empty"

    elif ext in {"png", "jpg", "jpeg", "tiff"}:
        try:
            text = ocr_image(path)
            used_ocr = True
            extraction_status = "ok_ocr" if text else "empty"
        except Exception as e:
            logger.warning("OCR falhou para %s: %s", path, e)
            extraction_status = "ocr_fail"

    elif ext == "txt":
        text = _read_text_safe(path)
        extraction_status = "ok" if text else "empty"

    else:
        text = _read_text_safe(path)
        extraction_status = "ok" if text else "empty"

    # Quality gate: reject anti-bot/redirect/interstitial pages and content that
    # is too thin to be a real document. These previously passed as "ok" and
    # polluted the corpus and the extracted-text counts.
    stripped_len = len((text or "").strip())
    is_html_like = ext in {"html", "htm"} or extraction_status == "fake_pdf_html"
    if extraction_status in _QUALITY_CHECKED_STATUSES and looks_like_junk_text(text):
        extraction_status = "junk_or_blocked"
    elif is_html_like and stripped_len < MIN_MEANINGFUL_CHARS and _raw_contains_junk_markers(path):
        # Junk HTML whose visible text extracted thin/empty but whose raw markup
        # is clearly an anti-bot/redirect page.
        extraction_status = "junk_or_blocked"
    elif extraction_status in {"ok", "fake_pdf_html", "fake_pdf_text"} and stripped_len < MIN_MEANINGFUL_CHARS:
        extraction_status = "too_short"

    out_dir.mkdir(parents=True, exist_ok=True)
    ocr_dir.mkdir(parents=True, exist_ok=True)

    # P4 guard: only persist a text file when extraction genuinely produced
    # usable text. Writing a .txt for empty/junk/too-short extractions created
    # silent 11-33 byte files that masked the "no full text" problem. When there
    # is no usable text we write nothing, return an empty text_path, and log it
    # so the failure is visible in 07_logs — never a silent empty artifact.
    text_body = text or ""
    has_usable_text = (
        extraction_status in _QUALITY_CHECKED_STATUSES and bool(text_body.strip())
    )
    if has_usable_text:
        txt_path = out_dir / f"{path.stem}.txt"
        txt_path.write_text(text_body, encoding="utf-8")
        if used_ocr:
            (ocr_dir / f"{path.stem}.txt").write_text(text_body, encoding="utf-8")
        text_path_str = str(txt_path)
    else:
        text_path_str = ""
        logger.info(
            "extração sem texto útil path=%s status=%s chars=%s (nenhum .txt gravado)",
            path,
            extraction_status,
            len(text_body.strip()),
        )

    result = {
        "file": str(path),
        "ext": ext,
        "used_ocr": used_ocr,
        "ocr_failed_pages": ";".join(map(str, ocr_failed_pages)),
        "text_path": text_path_str,
        "chars": len(text_body),
        "extraction_status": extraction_status,
    }
    if capture_pages:
        # Per-page text for page-precise citation. Only populated for PDFs; for
        # single-body formats (HTML/txt) the whole document is page 1.
        result["pages"] = pages if pages else ([text_body] if text_body.strip() else [])
    return result