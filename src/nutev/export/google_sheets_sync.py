"""One-way Article 1 Engine -> Google Sheets transport.

The scientific Engine remains authoritative. This module only transports an
already-built ``article1_sheet_payload`` to Google Sheets. It is idempotent at
the tab-value level: missing tabs are created, existing values are cleared while
formatting is preserved, then canonical values are written from A1.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import requests

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: object) -> str:
    return str(value or "").strip()


def _sha_json(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(serialized.encode("utf-8")).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def _tab_values(value: Any) -> list[list[Any]]:
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(row, dict) for row in value):
            headers: list[str] = []
            for row in value:
                for key in row:
                    if str(key) not in headers:
                        headers.append(str(key))
            return [headers] + [[_cell(row.get(key)) for key in headers] for row in value]
        return [[_cell(item)] for item in value]
    if isinstance(value, dict):
        return [["key", "value"]] + [[str(key), _cell(item)] for key, item in value.items()]
    return [[_cell(value)]]


def _sheet_range(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def sheets_sync_configuration(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    spreadsheet_id = _clean(env.get("NUTEV_GOOGLE_SHEETS_SPREADSHEET_ID"))
    token = _clean(
        env.get("NUTEV_GOOGLE_SHEETS_ACCESS_TOKEN")
        or env.get("GOOGLE_SHEETS_ACCESS_TOKEN")
    )
    if not spreadsheet_id:
        return {
            "configured": False,
            "spreadsheet_id": None,
            "reason": "NUTEV_GOOGLE_SHEETS_SPREADSHEET_ID is missing",
            "access_token_present": bool(token),
        }
    if not token:
        return {
            "configured": False,
            "spreadsheet_id": spreadsheet_id,
            "reason": "NUTEV_GOOGLE_SHEETS_ACCESS_TOKEN/GOOGLE_SHEETS_ACCESS_TOKEN is missing",
            "access_token_present": False,
        }
    return {
        "configured": True,
        "spreadsheet_id": spreadsheet_id,
        "reason": "",
        "access_token_present": True,
    }


def _request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    token: str,
    timeout: float,
    **kwargs: Any,
) -> requests.Response:
    headers = dict(kwargs.pop("headers", {}) or {})
    headers["Authorization"] = f"Bearer {token}"
    headers.setdefault("Content-Type", "application/json")
    response = session.request(method, url, headers=headers, timeout=timeout, **kwargs)
    response.raise_for_status()
    return response


def _existing_sheets(
    session: requests.Session,
    spreadsheet_id: str,
    *,
    token: str,
    timeout: float,
) -> set[str]:
    response = _request(
        session,
        "GET",
        f"{SHEETS_API}/{quote(spreadsheet_id, safe='')}",
        token=token,
        timeout=timeout,
        params={"fields": "sheets.properties.title"},
    )
    body = response.json()
    return {
        str((sheet.get("properties") or {}).get("title") or "")
        for sheet in body.get("sheets") or []
        if str((sheet.get("properties") or {}).get("title") or "")
    }


def _ensure_sheets(
    session: requests.Session,
    spreadsheet_id: str,
    titles: list[str],
    *,
    token: str,
    timeout: float,
) -> list[str]:
    existing = _existing_sheets(session, spreadsheet_id, token=token, timeout=timeout)
    missing = [title for title in titles if title not in existing]
    if not missing:
        return []
    _request(
        session,
        "POST",
        f"{SHEETS_API}/{quote(spreadsheet_id, safe='')}:batchUpdate",
        token=token,
        timeout=timeout,
        json={
            "requests": [
                {"addSheet": {"properties": {"title": title}}}
                for title in missing
            ]
        },
    )
    return missing


def sync_article1_sheet_payload(
    project_root: Path,
    payload: dict[str, Any],
    *,
    spreadsheet_id: str | None = None,
    access_token: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 60.0,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Replace canonical tab values from one authoritative Engine payload."""
    root = Path(project_root)
    env = environ if environ is not None else os.environ
    config = sheets_sync_configuration(env)
    resolved_id = _clean(spreadsheet_id or config.get("spreadsheet_id"))
    token = _clean(
        access_token
        or env.get("NUTEV_GOOGLE_SHEETS_ACCESS_TOKEN")
        or env.get("GOOGLE_SHEETS_ACCESS_TOKEN")
    )
    audit_path = root / "08_exports" / "article1_final" / "google_sheets_sync.json"
    tabs = payload.get("tabs") or {}
    base = {
        "schema_version": 1,
        "sync_direction": "ENGINE_TO_SHEET",
        "runtime_is_authoritative": bool(payload.get("runtime_is_authoritative", True)),
        "execution_mode": str(payload.get("execution_mode") or "FORMAL"),
        "payload_sha256": _sha_json(payload),
        "spreadsheet_id": resolved_id or None,
        "tab_names": list(tabs),
        "attempted_at": _now(),
        "scientific_decision_inferred": False,
        "access_token_persisted": False,
    }
    if not resolved_id or not token:
        result = {
            **base,
            "status": "SKIPPED_NOT_CONFIGURED",
            "reason": (
                "spreadsheet_id missing"
                if not resolved_id
                else "Google Sheets OAuth access token missing"
            ),
        }
        result["audit_sha256"] = _atomic_json(audit_path, result)
        result["audit_path"] = str(audit_path)
        return result
    if str(payload.get("sync_direction") or "ENGINE_TO_SHEET") != "ENGINE_TO_SHEET":
        raise ValueError("Google Sheets sync only supports ENGINE_TO_SHEET")
    if not isinstance(tabs, dict) or not tabs:
        raise ValueError("sheet payload contains no tabs")

    client = session or requests.Session()
    try:
        created = _ensure_sheets(
            client,
            resolved_id,
            list(tabs),
            token=token,
            timeout=timeout,
        )
        ranges = [_sheet_range(title) for title in tabs]
        _request(
            client,
            "POST",
            f"{SHEETS_API}/{quote(resolved_id, safe='')}/values:batchClear",
            token=token,
            timeout=timeout,
            json={"ranges": ranges},
        )
        data = []
        row_counts: dict[str, int] = {}
        for title, value in tabs.items():
            values = _tab_values(value)
            row_counts[title] = len(values)
            if values:
                data.append(
                    {
                        "range": f"{_sheet_range(title)}!A1",
                        "majorDimension": "ROWS",
                        "values": values,
                    }
                )
        update_response: dict[str, Any] = {}
        if data:
            response = _request(
                client,
                "POST",
                f"{SHEETS_API}/{quote(resolved_id, safe='')}/values:batchUpdate",
                token=token,
                timeout=timeout,
                json={"valueInputOption": "RAW", "data": data},
            )
            update_response = response.json()
        result = {
            **base,
            "status": "SUCCEEDED",
            "reason": "",
            "tabs_created": created,
            "row_counts": row_counts,
            "total_updated_cells": int(update_response.get("totalUpdatedCells") or 0),
            "total_updated_rows": int(update_response.get("totalUpdatedRows") or 0),
            "completed_at": _now(),
        }
    except Exception as exc:
        result = {
            **base,
            "status": "FAILED",
            "reason": str(exc),
            "completed_at": _now(),
        }
    result["audit_sha256"] = _atomic_json(audit_path, result)
    result["audit_path"] = str(audit_path)
    return result


def sync_article1_export_bundle(
    project_root: Path,
    export_bundle_path: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    path = Path(export_bundle_path)
    if not path.is_file():
        raise FileNotFoundError(f"Article 1 export bundle not found: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Article 1 export bundle must be a JSON object")
    payload = value.get("sheet_payload") or {}
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Article 1 export bundle has no sheet_payload")
    return sync_article1_sheet_payload(project_root, payload, **kwargs)


__all__ = [
    "sheets_sync_configuration",
    "sync_article1_export_bundle",
    "sync_article1_sheet_payload",
]
