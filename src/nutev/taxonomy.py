from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable


TAXONOMY_REGISTRY_FILENAME = "taxonomy_registry.json"
_DEFAULT_ALLOWED_ROOTS = ("global", "clinical", "outcomes")
_DEFAULT_EXCLUDED_PATHS = ("global.document_types",)
_SPACE_RE = re.compile(r"\s+")


class TaxonomyError(RuntimeError):
    """Raised when taxonomy configuration cannot be mapped deterministically."""


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise TaxonomyError(f"Taxonomy file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaxonomyError(f"Invalid taxonomy JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TaxonomyError(f"Taxonomy JSON must be an object: {path}")
    return data


def taxonomy_source_files(config_dir: Path) -> list[Path]:
    """Return vocabulary source files in deterministic order."""

    return sorted(config_dir.glob("keyword_taxonomy*.json"))


def taxonomy_config_paths(config_dir: Path) -> list[Path]:
    paths = taxonomy_source_files(config_dir)
    registry = config_dir / TAXONOMY_REGISTRY_FILENAME
    if registry.is_file():
        paths.append(registry)
    return sorted(paths)


def _iter_leaf_terms(
    value: Any,
    path: tuple[str, ...] = (),
) -> Iterable[tuple[str, list[str]]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_leaf_terms(child, path + (str(key),))
        return

    if isinstance(value, list):
        terms: list[str] = []
        for item in value:
            if isinstance(item, str):
                terms.append(item)
            elif isinstance(item, (dict, list)):
                yield from _iter_leaf_terms(item, path)
        if terms:
            yield ".".join(path), terms
        return

    if isinstance(value, str):
        yield ".".join(path), [value]


def _is_excluded(raw_path: str, prefixes: Iterable[str]) -> bool:
    return any(raw_path == prefix or raw_path.startswith(prefix + ".") for prefix in prefixes)


def _canonical_source_map(registry: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    groups = registry.get("groups")
    if not isinstance(groups, dict) or not groups:
        raise TaxonomyError("taxonomy_registry.json has no non-empty 'groups' object")

    source_map: dict[str, str] = {}
    group_metadata: dict[str, Any] = {}
    for canonical_group, raw_metadata in groups.items():
        if not isinstance(raw_metadata, dict):
            raise TaxonomyError(f"Invalid metadata for canonical group {canonical_group}")
        source_paths = raw_metadata.get("source_paths")
        if not isinstance(source_paths, list) or not source_paths:
            raise TaxonomyError(f"Canonical group has no source_paths: {canonical_group}")
        dimension = str(canonical_group).split(".", 1)[0]
        metadata = dict(raw_metadata)
        metadata["dimension"] = dimension
        group_metadata[str(canonical_group)] = metadata
        for raw_path in source_paths:
            raw_path_text = str(raw_path).strip()
            if not raw_path_text:
                raise TaxonomyError(f"Empty source path in group {canonical_group}")
            previous = source_map.get(raw_path_text)
            if previous and previous != canonical_group:
                raise TaxonomyError(
                    f"Source path mapped twice: {raw_path_text} -> {previous}, {canonical_group}"
                )
            source_map[raw_path_text] = str(canonical_group)
    return source_map, group_metadata


def _sorted_terms(terms: set[str]) -> list[str]:
    return sorted(terms, key=lambda term: (-len(term), term))


def _compatibility_taxonomy(config_dir: Path) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Safe fallback for small external/test configs without the registry.

    Compatibility mode still excludes historical workstreams and document-type
    taxonomy so those sections cannot silently inflate reference ranking.
    """

    merged: dict[str, set[str]] = {}
    excluded: set[str] = set()
    source_files = taxonomy_source_files(config_dir)
    for path in source_files:
        data = _read_json(path)
        for raw_path, raw_terms in _iter_leaf_terms(data):
            root = raw_path.split(".", 1)[0]
            if root not in _DEFAULT_ALLOWED_ROOTS or _is_excluded(
                raw_path, _DEFAULT_EXCLUDED_PATHS
            ):
                excluded.add(raw_path)
                continue
            normalized = {_norm(term) for term in raw_terms}
            normalized.discard("")
            merged.setdefault(raw_path, set()).update(
                term for term in normalized if len(term) >= 3
            )

    groups = {group: _sorted_terms(terms) for group, terms in sorted(merged.items())}
    metadata = {
        "schema_version": 1,
        "taxonomy_version": "compatibility-unregistered",
        "registry_mode": "compatibility",
        "registry_path": None,
        "primary_dimension_order": ["global", "clinical", "outcomes"],
        "source_files": [str(path) for path in source_files],
        "raw_groups_mapped": len(groups),
        "raw_groups_excluded": len(excluded),
        "canonical_groups_loaded": len(groups),
        "canonical_terms_total": sum(len(terms) for terms in groups.values()),
        "excluded_raw_paths": sorted(excluded),
        "group_metadata": {},
    }
    return groups, metadata


def load_canonical_taxonomy(config_dir: Path) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Compile legacy vocabulary files into the canonical taxonomy registry.

    The registry is fail-closed: any semantic leaf under an allowed root that is
    not explicitly mapped causes an error instead of silently creating a new
    scoring group. Historical `workstreams.*` and `global.document_types.*`
    content is intentionally excluded from taxonomy scoring.
    """

    registry_path = config_dir / TAXONOMY_REGISTRY_FILENAME
    if not registry_path.is_file():
        return _compatibility_taxonomy(config_dir)

    registry = _read_json(registry_path)
    allowed_roots_raw = registry.get("allowed_roots", list(_DEFAULT_ALLOWED_ROOTS))
    excluded_raw = registry.get("excluded_paths", list(_DEFAULT_EXCLUDED_PATHS))
    if not isinstance(allowed_roots_raw, list) or not allowed_roots_raw:
        raise TaxonomyError("taxonomy_registry.json has invalid allowed_roots")
    if not isinstance(excluded_raw, list):
        raise TaxonomyError("taxonomy_registry.json has invalid excluded_paths")

    allowed_roots = {str(value).strip() for value in allowed_roots_raw if str(value).strip()}
    excluded_prefixes = [str(value).strip() for value in excluded_raw if str(value).strip()]
    source_map, group_metadata = _canonical_source_map(registry)

    merged: dict[str, set[str]] = {group: set() for group in group_metadata}
    raw_groups_mapped: set[str] = set()
    excluded_paths: set[str] = set()
    unmapped_paths: set[str] = set()
    source_files = taxonomy_source_files(config_dir)
    if not source_files:
        raise TaxonomyError(f"No keyword_taxonomy*.json files found in {config_dir}")

    for path in source_files:
        data = _read_json(path)
        for raw_path, raw_terms in _iter_leaf_terms(data):
            root = raw_path.split(".", 1)[0]
            if root not in allowed_roots or _is_excluded(raw_path, excluded_prefixes):
                excluded_paths.add(raw_path)
                continue
            canonical_group = source_map.get(raw_path)
            if not canonical_group:
                unmapped_paths.add(raw_path)
                continue
            raw_groups_mapped.add(raw_path)
            normalized = {_norm(term) for term in raw_terms}
            normalized.discard("")
            merged[canonical_group].update(term for term in normalized if len(term) >= 3)

    if unmapped_paths:
        sample = ", ".join(sorted(unmapped_paths)[:20])
        more = "" if len(unmapped_paths) <= 20 else f" (+{len(unmapped_paths) - 20} more)"
        raise TaxonomyError(
            "Unmapped semantic taxonomy paths found. Update taxonomy_registry.json: "
            + sample
            + more
        )

    groups = {
        group: _sorted_terms(terms)
        for group, terms in sorted(merged.items())
        if terms
    }
    primary_order_raw = registry.get(
        "primary_dimension_order", ["domain", "context", "condition", "outcome"]
    )
    primary_order = (
        [str(value) for value in primary_order_raw]
        if isinstance(primary_order_raw, list)
        else ["domain", "context", "condition", "outcome"]
    )
    metadata = {
        "schema_version": int(registry.get("schema_version") or 1),
        "taxonomy_version": str(registry.get("taxonomy_version") or "unknown"),
        "registry_mode": "canonical",
        "registry_path": str(registry_path),
        "primary_dimension_order": primary_order,
        "source_files": [str(path) for path in source_files],
        "raw_groups_mapped": len(raw_groups_mapped),
        "raw_groups_excluded": len(excluded_paths),
        "canonical_groups_loaded": len(groups),
        "canonical_terms_total": sum(len(terms) for terms in groups.values()),
        "excluded_raw_paths": sorted(excluded_paths),
        "group_metadata": {
            group: group_metadata[group]
            for group in groups
            if group in group_metadata
        },
    }
    return groups, metadata
