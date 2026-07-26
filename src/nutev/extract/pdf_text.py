from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from nutev.extract.image_ocr import ocr_pil_image

logger = logging.getLogger("nutev.extract.pdf_text")


def _ocr_max_pages() -> int:
    """Optional cap on pages OCR'd per PDF (env NUTEV_OCR_MAX_PAGES; 0 = all).

    Guards against a single huge scan monopolizing the batch. Default 0 keeps the
    behavior unchanged; set e.g. NUTEV_OCR_MAX_PAGES=150 to bound very long PDFs.
    """
    try:
        return max(0, int(os.environ.get("NUTEV_OCR_MAX_PAGES", "0") or 0))
    except ValueError:
        return 0


def _has_pymupdf() -> bool:
    """Whether PyMuPDF (fitz) is importable — a pip-only alternative to poppler."""
    try:
        import fitz  # noqa: F401  (PyMuPDF)

        return True
    except Exception:
        return False


def _has_poppler() -> bool:
    return shutil.which("pdftoppm") is not None or shutil.which("pdftocairo") is not None


def missing_ocr_dependencies() -> list[str]:
    """Return human-readable names of OCR prerequisites that are unavailable.

    Scanned/image-only PDFs need two capabilities: rendering the page to an
    image, and reading text from that image (OCR).

    - Rendering works with **PyMuPDF** (``pip install pymupdf`` — no system
      program needed) OR with ``pdf2image`` + the system ``poppler``. Only when
      *neither* path is available do we ask the user to install something.
    - OCR needs ``pytesseract`` (pip) plus the ``tesseract`` system program.

    When any are missing, extraction silently yields no text; this lets the
    pipeline report *why* and tell the user exactly what to install instead of
    masking it as an empty PDF.
    """
    missing: list[str] = []
    # Rendering: satisfied by PyMuPDF alone, or by pdf2image + poppler.
    try:
        import pdf2image  # noqa: F401

        has_pdf2image = True
    except Exception:
        has_pdf2image = False
    if not _has_pymupdf() and not (has_pdf2image and _has_poppler()):
        missing.append('PDF rendering: pip install pymupdf (no system install), OR pdf2image + poppler')
    # OCR engine.
    try:
        import pytesseract  # noqa: F401
    except Exception:
        missing.append('pytesseract (pip install -e ".[documents]")')
    if shutil.which("tesseract") is None:
        missing.append("tesseract (system package: apt install tesseract-ocr / brew install tesseract / Windows tesseract build)")
    return missing


def is_probably_pdf_file(path: Path) -> bool:
    try:
        header = path.read_bytes()[:8]
        return header.startswith(b"%PDF-")
    except Exception:
        return False


def extract_pdf_text(path: Path) -> tuple[str, bool]:
    if not is_probably_pdf_file(path):
        return "", False

    try:
        import pypdf
        reader = pypdf.PdfReader(str(path), strict=False)
        txt = "\n".join((p.extract_text() or "") for p in reader.pages).strip()
        return txt, bool(txt)
    except Exception:
        return "", False


