"""Config provenance for active scientific configuration families."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nutev.settings import load_json, resolve_config_sources

DEFAULT_CONFIG_FAMILIES = (
    "keyword_taxonomy.json",
    "official_sources_manifest.json",
    "thematic_taxonomy.json",
    "nutev_ontology.json",
    "evidence_lenses.json",
    "source_registry.json",
    "guideline_repository_registry.json",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_of(obj: object) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return _sha256(payload.encode("utf-8"))


def config_family_provenance(base_path: Path) -> dict:
    """Return ordered input hashes and the merged digest for one config family."""
    base_path = Path(base_path)
    sources: list[dict] = []
    for source in resolve_config_sources(base_path):
        try:
            sources.append({"name": source.name, "sha256": _sha256(source.read_bytes())})
        except OSError:
            sources.append({"name": source.name, "sha256": None})
    try:
        merged_digest = _digest_of(load_json(base_path)) if base_path.exists() else None
    except (OSError, ValueError):
        merged_digest = None
    return {
        "base": base_path.name,
        "present": base_path.exists(),
        "sources": sources,
        "supplement_count": max(len(sources) - 1, 0) if base_path.exists() else len(sources),
        "merged_digest": merged_digest,
    }


def build_config_provenance(
    config_root: Path | str,
    families: tuple[str, ...] = DEFAULT_CONFIG_FAMILIES,
) -> dict:
    """Return provenance for active config families plus one overall digest."""
    root = Path(config_root)
    family_records: dict[str, dict] = {}
    for family in families:
        family_records[family] = config_family_provenance(root / family)
    overall = {name: rec["merged_digest"] for name, rec in family_records.items()}
    return {
        "config_root": str(root),
        "config_digest": _digest_of(overall),
        "families": family_records,
    }


def write_config_provenance(
    path: Path | str,
    config_root: Path | str,
    families: tuple[str, ...] = DEFAULT_CONFIG_FAMILIES,
) -> dict:
    """Compute and write ``config_provenance.json``; return the record."""
    record = build_config_provenance(config_root, families)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record
