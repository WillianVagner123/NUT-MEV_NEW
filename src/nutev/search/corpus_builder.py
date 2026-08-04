"""Build an auditable normalized corpus from immutable search snapshots."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.analysis.dedup import (
    merge_article_rows,
    normalize_title as dedup_normalize_title,
    normalize_url as dedup_normalize_url,
)
from nutev.engine.validators import (
    normalize_doi,
    normalize_pmcid,
    normalize_pmid,
    normalize_url,
    normalize_year,
)
from nutev.export.metadata_tables import write_metadata_csv
from nutev.search.corpus_build_ledger import (
    create_corpus_build,
    finish_corpus_build,
    record_dedup_decisions,
    record_duplicate_candidates,
)
from nutev.search.strategy_execution_ledger import (
    get_search_run,
    list_execution_artifacts,
)
from nutev.search.strategy_registry import (
    default_registry_path,
    get_strategy_version,
)

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
STRONG_KEY_PRIORITY = ("doi", "pmid", "pmcid", "url")
PROVIDER_PRIORITY = {
    "pubmed": 4,
    "europepmc": 3,
    "openalex": 2,
    "crossref": 1,
}


def default_processed_search_root(project_root: Path) -> Path:
    return Path(project_root) / "03_corpus" / "search_processed"


def _safe_component(value: str) -> str:
    return "".join(
        char if char.isalnum() or char in {"-", "_"} else "_" for char in value
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(_canonical_json(row))
            handle.write("\n")
    temporary.replace(path)
    return _sha256_file(path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)
    return _sha256_file(path)


def _atomic_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    return _sha256_file(path)


def _atomic_metadata_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    write_metadata_csv(rows, temporary)
    temporary.replace(path)
    return _sha256_file(path)


def _read_verified_jsonl(
    path: Path,
    expected_sha256: str,
    *,
    provider: str,
) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"snapshot not found for {provider}: {path}")
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"snapshot checksum mismatch for {provider}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid JSONL for {provider} at line {line_number}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"JSONL row for {provider} at line {line_number} is not an object"
                )
            rows.append(value)
    return rows


def _authors_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(
            str(item).strip() for item in value if str(item).strip()
        )
    return str(value).strip()


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return str(value).strip()
    return ""


def _normalize_record(
    row: dict[str, Any],
    *,
    provider: str,
    artifact_id: str,
    run_id: str,
    version_id: str,
    source_row_number: int,
) -> dict[str, Any]:
    raw_url = _first_text(
        row,
        "final_url",
        "resolved_url",
        "original_url",
        "url",
        "oa_url",
    )
    final_url = normalize_url(raw_url) or ""
    title = _first_text(row, "title")
    normalized_title = dedup_normalize_title(title)
    publication_date = _first_text(row, "publication_date")
    normalized_year = normalize_year(
        row.get("year") or publication_date[:4]
    )
    doi = normalize_doi(_first_text(row, "doi")) or ""
    pmid = normalize_pmid(row.get("pmid")) or ""
    pmcid = normalize_pmcid(_first_text(row, "pmcid")) or ""
    identity_payload = {
        "run_id": run_id,
        "artifact_id": artifact_id,
        "provider": provider,
        "source_row_number": source_row_number,
        "row": row,
    }
    source_record_id = (
        "source_record_"
        + sha256(_canonical_json(identity_payload).encode("utf-8")).hexdigest()[:24]
    )

    normalized = dict(row)
    normalized.update(
        {
            "source_record_id": source_record_id,
            "search_run_id": run_id,
            "strategy_version_id": version_id,
            "source_artifact_id": artifact_id,
            "source_row_number": source_row_number,
            "source_provider": provider,
            "source": provider,
            "title": title,
            "title_normalized": normalized_title,
            "doi": doi,
            "pmid": pmid,
            "pmcid": pmcid,
            "original_url": _first_text(row, "original_url", "url", "oa_url"),
            "final_url": final_url,
            "url": final_url or raw_url,
            "year": normalized_year,
            "publication_date": publication_date,
            "journal": _first_text(row, "journal"),
            "article_type": _first_text(row, "article_type", "evidence_type"),
            "authors": _authors_text(row.get("authors")),
            "abstract": _first_text(row, "abstract", "summary", "snippet"),
            "metadata_status": (
                _first_text(row, "metadata_status") or f"{provider}_snapshot"
            ),
            "retrieved_at": _first_text(row, "retrieved_at"),
        }
    )
    return normalized


def _strong_tokens(row: dict[str, Any]) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    if row.get("doi"):
        tokens.append(("doi", str(row["doi"]).lower()))
    if row.get("pmid"):
        tokens.append(("pmid", str(row["pmid"])))
    if row.get("pmcid"):
        tokens.append(("pmcid", str(row["pmcid"]).upper()))
    url_key = dedup_normalize_url(row.get("final_url") or row.get("url"))
    if url_key:
        tokens.append(("url", url_key))
    return tokens


def _title_year_key(row: dict[str, Any]) -> str:
    title = str(row.get("title_normalized") or "").strip()
    year = str(row.get("year") or "").strip()
    return f"{title}|{year}" if title and year else ""


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1


def _record_score(row: dict[str, Any]) -> tuple[int, int, int, int, int]:
    identifiers = sum(
        bool(row.get(key)) for key in ("doi", "pmid", "pmcid")
    )
    metadata_fields = sum(
        bool(row.get(key))
        for key in (
            "title",
            "authors",
            "journal",
            "year",
            "publication_date",
            "article_type",
        )
    )
    abstract_length = len(str(row.get("abstract") or ""))
    url = str(row.get("url") or "").lower()
    url_strength = (
        2
        if "pmc.ncbi.nlm.nih.gov" in url or url.endswith(".pdf")
        else int(bool(url))
    )
    provider_rank = PROVIDER_PRIORITY.get(
        str(row.get("source_provider") or "").lower(),
        0,
    )
    return (
        identifiers,
        metadata_fields,
        abstract_length,
        url_strength,
        provider_rank,
    )


def _cluster_key(cluster: list[dict[str, Any]]) -> tuple[str, str]:
    for key_type in STRONG_KEY_PRIORITY:
        values = sorted(
            {
                value
                for row in cluster
                for kind, value in _strong_tokens(row)
                if kind == key_type
            }
        )
        if values:
            return key_type, values[0]

    title_year = sorted(
        {_title_year_key(row) for row in cluster if _title_year_key(row)}
    )
    if title_year:
        return "title_year", title_year[0]
    source_ids = sorted(str(row["source_record_id"]) for row in cluster)
    return "source_record", source_ids[0]


def _document_id(key_type: str, key_value: str) -> str:
    return (
        "doc_"
        + sha256(f"{key_type}:{key_value}".encode("utf-8")).hexdigest()[:24]
    )


def _best_duplicate_match(
    row: dict[str, Any],
    token_counts: Counter[tuple[str, str]],
) -> tuple[str, str, str]:
    for key_type in STRONG_KEY_PRIORITY:
        for token in _strong_tokens(row):
            if token[0] == key_type and token_counts[token] > 1:
                confidence = (
                    "HIGH"
                    if key_type in {"doi", "pmid", "pmcid"}
                    else "MEDIUM"
                )
                return key_type, token[1], confidence
    key = _title_year_key(row)
    if key:
        return "title_year", key, "LOW"
    return "cluster", "transitive", "MEDIUM"


def _build_master_records(
    normalized_rows: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    union_find = _UnionFind(len(normalized_rows))
    token_owner: dict[tuple[str, str], int] = {}
    for index, row in enumerate(normalized_rows):
        for token in _strong_tokens(row):
            if token in token_owner:
                union_find.union(index, token_owner[token])
            else:
                token_owner[token] = index

    clusters: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(normalized_rows):
        clusters[union_find.find(index)].append(row)

    masters: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for cluster in clusters.values():
        representative = max(cluster, key=_record_score)
        key_type, key_value = _cluster_key(cluster)
        document_id = _document_id(key_type, key_value)
        merged = dict(representative)
        for row in cluster:
            if row is not representative:
                merged = merge_article_rows(merged, row)

        providers = sorted(
            {
                str(row.get("source_provider") or "")
                for row in cluster
                if row.get("source_provider")
            }
        )
        source_ids = [str(row["source_record_id"]) for row in cluster]
        retrieved_dates = [
            str(row.get("retrieved_at") or "")
            for row in cluster
            if row.get("retrieved_at")
        ]
        merged.update(
            {
                "document_id": document_id,
                "canonical_key_type": key_type,
                "canonical_key_value": key_value,
                "source_record_count": len(cluster),
                "duplicate_count": max(0, len(cluster) - 1),
                "source_record_ids": "|".join(source_ids),
                "matched_providers": "|".join(providers),
                "source_provider": (
                    representative.get("source_provider")
                    or (providers[0] if providers else "")
                ),
                "first_seen_date": min(retrieved_dates, default=""),
                "last_seen_date": max(retrieved_dates, default=""),
                "is_new": True,
                "capture_status": merged.get("capture_status") or "missing",
                "download_status": (
                    merged.get("download_status") or "metadata_only"
                ),
                "extraction_status": (
                    merged.get("extraction_status") or "missing"
                ),
            }
        )
        masters.append(merged)

        token_counts: Counter[tuple[str, str]] = Counter(
            token for row in cluster for token in _strong_tokens(row)
        )
        for row in cluster:
            retained = (
                row["source_record_id"] == representative["source_record_id"]
            )
            if retained:
                match_type, match_value, confidence = (
                    key_type,
                    key_value,
                    "HIGH",
                )
            else:
                match_type, match_value, confidence = _best_duplicate_match(
                    row,
                    token_counts,
                )
            decisions.append(
                {
                    "source_record_id": row["source_record_id"],
                    "provider": row["source_provider"],
                    "source_row_number": row["source_row_number"],
                    "master_document_id": document_id,
                    "decision_status": (
                        "RETAINED" if retained else "AUTO_DUPLICATE"
                    ),
                    "match_type": match_type,
                    "match_value": match_value,
                    "confidence": confidence,
                }
            )

    masters.sort(
        key=lambda row: (
            str(row.get("title") or "").casefold(),
            str(row["document_id"]),
        )
    )
    by_title_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in masters:
        key = _title_year_key(row)
        if key:
            by_title_year[key].append(row)

    candidates: list[dict[str, Any]] = []
    for key, group in by_title_year.items():
        if len(group) < 2:
            continue
        group_id = (
            "possible_duplicate_group_"
            + sha256(key.encode("utf-8")).hexdigest()[:16]
        )
        group = sorted(group, key=lambda row: str(row["document_id"]))
        for row in group:
            row["possible_duplicate_group_id"] = group_id
            row["dedup_review_required"] = True
        anchor = group[0]
        for other in group[1:]:
            candidates.append(
                {
                    "left_document_id": anchor["document_id"],
                    "right_document_id": other["document_id"],
                    "match_type": "title_year",
                    "match_value": key,
                    "confidence": "LOW",
                    "review_status": "PENDING_HUMAN_REVIEW",
                }
            )
    for row in masters:
        row.setdefault("possible_duplicate_group_id", "")
        row.setdefault("dedup_review_required", False)
    return masters, decisions, candidates


def build_corpus_from_search_run(
    project_root: Path,
    *,
    run_id: str,
    registry_path: Path | None = None,
    build_id: str | None = None,
    started_at: str | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    db_path = (
        Path(registry_path)
        if registry_path
        else default_registry_path(root)
    )
    run = get_search_run(db_path, run_id)
    if run is None:
        raise ValueError(f"unknown search run: {run_id}")
    if run["status"] == "RUNNING":
        raise ValueError("cannot build a corpus from a running search")
    version = get_strategy_version(db_path, str(run["version_id"]))
    if version is None:
        raise ValueError(f"missing strategy version for run: {run_id}")
    artifacts = list_execution_artifacts(
        db_path,
        run_id=run_id,
        limit=1000,
    )
    if not artifacts:
        raise ValueError("search run has no provider snapshots")

    timestamp = started_at or datetime.now(LOCAL_TIMEZONE).isoformat(
        timespec="seconds"
    )
    build = create_corpus_build(
        db_path,
        run_id=run_id,
        version_id=str(run["version_id"]),
        build_id=build_id,
        started_at=timestamp,
    )
    resolved_build_id = str(build["build_id"])
    build_dir = (
        default_processed_search_root(root)
        / _safe_component(str(run["version_id"]))
        / _safe_component(run_id)
        / _safe_component(resolved_build_id)
    )
    paths: dict[str, str] = {}

    try:
        normalized_rows: list[dict[str, Any]] = []
        input_artifacts: list[dict[str, Any]] = []
        for artifact in sorted(
            artifacts,
            key=lambda item: (
                str(item["provider"]),
                str(item["artifact_id"]),
            ),
        ):
            provider = str(artifact["provider"])
            snapshot_path = Path(str(artifact["snapshot_path"]))
            rows = _read_verified_jsonl(
                snapshot_path,
                str(artifact["snapshot_sha256"]),
                provider=provider,
            )
            input_artifacts.append(
                {
                    "artifact_id": artifact["artifact_id"],
                    "provider": provider,
                    "snapshot_path": str(snapshot_path),
                    "snapshot_sha256": artifact["snapshot_sha256"],
                    "records_loaded": len(rows),
                }
            )
            for source_row_number, row in enumerate(rows, start=1):
                normalized_rows.append(
                    _normalize_record(
                        row,
                        provider=provider,
                        artifact_id=str(artifact["artifact_id"]),
                        run_id=run_id,
                        version_id=str(run["version_id"]),
                        source_row_number=source_row_number,
                    )
                )

        master_rows, decisions, candidates = _build_master_records(
            normalized_rows
        )
        input_records = len(normalized_rows)
        unique_records = len(master_rows)
        duplicates_removed = input_records - unique_records
        prisma_eligible = bool(version["prisma_eligible"])
        metrics = {
            "input_records": input_records,
            "unique_records": unique_records,
            "duplicates_removed": duplicates_removed,
            "possible_duplicates": len(candidates),
            "prisma_records_identified": (
                input_records if prisma_eligible else 0
            ),
            "prisma_duplicates_removed": (
                duplicates_removed if prisma_eligible else 0
            ),
            "prisma_records_after_deduplication": (
                unique_records if prisma_eligible else 0
            ),
        }

        normalized_path = build_dir / "normalized_records.jsonl"
        master_path = build_dir / "master_records.jsonl"
        metadata_path = build_dir / "metadata_master.csv"
        decisions_path = build_dir / "dedup_decisions.csv"
        candidates_path = build_dir / "duplicate_candidates.csv"
        prisma_path = build_dir / "prisma_identification.json"
        manifest_path = build_dir / "corpus_manifest.json"

        output_hashes = {
            "normalized_records_sha256": _atomic_jsonl(
                normalized_path,
                normalized_rows,
            ),
            "master_records_sha256": _atomic_jsonl(
                master_path,
                master_rows,
            ),
            "metadata_master_sha256": _atomic_metadata_csv(
                metadata_path,
                master_rows,
            ),
            "dedup_decisions_sha256": _atomic_csv(
                decisions_path,
                decisions,
                [
                    "source_record_id",
                    "provider",
                    "source_row_number",
                    "master_document_id",
                    "decision_status",
                    "match_type",
                    "match_value",
                    "confidence",
                ],
            ),
            "duplicate_candidates_sha256": _atomic_csv(
                candidates_path,
                candidates,
                [
                    "left_document_id",
                    "right_document_id",
                    "match_type",
                    "match_value",
                    "confidence",
                    "review_status",
                ],
            ),
        }
        prisma_summary = {
            "run_id": run_id,
            "version_id": run["version_id"],
            "build_id": resolved_build_id,
            "search_type": version["search_type"],
            "prisma_eligible": prisma_eligible,
            "records_identified_before_deduplication": input_records,
            "duplicate_records_removed_automatically": duplicates_removed,
            "records_after_automatic_deduplication": unique_records,
            "possible_duplicates_pending_human_review": len(candidates),
            "prisma_records_identified": metrics[
                "prisma_records_identified"
            ],
            "prisma_duplicate_records_removed": metrics[
                "prisma_duplicates_removed"
            ],
            "prisma_records_after_deduplication": metrics[
                "prisma_records_after_deduplication"
            ],
            "screening_not_started": True,
        }
        output_hashes["prisma_identification_sha256"] = _atomic_json(
            prisma_path,
            prisma_summary,
        )
        manifest = {
            "build_id": resolved_build_id,
            "run_id": run_id,
            "version_id": run["version_id"],
            "strategy_id": version["strategy_id"],
            "created_at": timestamp,
            "status": "SUCCEEDED",
            "metrics": metrics,
            "inputs": input_artifacts,
            "outputs": {
                "normalized_jsonl_path": str(normalized_path),
                "master_jsonl_path": str(master_path),
                "metadata_csv_path": str(metadata_path),
                "decisions_csv_path": str(decisions_path),
                "candidates_csv_path": str(candidates_path),
                "prisma_summary_path": str(prisma_path),
                **output_hashes,
            },
            "deduplication_policy": {
                "automatic_exact_keys": list(STRONG_KEY_PRIORITY),
                "title_year": "candidate_only_pending_human_review",
                "transitive_identifier_matching": True,
            },
        }
        manifest_sha256 = _atomic_json(manifest_path, manifest)
        paths = {
            "normalized_jsonl_path": str(normalized_path),
            "master_jsonl_path": str(master_path),
            "metadata_csv_path": str(metadata_path),
            "decisions_csv_path": str(decisions_path),
            "candidates_csv_path": str(candidates_path),
            "prisma_summary_path": str(prisma_path),
            "manifest_path": str(manifest_path),
        }
        record_dedup_decisions(
            db_path,
            build_id=resolved_build_id,
            rows=decisions,
        )
        record_duplicate_candidates(
            db_path,
            build_id=resolved_build_id,
            rows=candidates,
        )
        finished = finish_corpus_build(
            db_path,
            build_id=resolved_build_id,
            status="SUCCEEDED",
            metrics=metrics,
            paths=paths,
            manifest_sha256=manifest_sha256,
        )
        return {
            **finished,
            "metrics": metrics,
            "prisma": prisma_summary,
            "output_hashes": output_hashes,
        }
    except Exception as exc:
        finish_corpus_build(
            db_path,
            build_id=resolved_build_id,
            status="FAILED",
            metrics={},
            paths=paths,
            error_message=str(exc),
        )
        raise