def extract_pdf_text_pages(path: Path) -> list[str]:
    """Return native (non-OCR) text per page, or [] if unreadable."""
    if not is_probably_pdf_file(path):
        return []
    try:
        import pypdf

        reader = pypdf.PdfReader(str(path), strict=False)
        return [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:
        # Native text failing here is normal for scanned PDFs (OCR follows), but
        # log it so a genuinely corrupt/unreadable file is not silently counted
        # as "no text" with no trace.
        logger.warning("native PDF text extraction failed, falling back: path=%s error=%s", path, exc)
        return []


def _render_pdf_pages(path: Path, dpi: int = 300):
    """Yield PDF pages as PIL images at ``dpi``, one at a time (render on demand).

    A generator so only one page image is held in memory at once — a big scanned
    guide no longer materializes every page bitmap up front. Prefers PyMuPDF
    (pip-only); falls back to pdf2image + poppler. Raises if no renderer exists.
    """
    if _has_pymupdf():
        import fitz  # PyMuPDF
        from PIL import Image

        with fitz.open(str(path)) as doc:
            for page in doc:
                # alpha=False keeps 3 (RGB) or 1 (grayscale) bytes/pixel; picking
                # the PIL mode from pix.n avoids a frombytes ValueError on
                # grayscale/CMYK pages (which would silently abort OCR).
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                mode = "RGB" if pix.n >= 3 else "L"
                yield Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        return
    # Fallback: pdf2image needs the system poppler binaries.
    from pdf2image import convert_from_path

    yield from convert_from_path(str(path), dpi=dpi)


# OCR minimum useful length and the minimum share of alphabetic characters below
# which the output is treated as garbage (a scanned page that rendered/OCR'd
# poorly typically yields either almost nothing or a soup of symbols).
_OCR_MIN_CHARS = 40
_OCR_MIN_ALPHA_RATIO = 0.35


def ocr_output_looks_failed(text: str) -> bool:
    """Heuristic failure detector for a page/doc's OCR output."""
    s = (text or "").strip()
    if len(s) < _OCR_MIN_CHARS:
        return True
    alpha = sum(c.isalpha() for c in s)
    return (alpha / len(s)) < _OCR_MIN_ALPHA_RATIO


def _ocr_pages_at_dpi(path: Path, dpi: int, logger) -> tuple[list[str], list[int]]:
    """OCR every page at ``dpi``; return (per-page texts, failed page numbers).

    Resilient: a single page that fails to *render* (corrupt/unsupported page) is
    skipped instead of aborting the whole document — earlier pages are kept. A
    failure on the very first page (no renderer / unreadable PDF) is re-raised so
    the caller can retry at a higher DPI or flag the OCR-setup gap. Honors the
    optional per-PDF page cap.
    """
    max_pages = _ocr_max_pages()
    failed: list[int] = []
    texts: list[str] = []
    gen = _render_pdf_pages(path, dpi=dpi)
    page_no = 0
    while True:
        if max_pages and page_no >= max_pages:
            logger.info("OCR: limite de %d páginas atingido em %s", max_pages, path)
            break
        try:
            img = next(gen)
        except StopIteration:
            break
        except Exception:
            if page_no == 0:
                raise  # no renderer / cannot open — let ocr_scanned_pdf_pages handle it
            logger.warning("OCR: página %d de %s falhou ao renderizar (pulada)", page_no + 1, path)
            failed.append(page_no + 1)
            texts.append("")
            page_no += 1
            continue
        page_no += 1
        try:
            texts.append(ocr_pil_image(img))
        except Exception:
            failed.append(page_no)
            texts.append("")
    return texts, failed


def _ocr_at_dpi(path: Path, dpi: int, logger) -> tuple[str, list[int]]:
    texts, failed = _ocr_pages_at_dpi(path, dpi, logger)
    return "\n".join(texts), failed


# DPI ladder for OCR: 300 DPI is the accepted floor for reliable OCR; a weak
# first pass retries at 450 (finer scans, small type) before giving up.
_OCR_DPI_LADDER = (300, 450)


def ocr_scanned_pdf_pages(path: Path, logger) -> tuple[list[str], list[int]]:
    """OCR a scanned PDF and return per-page text (for page-precise citations).

    Renders at 300 DPI; if the joined output looks failed (too short / mostly
    non-alphabetic), retries once at 450 DPI and keeps the better pass.
    """
    if not is_probably_pdf_file(path):
        return [], [0]

    pages: list[str] = []
    failed: list[int] = [0]
    for attempt, dpi in enumerate(_OCR_DPI_LADDER, start=1):
        try:
            pages, failed = _ocr_pages_at_dpi(path, dpi, logger)
        except Exception as e:
            logger.warning("Falha ao renderizar PDF para OCR %s (dpi=%s): %s", path, dpi, e)
            continue
        if not ocr_output_looks_failed("\n".join(pages)):
            return pages, failed
        logger.info(
            "OCR fraco em %s (dpi=%s, chars=%s) — %s",
            path, dpi, len("\n".join(pages).strip()),
            "tentando DPI maior" if attempt < len(_OCR_DPI_LADDER) else "sem melhora",
        )
    return pages, failed


def ocr_scanned_pdf(path: Path, logger) -> tuple[str, list[int]]:
    """OCR a scanned PDF into a single joined string (see ``ocr_scanned_pdf_pages``)."""
    pages, failed = ocr_scanned_pdf_pages(path, logger)
    return "\n".join(pages), failed


def ocr_cache_signature() -> str:
    """Short hash of the OCR settings (language, engine config, DPI ladder).

    A content-addressed OCR cache is only safe to reuse when these are unchanged,
    so the cache key includes this signature — changing NUTEV_OCR_LANG /
    NUTEV_OCR_CONFIG (or the DPI ladder) automatically invalidates old entries.
    """
    import hashlib
    import os

    from nutev.extract.image_ocr import _DEFAULT_CONFIG, _DEFAULT_LANG

    # The selected OCR backend is part of the settings: switching to/from olmOCR
    # must invalidate the Tesseract-produced cache (different engine, different
    # output), so it is folded into the signature.
    backend = os.environ.get("NUTEV_OCR_BACKEND", "tesseract").strip().lower()
    raw = f"{backend}|{_DEFAULT_LANG}|{_DEFAULT_CONFIG}|{_OCR_DPI_LADDER}".encode()
    return hashlib.sha1(raw).hexdigest()[:10]  # noqa: S324  (cache key, not security)