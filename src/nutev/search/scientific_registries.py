"""Validation views for institutional sources and guideline repositories.

The module evolves existing NutEV configuration instead of creating a second
search engine. Candidate entries may be incomplete while they are being audited;
formal/frozen entries must carry enough operational metadata to be reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable
from urllib.parse import urlparse

from nutev.engine.validators import validate_workstream

SOURCE_STATUSES = {"CANDIDATE", "PILOT", "FROZEN", "EXCLUDED", "QA_ONLY"}
REPOSITORY_PILOT_STATUSES = {"PENDING", "PILOT", "COMPLETED", "BLOCKED"}
REPOSITORY_FORMAL_STATUSES = {"NOT_AUTHORIZED", "AUTHORIZED", "EXECUTED"}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _stable_source_id(name: str, url: str) -> str:
    digest = sha256(f"{name.strip()}|{url.strip()}".encode("utf-8")).hexdigest()[:12]
    return f"SRC-{digest.upper()}"


@dataclass(frozen=True)
class SourceRegistryRecord:
    source_id: str
    source_class: str
    organization: str
    geographic_scope: str
    eligible_evidence_families: tuple[str, ...] = ()
    inclusion_rule: str = ""
    naming_rule: str = ""
    search_mechanism: str = ""
    base_terms: tuple[str, ...] = ()
    stopping_rule: str = ""
    version_rule: str = ""
    sentinel_relationship: str = ""
    independent_of_sentinels: bool = True
    status: str = "CANDIDATE"
    canonical_url: str = ""
    verification_date: str = ""
    reviewer: str = ""
    safety_note: str = ""
    analytical_labels: tuple[str, ...] = ()
    display_name: str = ""


@dataclass(frozen=True)
class GuidelineRepositoryRecord:
    repository_id: str
    repository_name: str
    scope: str
    country_or_region: str = ""
    search_interface: str = ""
    filters: tuple[str, ...] = ()
    query_terms: tuple[str, ...] = ()
    stopping_rule: str = ""
    version_rule: str = ""
    pilot_status: str = "PENDING"
    formal_status: str = "NOT_AUTHORIZED"
    access_limitations: str = ""
    notes: str = ""


def validate_source_record(record: SourceRegistryRecord) -> SourceRegistryRecord:
    status = record.status.strip().upper()
    if status not in SOURCE_STATUSES:
        raise ValueError(f"invalid source status: {record.status}")
    if not record.source_id.strip() or not record.display_name.strip():
        raise ValueError("source_id and display_name are required")
    if not _valid_http_url(record.canonical_url.strip()):
        raise ValueError(f"invalid canonical_url for {record.source_id}")

    if status == "FROZEN":
        required = {
            "source_class": record.source_class,
            "organization": record.organization,
            "geographic_scope": record.geographic_scope,
            "inclusion_rule": record.inclusion_rule,
            "naming_rule": record.naming_rule,
            "search_mechanism": record.search_mechanism,
            "stopping_rule": record.stopping_rule,
            "version_rule": record.version_rule,
            "verification_date": record.verification_date,
            "reviewer": record.reviewer,
        }
        missing = [name for name, value in required.items() if not _clean(value)]
        if not record.eligible_evidence_families:
            missing.append("eligible_evidence_families")
        if missing:
            raise ValueError(
                f"frozen source {record.source_id} lacks reproducibility fields: "
                + ", ".join(missing)
            )
    return record


def source_records_from_official_manifest(manifest: dict[str, Any]) -> list[SourceRegistryRecord]:
    """Build a deduplicated candidate registry view from the existing manifest.

    Missing methodological fields are kept empty and therefore cannot be
    promoted to FROZEN accidentally. Historical workstream keys are normalized
    to semantic analytical labels at ingest.
    """
    groups = manifest.get("workstreams", {}) if isinstance(manifest, dict) else {}
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    if not isinstance(groups, dict):
        return []

    for raw_label, sources in groups.items():
        canonical_label = validate_workstream(str(raw_label))
        if not canonical_label or not isinstance(sources, list):
            continue
        for source in sources:
            if not isinstance(source, dict):
                continue
            name = _clean(source.get("name") or source.get("title"))
            url = _clean(source.get("url"))
            if not name or not _valid_http_url(url):
                continue
            key = (name.casefold(), url.casefold().rstrip("/"))
            item = by_key.setdefault(
                key,
                {
                    "name": name,
                    "url": url,
                    "organization": _clean(
                        source.get("institution") or source.get("authority_name")
                    ),
                    "labels": set(),
                },
            )
            item["labels"].add(canonical_label)

    records: list[SourceRegistryRecord] = []
    for item in by_key.values():
        record = SourceRegistryRecord(
            source_id=_stable_source_id(item["name"], item["url"]),
            source_class="official_institutional",
            organization=item["organization"],
            geographic_scope="",
            status="CANDIDATE",
            canonical_url=item["url"],
            analytical_labels=tuple(sorted(item["labels"])),
            display_name=item["name"],
            safety_note="Candidate imported from official_sources_manifest; freeze requires verified operational rules.",
        )
        records.append(validate_source_record(record))
    return sorted(records, key=lambda row: row.source_id)


def validate_guideline_repository_record(
    record: GuidelineRepositoryRecord,
) -> GuidelineRepositoryRecord:
    if not record.repository_id.strip() or not record.repository_name.strip():
        raise ValueError("repository_id and repository_name are required")
    pilot = record.pilot_status.strip().upper()
    formal = record.formal_status.strip().upper()
    if pilot not in REPOSITORY_PILOT_STATUSES:
        raise ValueError(f"invalid pilot_status for {record.repository_id}: {record.pilot_status}")
    if formal not in REPOSITORY_FORMAL_STATUSES:
        raise ValueError(f"invalid formal_status for {record.repository_id}: {record.formal_status}")

    if formal in {"AUTHORIZED", "EXECUTED"}:
        required = {
            "scope": record.scope,
            "search_interface": record.search_interface,
            "stopping_rule": record.stopping_rule,
            "version_rule": record.version_rule,
        }
        missing = [name for name, value in required.items() if not _clean(value)]
        if not record.query_terms:
            missing.append("query_terms")
        if missing:
            raise ValueError(
                f"formal repository {record.repository_id} lacks reproducibility fields: "
                + ", ".join(missing)
            )
    return record


def guideline_repository_records(payload: dict[str, Any]) -> list[GuidelineRepositoryRecord]:
    rows = payload.get("repositories", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        raise ValueError("repositories must be a list")
    records: list[GuidelineRepositoryRecord] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("repository row must be an object")
        record = GuidelineRepositoryRecord(
            repository_id=_clean(row.get("repository_id")),
            repository_name=_clean(row.get("repository_name")),
            scope=_clean(row.get("scope")),
            country_or_region=_clean(row.get("country_or_region")),
            search_interface=_clean(row.get("search_interface")),
            filters=tuple(_clean(x) for x in row.get("filters", []) if _clean(x)),
            query_terms=tuple(_clean(x) for x in row.get("query_terms", []) if _clean(x)),
            stopping_rule=_clean(row.get("stopping_rule")),
            version_rule=_clean(row.get("version_rule")),
            pilot_status=_clean(row.get("pilot_status")) or "PENDING",
            formal_status=_clean(row.get("formal_status")) or "NOT_AUTHORIZED",
            access_limitations=_clean(row.get("access_limitations")),
            notes=_clean(row.get("notes")),
        )
        key = record.repository_id.casefold()
        if key in seen:
            raise ValueError(f"duplicate repository_id: {record.repository_id}")
        seen.add(key)
        records.append(validate_guideline_repository_record(record))
    return records


def registry_freeze_blockers(
    sources: Iterable[SourceRegistryRecord],
    repositories: Iterable[GuidelineRepositoryRecord],
) -> list[str]:
    """Return explicit blockers; never promote candidate registry data silently."""
    blockers: list[str] = []
    source_rows = list(sources)
    repo_rows = list(repositories)
    if not source_rows:
        blockers.append("source_registry_empty")
    for source in source_rows:
        if source.status.strip().upper() == "FROZEN":
            try:
                validate_source_record(source)
            except ValueError as exc:
                blockers.append(str(exc))
        elif source.status.strip().upper() not in {"EXCLUDED", "QA_ONLY"}:
            blockers.append(f"{source.source_id}:source_not_frozen")

    if not repo_rows:
        blockers.append("guideline_repository_registry_empty")
    for repo in repo_rows:
        if repo.formal_status.strip().upper() not in {"AUTHORIZED", "EXECUTED"}:
            blockers.append(f"{repo.repository_id}:formal_not_authorized")
        else:
            try:
                validate_guideline_repository_record(repo)
            except ValueError as exc:
                blockers.append(str(exc))
    return blockers


__all__ = [
    "GuidelineRepositoryRecord",
    "SourceRegistryRecord",
    "guideline_repository_records",
    "registry_freeze_blockers",
    "source_records_from_official_manifest",
    "validate_guideline_repository_record",
    "validate_source_record",
]
