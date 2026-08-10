import csv
from collections.abc import Iterable, Sequence
from pathlib import Path


WATCH_RESULT_FIELDS = [
    "document_id",
    "title",
    "abstract",
    "snippet",
    "url",
    "doi",
    "year",
    "source_provider",
    "category",
    "query",
    "evidence_type",
    "workstream_affinity",
    "matched_categories",
    "matched_providers",
    "download_status",
    "capture_status",
    "artifact_paths",
    "relevance_score",
    "watch_score",
    "novelty_score",
    "is_new",
    "is_new_to_system",
    "is_recent_publication",
    "fallback_used",
    "failure_reason",
    "http_status",
    "host",
    "webhook_included",
]

PROVIDER_PERFORMANCE_FIELDS = ["provider", "hits", "captured"]
HOST_FAILURE_FIELDS = ["host", "failure_reason", "http_status"]
CAPTURE_MANIFEST_FIELDS = [
    "document_id",
    "download_status",
    "capture_status",
    "artifact_paths",
]


def _fieldnames(rows: Iterable[dict], preferred_fields: Sequence[str]) -> list[str]:
    preferred = list(dict.fromkeys(preferred_fields))
    extras = sorted({key for row in rows for key in row.keys()} - set(preferred))
    return [*preferred, *extras]


def _write_csv(rows, path: Path, fieldnames: Sequence[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized_rows = list(rows)
    keys = _fieldnames(materialized_rows, fieldnames or [])
    if not keys and materialized_rows:
        keys = sorted({key for row in materialized_rows for key in row.keys()})

    with path.open("w", newline="", encoding="utf-8") as handle:
        if not keys:
            return
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized_rows)


def export_watch_outputs(
    rows,
    new_rows,
    base_dir,
    run_dir,
    provider_perf=None,
    host_failures=None,
    capture_manifest=None,
):
    _write_csv(rows, base_dir / "global_watch_master.csv", WATCH_RESULT_FIELDS)
    _write_csv(new_rows, base_dir / "global_watch_new_items.csv", WATCH_RESULT_FIELDS)
    _write_csv(rows, run_dir / "global_watch_results.csv", WATCH_RESULT_FIELDS)
    _write_csv(new_rows, run_dir / "global_watch_new_items.csv", WATCH_RESULT_FIELDS)
    _write_csv(
        provider_perf or [],
        run_dir / "provider_performance.csv",
        PROVIDER_PERFORMANCE_FIELDS,
    )
    _write_csv(host_failures or [], run_dir / "host_failures.csv", HOST_FAILURE_FIELDS)
    _write_csv(
        capture_manifest or [],
        run_dir / "capture_manifest.csv",
        CAPTURE_MANIFEST_FIELDS,
    )
