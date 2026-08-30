from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

import pytest

from nutev.cli import main as cli_main
from nutev.science import WorkbenchIndexError, run_workbench_index


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from article_workbench_data import load_article_detail, load_article_page, workbench_status


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _card(document_id: str, title: str, year: int, provider: str = "pubmed") -> dict:
    return {
        "schema_version": 1,
        "document_id": document_id,
        "record_id": f"nutev-core:{document_id}",
        "cache_key": sha256(f"cache:{document_id}".encode()).hexdigest(),
        "extractor_version": "evidence_excerpt_rule_v1",
        "identity": {
            "title": title,
            "year": year,
            "doi": document_id.removeprefix("doi:"),
            "pmid": None,
            "source_provider": provider,
        },
        "reference": {
            "reference_stub": f"Author. {title}. Journal. {year}.",
            "doi": document_id.removeprefix("doi:"),
        },
        "document_class": "primary_randomized",
        "full_text_status": "retrieved",
        "study_snapshot": {
            "population": ["Adults"],
            "outcome": ["Recovery score"],
        },
        "excerpt_ids": [f"excerpt:{document_id}:main"],
        "result_bundle_ids": [f"result:{document_id}:main"],
        "counts": {"evidence_excerpts": 1, "result_bundles": 1, "semantic_facts": 4},
        "llm_context": {"study_snapshot": {"population": ["Adults"]}},
        "llm_context_chars": 420,
        "token_cost_policy": {
            "external_llm_calls": 0,
            "full_text_sent_to_llm": False,
        },
    }


def _excerpt(document_id: str, text: str) -> dict:
    digest = sha256(text.encode()).hexdigest()
    return {
        "id": f"excerpt:{document_id}:{digest[:8]}",
        "document_id": document_id,
        "kind": "main_result",
        "section": "Results",
        "locator": "section:Results:p3",
        "verbatim_excerpt": text,
        "excerpt_sha256": digest,
        "source_sentence_sha256": digest,
        "source_object_ids": [],
        "semantic_fields": ["outcome", "effect_measure"],
        "priority_score": 12.5,
        "reference": {"doi": document_id.removeprefix("doi:")},
        "status": "machine_candidate",
    }


def _bundle(document_id: str, excerpt_id: str, text: str) -> dict:
    return {
        "id": f"result:{document_id}:main",
        "document_id": document_id,
        "result_kind": "main_result",
        "excerpt_id": excerpt_id,
        "source_sentence_sha256": sha256(text.encode()).hexdigest(),
        "outcomes": ["Recovery score"],
        "effect_measures": ["OR=1.42"],
        "confidence_intervals": ["95% CI 1.05 to 1.92"],
        "p_values": ["p=0.03"],
        "table_references": [],
        "figure_references": [],
        "result_text": text,
        "priority_score": 12.5,
        "reference": {"doi": document_id.removeprefix("doi:")},
        "status": "machine_candidate_not_evidence_claim",
    }


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    cards = [
        _card("doi:10.1000/newer", "Food literacy intervention", 2026),
        _card("doi:10.1000/older", "Nutrition care framework", 2024, "europepmc"),
    ]
    texts = {
        cards[0]["document_id"]: "Food literacy improved recovery (OR=1.42, p=0.03).",
        cards[1]["document_id"]: "The framework improved nutrition care documentation.",
    }
    excerpts = [_excerpt(card["document_id"], texts[card["document_id"]]) for card in cards]
    bundles = [
        _bundle(card["document_id"], excerpt["id"], texts[card["document_id"]])
        for card, excerpt in zip(cards, excerpts, strict=True)
    ]

    excerpts_path = tmp_path / "evidence_excerpts.jsonl"
    bundles_path = tmp_path / "result_bundles.jsonl"
    cards_path = tmp_path / "article_evidence_cards.jsonl"
    manifest_path = tmp_path / "EXCERPT_MANIFEST.json"
    _write_jsonl(excerpts_path, excerpts)
    _write_jsonl(bundles_path, bundles)
    _write_jsonl(cards_path, cards)
    manifest_path.write_text(
        json.dumps(
            {
                "excerpt_type": "NUTEV_EVIDENCE_EXCERPTS_RESULTS",
                "status": "PASS",
                "outputs": {
                    "evidence_excerpts": {"path": str(excerpts_path), "sha256": _sha(excerpts_path)},
                    "result_bundles": {"path": str(bundles_path), "sha256": _sha(bundles_path)},
                    "article_evidence_cards": {"path": str(cards_path), "sha256": _sha(cards_path)},
                },
            }
        ),
        encoding="utf-8",
    )
    return excerpts_path, bundles_path, cards_path, manifest_path


