#!/usr/bin/env python3
"""Read-only integrity audit for completed selective deepening batches."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable


PIPELINE_VERSION = "oa_resolver_v3_fallback_probe"
STAGE_MANIFESTS = (
    "export/SCIENTIFIC_EXPORT_MANIFEST.json",
    "enrichment/ENRICHMENT_MANIFEST.json",
    "core/CORE_MANIFEST.json",
    "semantic/SEMANTIC_MANIFEST.json",
    "excerpts/EXCERPT_MANIFEST.json",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_sha_pairs(value: Any) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        path_value = value.get("path")
        sha_value = value.get("sha256")
        if isinstance(path_value, str) and isinstance(sha_value, str):
            yield path_value, sha_value
        for child in value.values():
            yield from _path_sha_pairs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _path_sha_pairs(child)


def _resolve_declared_path(raw: str, manifest_path: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    candidate = manifest_path.parent / path
    if candidate.exists():
        return candidate
    return Path(raw).resolve()


def audit_deepening(output_root: Path, search_id: str, tier: str) -> dict[str, Any]:
    output_root = output_root.resolve()
    tier = tier.upper()
    tier_root = output_root / "scientific" / "deepening" / search_id / f"tier-{tier}"
    top_manifest_path = tier_root / "DEEPENING_MANIFEST.json"
    top = _read_json(top_manifest_path)
    target = int(top.get("target_tier_records") or 0)
    if target < 1:
        raise ValueError("DEEPENING_MANIFEST has no positive target_tier_records")

    errors: list[str] = []
    warnings: list[str] = []
    coverage: list[int] = []
    checked_hashes = 0
    batches = 0

    for batch_manifest_path in sorted((tier_root / "batches").glob("*/BATCH_MANIFEST.json")):
        batch = _read_json(batch_manifest_path)
        if batch.get("status") != "PASS":
            continue
        if batch.get("pipeline_version") != PIPELINE_VERSION:
            continue
        batches += 1
        first = int(batch.get("first_rank") or 0)
        last = int(batch.get("last_rank") or 0)
        documents = int(batch.get("documents") or 0)
        if first < 1 or last < first:
            errors.append(f"invalid rank interval: {batch_manifest_path}")
            continue
        if documents != last - first + 1:
            errors.append(
                f"document/rank count mismatch: {batch_manifest_path}: "
                f"documents={documents}, interval={first}-{last}"
            )
        coverage.extend(range(first, last + 1))

        batch_root = batch_manifest_path.parent
        for relative in STAGE_MANIFESTS:
            manifest_path = batch_root / relative
            if not manifest_path.is_file():
                errors.append(f"missing stage manifest: {manifest_path}")
                continue
            manifest = _read_json(manifest_path)
            pairs = list(_path_sha_pairs(manifest))
            if not pairs:
                warnings.append(f"no path+sha256 declarations found: {manifest_path}")
            for raw_path, expected in pairs:
                artifact_path = _resolve_declared_path(raw_path, manifest_path)
                if not artifact_path.is_file():
                    errors.append(f"missing declared artifact: {artifact_path}")
                    continue
                actual = _sha256(artifact_path)
                checked_hashes += 1
                if actual.lower() != expected.strip().lower():
                    errors.append(
                        f"sha256 mismatch: {artifact_path}: expected={expected}, actual={actual}"
                    )

    expected = list(range(1, target + 1))
    ordered = sorted(coverage)
    missing = sorted(set(expected) - set(coverage))
    duplicates = sorted({rank for rank in coverage if coverage.count(rank) > 1})
    out_of_range = sorted({rank for rank in coverage if rank < 1 or rank > target})
    if ordered != expected:
        if missing:
            errors.append(f"rank coverage has gaps: {missing[:30]}")
        if duplicates:
            errors.append(f"rank coverage has overlaps: {duplicates[:30]}")
        if out_of_range:
            errors.append(f"rank coverage outside 1-{target}: {out_of_range[:30]}")

    return {
        "mode": "NUTEV_DEEPENING_INTEGRITY_AUDIT",
        "status": "PASS" if not errors else "FAIL",
        "search_id": search_id,
        "tier": tier,
        "pipeline_version": PIPELINE_VERSION,
        "target_tier_records": target,
        "v3_batches": batches,
        "rank_coverage_count": len(set(coverage)),
        "checked_sha256_artifacts": checked_hashes,
        "errors": errors,
        "warnings": warnings,
        "read_only": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-id", required=True)
    parser.add_argument("--output-root", default="project_output_reference")
    parser.add_argument("--tier", choices=["A", "B", "C", "D"], default="A")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = audit_deepening(Path(args.output_root), args.search_id, args.tier)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
