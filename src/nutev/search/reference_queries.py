from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REQUIRED_QUERIES = ("pubmed", "generic", "web")


def load_reference_search(path: Path) -> dict[str, Any]:
    """Load and validate the canonical Reference Engine search configuration."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("reference search configuration must be a JSON object")
    if int(data.get("schema_version") or 0) != 1:
        raise ValueError("unsupported reference search schema version")
    if data.get("mode") != "REFERENCE_COLLECTION":
        raise ValueError("reference search mode must be REFERENCE_COLLECTION")
    queries = data.get("queries")
    if not isinstance(queries, dict):
        raise ValueError("reference search queries must be an object")
    for key in _REQUIRED_QUERIES:
        value = str(queries.get(key) or "").strip()
        if not value:
            raise ValueError(f"missing reference search query: {key}")
        queries[key] = value
    limits = data.get("provider_limits")
    if limits is not None and not isinstance(limits, dict):
        raise ValueError("provider_limits must be an object")
    return data


def reference_queries(path: Path) -> dict[str, str]:
    data = load_reference_search(path)
    queries = data["queries"]
    return {key: str(queries[key]) for key in _REQUIRED_QUERIES}


def provider_limit(path: Path, provider: str, default: int) -> int:
    data = load_reference_search(path)
    limits = data.get("provider_limits") or {}
    value = int(limits.get(provider) or default)
    if value < 1:
        raise ValueError(f"provider limit must be positive: {provider}")
    return value
