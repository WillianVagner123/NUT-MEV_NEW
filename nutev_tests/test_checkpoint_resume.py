from __future__ import annotations

import json
from pathlib import Path

from nutev.search.checkpoint import load_checkpoint, save_checkpoint


def test_corrupt_checkpoint_is_ignored_and_renamed(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    assert load_checkpoint(path) is None
    assert not path.exists() or path.with_suffix(".json.corrupt").exists()


def test_checkpoint_roundtrip(tmp_path: Path):
    path = tmp_path / "provider" / "x.json"
    save_checkpoint(path, {"status": "partial", "rows": [{"pmid": "1"}]})
    data = load_checkpoint(path)
    assert data and data["status"] == "partial"
    assert data["rows"][0]["pmid"] == "1"


def test_checkpoint_serialization_is_deterministically_key_sorted(tmp_path: Path):
    path = tmp_path / "provider" / "sorted.json"
    save_checkpoint(path, {"zeta": 1, "alpha": 2})

    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["alpha"] == 2
    assert payload["zeta"] == 1
    assert "updated_at" in payload
    assert text.index('"alpha"') < text.index('"updated_at"') < text.index('"zeta"')
    assert load_checkpoint(path) == payload
