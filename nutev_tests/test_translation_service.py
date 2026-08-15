from __future__ import annotations

import json
from pathlib import Path

from nutev.translation_service import (
    translate_metadata_record,
    translate_strategy_candidate,
    translate_text_artifact,
    translation_configuration,
)


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _GoogleSession:
    def __init__(self):
        self.calls: list[dict] = []

    def post(self, url, *, params=None, json=None, timeout=None):
        self.calls.append({"url": url, "params": params, "json": json, "timeout": timeout})
        source = str((json or {}).get("q") or "")
        return _Response(
            {
                "data": {
                    "translations": [
                        {
                            "translatedText": f"PT::{source}",
                            "model": "nmt",
                        }
                    ]
                }
            }
        )


def _env() -> dict[str, str]:
    return {
        "NUTEV_TRANSLATION_PROVIDER": "google_cloud_v2",
        "NUTEV_TRANSLATION_TARGET": "pt",
        "GOOGLE_TRANSLATE_API_KEY": "secret-test-key",
    }


def test_translation_configuration_never_requires_translation_by_default() -> None:
    status = translation_configuration({})
    assert status["configured"] is False
    assert status["target_language"] == "pt"


def test_text_translation_writes_separate_artifact_and_preserves_original(tmp_path: Path) -> None:
    original = tmp_path / "doc.txt"
    original.write_text("Nutrition care improves health outcomes.", encoding="utf-8")
    before = original.read_bytes()
    session = _GoogleSession()

    record = translate_text_artifact(
        "doc-1",
        original,
        tmp_path / "translated",
        source_language="en",
        target_language="pt",
        session=session,
        environ=_env(),
    )

    assert record["status"] == "COMPLETED"
    assert original.read_bytes() == before
    translated = Path(record["translated_text_path"])
    assert translated.is_file()
    assert translated != original
    assert translated.read_text(encoding="utf-8").startswith("PT::")
    assert record["original_sha256"] != ""
    assert record["translated_sha256"] != ""
    assert record["translator"] == "google_cloud_translation_v2"
    assert all("secret-test-key" not in json.dumps(call) or call["params"]["key"] == "secret-test-key" for call in session.calls)


def test_metadata_translation_keeps_original_fields_side_by_side() -> None:
    session = _GoogleSession()
    metadata = {
        "document_id": "doc-2",
        "title": "Nutrition guideline",
        "abstract": "Clinical nutrition guidance.",
        "keywords": "nutrition; health",
        "language": "en",
    }
    result = translate_metadata_record(
        "doc-2",
        metadata,
        target_language="pt",
        session=session,
        environ=_env(),
    )
    assert result["status"] == "COMPLETED"
    assert result["original"]["title"] == "Nutrition guideline"
    assert result["translated"]["title"] == "PT::Nutrition guideline"
    assert result["original_preserved"] is True
    assert metadata["title"] == "Nutrition guideline"


def test_strategy_translation_is_never_auto_applied() -> None:
    session = _GoogleSession()
    result = translate_strategy_candidate(
        '"healthy diet" AND guideline',
        source_language="en",
        target_language="pt",
        session=session,
        environ=_env(),
    )
    assert result["status"] == "PROVISIONAL_NOT_EXECUTABLE"
    assert result["human_validation_required"] is True
    assert result["automatically_applied_to_strategy"] is False
    assert result["original_strategy"] == '"healthy diet" AND guideline'
    assert result["translated_candidate"].startswith("PT::")