def test_workbench_builds_queryable_index_and_lazy_detail(tmp_path: Path) -> None:
    excerpts, bundles, cards, manifest = _write_inputs(tmp_path)
    output = tmp_path / "workbench"

    result = run_workbench_index(excerpts, bundles, cards, manifest, output)

    assert result["status"] == "COMPLETE"
    assert result["articles"] == 2
    database = output / "evidence_workbench.sqlite"
    assert database.is_file()
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT COUNT(*) FROM article_cards").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM evidence_excerpts").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM result_bundles").fetchone()[0] == 2

    status = workbench_status(output)
    assert status["status"] == "ready"
    assert status["articles"] == 2
    assert status["full_corpus_sent_to_browser"] is False

    first = load_article_page(root=output, limit=1)
    assert first["page_size"] == 1
    assert first["total_filtered"] == 2
    assert first["next_cursor"]
    assert first["articles"][0]["year"] == 2026
    assert "card_json" not in first["articles"][0]

    second = load_article_page(root=output, limit=1, cursor=first["next_cursor"])
    assert second["articles"][0]["year"] == 2024

    filtered = load_article_page(root=output, q="food literacy")
    assert filtered["total_filtered"] == 1
    assert filtered["articles"][0]["document_id"] == "doi:10.1000/newer"

    provider_filtered = load_article_page(root=output, source_provider="europepmc")
    assert provider_filtered["total_filtered"] == 1
    assert provider_filtered["articles"][0]["document_id"] == "doi:10.1000/older"

    detail = load_article_detail("doi:10.1000/newer", root=output)
    assert detail["full_text_in_response"] is False
    assert detail["card"]["identity"]["title"] == "Food literacy intervention"
    assert detail["evidence_excerpts"][0]["kind"] == "main_result"
    assert detail["result_bundles"][0]["effect_measures"] == ["OR=1.42"]


def test_workbench_page_limit_is_hard_capped(tmp_path: Path) -> None:
    excerpts, bundles, cards, manifest = _write_inputs(tmp_path)
    output = tmp_path / "workbench"
    run_workbench_index(excerpts, bundles, cards, manifest, output)
    page = load_article_page(root=output, limit=999)
    assert page["performance"]["max_page_size"] == 100
    assert page["page_size"] == 2


def test_workbench_fails_closed_when_excerpt_source_changes(tmp_path: Path) -> None:
    excerpts, bundles, cards, manifest = _write_inputs(tmp_path)
    excerpts.write_text(excerpts.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(WorkbenchIndexError, match="SHA-256 mismatch"):
        run_workbench_index(excerpts, bundles, cards, manifest, tmp_path / "workbench")


def test_cli_science_workbench_index(tmp_path: Path, capsys) -> None:
    excerpts, bundles, cards, manifest = _write_inputs(tmp_path)
    output = tmp_path / "workbench"
    code = cli_main(
        [
            "science-workbench-index",
            "--excerpts-jsonl",
            str(excerpts),
            "--result-bundles-jsonl",
            str(bundles),
            "--article-cards-jsonl",
            str(cards),
            "--excerpt-manifest",
            str(manifest),
            "--output-dir",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert '"mode": "NUTEV_ARTICLE_WORKBENCH_INDEX"' in captured.out
    assert '"articles": 2' in captured.out
