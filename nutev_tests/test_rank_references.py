from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "rank_references.py"
SPEC = importlib.util.spec_from_file_location("rank_references", MODULE_PATH)
assert SPEC and SPEC.loader
rank_references = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rank_references)


def test_reference_ranker_prioritizes_taxonomy_and_focus_keywords(tmp_path: Path) -> None:
    config = tmp_path / "config"
    project = tmp_path / "project"
    run_dir = project / "run"
    logs = project / "07_logs" / "collect_everything"
    config.mkdir()
    run_dir.mkdir(parents=True)
    logs.mkdir(parents=True)

    (config / "keyword_taxonomy.json").write_text(
        json.dumps({"global": {"nutrition": {"core": ["nutrition care", "dietary pattern"]}}}),
        encoding="utf-8",
    )
    (config / "reference_mode.json").write_text(
        json.dumps(
            {
                "focus_keywords": ["lifestyle medicine"],
                "provider_weights": {"pubmed": 6, "crossref": 1},
            }
        ),
        encoding="utf-8",
    )

    master = run_dir / "master.jsonl"
    master.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "title": "Clinical practice guideline for nutrition care and lifestyle medicine",
                        "abstract": "Dietary pattern recommendations",
                        "source_provider": "pubmed",
                        "pmid": "123",
                        "year": 2025,
                        "prisma_eligible": False,
                        "formal_execution_authorized": False,
                    }
                ),
                json.dumps(
                    {
                        "title": "Unrelated technical note",
                        "abstract": "No matching concepts",
                        "source_provider": "crossref",
                        "doi": "10.1/example",
                        "year": 2026,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (logs / "latest.json").write_text(json.dumps({"master_records_path": str(master)}), encoding="utf-8")

    summary = rank_references.run(project, config, 10)
    rows = [
        json.loads(line)
        for line in (project / "reference_ranking" / "reference_ranking.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert summary["mode"] == "REFERENCE_RANKING"
    assert "prisma" not in summary
    assert "screening" not in summary
    assert rows[0]["pmid"] == "123"
    assert rows[0]["reference_score"] > rows[1]["reference_score"]
    assert "global.nutrition.core" in rows[0]["taxonomy_groups"]
    assert "prisma_eligible" not in rows[0]
    assert "formal_execution_authorized" not in rows[0]
