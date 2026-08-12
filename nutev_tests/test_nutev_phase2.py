from pathlib import Path

from nutev.download.filters import should_download
from nutev.download.naming import build_filename, infer_ext
from nutev.export.metadata_tables import write_metadata_csv
from nutev.extract.html_text import extract_html_text


def test_naming_and_ext():
    fn = build_filename("play", "pubmed", "My Title", "https://x.org/a.pdf", "pdf")
    assert fn.startswith("NTV__play__") and fn.endswith(".pdf")
    assert infer_ext("https://x.org/noext", "application/pdf") == "pdf"


def test_filters():
    assert should_download("https://site.org/guideline-report.html", "html")
    assert not should_download("https://site.org/login", "html")


def test_html_extract_and_export(tmp_path: Path):
    data = extract_html_text("<html><title>T</title><h1>H</h1><p>Body</p></html>")
    assert data["title"] == "T" and "Body" in data["body"]
    out = tmp_path / "meta.csv"
    write_metadata_csv([{"a": 1, "b": 2}], out)
    assert out.exists()
