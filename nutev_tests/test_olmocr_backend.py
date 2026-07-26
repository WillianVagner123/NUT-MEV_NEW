"""Optional olmOCR OCR backend: opt-in selection, availability, and safe
fallback to the deterministic Tesseract path. No GPU / real olmOCR is ever
invoked — the subprocess boundary and the availability probe are mocked.
"""
from __future__ import annotations

import logging

import nutev.extract.olmocr_backend as ob
import nutev.extract.smart_extract as se
from nutev.extract.pdf_text import ocr_cache_signature

_LOG = logging.getLogger("test")


class _Proc:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


# --------------------------------------------------------------------------- #
# Selection + availability
# --------------------------------------------------------------------------- #

def test_default_backend_is_tesseract(monkeypatch):
    monkeypatch.delenv("NUTEV_OCR_BACKEND", raising=False)
    assert ob.olmocr_selected() is False


def test_selected_when_env_set(monkeypatch):
    monkeypatch.setenv("NUTEV_OCR_BACKEND", "olmocr")
    assert ob.olmocr_selected() is True


def test_skip_env_forces_unavailable(monkeypatch):
    monkeypatch.setenv("NUTEV_SKIP_OLMOCR", "1")
    monkeypatch.setattr(ob.shutil, "which", lambda _: "/usr/bin/olmocr")
    assert ob.olmocr_available() is False


# --------------------------------------------------------------------------- #
# ocr_pdf_olmocr — returns None (=> fall back) unless selected+available+ok
# --------------------------------------------------------------------------- #

def test_returns_none_when_not_selected(monkeypatch, tmp_path):
    monkeypatch.delenv("NUTEV_OCR_BACKEND", raising=False)
    # subprocess must never be called when the backend isn't selected.
    monkeypatch.setattr(ob.subprocess, "run", lambda *a, **k: pytest_fail())
    assert ob.ocr_pdf_olmocr(tmp_path / "x.pdf", _LOG) is None


def test_returns_none_when_selected_but_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("NUTEV_OCR_BACKEND", "olmocr")
    monkeypatch.setattr(ob, "olmocr_available", lambda: False)
    assert ob.ocr_pdf_olmocr(tmp_path / "x.pdf", _LOG) is None


def test_returns_markdown_when_available_and_ok(monkeypatch, tmp_path):
    monkeypatch.setenv("NUTEV_OCR_BACKEND", "olmocr")
    monkeypatch.setattr(ob, "olmocr_available", lambda: True)
    monkeypatch.setattr(ob, "read_markdown", lambda ws: "## Title\n\nExtracted body text.")
    monkeypatch.setattr(ob.subprocess, "run", lambda *a, **k: _Proc(returncode=0))
    out = ob.ocr_pdf_olmocr(tmp_path / "x.pdf", _LOG)
    assert out == ["## Title\n\nExtracted body text."]


def test_nonzero_returncode_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("NUTEV_OCR_BACKEND", "olmocr")
    monkeypatch.setattr(ob, "olmocr_available", lambda: True)
    monkeypatch.setattr(ob.subprocess, "run", lambda *a, **k: _Proc(returncode=1, stderr="boom"))
    assert ob.ocr_pdf_olmocr(tmp_path / "x.pdf", _LOG) is None


def test_empty_markdown_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("NUTEV_OCR_BACKEND", "olmocr")
    monkeypatch.setattr(ob, "olmocr_available", lambda: True)
    monkeypatch.setattr(ob, "read_markdown", lambda ws: "   ")
    monkeypatch.setattr(ob.subprocess, "run", lambda *a, **k: _Proc(returncode=0))
    assert ob.ocr_pdf_olmocr(tmp_path / "x.pdf", _LOG) is None


def test_subprocess_exception_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("NUTEV_OCR_BACKEND", "olmocr")
    monkeypatch.setattr(ob, "olmocr_available", lambda: True)

    def _boom(*a, **k):
        raise TimeoutError("olmocr hung")

    monkeypatch.setattr(ob.subprocess, "run", _boom)
    assert ob.ocr_pdf_olmocr(tmp_path / "x.pdf", _LOG) is None


# --------------------------------------------------------------------------- #
# read_markdown — globs the workspace robustly
# --------------------------------------------------------------------------- #

def test_read_markdown_prefers_markdown_subdir(tmp_path):
    ws = tmp_path / "ws"
    (ws / "markdown").mkdir(parents=True)
    (ws / "markdown" / "doc.md").write_text("# From markdown dir", encoding="utf-8")
    assert "From markdown dir" in ob.read_markdown(ws)


def test_read_markdown_empty_when_nothing(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    assert ob.read_markdown(ws) == ""


# --------------------------------------------------------------------------- #
# Seam + cache signature
# --------------------------------------------------------------------------- #

def test_backend_dispatch_uses_olmocr_then_tesseract(monkeypatch, tmp_path):
    # olmOCR yields text -> Tesseract must not be called.
    monkeypatch.setattr(se, "ocr_pdf_olmocr", lambda p, log: ["olm text"])
    monkeypatch.setattr(se, "ocr_scanned_pdf_pages", lambda p, log: (_ for _ in ()).throw(AssertionError("tesseract called")))
    pages, failed = se._ocr_pdf_pages_backend(tmp_path / "x.pdf", _LOG)
    assert pages == ["olm text"] and failed == []


def test_backend_dispatch_falls_back_to_tesseract(monkeypatch, tmp_path):
    monkeypatch.setattr(se, "ocr_pdf_olmocr", lambda p, log: None)
    monkeypatch.setattr(se, "ocr_scanned_pdf_pages", lambda p, log: (["tess text"], []))
    pages, failed = se._ocr_pdf_pages_backend(tmp_path / "x.pdf", _LOG)
    assert pages == ["tess text"]


def test_cache_signature_changes_with_backend(monkeypatch):
    monkeypatch.delenv("NUTEV_OCR_BACKEND", raising=False)
    tesseract_sig = ocr_cache_signature()
    monkeypatch.setenv("NUTEV_OCR_BACKEND", "olmocr")
    assert ocr_cache_signature() != tesseract_sig


def pytest_fail():
    raise AssertionError("subprocess.run must not be called")
