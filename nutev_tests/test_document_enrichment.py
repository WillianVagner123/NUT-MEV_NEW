from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

import nutev.science.enrichment as enrichment_module
from nutev.cli import main as cli_main
from nutev.science import (
    DocumentEnrichmentError,
    ExtractionMethod,
    RetrievalStatus,
    run_document_enrichment,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_documents(tmp_path: Path) -> tuple[Path, Path]:
    documents = tmp_path / "document_candidates.jsonl"
    row = {
        "id": "doi:10.1000/enrich.1",
        "source_provider": "pubmed",
        "title": "Nutrition intervention study",
        "doi": "10.1000/enrich.1",
        "pmid": "12345678",
        "url": "https://example.org/article",
        "year": 2025,
        "metadata": {
            "abstract": (
                "This randomized controlled trial evaluated a nutrition intervention "
                "in adults with n=42 participants."
            ),
            "journal": "Example Journal",
            "authors": "A Author; B Author",
            "article_type": "Journal Article",
            "reference_rank": 1,
            "reference_score": 99.0,
            "reference_tier": "A_TOP_REFERENCE",
        },
    }
    documents.write_text(json.dumps(row) + "\n", encoding="utf-8")
    manifest = tmp_path / "SCIENTIFIC_EXPORT_MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "export_type": "NUTEV_SCIENTIFIC_OBJECT_EXPORT",
                "status": "PASS",
                "outputs": {
                    "document_candidates": {
                        "path": str(documents),
                        "sha256": _sha(documents),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return documents, manifest


def _read_one(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8").strip())


def test_enrichment_falls_back_to_abstract_without_fabricating_full_text(tmp_path: Path):
    documents, manifest = _write_documents(tmp_path)
    output = tmp_path / "enrichment"

    result = run_document_enrichment(documents, manifest, output)

    assert result["status"] == "COMPLETE"
    assert result["abstract_only"] == 1
    dossier = _read_one(output / "reviewer_dossiers.jsonl")
    enrichment = _read_one(output / "document_enrichments.jsonl")
    artifact = _read_one(output / "full_text_artifacts.jsonl")

    assert dossier["extraction_method"] == "abstract_only"
    assert dossier["full_text_status"] == "not_attempted"
    assert dossier["guardrails"]["blind_to_nutev_rank"] is True
    assert dossier["guardrails"]["blind_to_nutev_taxonomy"] is True
    assert "reference_rank" not in dossier
    assert "reference_score" not in dossier
    assert "taxonomy" not in dossier
    assert "randomized controlled trial" in dossier["content_signals"]["study_design_signals"]
    assert "n=42" in dossier["content_signals"]["sample_size_mentions"]
    assert "full_text_unavailable_using_abstract_only" in enrichment["warnings"]
    assert artifact["retrieval_status"] == "not_attempted"


def test_enrichment_extracts_local_html_and_builds_section_map(tmp_path: Path):
    documents, manifest = _write_documents(tmp_path)
    html = tmp_path / "article.html"
    html.write_text(
        """
        <html><body>
          <h1>Introduction</h1>
          <p>Nutrition behavior and adherence were evaluated.</p>
          <h2>Methods</h2>
          <p>This randomized controlled trial enrolled n=84 adults.</p>
          <h2>Results</h2>
          <p>Table 1 summarizes baseline data. Figure 1 shows the primary outcome.</p>
          <h2>Conclusion</h2>
          <p>The intervention changed dietary behavior.</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    assets = tmp_path / "assets.jsonl"
    assets.write_text(
        json.dumps(
            {
                "document_id": "doi:10.1000/enrich.1",
                "path": str(html),
                "media_type": "text/html",
                "scope": "full_text",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "enrichment"

    result = run_document_enrichment(
        documents,
        manifest,
        output,
        assets_jsonl=assets,
    )

    assert result["abstract_only"] == 0
    dossier = _read_one(output / "reviewer_dossiers.jsonl")
    assert dossier["full_text_status"] == "retrieved"
    assert dossier["extraction_method"] == "html_text"
    assert dossier["ocr_used"] is False
    headings = [item["heading"] for item in dossier["section_map"]]
    assert "Introduction" in headings
    assert "Methods" in headings
    assert "Results" in headings
    assert "Conclusion" in headings
    assert "Table 1" in dossier["content_signals"]["table_mentions"]
    assert "Figure 1" in dossier["content_signals"]["figure_mentions"]
    assert "n=84" in dossier["content_signals"]["sample_size_mentions"]
    assert (output / "private_text").is_dir()
    assert (output / "ENRICHMENT_MANIFEST.json").is_file()


def test_enrichment_rejects_asset_for_unknown_document(tmp_path: Path):
    documents, manifest = _write_documents(tmp_path)
    asset_file = tmp_path / "article.txt"
    asset_file.write_text("Methods\nExample", encoding="utf-8")
    assets = tmp_path / "assets.jsonl"
    assets.write_text(
        json.dumps(
            {
                "document_id": "doi:10.1000/unknown",
                "path": str(asset_file),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DocumentEnrichmentError, match="unknown document"):
        run_document_enrichment(
            documents,
            manifest,
            tmp_path / "enrichment",
            assets_jsonl=assets,
        )


def test_private_ip_is_rejected_before_network_fetch():
    with pytest.raises(DocumentEnrichmentError, match="private/link-local"):
        enrichment_module._validate_remote_url("http://127.0.0.1/article.pdf")


def test_pdf_content_type_is_classified_as_full_text():
    status = enrichment_module._artifact_scope(
        "https://doi.org/10.1000/example",
        None,
        "application/pdf",
    )
    assert status is RetrievalStatus.RETRIEVED


def test_pdf_extraction_reports_missing_ocr_backends(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    fake_pdf = tmp_path / "scan.pdf"
    fake_pdf.write_bytes(b"not-a-real-pdf")
    monkeypatch.setattr(enrichment_module.shutil, "which", lambda _name: None)

    text, method, ocr_used, ocr_engine, warnings = enrichment_module._extract_pdf(fake_pdf)

    assert text == ""
    assert method is ExtractionMethod.UNAVAILABLE
    assert ocr_used is False
    assert ocr_engine is None
    assert "pdftotext_unavailable_ocr_attempted" in warnings
    assert any(item.startswith("ocr_backend_unavailable:") for item in warnings)


def test_cli_science_enrich_builds_reviewer_dossier(tmp_path: Path, capsys):
    documents, manifest = _write_documents(tmp_path)
    output = tmp_path / "enrichment"

    code = cli_main(
        [
            "science-enrich",
            "--documents-jsonl",
            str(documents),
            "--science-manifest",
            str(manifest),
            "--output-dir",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert '"mode": "PRE_SCREENING_DOCUMENT_ENRICHMENT"' in captured.out
    assert (output / "reviewer_dossiers.jsonl").is_file()


def test_cli_screening_requires_verified_enrichment_by_default(tmp_path: Path, capsys):
    documents, manifest = _write_documents(tmp_path)
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(
        json.dumps(
            {
                "id": "decision-1",
                "document_id": "doi:10.1000/enrich.1",
                "stage": "title_abstract",
                "decision": "include",
                "decided_at": "2026-08-26T20:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    code = cli_main(
        [
            "science-screening",
            "--documents-jsonl",
            str(documents),
            "--science-manifest",
            str(manifest),
            "--decisions-jsonl",
            str(decisions),
            "--dossiers-jsonl",
            str(tmp_path / "missing-dossiers.jsonl"),
            "--enrichment-manifest",
            str(tmp_path / "missing-enrichment.json"),
            "--output-dir",
            str(tmp_path / "screening"),
        ]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "Scientific screening import failure" in captured.out


def test_cli_screening_accepts_decision_after_verified_dossier(tmp_path: Path, capsys):
    documents, manifest = _write_documents(tmp_path)
    enrichment_dir = tmp_path / "enrichment"
    run_document_enrichment(documents, manifest, enrichment_dir)

    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(
        json.dumps(
            {
                "id": "decision-1",
                "document_id": "doi:10.1000/enrich.1",
                "stage": "title_abstract",
                "decision": "include",
                "decided_at": "2026-08-26T20:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    screening_dir = tmp_path / "screening"

    code = cli_main(
        [
            "science-screening",
            "--documents-jsonl",
            str(documents),
            "--science-manifest",
            str(manifest),
            "--dossiers-jsonl",
            str(enrichment_dir / "reviewer_dossiers.jsonl"),
            "--enrichment-manifest",
            str(enrichment_dir / "ENRICHMENT_MANIFEST.json"),
            "--decisions-jsonl",
            str(decisions),
            "--output-dir",
            str(screening_dir),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert '"pre_screening_enrichment_required": true' in captured.out
    assert (screening_dir / "SCREENING_IMPORT_MANIFEST.json").is_file()
