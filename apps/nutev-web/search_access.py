from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4

from search_adapter import _output_root

_REGISTRY_LOCK = threading.Lock()


def _registry_path(output_root: Path | None = None) -> Path:
    return _output_root(output_root) / "15_web_searches" / ".ownership.json"


def _read_registry(output_root: Path | None = None) -> dict[str, str]:
    path = _registry_path(output_root)
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        str(search_id): str(owner_scope)
        for search_id, owner_scope in value.items()
        if search_id and owner_scope
    }


def _write_registry(registry: dict[str, str], output_root: Path | None = None) -> None:
    path = _registry_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def record_search_owner(
    search_id: str,
    owner_scope: str,
    *,
    output_root: Path | None = None,
) -> None:
    search_id = str(search_id or "").strip()
    owner_scope = str(owner_scope or "").strip()
    if not search_id or not owner_scope:
        raise ValueError("search_id e owner_scope são obrigatórios")
    with _REGISTRY_LOCK:
        registry = _read_registry(output_root)
        existing = registry.get(search_id)
        if existing and existing != owner_scope:
            raise PermissionError("search ownership conflict")
        registry[search_id] = owner_scope
        _write_registry(registry, output_root)


def search_owned_by(
    search_id: str,
    owner_scope: str,
    *,
    output_root: Path | None = None,
) -> bool:
    with _REGISTRY_LOCK:
        return _read_registry(output_root).get(str(search_id)) == str(owner_scope)


def filter_owned_runs(
    runs: list[dict[str, Any]],
    owner_scope: str,
    *,
    output_root: Path | None = None,
) -> list[dict[str, Any]]:
    with _REGISTRY_LOCK:
        registry = _read_registry(output_root)
    return [
        run
        for run in runs
        if registry.get(str(run.get("search_id") or "")) == str(owner_scope)
    ]
