from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def query_hash(provider: str, workstream: str, query: str) -> str:
    payload = f"{provider}\0{workstream}\0{query}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:16]  # noqa: S324


def checkpoint_path(base_dir: Path, provider: str, workstream: str, query: str) -> Path:
    return base_dir / provider / f"{query_hash(provider, workstream, query)}.json"


def load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        corrupt_path = path.with_suffix(path.suffix + ".corrupt")
        try:
            path.replace(corrupt_path)
        except Exception:
            import logging

            logging.getLogger(__name__).debug("could not quarantine corrupt checkpoint %s", path, exc_info=True)
        return None
    return payload if isinstance(payload, dict) else None


def save_checkpoint(path: Path, data: dict[str, Any]) -> None:
    payload = dict(data)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp_path.replace(path)
