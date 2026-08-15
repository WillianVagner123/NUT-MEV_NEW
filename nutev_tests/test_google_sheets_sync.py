from __future__ import annotations

import json
from pathlib import Path

from nutev.export.google_sheets_sync import sync_article1_sheet_payload


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _Session:
    def __init__(self):
        self.calls: list[dict] = []

    def request(self, method, url, *, headers=None, timeout=None, **kwargs):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers or {}),
                "timeout": timeout,
                **kwargs,
            }
        )
        if method == "GET":
            return _Response({"sheets": [{"properties": {"title": "08_CODEBOOK_ABCD"}}]})
        if url.endswith("/values:batchUpdate"):
            return _Response({"totalUpdatedCells": 8, "totalUpdatedRows": 4})
        return _Response({})


def _payload() -> dict:
    return {
        "sync_direction": "ENGINE_TO_SHEET",
        "runtime_is_authoritative": True,
        "execution_mode": "FORMAL",
        "tabs": {
            "08_CODEBOOK_ABCD": [{"code": "A1", "label": "Adequação"}],
            "10_EXTRACAO_ABCD": [{"document_id": "doc-1", "code": "A1", "presence": "YES"}],
            "13_SINTESE": {"ready": True, "included_documents": 1},
        },
    }


def test_missing_credentials_are_explicit_skip_not_success(tmp_path: Path) -> None:
    result = sync_article1_sheet_payload(tmp_path, _payload(), environ={})
    assert result["status"] == "SKIPPED_NOT_CONFIGURED"
    assert result["access_token_persisted"] is False
    audit = Path(result["audit_path"])
    assert audit.is_file()
    assert "access_token" not in audit.read_text(encoding="utf-8").casefold()


def test_sync_creates_missing_tabs_clears_values_and_batch_writes(tmp_path: Path) -> None:
    session = _Session()
    env = {
        "NUTEV_GOOGLE_SHEETS_SPREADSHEET_ID": "sheet-123",
        "NUTEV_GOOGLE_SHEETS_ACCESS_TOKEN": "top-secret-token",
    }
    result = sync_article1_sheet_payload(
        tmp_path,
        _payload(),
        session=session,
        environ=env,
    )
    assert result["status"] == "SUCCEEDED"
    assert set(result["tabs_created"]) == {"10_EXTRACAO_ABCD", "13_SINTESE"}
    assert result["row_counts"]["08_CODEBOOK_ABCD"] == 2
    assert any(call["url"].endswith(":batchUpdate") for call in session.calls)
    assert any(call["url"].endswith("/values:batchClear") for call in session.calls)
    assert any(call["url"].endswith("/values:batchUpdate") for call in session.calls)
    audit_text = Path(result["audit_path"]).read_text(encoding="utf-8")
    assert "top-secret-token" not in audit_text
    assert json.loads(audit_text)["status"] == "SUCCEEDED"
