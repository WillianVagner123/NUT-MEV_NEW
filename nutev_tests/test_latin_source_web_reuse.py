import importlib.util
from pathlib import Path


def _load_latin_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "run_latin_sources.py"
    spec = importlib.util.spec_from_file_location("nutev_test_run_latin_sources", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_latin_runner_can_select_one_provider_without_touching_the_other(monkeypatch, tmp_path: Path) -> None:
    latin = _load_latin_module()
    calls: list[str] = []

    def fake_run(provider: str, search_url: str, query: str, run_dir: Path):
        calls.append(provider)
        records_path = run_dir / "providers" / f"{provider}.jsonl"
        records_path.parent.mkdir(parents=True, exist_ok=True)
        records_path.write_text(
            '{"source":"%s","source_provider":"%s","title":"A sufficiently long synthetic reference title for testing","url":"https://example.org/ref"}\n'
            % (provider, provider),
            encoding="utf-8",
        )
        return {
            "provider": provider,
            "status": "completed",
            "started_at": "2026-08-20T00:00:00-03:00",
            "finished_at": "2026-08-20T00:00:01-03:00",
            "search_url": search_url,
            "query": query,
            "records_path": str(records_path),
            "records": 1,
        }

    monkeypatch.setattr(latin, "_run_provider", fake_run)
    result = latin.run(tmp_path, "dietary patterns", providers=["scielo_native"])

    assert calls == ["scielo_native"]
    assert result["requested_providers"] == ["scielo_native"]
    assert result["records"] == 1
    assert result["failed_providers"] == []
    assert result["unavailable_providers"] == []
