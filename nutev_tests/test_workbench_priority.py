from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

from nutev.science.workbench import run_workbench_index
from nutev.science.workbench_priority import augment_workbench_priority


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from article_workbench_data import load_article_detail, load_article_page, workbench_status


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _card(document_id: str, title: str, year: int, provider: str) -> dict:
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
        "document_class": "guidance",
        "full_text_status": "not_attempted",
        "study_snapshot": {"objective": ["Test objective"]},
        "excerpt_ids": [f"excerpt:{document_id}:main"],
        "result_bundle_ids": [f"result:{document_id}:main"],
        "counts": {"evidence_excerpts": 1, "result_bundles": 1, "semantic_facts": 1},
        "llm_context": {"study_snapshot": {"objective": ["Test objective"]}},
        "llm_context_chars": 240,
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
        "kind": "objective",
        "section": "Abstract",
        "locator": "section:Abstract",
        "verbatim_excerpt": text,
        "excerpt_sha256": digest,
        "source_sentence_sha256": digest,
        "source_object_ids": [],
        "semantic_fields": ["objective"],
        "priority_score": 5.0,
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
        "outcomes": [],
        "effect_measures": [],
        "confidence_intervals": [],
        "p_values": [],
        "table_references": [],
        "figure_references": [],
        "result_text": text,
        "priority_score": 5.0,
        "reference": {"doi": document_id.removeprefix("doi:")},
        "status": "machine_candidate_not_evidence_claim",
    }


def _build_workbench(output_root: Path) -> tuple[Path, str]:
    workbench_root = output_root / "scientific" / "workbench"
    inputs = output_root / "test_inputs"
    inputs.mkdir(parents=True, exist_ok=True)

    cards = [
        _card("doi:10.1000/newer", "Recent peripheral article", 2026, "pubmed"),
        _card("doi:10.1000/older", "Nutrition care framework", 2022, "europepmc"),
    ]
    texts = {
        "doi:10.1000/newer": "A recent peripheral article abstract.",
        "doi:10.1000/older": "A nutrition care framework abstract.",
    }
    excerpts = [_excerpt(card["document_id"], texts[card["document_id"]]) for card in cards]
    bundles = [
        _bundle(card["document_id"], excerpt["id"], texts[card["document_id"]])
        for card, excerpt in zip(cards, excerpts, strict=True)
    ]

    excerpts_path = inputs / "evidence_excerpts.jsonl"
    bundles_path = inputs / "result_bundles.jsonl"
    cards_path = inputs / "article_evidence_cards.jsonl"
    excerpt_manifest = inputs / "EXCERPT_MANIFEST.json"
    _write_jsonl(excerpts_path, excerpts)
    _write_jsonl(bundles_path, bundles)
    _write_jsonl(cards_path, cards)
    excerpt_manifest.write_text(
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
    run_workbench_index(
        excerpts_path,
        bundles_path,
        cards_path,
        excerpt_manifest,
        workbench_root,
    )

    search_id = "web_20260830T182743+0000_testpriority"
    bank_root = output_root / "bank" / "searches" / search_id
    ranking = bank_root / "reference_ranking.jsonl"
    audit = bank_root / "AUDIT_MANIFEST.json"
    ranking_rows = [
        {
            "title": "Nutrition care framework",
            "doi": "10.1000/older",
            "source_provider": "europepmc",
            "reference_rank": 1,
            "reference_score": 99.5,
            "bank_processing_tier": "A",
            "reference_tier": "BANK_A_PROCESSING_PRIORITY",
        },
        {
            "title": "Recent peripheral article",
            "doi": "10.1000/newer",
            "source_provider": "pubmed",
            "reference_rank": 2,
            "reference_score": 71.0,
            "bank_processing_tier": "B",
            "reference_tier": "BANK_B_PROCESSING_PRIORITY",
        },
    ]
    _write_jsonl(ranking, ranking_rows)
    audit.write_text(
        json.dumps(
            {
                "audit_type": "REFERENCE_RANKING_AUDIT",
                "status": "PASS",
                "outputs": {
                    "ranking_jsonl": {"path": str(ranking), "sha256": _sha(ranking)}
                },
            }
        ),
        encoding="utf-8",
    )
    return workbench_root, search_id


def test_priority_extension_is_atomic_queryable_and_audited(tmp_path: Path) -> None:
    output_root = tmp_path / "project_output_reference"
    workbench_root, search_id = _build_workbench(output_root)

    result = augment_workbench_priority(search_id, output_root=output_root)

    assert result["status"] == "COMPLETE"
    assert result["articles"] == 2
    assert result["matched_articles"] == 2
    database = Path(result["database"])
    assert database.name == "evidence_workbench_priority.sqlite"
    assert _sha(database) == result["database_sha256"]

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        columns = {row[1] for row in connection.execute("PRAGMA table_info(article_cards)")}
        assert {"reference_rank", "reference_score", "reference_tier"}.issubset(columns)
        older = connection.execute(
            "SELECT reference_rank, reference_score, reference_tier FROM article_cards WHERE document_id=?",
            ("doi:10.1000/older",),
        ).fetchone()
        assert older == (1, 99.5, "BANK_A_PROCESSING_PRIORITY")

    manifest = json.loads((workbench_root / "WORKBENCH_MANIFEST.json").read_text())
    assert manifest["extensions"]["bank_priority"]["status"] == "PASS"
    assert manifest["extensions"]["bank_priority"]["search_id"] == search_id
    assert manifest["outputs"]["database"]["sha256"] == result["database_sha256"]

    status = workbench_status(workbench_root)
    assert status["priority_index"] is True
    assert status["priority_search_id"] == search_id


def test_relevance_tier_and_recency_are_distinct_server_side_modes(tmp_path: Path) -> None:
    output_root = tmp_path / "project_output_reference"
    workbench_root, search_id = _build_workbench(output_root)
    augment_workbench_priority(search_id, output_root=output_root)

    relevant = load_article_page(root=workbench_root, q="__nutev_sort:relevance")
    assert relevant["articles"][0]["document_id"] == "doi:10.1000/older"
    assert relevant["articles"][0]["reference_rank"] == 1
    assert relevant["filters"]["sort"] == "relevance"

    newest = load_article_page(root=workbench_root, q="__nutev_sort:newest")
    assert newest["articles"][0]["document_id"] == "doi:10.1000/newer"
    assert newest["filters"]["sort"] == "newest"

    tier_b = load_article_page(
        root=workbench_root,
        q="Recent __nutev_tier:B __nutev_sort:relevance",
    )
    assert tier_b["total_filtered"] == 1
    assert tier_b["filters"]["q"] == "Recent"
    assert tier_b["filters"]["tier"] == "B"
    assert tier_b["articles"][0]["document_id"] == "doi:10.1000/newer"

    detail = load_article_detail("doi:10.1000/older", root=workbench_root)
    assert detail["bank_priority"]["reference_rank"] == 1
    assert detail["bank_priority"]["reference_score"] == 99.5
    assert detail["bank_priority"]["reference_tier"] == "BANK_A_PROCESSING_PRIORITY"
