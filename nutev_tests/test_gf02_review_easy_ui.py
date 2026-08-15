from __future__ import annotations

import csv
from pathlib import Path

import pytest

from nutev.review.gf02_noise_review import (
    read_rescue_only_sample,
    review_progress,
    save_rescue_only_progress,
)


def _sample(path: Path) -> None:
    fields = [
        "sample_id",
        "record_id",
        "pmid",
        "doi",
        "title",
        "provider",
        "strategy_version",
        "sampling_rule",
        "classification",
        "reviewer",
        "note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(1, 4):
            writer.writerow(
                {
                    "sample_id": f"GF02-RESCUE-{index:03d}",
                    "record_id": str(index),
                    "pmid": str(index),
                    "doi": f"10.1/{index}",
                    "title": f"Record {index}",
                    "provider": "PUBMED",
                    "strategy_version": "v0.5",
                    "sampling_rule": "fixed",
                    "classification": "",
                    "reviewer": "",
                    "note": "",
                }
            )


def test_save_progress_persists_only_explicit_subset(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    _sample(path)

    result = save_rescue_only_progress(
        path,
        reviewer="Willian",
        decisions=[
            {
                "sample_id": "GF02-RESCUE-002",
                "classification": "DOUBT",
                "note": "needs more information",
            }
        ],
    )

    assert result["updated"] == 1
    rows = read_rescue_only_sample(path)
    assert rows[0]["classification"] == ""
    assert rows[1]["classification"] == "DOUBT"
    assert rows[1]["reviewer"] == "Willian"
    assert rows[1]["note"] == "needs more information"
    assert rows[2]["classification"] == ""
    assert review_progress(path)["resolved"] == 1
    assert review_progress(path)["pending"] == 2


def test_save_progress_rejects_unknown_or_blank_decisions(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    _sample(path)

    with pytest.raises(ValueError, match="classification"):
        save_rescue_only_progress(
            path,
            reviewer="Willian",
            decisions=[{"sample_id": "GF02-RESCUE-001", "classification": "", "note": ""}],
        )

    with pytest.raises(ValueError, match="unknown sample_id"):
        save_rescue_only_progress(
            path,
            reviewer="Willian",
            decisions=[{"sample_id": "GF02-RESCUE-999", "classification": "RELEVANT", "note": ""}],
        )


def test_easy_review_surface_has_filters_bulk_actions_and_classification_help() -> None:
    source = (Path("src") / "nutev" / "ui" / "gf02_review_workbench.py").read_text(encoding="utf-8")
    play = (Path("src") / "nutev" / "ui" / "article1_play_panel.py").read_text(encoding="utf-8")

    assert "Como classificar" in source
    assert "RELEVANT · manter" in source
    assert "IRRELEVANT · ruído" in source
    assert "DOUBT · revisar" in source
    assert "Buscar nos registros" in source
    assert "Não classificados" in source
    assert "Linhas selecionadas" in source
    assert "Todos os resultados filtrados" in source
    assert "Marcar RELEVANT" in source
    assert "Marcar IRRELEVANT" in source
    assert "Marcar DOUBT" in source
    assert "Salvar progresso" in source
    assert "Finalizar revisão" in source
    assert "Preencher somente as vazias" in source
    assert "render_gf02_easy_review(scientific)" in play
