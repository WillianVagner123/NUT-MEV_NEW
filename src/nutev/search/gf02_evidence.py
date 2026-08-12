"""Auditable evidence containers for the Article 1 GF-02 search-validation gate.

This module records and evaluates *evidence about validation*. It deliberately
never invents sentinel identities, licensed-provider executions, PRESS approval,
or formal/PRISMA eligibility.

The scientific sequence is owned by issues #1010/#1012. GF-02 is a PILOT gate:
records here may support a later human decision to proceed to PRESS, but they do
not become formal identification counts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

GF02_SCHEMA_VERSION = 1
SENTINEL_IDENTITY_STATUSES = ("UNRESOLVED", "RESOLVED")
NOISE_CLASSES = (
    "likely_eligible",
    "possibly_eligible",
    "irrelevant",
    "editorial",
    "commentary",
    "erratum",
    "executive_summary",
    "duplicate_manifestation",
    "wrong_population",
    "wrong_document_type",
)
MANUAL_EXECUTION_STATUSES = ("MANUAL_EXECUTION_REQUIRED", "IMPORTED")
GATE_DECISIONS = ("READY_FOR_PRESS", "NOT_READY_FOR_PRESS")
PRIORITY_SENTINELS = ("NORM-035", "NORM-063")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SentinelRecord:
    """Canonical identity declaration for one known-item sentinel.

    `UNRESOLVED` entries may be stored so missing identity work is explicit, but
    they are never allowed into the recall denominator or recovered count.
    """

    sentinel_id: str
    canonical_title: str = ""
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    issuer: str = ""
    version_year: str = ""
    document_unit_rule: str = ""
    relationship_notes: str = ""
    expected_routes: tuple[str, ...] = ()
    identity_status: str = "UNRESOLVED"
    allow_title_match: bool = False


@dataclass(frozen=True)
class NoiseSampleRecord:
    sample_id: str
    record_id: str
    provider: str
    strategy_version: str
    sampling_rule: str
    classification: str
    reviewer: str
    note: str = ""


@dataclass(frozen=True)
class ManualProviderEvidence:
    provider: str
    status: str
    expression: str = ""
    executed_at: str = ""
    executor: str = ""
    interface_name: str = ""
    total_reported: int | None = None
    export_file: str = ""
    export_sha256: str = ""
    sentinel_results: dict[str, bool | None] = field(default_factory=dict)
    limitations: str = ""


def default_gf02_dir(project_root: Path) -> Path:
    return Path(project_root) / "07_logs" / "gf02"


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_doi(value: object) -> str:
    text = _clean_text(value).casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    return text


def _normalize_pmid(value: object) -> str:
    text = _clean_text(value).casefold()
    if text.startswith("pmid:"):
        text = text[5:].strip()
    return text


def _normalize_pmcid(value: object) -> str:
    text = _clean_text(value).upper()
    if text.startswith("PMCID:"):
        text = text[6:].strip()
    return text


def _normalize_title(value: object) -> str:
    text = _clean_text(value).casefold()
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace())


def _row_value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return _clean_text(value)
    return ""


def _has_explicit_identifier(sentinel: SentinelRecord) -> bool:
    return bool(sentinel.doi.strip() or sentinel.pmid.strip() or sentinel.pmcid.strip())


def _fallback_identity_complete(sentinel: SentinelRecord) -> bool:
    return bool(
        sentinel.canonical_title.strip()
        and sentinel.issuer.strip()
        and sentinel.version_year.strip()
        and sentinel.document_unit_rule.strip()
    )


def sentinel_identity_complete(sentinel: SentinelRecord) -> bool:
    """Return whether a sentinel has enough declared identity to be audited."""
    if not sentinel.sentinel_id.strip() or not sentinel.canonical_title.strip():
        return False
    return _has_explicit_identifier(sentinel) or _fallback_identity_complete(sentinel)


def validate_sentinel_registry(records: Iterable[SentinelRecord]) -> list[SentinelRecord]:
    """Validate IDs and resolved-identity claims without filling missing science."""
    validated = list(records)
    seen: set[str] = set()
    for record in validated:
        sentinel_id = record.sentinel_id.strip()
        if not sentinel_id:
            raise ValueError("sentinel_id is required")
        key = sentinel_id.casefold()
        if key in seen:
            raise ValueError(f"duplicate sentinel_id: {sentinel_id}")
        seen.add(key)

        status = record.identity_status.strip().upper()
        if status not in SENTINEL_IDENTITY_STATUSES:
            raise ValueError(
                f"identity_status for {sentinel_id} must be one of "
                f"{SENTINEL_IDENTITY_STATUSES}"
            )
        if status == "RESOLVED" and not sentinel_identity_complete(record):
            raise ValueError(
                f"resolved sentinel {sentinel_id} lacks a complete canonical identity"
            )
    return validated


def sentinel_matches_row(sentinel: SentinelRecord, row: dict[str, Any]) -> bool:
    """Conservatively match one resolved sentinel to a retrieved record.

    Explicit DOI/PMID/PMCID identity wins. Title matching is permitted only when
    the sentinel has no explicit bibliographic identifier and the registry has
    explicitly enabled it; issuer/year constraints are then enforced when set.
    """
    if sentinel.identity_status.strip().upper() != "RESOLVED":
        return False
    if not sentinel_identity_complete(sentinel):
        return False

    sentinel_ids = {
        "doi": _normalize_doi(sentinel.doi),
        "pmid": _normalize_pmid(sentinel.pmid),
        "pmcid": _normalize_pmcid(sentinel.pmcid),
    }
    row_ids = {
        "doi": _normalize_doi(_row_value(row, "doi", "DOI")),
        "pmid": _normalize_pmid(_row_value(row, "pmid", "PMID")),
        "pmcid": _normalize_pmcid(_row_value(row, "pmcid", "PMCID")),
    }
    explicit = [(kind, value) for kind, value in sentinel_ids.items() if value]
    if explicit:
        return any(row_ids[kind] and row_ids[kind] == value for kind, value in explicit)

    if not sentinel.allow_title_match:
        return False
    if _normalize_title(_row_value(row, "title", "document_title")) != _normalize_title(
        sentinel.canonical_title
    ):
        return False

    if sentinel.issuer.strip():
        row_issuer = _row_value(row, "issuer", "publisher", "institution")
        if not row_issuer or row_issuer.casefold() != sentinel.issuer.strip().casefold():
            return False
    if sentinel.version_year.strip():
        row_year = _row_value(row, "year", "publication_year", "version_year")
        if not row_year or row_year != sentinel.version_year.strip():
            return False
    return True


def compute_sentinel_recall(
    records: Iterable[SentinelRecord],
    retrieved_rows: Iterable[dict[str, Any]],
    *,
    provider: str,
    strategy_version: str,
    route: str,
) -> dict[str, Any]:
    """Compute known-item recall using resolved sentinels only."""
    sentinels = validate_sentinel_registry(records)
    rows = list(retrieved_rows)

    resolved = [s for s in sentinels if s.identity_status.strip().upper() == "RESOLVED"]
    unresolved = [s for s in sentinels if s.identity_status.strip().upper() != "RESOLVED"]
    recovered_ids = [
        s.sentinel_id for s in resolved if any(sentinel_matches_row(s, row) for row in rows)
    ]
    missing_ids = [s.sentinel_id for s in resolved if s.sentinel_id not in recovered_ids]
    denominator = len(resolved)
    recovered = len(recovered_ids)

    return {
        "schema_version": GF02_SCHEMA_VERSION,
        "provider": provider.strip(),
        "strategy_version": strategy_version.strip(),
        "route": route.strip(),
        "sentinels_declared": len(sentinels),
        "sentinels_resolved": denominator,
        "sentinels_unresolved": len(unresolved),
        "recovered": recovered,
        "recall": (recovered / denominator) if denominator else None,
        "recovered_sentinel_ids": recovered_ids,
        "missing_resolved_sentinel_ids": missing_ids,
        "unresolved_sentinel_ids": [s.sentinel_id for s in unresolved],
    }


def validate_noise_sample(records: Iterable[NoiseSampleRecord]) -> list[NoiseSampleRecord]:
    validated = list(records)
    seen: set[tuple[str, str]] = set()
    for row in validated:
        if not row.sample_id.strip():
            raise ValueError("noise sample_id is required")
        if not row.record_id.strip():
            raise ValueError("noise record_id is required")
        if not row.provider.strip() or not row.strategy_version.strip():
            raise ValueError("noise provider and strategy_version are required")
        if not row.sampling_rule.strip():
            raise ValueError("noise sampling_rule is required")
        if not row.reviewer.strip():
            raise ValueError("noise reviewer is required")
        classification = row.classification.strip().casefold()
        if classification not in NOISE_CLASSES:
            raise ValueError(
                f"noise classification must be one of {NOISE_CLASSES}; got {row.classification!r}"
            )
        key = (row.sample_id.strip(), row.record_id.strip())
        if key in seen:
            raise ValueError(f"duplicate noise sample record: {key}")
        seen.add(key)
    return validated


def summarize_noise_sample(records: Iterable[NoiseSampleRecord]) -> dict[str, Any]:
    """Summarize a frozen sample; likely+possibly eligible form the precision estimate."""
    rows = validate_noise_sample(records)
    counts = {label: 0 for label in NOISE_CLASSES}
    for row in rows:
        counts[row.classification.strip().casefold()] += 1
    sample_size = len(rows)
    relevant = counts["likely_eligible"] + counts["possibly_eligible"]
    precision = (relevant / sample_size) if sample_size else None
    return {
        "schema_version": GF02_SCHEMA_VERSION,
        "sample_size": sample_size,
        "estimated_precision": precision,
        "noise_rate": (1.0 - precision) if precision is not None else None,
        "classification_counts": counts,
        "sample_ids": sorted({row.sample_id for row in rows}),
        "sampling_rules": sorted({row.sampling_rule for row in rows}),
    }


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manual_provider_evidence(
    evidence: ManualProviderEvidence,
) -> ManualProviderEvidence:
    provider = evidence.provider.strip().casefold()
    if provider not in {"scopus", "web_of_science", "web of science", "wos"}:
        raise ValueError("manual provider must be Scopus or Web of Science")
    status = evidence.status.strip().upper()
    if status not in MANUAL_EXECUTION_STATUSES:
        raise ValueError(f"status must be one of {MANUAL_EXECUTION_STATUSES}")
    if evidence.total_reported is not None and evidence.total_reported < 0:
        raise ValueError("total_reported cannot be negative")

    if status == "IMPORTED":
        required = {
            "expression": evidence.expression,
            "executed_at": evidence.executed_at,
            "executor": evidence.executor,
            "interface_name": evidence.interface_name,
            "export_file": evidence.export_file,
            "export_sha256": evidence.export_sha256,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if evidence.total_reported is None:
            missing.append("total_reported")
        if missing:
            raise ValueError(
                "IMPORTED manual execution is missing required evidence: " + ", ".join(missing)
            )
        digest = evidence.export_sha256.strip().casefold()
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError("export_sha256 must be a lowercase/uppercase 64-character SHA-256")
    return evidence


def manual_execution_from_export(
    *,
    provider: str,
    expression: str,
    executed_at: str,
    executor: str,
    interface_name: str,
    total_reported: int,
    export_path: Path,
    sentinel_results: dict[str, bool | None] | None = None,
    limitations: str = "",
) -> ManualProviderEvidence:
    """Create IMPORTED evidence from a real local export and its SHA-256."""
    path = Path(export_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    evidence = ManualProviderEvidence(
        provider=provider,
        status="IMPORTED",
        expression=expression.strip(),
        executed_at=executed_at.strip(),
        executor=executor.strip(),
        interface_name=interface_name.strip(),
        total_reported=int(total_reported),
        export_file=path.name,
        export_sha256=sha256_file(path),
        sentinel_results=dict(sentinel_results or {}),
        limitations=limitations.strip(),
    )
    return validate_manual_provider_evidence(evidence)


def validate_gf02_pilot_strategy(strategy_version: dict[str, Any]) -> None:
    """Guard against GF-02 validation artifacts being treated as formal PRISMA runs."""
    search_type = str(strategy_version.get("search_type") or "").strip().upper()
    prisma_eligible = bool(strategy_version.get("prisma_eligible"))
    if search_type != "PILOT":
        raise ValueError("GF-02 validation must reference a PILOT strategy version")
    if prisma_eligible:
        raise ValueError("GF-02 PILOT strategy must not be PRISMA-eligible")


def _manual_provider_complete(
    evidence: ManualProviderEvidence | None,
    *,
    priority_sentinels: tuple[str, ...],
) -> bool:
    if evidence is None:
        return False
    try:
        validate_manual_provider_evidence(evidence)
    except ValueError:
        return False
    if evidence.status.strip().upper() != "IMPORTED":
        return False
    # A false result is still valid evidence; None/missing means the sentinel
    # assessment itself has not been completed for that provider.
    return all(
        sentinel_id in evidence.sentinel_results
        and evidence.sentinel_results[sentinel_id] is not None
        for sentinel_id in priority_sentinels
    )


def evaluate_gf02_gate(
    *,
    strategy_version: dict[str, Any],
    pubmed_recall: dict[str, Any],
    noise_summary: dict[str, Any],
    scopus_evidence: ManualProviderEvidence | None,
    wos_evidence: ManualProviderEvidence | None,
    priority_sentinels: tuple[str, ...] = PRIORITY_SENTINELS,
    human_decision: str | None = None,
    human_decision_by: str = "",
) -> dict[str, Any]:
    """Evaluate completeness while reserving READY_FOR_PRESS for a human decision."""
    blockers: list[str] = []
    try:
        validate_gf02_pilot_strategy(strategy_version)
    except ValueError as exc:
        blockers.append(str(exc))

    unresolved = set(pubmed_recall.get("unresolved_sentinel_ids") or [])
    recovered = set(pubmed_recall.get("recovered_sentinel_ids") or [])
    missing = set(pubmed_recall.get("missing_resolved_sentinel_ids") or [])
    for sentinel_id in priority_sentinels:
        if sentinel_id in unresolved:
            blockers.append(f"{sentinel_id}:identity_unresolved")
        elif sentinel_id not in recovered and sentinel_id not in missing:
            blockers.append(f"{sentinel_id}:pubmed_assessment_missing")

    if int(noise_summary.get("sample_size") or 0) <= 0:
        blockers.append("noise_sample_missing")
    if not _manual_provider_complete(scopus_evidence, priority_sentinels=priority_sentinels):
        blockers.append("scopus_manual_evidence_incomplete")
    if not _manual_provider_complete(wos_evidence, priority_sentinels=priority_sentinels):
        blockers.append("wos_manual_evidence_incomplete")

    normalized_decision = (human_decision or "").strip().upper()
    if normalized_decision and normalized_decision not in GATE_DECISIONS:
        raise ValueError(f"human_decision must be one of {GATE_DECISIONS}")
    if normalized_decision and not human_decision_by.strip():
        raise ValueError("human_decision_by is required when a human_decision is recorded")

    evidence_complete = not blockers
    if not evidence_complete:
        decision = "NOT_READY_FOR_PRESS"
    elif not normalized_decision:
        decision = "EVIDENCE_COMPLETE_AWAITING_HUMAN_DECISION"
    else:
        decision = normalized_decision

    return {
        "schema_version": GF02_SCHEMA_VERSION,
        "gate": "GF-02",
        "evidence_complete": evidence_complete,
        "decision": decision,
        "human_decision": normalized_decision or None,
        "human_decision_by": human_decision_by.strip() or None,
        "blockers": blockers,
        "priority_sentinels": list(priority_sentinels),
        "press_approval_inferred": False,
        "formal_execution_authorized": False,
        "prisma_eligible": False,
    }


def _json_default(value: object) -> object:
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _write_json(path: Path, payload: object) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default)
        + "\n",
        encoding="utf-8",
    )
    return target


def save_sentinel_registry(
    path: Path,
    *,
    suite_version: str,
    records: Iterable[SentinelRecord],
    created_by: str,
    notes: str = "",
) -> Path:
    validated = validate_sentinel_registry(records)
    if not suite_version.strip():
        raise ValueError("suite_version is required")
    if not created_by.strip():
        raise ValueError("created_by is required")
    payload = {
        "schema_version": GF02_SCHEMA_VERSION,
        "suite_version": suite_version.strip(),
        "created_by": created_by.strip(),
        "notes": notes.strip(),
        "sentinels": [asdict(record) for record in validated],
    }
    return _write_json(path, payload)


def save_recall_report(path: Path, report: dict[str, Any]) -> Path:
    return _write_json(path, report)


def save_noise_sample(path: Path, records: Iterable[NoiseSampleRecord]) -> Path:
    validated = validate_noise_sample(records)
    payload = {
        "schema_version": GF02_SCHEMA_VERSION,
        "records": [asdict(record) for record in validated],
        "summary": summarize_noise_sample(validated),
    }
    return _write_json(path, payload)


def save_manual_provider_evidence(
    path: Path, evidence: Iterable[ManualProviderEvidence]
) -> Path:
    validated = [validate_manual_provider_evidence(item) for item in evidence]
    payload = {
        "schema_version": GF02_SCHEMA_VERSION,
        "executions": [asdict(item) for item in validated],
    }
    return _write_json(path, payload)


def save_gate_status(path: Path, status: dict[str, Any]) -> Path:
    if status.get("gate") != "GF-02":
        raise ValueError("gate status must describe GF-02")
    return _write_json(path, status)
