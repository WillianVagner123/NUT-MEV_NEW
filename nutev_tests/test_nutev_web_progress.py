from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

import progress_search


def test_progressive_search_emits_provider_completion_without_changing_engine_primitives(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    monkeypatch.setattr(
        progress_search,
        "_provider_call",
        lambda provider, query, limit: lambda: [
            {
                "source": provider,
                "source_provider": provider,
                "title": f"{provider} result",
                "url": f"https://example.org/{provider}",
            }
        ],
    )

    def fake_latin(query: str, selected: list[str], *, output_root: Path):
        provider = selected[0]
        rows = [
            {
                "source": provider,
                "source_provider": provider,
                "title": f"{provider} result",
                "url": f"https://example.org/{provider}",
            }
        ]
        status = [
            {
                "provider": provider,
                "label": progress_search.PROVIDER_LABELS[provider],
                "status": "completed",
                "returned": 1,
                "total_found": None,
                "error": "",
            }
        ]
        return rows, status, str(output_root / "latin-summary.json")

    monkeypatch.setattr(progress_search, "_latin_rows_and_status", fake_latin)
    monkeypatch.setattr(progress_search, "dedupe_records", lambda rows: rows)
    monkeypatch.setattr(
        progress_search,
        "_score_rows",
        lambda rows: [
            {**row, "reference_score": 1.0, "reference_rank": index}
            for index, row in enumerate(rows, start=1)
        ],
    )
    monkeypatch.setattr(progress_search, "_persist_search", lambda result, root: None)

    events: list[dict] = []
    result = progress_search.search_evidence_progressive(
        "lifestyle nutrition",
        providers=["pubmed", "lilacs_bvs_native"],
        per_provider=1,
        max_results=10,
        output_root=tmp_path,
        on_progress=events.append,
    )

    types = [event["type"] for event in events]
    assert types[0] == "search_started"
    assert types.count("provider_started") == 2
    assert types.count("provider_completed") == 2
    assert "finalizing" in types
    assert types[-1] == "search_completed"
    assert result["returned_records"] == 2
    assert [item["provider"] for item in result["providers"]] == [
        "pubmed",
        "lilacs_bvs_native",
    ]
