from __future__ import annotations

import json
from pathlib import Path

import nutev.pipelines.article1_formal_pipeline as formal


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_formal_chain_runs_all_computational_stages_and_then_resumes(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    version = {
        "strategy_id": "article1",
        "version_id": "formal-v1",
        "version": 1,
        "search_type": "FORMAL",
        "prisma_eligible": True,
        "checksum_sha256": "a" * 64,
    }
    calls = {
        "execute": 0,
        "corpus": 0,
        "resolve": 0,
        "download": 0,
        "extract": 0,
        "bundle": 0,
    }

    monkeypatch.setattr(formal, "list_strategy_versions", lambda db, limit=100: [version])

    def fake_execute(root: Path, **kwargs):
        calls["execute"] += 1
        assert kwargs["version_id"] == "formal-v1"
        assert kwargs["resume"] is True
        return {
            "status": "SUCCEEDED",
            "run_id": "formal-run-1",
            "formal_authorization": {"authorized": True, "freeze_id": "freeze-1"},
        }

    monkeypatch.setattr(formal, "execute_strategy_version", fake_execute)

    master_path = project / "03_corpus" / "master.jsonl"

    def fake_corpus(root: Path, *, run_id: str):
        calls["corpus"] += 1
        assert run_id == "formal-run-1"
        _write_jsonl(
            master_path,
            [
                {
                    "document_id": "doc-1",
                    "title": "Lifestyle nutrition guideline",
                    "abstract": "Guidance for health and nutrition.",
                    "language": "en",
                    "source_provider": "pubmed",
                },
                {
                    "document_id": "doc-2",
                    "title": "Guia de alimentação",
                    "abstract": "Recomendações de alimentação e saúde.",
                    "language": "pt",
                    "source_provider": "pubmed",
                },
            ],
        )
        return {
            "status": "SUCCEEDED",
            "build_id": "corpus-1",
            "master_jsonl_path": str(master_path),
        }

    monkeypatch.setattr(formal, "build_corpus_from_search_run", fake_corpus)

    def fake_resolve(rows, **kwargs):
        calls["resolve"] += 1
        assert len(rows) == 2
        return [
            {
                **row,
                "url": f"https://metadata.test/{row['document_id']}",
                "fulltext_status": "fulltext_oa",
                "fulltext_url": f"https://oa.test/{row['document_id']}.pdf",
            }
            for row in rows
        ]

    monkeypatch.setattr(formal, "resolve_many", fake_resolve)

    def fake_download(records, public_dir, official_dir, logger):
        calls["download"] += 1
        out = []
        for record in records:
            document_id = str(record["document_id"])
            path = project / "downloads" / f"{document_id}.pdf"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"%PDF-1.4 deterministic fixture")
            out.append(
                {
                    "url": record["url"],
                    "path": str(path),
                    "status": "ok",
                }
            )
        return out, []

    monkeypatch.setattr(formal, "download_records", fake_download)

    def fake_extract(path: Path, ocr_dir: Path, extraction_dir: Path, logger, *, capture_pages: bool):
        calls["extract"] += 1
        assert capture_pages is True
        text_path = project / "texts" / f"{path.stem}.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        if path.stem == "doc-2":
            text_path.write_text(
                "Este documento apresenta recomendações para alimentação, saúde e estilo de vida.",
                encoding="utf-8",
            )
        else:
            text_path.write_text(
                "This document presents recommendations for health, nutrition and lifestyle.",
                encoding="utf-8",
            )
        return {
            "file": str(path),
            "used_ocr": path.stem == "doc-2",
            "text_path": str(text_path),
            "chars": len(text_path.read_text(encoding="utf-8")),
            "extraction_status": "ok_ocr" if path.stem == "doc-2" else "ok",
        }

    monkeypatch.setattr(formal, "extract_document", fake_extract)

    bundle_path = project / "03_corpus" / "document_bundles" / "document_bundles.jsonl"

    def fake_bundle(root: Path, **kwargs):
        calls["bundle"] += 1
        assert len(kwargs["master_rows"]) == 2
        assert len(kwargs["extraction_manifest"]) == 2
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text("{}\n", encoding="utf-8")
        return {
            "bundle_path": str(bundle_path),
            "bundle_count": 2,
            "bundle_sha256": "b" * 64,
        }

    monkeypatch.setattr(formal, "build_document_bundle_index", fake_bundle)
    monkeypatch.setattr(
        formal,
        "list_execution_artifacts",
        lambda db, run_id: [
            {
                "provider": "pubmed",
                "provider_status": "completed",
                "records_returned": 2,
                "total_found": 2,
                "snapshot_path": "snapshot.json",
                "snapshot_sha256": "c" * 64,
                "exact_expression": "diet AND guideline",
            }
        ],
    )

    progress: list[str] = []
    summary = formal.run_or_resume_formal_chain(project, progress_fn=progress.append)

    assert summary["status"]["execution_status"] == "COMPLETE"
    assert summary["status"]["formal_freeze_authorized"] is True
    assert summary["status"]["prisma_eligible"] is True
    assert summary["human_review"]["automatic_include_exclude_decisions"] == 0
    assert summary["corpus"]["unique_records"] == 2
    assert summary["fulltext"]["downloaded"] == 2
    assert summary["extraction"]["processed"] == 2
    assert summary["extraction"]["ocr_used"] == 1
    assert calls == {
        "execute": 1,
        "corpus": 1,
        "resolve": 1,
        "download": 1,
        "extract": 2,
        "bundle": 1,
    }
    assert any("FORMAL 6/6" in item for item in progress)

    extraction_rows = [
        json.loads(line)
        for line in Path(summary["artifacts"]["extraction_manifest_path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    by_document = {row["document_id"]: row for row in extraction_rows}
    assert by_document["doc-1"]["language_detected"] == "en"
    assert by_document["doc-2"]["language_detected"] == "pt"

    # A second invocation must reuse search/corpus/fulltext/download/extraction.
    monkeypatch.setattr(
        formal,
        "get_search_run",
        lambda db, run_id: {
            "run_id": run_id,
            "status": "SUCCEEDED",
            "manifest_path": str(project / "search_manifest.json"),
        },
    )
    (project / "search_manifest.json").write_text(
        json.dumps({"formal_authorization": {"authorized": True, "freeze_id": "freeze-1"}}),
        encoding="utf-8",
    )

    progress.clear()
    resumed = formal.run_or_resume_formal_chain(project, progress_fn=progress.append)
    assert resumed["status"]["execution_status"] == "COMPLETE"
    assert calls["execute"] == 1
    assert calls["corpus"] == 1
    assert calls["resolve"] == 1
    assert calls["download"] == 1
    assert calls["extract"] == 2
    assert calls["bundle"] == 2
    assert any("checkpoint da busca reutilizado" in item for item in progress)
    assert any("checkpoint do corpus reutilizado" in item for item in progress)


def test_formal_chain_refuses_to_guess_a_formal_strategy(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(formal, "list_strategy_versions", lambda db, limit=100: [])
    try:
        formal.run_or_resume_formal_chain(tmp_path)
    except RuntimeError as exc:
        assert "não cria uma estratégia formal" in str(exc)
    else:  # pragma: no cover - guard against accidental authorization regression
        raise AssertionError("FORMAL chain should refuse a missing strategy")
