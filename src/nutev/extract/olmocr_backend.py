"""Optional olmOCR extraction backend (opt-in, off by default).

olmOCR (github.com/allenai/olmocr, Apache-2.0 *code*) converts PDFs to clean
Markdown with a Qwen2.5-VL model. It is heavy, GPU-bound, and — unlike Tesseract —
**non-deterministic**, so it is strictly opt-in via ``NUTEV_OCR_BACKEND=olmocr``
and *always* falls back to the deterministic Tesseract path when unavailable or on
any error.

NutEV ships **no model weights**: the user installs ``olmocr`` themselves and is
responsible for reviewing the model's weight license. This module only shells out
to that user-provided install, so nothing about the weights' license flows into
this repository. Treat olmOCR output as *assistive* extraction (human review
still governs), and note in reproducibility reporting that it is not byte-stable.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def olmocr_selected() -> bool:
    """True when the operator opted into the olmOCR backend."""
    return os.environ.get("NUTEV_OCR_BACKEND", "tesseract").strip().lower() == "olmocr"


def olmocr_available() -> bool:
    """True when a user-provided ``olmocr`` install can be invoked.

    ``NUTEV_SKIP_OLMOCR=1`` force-disables it (e.g. CI, or to pin the
    deterministic path) regardless of what is installed.
    """
    if os.environ.get("NUTEV_SKIP_OLMOCR") == "1":
        return False
    if shutil.which("olmocr"):
        return True
    try:
        import olmocr  # noqa: F401
        return True
    except Exception:
        return False


def _olmocr_cmd(workspace: Path, path: Path) -> list[str]:
    """The documented olmOCR invocation, preferring the CLI, else the module."""
    if shutil.which("olmocr"):
        return ["olmocr", str(workspace), "--markdown", "--pdfs", str(path)]
    return [sys.executable, "-m", "olmocr.pipeline", str(workspace), "--markdown", "--pdfs", str(path)]


def _timeout_seconds() -> int:
    raw = os.environ.get("NUTEV_OLMOCR_TIMEOUT", "600")
    return int(raw) if raw.isdigit() and int(raw) > 0 else 600


def read_markdown(workspace: Path) -> str:
    """Join every Markdown file olmOCR wrote under the workspace (``markdown/``
    subdir first, then anywhere) into a single string. Robust to the exact output
    layout: if nothing usable is found, returns ``''`` so the caller falls back."""
    for root in (workspace / "markdown", workspace):
        if not root.is_dir():
            continue
        parts: list[str] = []
        for md in sorted(root.rglob("*.md")):
            try:
                parts.append(md.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
        joined = "\n\n".join(p for p in parts if p.strip()).strip()
        if joined:
            return joined
    return ""


def ocr_pdf_olmocr(path: Path, logger) -> list[str] | None:
    """Run olmOCR on a PDF and return its Markdown as a single page.

    Returns ``None`` to signal the caller to fall back to Tesseract — when the
    backend is not selected, not available, times out, exits non-zero, or yields
    no text. Never raises: every failure degrades to the deterministic path.

    The result is a single "page" (whole-document Markdown); olmOCR does not
    expose a stable per-page split here, so page-precise citation falls back to
    document level for olmOCR-extracted PDFs (documented trade-off).
    """
    if not olmocr_selected() or not olmocr_available():
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="nutev-olmocr-") as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir(parents=True, exist_ok=True)
            proc = subprocess.run(  # noqa: S603 (fixed, non-shell argv)
                _olmocr_cmd(workspace, path),
                capture_output=True,
                text=True,
                timeout=_timeout_seconds(),
            )
            if proc.returncode != 0:
                logger.warning(
                    "olmOCR retornou %s para %s — fallback Tesseract: %s",
                    proc.returncode, path, (proc.stderr or "")[-500:],
                )
                return None
            text = read_markdown(workspace)
            if not text.strip():
                logger.info("olmOCR não produziu markdown para %s — fallback Tesseract", path)
                return None
            return [text]
    except Exception as exc:
        logger.warning("olmOCR falhou para %s: %s — fallback Tesseract", path, exc)
        return None
