from pathlib import Path
from unittest.mock import Mock

from nutev.download.downloader import _request_with_retry as _get_with_retry_response
from nutev.extract.smart_extract import extract_document


def test_retry_logic():
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.status_code = 200
    response.content = b"abc"
    session.get.side_effect = [Exception("x"), response]

    out = _get_with_retry_response(session, "http://x", Mock(), retries=2)
    assert out.content == b"abc"


def test_ocr_fallback_smoke(tmp_path: Path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    result = extract_document(pdf, tmp_path / "ocr", tmp_path / "ext", Mock())
    assert "extraction_status" in result
