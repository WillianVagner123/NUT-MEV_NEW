from __future__ import annotations

from pathlib import Path

import pytest

from nutev.search.native_export import read_native_export, search_native_export
from nutev.search.strategy_executor import parse_provider_expression


def test_scielo_native_csv_preserves_query_and_export_hash(tmp_path: Path) -> None:
    export = tmp_path / "scielo.csv"
    export.write_text(
        "title;authors;abstract;language;doi;year;url\n"
        '"Guia alimentar";"Silva A;Souza B";"Resumo em português";pt;10.1234/x;2024;https://example.org/x\n',
        encoding="utf-8",
    )
    query = 'subject:("alimentação saudável") AND la:pt'
    result = search_native_export(
        "scielo_native",
        query,
        export_path=export,
        limit=100,
    )
    assert result.status == "completed"
    assert result.total_found == 1
    assert result.total_returned == 1
    row = result.rows[0]
    assert row["source_provider"] == "scielo_native"
    assert row["provider_query"] == query
    assert row["title"] == "Guia alimentar"
    assert row["authors"] == ["Silva A", "Souza B"]
    assert row["native_export_sha256"] == result.meta["native_export_sha256"]
    assert result.meta["provider_substitution"] is False


def test_lilacs_ris_is_normalized_without_scraping(tmp_path: Path) -> None:
    export = tmp_path / "lilacs.ris"
    export.write_text(
        "TY  - JOUR\n"
        "TI  - Atención nutricional en salud\n"
        "AU  - Pérez, Ana\n"
        "AU  - Silva, Bruno\n"
        "AB  - Resumen del documento.\n"
        "LA  - es\n"
        "PY  - 2023\n"
        "DO  - 10.5555/lilacs\n"
        "UR  - https://example.org/lilacs\n"
        "ER  - \n",
        encoding="utf-8",
    )
    rows = read_native_export(
        "lilacs_bvs",
        query="tw:(nutrición) AND la:es",
        export_path=export,
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Atención nutricional en salud"
    assert rows[0]["authors"] == ["Pérez, Ana", "Silva, Bruno"]
    assert rows[0]["language_original"] == "es"
    assert rows[0]["native_export_format"] == "RIS"


def test_native_provider_expression_requires_exact_query_and_export_path() -> None:
    query, export_filter = parse_provider_expression(
        "scielo_native",
        "query=subject:nutrition AND la:pt | export=02_sources/scielo.csv",
    )
    assert query == "subject:nutrition AND la:pt"
    assert export_filter == "export=02_sources/scielo.csv"
    with pytest.raises(ValueError, match="official CSV/RIS export"):
        parse_provider_expression("lilacs_bvs", "query=tw:nutrition")


def test_native_export_missing_file_is_not_zero_results(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        search_native_export(
            "lilacs_bvs",
            "tw:nutrition",
            export_path=tmp_path / "missing.csv",
        )
