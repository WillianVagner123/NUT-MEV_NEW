"""Config provenance: record exactly which config files produced a run.

The taxonomy/scoring configs are assembled by deep-merging a base JSON with any
sibling ``*_supplement*.json`` layers (see ``nutev.settings.load_json``). That
merge is deterministic, but before this module nothing recorded *which* files —
or which versions of them — actually fed a run, so a citation-grade result could
not be tied back to its exact configuration.

This module enumerates the ordered source files for each config family (through
the same ``resolve_config_sources`` the loader uses, so the two can never
disagree), hashes each one and the merged result, and emits a compact
``config_provenance`` record with a single ``config_digest``. Recording that
digest in the run manifest makes a run reproducible and auditable: the same
inputs and the same digest guarantee the same taxonomy/scoring was applied, and
a changed digest flags that the configuration moved.

Pure provenance — it never changes what ``load_json`` merges.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nutev.settings import load_json, resolve_config_sources

# The config families whose provenance is worth pinning to a run. Each is a base
# filename under the config root; supplements are discovered automatically.
DEFAULT_CONFIG_FAMILIES = (
    "keyword_taxonomy.json",
    "scoring_rules.json",
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
    """Provenance for one config family: its ordered source files + merged digest.

    ``sources`` lists the base then each supplement (in the exact merge order),
    each with a relative name and its own content ``sha256``. ``merged_digest``
    is the digest of the fully merged config — the value that determines run
    behavior. Missing/unreadable files are recorded with ``sha256: null`` rather
    than raising, so provenance capture never breaks a run.
    """
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
    """Provenance for every declared config family + one overall ``config_digest``.

    ``config_digest`` is a deterministic hash over each family's merged digest,
    so two runs share it iff every merged config matched. Record it in the run
    manifest to make the run's configuration reproducible and citable.
    """
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
