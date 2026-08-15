"""Post-FORMAL preparation that remains automatic and non-decisional."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nutev.pipelines.formal_review_queue import build_formal_review_queue


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def prepare_formal_human_review(project_root: Path, formal_summary: dict[str, Any]) -> dict[str, Any]:
    """Create/rebuild the human screening queue from a completed FORMAL summary."""
    root = Path(project_root)
    master_path = Path(str((formal_summary.get("corpus") or {}).get("master_jsonl_path") or ""))
    extraction_path = Path(str((formal_summary.get("artifacts") or {}).get("extraction_manifest_path") or ""))
    if not master_path.is_file():
        raise FileNotFoundError(f"formal master corpus not found: {master_path}")
    master_rows = _read_jsonl(master_path)
    extraction_rows = _read_jsonl(extraction_path) if extraction_path.is_file() else []
    return build_formal_review_queue(
        root,
        master_rows=master_rows,
        extraction_manifest=extraction_rows,
    )


__all__ = ["prepare_formal_human_review"]
