"""Canonical NutEV CORE record and evidence-bank export.

The CORE is intentionally independent from PRISMA. It materializes one durable,
traceable macro record per article after document enrichment. Human screening,
PRISMA, risk-of-bias, certainty, and recommendations remain optional downstream
workflows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


class NutEVCoreError(RuntimeError):
    """Raised when the CORE bank cannot prove source integrity or schema safety."""


@dataclass(frozen=True, slots=True)
class FindingCandidate:
    """Machine-selected source excerpt that may represent a major article finding.

    This is not an accepted EvidenceClaim. It is a reading/indexing candidate that
    must retain its source locator and provenance.
    """

    id: str
    document_id: str
    section: str
    locator: str | None
    source_excerpt: str
    sentence_sha256: str
    importance_score: float
    signals: tuple[str, ...] = ()
    status: str = "machine_candidate"


@dataclass(frozen=True, slots=True)
class ScoreBlockResult:
    id: str
    label: str
    score: float
    max_score: float
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Scorecard:
    profile_id: str
    profile_version: str
    semantic_kind: str
    status: str
    total_score: float
    max_score: float
    normalized_score: float
    blocks: tuple[ScoreBlockResult, ...]
    guardrail: str


@dataclass(frozen=True, slots=True)
class NutEVCoreRecord:
    """One macro scientific-information record suitable for the future NutEV bank."""

    id: str
    document_id: str
    evidence_record_id: str | None
    schema_version: int
    identity: Mapping[str, Any]
    bibliographic: Mapping[str, Any]
    reference_layer: Mapping[str, Any]
    provenance: Mapping[str, Any]
    acquisition: Mapping[str, Any]
    structure: Mapping[str, Any]
    classification: Mapping[str, Any]
    main_findings: tuple[FindingCandidate, ...]
    scores: Mapping[str, Any]
    workflow: Mapping[str, Any]
    content_refs: Mapping[str, Any]
    guardrails: Mapping[str, Any]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


_FINDING_SECTION_PRIORITY = {
    "results": 6.0,
    "result": 6.0,
    "findings": 6.0,
    "conclusion": 5.0,
    "conclusions": 5.0,
    "discussion": 3.0,
    "abstract": 2.0,
    "document text": 1.0,
}
_FINDING_SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("association", re.compile(r"\b(?:associated|association|correlat(?:ed|ion))\b", re.I)),
    ("increase", re.compile(r"\b(?:increased?|higher|greater|improved?)\b", re.I)),
    ("decrease", re.compile(r"\b(?:decreased?|lower|reduced?|declined?)\b", re.I)),
    ("difference", re.compile(r"\b(?:difference|different|versus|compared with)\b", re.I)),
    ("significance", re.compile(r"\b(?:significant|significantly|p\s*[<=>])\b", re.I)),
    ("effect", re.compile(r"\b(?:effect|odds ratio|risk ratio|hazard ratio|confidence interval)\b", re.I)),
    ("no_effect", re.compile(r"\b(?:no difference|not significant|did not|was not associated)\b", re.I)),
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9À-ÖØ-Þ])")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise NutEVCoreError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NutEVCoreError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise NutEVCoreError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise NutEVCoreError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise NutEVCoreError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise NutEVCoreError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    if not rows:
        raise NutEVCoreError(f"{label} JSONL is empty: {path}")
    return rows


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256_file(path)


def _write_json(path: Path, value: Any) -> str:
    return _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        for row in rows
    )
    return _atomic_text(path, payload)


def _manifest_output_sha(
    manifest: Mapping[str, Any], output_name: str, *, label: str
) -> str:
    value = str(
        (((manifest.get("outputs") or {}).get(output_name) or {}).get("sha256"))
        or ""
    ).strip().lower()
    if not value:
        raise NutEVCoreError(f"{output_name} SHA-256 missing from {label}")
    return value


def _verify_sha(path: Path, expected: str, *, label: str) -> str:
    if not path.is_file():
        raise NutEVCoreError(f"missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise NutEVCoreError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def _verify_sources(
    documents_jsonl: Path,
    evidence_records_jsonl: Path,
    science_manifest_path: Path,
    artifacts_jsonl: Path,
    enrichments_jsonl: Path,
    dossiers_jsonl: Path,
    enrichment_manifest_path: Path,
) -> dict[str, str]:
    science_manifest = _read_json(science_manifest_path)
    if science_manifest.get("export_type") != "NUTEV_SCIENTIFIC_OBJECT_EXPORT":
        raise NutEVCoreError("unexpected scientific export manifest type")
    if science_manifest.get("status") != "PASS":
        raise NutEVCoreError("scientific export manifest is not PASS")

    enrichment_manifest = _read_json(enrichment_manifest_path)
    if enrichment_manifest.get("enrichment_type") != "NUTEV_PRE_SCREENING_DOCUMENT_ENRICHMENT":
        raise NutEVCoreError("unexpected enrichment manifest type")
    if enrichment_manifest.get("status") != "PASS":
        raise NutEVCoreError("enrichment manifest is not PASS")

    return {
        "documents": _verify_sha(
            documents_jsonl,
            _manifest_output_sha(
                science_manifest, "document_candidates", label="scientific manifest"
            ),
            label="document_candidates",
        ),
        "evidence_records": _verify_sha(
            evidence_records_jsonl,
            _manifest_output_sha(
                science_manifest, "evidence_records", label="scientific manifest"
            ),
            label="evidence_records",
        ),
        "artifacts": _verify_sha(
            artifacts_jsonl,
            _manifest_output_sha(
                enrichment_manifest, "full_text_artifacts", label="enrichment manifest"
            ),
            label="full_text_artifacts",
        ),
        "enrichments": _verify_sha(
            enrichments_jsonl,
            _manifest_output_sha(
                enrichment_manifest, "document_enrichments", label="enrichment manifest"
            ),
            label="document_enrichments",
        ),
        "dossiers": _verify_sha(
            dossiers_jsonl,
            _manifest_output_sha(
                enrichment_manifest, "reviewer_dossiers", label="enrichment manifest"
            ),
            label="reviewer_dossiers",
        ),
        "science_manifest": sha256_file(science_manifest_path),
        "enrichment_manifest": sha256_file(enrichment_manifest_path),
    }


def _index_unique(
    rows: Iterable[dict[str, Any]], *, key: str, label: str
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value:
            raise NutEVCoreError(f"{label} row missing {key}")
        if value in indexed:
            raise NutEVCoreError(f"duplicate {label} {key}: {value}")
        indexed[value] = row
    return indexed


def _evidence_by_document(
    rows: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        document_id = str(row.get("document_id") or "").strip()
        if not document_id:
            raise NutEVCoreError("evidence record missing document_id")
        if document_id in indexed:
            raise NutEVCoreError(
                f"multiple evidence records for document are not supported: {document_id}"
            )
        indexed[document_id] = row
    return indexed


def _heading_key(value: Any) -> str:
    return str(value or "").strip().casefold().rstrip(":.")


def _section_flags(enrichment: Mapping[str, Any]) -> dict[str, bool]:
    headings = {
        _heading_key(block.get("heading"))
        for block in (enrichment.get("blocks") or [])
        if isinstance(block, dict)
    }
    return {
        "has_abstract": "abstract" in headings,
        "has_introduction": bool(headings & {"introduction", "background"}),
        "has_methods": bool(
            headings
            & {
                "method",
                "methods",
                "methodology",
                "materials and methods",
                "participants",
                "population",
                "procedures",
            }
        ),
        "has_results": bool(headings & {"result", "results", "findings"}),
        "has_discussion": "discussion" in headings,
        "has_conclusion": bool(headings & {"conclusion", "conclusions"}),
        "has_references": "references" in headings,
    }


def _classification(
    dossier: Mapping[str, Any], enrichment: Mapping[str, Any]
) -> dict[str, Any]:
    signals = enrichment.get("content_signals") or {}
    if not isinstance(signals, dict):
        signals = {}
    designs = [
        str(item).strip().casefold()
        for item in (signals.get("study_design_signals") or [])
        if str(item).strip()
    ]
    joined = " | ".join(designs)
    if "systematic review" in joined or "meta-analysis" in joined or "meta analysis" in joined:
        document_class = "evidence_synthesis"
    elif "scoping review" in joined or "narrative review" in joined:
        document_class = "review"
    elif any(token in joined for token in ("guideline", "consensus statement", "position statement")):
        document_class = "guidance"
    elif "randomized" in joined or "randomised" in joined:
        document_class = "primary_randomized"
    elif any(
        token in joined
        for token in (
            "cohort",
            "cross-sectional",
            "cross sectional",
            "case-control",
            "case control",
        )
    ):
        document_class = "primary_observational"
    elif "qualitative study" in joined:
        document_class = "primary_qualitative"
    else:
        document_class = "unclassified"

    frequent = signals.get("frequent_terms") or []
    topics: list[str] = []
    for item in frequent:
        if isinstance(item, dict) and item.get("term"):
            topics.append(str(item["term"]))
        elif isinstance(item, str) and item.strip():
            topics.append(item.strip())

    flags = _section_flags(enrichment)
    return {
        "document_class": document_class,
        "classification_basis": "explicit_machine_signals"
        if designs
        else "insufficient_signal",
        "article_type_recorded": dossier.get("article_type"),
        "study_design_candidates": designs,
        "topics": topics[:20],
        "sample_size_mentions": list(signals.get("sample_size_mentions") or [])[:30],
        "table_mentions": list(signals.get("table_mentions") or [])[:40],
        "figure_mentions": list(signals.get("figure_mentions") or [])[:40],
        "section_coverage": flags,
        "guardrail": (
            "Classification is a machine indexing aid derived from extracted text/metadata; "
            "it is not an eligibility, risk-of-bias, certainty, or recommendation judgment."
        ),
    }


def _sentence_candidates(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    parts = _SENTENCE_SPLIT_RE.split(normalized)
    return [part.strip() for part in parts if part.strip()]


def _finding_signal_names(sentence: str) -> tuple[str, ...]:
    names = [name for name, pattern in _FINDING_SIGNAL_PATTERNS if pattern.search(sentence)]
    if re.search(r"\b\d+(?:\.\d+)?\s*%\b", sentence):
        names.append("percentage")
    if re.search(r"\b(?:CI|OR|RR|HR)\b", sentence):
        names.append("effect_measure")
    return tuple(dict.fromkeys(names))


def _finding_candidates(
    document_id: str,
    enrichment: Mapping[str, Any],
    *,
    limit: int = 8,
) -> tuple[FindingCandidate, ...]:
    ranked: list[FindingCandidate] = []
    for block in enrichment.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        section = str(block.get("heading") or "Document text").strip()
        section_key = _heading_key(section)
        base = _FINDING_SECTION_PRIORITY.get(section_key, 0.0)
        if base <= 0:
            continue
        locator = str(block.get("locator") or "").strip() or None
        text = str(block.get("text") or "")
        for sentence in _sentence_candidates(text):
            if len(sentence) < 45 or len(sentence) > 900:
                continue
            signal_names = _finding_signal_names(sentence)
            score = base + min(4.0, float(len(signal_names)))
            if re.search(r"\b\d+(?:\.\d+)?\b", sentence):
                score += 0.5
            if not signal_names and base < 5.0:
                continue
            excerpt = sentence[:320].strip()
            digest = sha256(sentence.encode("utf-8")).hexdigest()
            ranked.append(
                FindingCandidate(
                    id=f"finding:{document_id}:{digest[:16]}",
                    document_id=document_id,
                    section=section,
                    locator=locator,
                    source_excerpt=excerpt,
                    sentence_sha256=digest,
                    importance_score=round(score, 2),
                    signals=signal_names,
                )
            )

    unique: dict[str, FindingCandidate] = {}
    for item in sorted(ranked, key=lambda candidate: candidate.importance_score, reverse=True):
        unique.setdefault(item.sentence_sha256, item)
        if len(unique) >= limit:
            break
    return tuple(unique.values())


def _block(
    block_id: str,
    label: str,
    max_score: float,
    earned: Iterable[tuple[float, str, bool]],
) -> ScoreBlockResult:
    score = 0.0
    rationale: list[str] = []
    for points, reason, condition in earned:
        if condition:
            score += points
            rationale.append(f"+{points:g} {reason}")
    return ScoreBlockResult(
        id=block_id,
        label=label,
        score=round(min(score, max_score), 2),
        max_score=max_score,
        rationale=tuple(rationale),
    )


def _core_readiness_score(
    document: Mapping[str, Any],
    evidence: Mapping[str, Any],
    artifact: Mapping[str, Any],
    enrichment: Mapping[str, Any],
    dossier: Mapping[str, Any],
    classification: Mapping[str, Any],
    findings: tuple[FindingCandidate, ...],
) -> Scorecard:
    metadata = document.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    flags = classification.get("section_coverage") or {}
    retrieval_status = str(artifact.get("retrieval_status") or "")
    extraction_method = str(enrichment.get("extraction_method") or "")
    text_chars = int(enrichment.get("text_chars") or 0)
    topics = classification.get("topics") or []
    sample_mentions = classification.get("sample_size_mentions") or []
    table_mentions = classification.get("table_mentions") or []
    figure_mentions = classification.get("figure_mentions") or []

    identity = _block(
        "identity_traceability",
        "Identity and traceability",
        20.0,
        (
            (4.0, "title present", bool(document.get("title"))),
            (4.0, "source provider present", bool(document.get("source_provider"))),
            (6.0, "DOI or PMID present", bool(document.get("doi") or document.get("pmid"))),
            (2.0, "URL present", bool(document.get("url"))),
            (2.0, "year present", document.get("year") not in (None, "")),
            (2.0, "evidence provenance record present", bool(evidence.get("id"))),
        ),
    )
    access = _block(
        "document_access",
        "Document access and extraction",
        20.0,
        (
            (8.0, "full document retrieved", retrieval_status == "retrieved"),
            (5.0, "partial document material retrieved", retrieval_status == "partial"),
            (4.0, "full-text extraction method used", extraction_method not in {"", "unavailable", "abstract_only"}),
            (1.0, "abstract-only text available", extraction_method == "abstract_only"),
            (4.0, "substantial extracted text", text_chars >= 5000),
            (2.0, "moderate extracted text", 1000 <= text_chars < 5000),
            (1.0, "some extracted text", 0 < text_chars < 1000),
            (4.0, "extracted text hash present", bool(enrichment.get("text_sha256"))),
        ),
    )
    structure = _block(
        "structural_mapping",
        "Structural mapping",
        20.0,
        (
            (5.0, "methods section detected", bool(flags.get("has_methods"))),
            (5.0, "results/findings section detected", bool(flags.get("has_results"))),
            (4.0, "discussion/conclusion detected", bool(flags.get("has_discussion") or flags.get("has_conclusion"))),
            (3.0, "four or more text blocks mapped", len(enrichment.get("blocks") or []) >= 4),
            (3.0, "table or figure references detected", bool(table_mentions or figure_mentions)),
        ),
    )
    classification_block = _block(
        "classification_metadata",
        "Classification metadata",
        20.0,
        (
            (4.0, "article type recorded", bool(dossier.get("article_type"))),
            (6.0, "study-design candidate detected", bool(classification.get("study_design_candidates"))),
            (4.0, "sample-size signal detected", bool(sample_mentions)),
            (3.0, "topic terms available", len(topics) >= 5),
            (3.0, "journal or authors recorded", bool(dossier.get("journal") or dossier.get("authors"))),
        ),
    )
    finding_block = _block(
        "finding_traceability",
        "Finding traceability",
        20.0,
        (
            (8.0, "at least one finding candidate", len(findings) >= 1),
            (4.0, "three or more finding candidates", len(findings) >= 3),
            (4.0, "all finding candidates have locators", bool(findings) and all(item.locator for item in findings)),
            (4.0, "result/conclusion finding candidate present", any(_heading_key(item.section) in {"result", "results", "findings", "conclusion", "conclusions"} for item in findings)),
        ),
    )

    blocks = (identity, access, structure, classification_block, finding_block)
    total = round(sum(block.score for block in blocks), 2)
    maximum = round(sum(block.max_score for block in blocks), 2)
    normalized = round((total / maximum) * 100.0, 2) if maximum else 0.0
    return Scorecard(
        profile_id="NUTEV_CORE_READINESS",
        profile_version="1",
        semantic_kind="technical_record_readiness",
        status="scored",
        total_score=total,
        max_score=maximum,
        normalized_score=normalized,
        blocks=blocks,
        guardrail=(
            "This score measures completeness/traceability of the NutEV CORE record. "
            "It is not evidence quality, risk of bias, certainty, eligibility, or recommendation strength."
        ),
    )


def _resolve_field(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, Mapping):
            current = current.get(part)
        else:
            return None
    return current


def _rule_matches(actual: Any, rule: Mapping[str, Any]) -> bool:
    operator = str(rule.get("operator") or "present")
    expected = rule.get("value")
    if operator == "present":
        return actual not in (None, "", [], {}, ())
    if operator == "truthy":
        return bool(actual)
    if operator == "equals":
        return actual == expected
    if operator == "contains":
        if isinstance(actual, str):
            return str(expected).casefold() in actual.casefold()
        if isinstance(actual, (list, tuple, set)):
            return expected in actual
        return False
    if operator == "count_gte":
        try:
            return len(actual) >= int(expected)
        except (TypeError, ValueError):
            return False
    if operator == "numeric_gte":
        try:
            return float(actual) >= float(expected)
        except (TypeError, ValueError):
            return False
    raise NutEVCoreError(f"unsupported score rule operator: {operator}")


def _score_configured_profile(
    record: Mapping[str, Any], profile: Mapping[str, Any]
) -> Scorecard:
    profile_id = str(profile.get("profile_id") or "").strip()
    version = str(profile.get("version") or "").strip()
    blocks_raw = profile.get("blocks")
    if not profile_id or not version or not isinstance(blocks_raw, list) or not blocks_raw:
        raise NutEVCoreError(
            "MEV profile requires profile_id, version, and non-empty blocks"
        )

    blocks: list[ScoreBlockResult] = []
    for index, raw in enumerate(blocks_raw, start=1):
        if not isinstance(raw, dict):
            raise NutEVCoreError(f"MEV block {index} must be an object")
        block_id = str(raw.get("id") or "").strip()
        label = str(raw.get("label") or block_id).strip()
        try:
            max_score = float(raw.get("max_score"))
        except (TypeError, ValueError) as exc:
            raise NutEVCoreError(f"MEV block {index} max_score must be numeric") from exc
        if not block_id or max_score <= 0:
            raise NutEVCoreError(f"MEV block {index} requires id and max_score > 0")
        rules = raw.get("rules") or []
        if not isinstance(rules, list):
            raise NutEVCoreError(f"MEV block {block_id} rules must be a list")

        score = 0.0
        rationale: list[str] = []
        for rule_index, rule in enumerate(rules, start=1):
            if not isinstance(rule, dict):
                raise NutEVCoreError(
                    f"MEV block {block_id} rule {rule_index} must be an object"
                )
            field_path = str(rule.get("field") or "").strip()
            try:
                points = float(rule.get("points") or 0)
            except (TypeError, ValueError) as exc:
                raise NutEVCoreError(
                    f"MEV block {block_id} rule {rule_index} points must be numeric"
                ) from exc
            if not field_path or points < 0:
                raise NutEVCoreError(
                    f"MEV block {block_id} rule {rule_index} requires field and points >= 0"
                )
            actual = _resolve_field(record, field_path)
            if _rule_matches(actual, rule):
                score += points
                rationale.append(
                    f"+{points:g} {field_path} {rule.get('operator', 'present')}"
                )
        blocks.append(
            ScoreBlockResult(
                id=block_id,
                label=label,
                score=round(min(score, max_score), 2),
                max_score=max_score,
                rationale=tuple(rationale),
            )
        )

    total = round(sum(block.score for block in blocks), 2)
    maximum = round(sum(block.max_score for block in blocks), 2)
    normalized = round((total / maximum) * 100.0, 2) if maximum else 0.0
    return Scorecard(
        profile_id=profile_id,
        profile_version=version,
        semantic_kind=str(profile.get("semantic_kind") or "configured_mev_score"),
        status="scored_configured_profile",
        total_score=total,
        max_score=maximum,
        normalized_score=normalized,
        blocks=tuple(blocks),
        guardrail=(
            "NutEV executed a versioned external scoring profile. The scientific meaning "
            "of the score comes from that profile; the engine does not invent or validate MEV semantics."
        ),
    )


def _record_dict(record: NutEVCoreRecord) -> dict[str, Any]:
    return asdict(record)


def _record_sha(record: Mapping[str, Any]) -> str:
    payload = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _write_sqlite(
    path: Path,
    records: Iterable[dict[str, Any]],
    findings: Iterable[dict[str, Any]],
    scorecards: Iterable[dict[str, Any]],
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    if tmp.exists():
        tmp.unlink()
    connection = sqlite3.connect(tmp)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=DELETE;
            CREATE TABLE core_records (
                record_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL UNIQUE,
                schema_version INTEGER NOT NULL,
                title TEXT,
                doi TEXT,
                pmid TEXT,
                year INTEGER,
                source_provider TEXT,
                document_class TEXT,
                full_text_status TEXT,
                extraction_method TEXT,
                ocr_used INTEGER NOT NULL DEFAULT 0,
                core_readiness_score REAL,
                mev_profile_id TEXT,
                mev_total_score REAL,
                record_sha256 TEXT NOT NULL,
                record_json TEXT NOT NULL,
                generated_at TEXT NOT NULL
            );
            CREATE INDEX idx_core_records_doi ON core_records(doi);
            CREATE INDEX idx_core_records_pmid ON core_records(pmid);
            CREATE INDEX idx_core_records_class ON core_records(document_class);

            CREATE TABLE finding_candidates (
                finding_id TEXT PRIMARY KEY,
                record_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                section TEXT,
                locator TEXT,
                source_excerpt TEXT NOT NULL,
                sentence_sha256 TEXT NOT NULL,
                importance_score REAL NOT NULL,
                status TEXT NOT NULL,
                finding_json TEXT NOT NULL,
                FOREIGN KEY(record_id) REFERENCES core_records(record_id)
            );
            CREATE INDEX idx_findings_record ON finding_candidates(record_id);

            CREATE TABLE scorecards (
                record_id TEXT NOT NULL,
                score_kind TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                profile_version TEXT NOT NULL,
                status TEXT NOT NULL,
                total_score REAL,
                max_score REAL,
                normalized_score REAL,
                score_json TEXT NOT NULL,
                PRIMARY KEY(record_id, score_kind, profile_id, profile_version),
                FOREIGN KEY(record_id) REFERENCES core_records(record_id)
            );

            CREATE TABLE bank_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO bank_meta(key, value) VALUES (?, ?)",
            ("schema", "NUTEV_CORE_BANK_V1"),
        )
        connection.execute(
            "INSERT INTO bank_meta(key, value) VALUES (?, ?)",
            ("prisma_dependency", "optional_downstream"),
        )

        for record in records:
            scores = record.get("scores") or {}
            core_score = (scores.get("core_readiness") or {}).get("normalized_score")
            mev = scores.get("mev") or {}
            mev_profile_id = mev.get("profile_id") if mev.get("status", "").startswith("scored") else None
            mev_total = mev.get("normalized_score") if mev_profile_id else None
            record_json = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
            connection.execute(
                """
                INSERT INTO core_records(
                    record_id, document_id, schema_version, title, doi, pmid, year,
                    source_provider, document_class, full_text_status, extraction_method,
                    ocr_used, core_readiness_score, mev_profile_id, mev_total_score,
                    record_sha256, record_json, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["document_id"],
                    record["schema_version"],
                    (record.get("identity") or {}).get("title"),
                    (record.get("identity") or {}).get("doi"),
                    (record.get("identity") or {}).get("pmid"),
                    (record.get("identity") or {}).get("year"),
                    (record.get("identity") or {}).get("source_provider"),
                    (record.get("classification") or {}).get("document_class"),
                    (record.get("acquisition") or {}).get("full_text_status"),
                    (record.get("acquisition") or {}).get("extraction_method"),
                    1 if (record.get("acquisition") or {}).get("ocr_used") else 0,
                    core_score,
                    mev_profile_id,
                    mev_total,
                    _record_sha(record),
                    record_json,
                    record["generated_at"],
                ),
            )

        for finding in findings:
            connection.execute(
                """
                INSERT INTO finding_candidates(
                    finding_id, record_id, document_id, section, locator,
                    source_excerpt, sentence_sha256, importance_score, status, finding_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding["id"],
                    finding["record_id"],
                    finding["document_id"],
                    finding.get("section"),
                    finding.get("locator"),
                    finding["source_excerpt"],
                    finding["sentence_sha256"],
                    finding["importance_score"],
                    finding["status"],
                    json.dumps(finding, ensure_ascii=False, sort_keys=True, default=str),
                ),
            )

        for score in scorecards:
            connection.execute(
                """
                INSERT INTO scorecards(
                    record_id, score_kind, profile_id, profile_version, status,
                    total_score, max_score, normalized_score, score_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score["record_id"],
                    score["score_kind"],
                    score["profile_id"],
                    score["profile_version"],
                    score["status"],
                    score.get("total_score"),
                    score.get("max_score"),
                    score.get("normalized_score"),
                    json.dumps(score, ensure_ascii=False, sort_keys=True, default=str),
                ),
            )
        connection.commit()
    finally:
        connection.close()
    tmp.replace(path)
    return sha256_file(path)


def run_core_bank_export(
    documents_jsonl: Path,
    evidence_records_jsonl: Path,
    science_manifest: Path,
    artifacts_jsonl: Path,
    enrichments_jsonl: Path,
    dossiers_jsonl: Path,
    enrichment_manifest: Path,
    output_dir: Path,
    *,
    mev_profile: Path | None = None,
) -> dict[str, Any]:
    """Materialize the NutEV CORE macro record independently from PRISMA."""

    source_shas = _verify_sources(
        documents_jsonl,
        evidence_records_jsonl,
        science_manifest,
        artifacts_jsonl,
        enrichments_jsonl,
        dossiers_jsonl,
        enrichment_manifest,
    )
    documents = _read_jsonl(documents_jsonl, label="document candidates")
    evidence_records = _read_jsonl(evidence_records_jsonl, label="evidence records")
    artifacts = _read_jsonl(artifacts_jsonl, label="full-text artifacts")
    enrichments = _read_jsonl(enrichments_jsonl, label="document enrichments")
    dossiers = _read_jsonl(dossiers_jsonl, label="reviewer dossiers")

    documents_by_id = _index_unique(documents, key="id", label="document candidate")
    evidence_by_id = _evidence_by_document(evidence_records)
    artifacts_by_doc = _index_unique(artifacts, key="document_id", label="artifact")
    enrichments_by_doc = _index_unique(enrichments, key="document_id", label="enrichment")
    dossiers_by_doc = _index_unique(dossiers, key="document_id", label="dossier")

    document_ids = set(documents_by_id)
    for label, indexed in (
        ("evidence records", evidence_by_id),
        ("artifacts", artifacts_by_doc),
        ("enrichments", enrichments_by_doc),
        ("dossiers", dossiers_by_doc),
    ):
        if set(indexed) != document_ids:
            missing = sorted(document_ids - set(indexed))
            extra = sorted(set(indexed) - document_ids)
            raise NutEVCoreError(
                f"{label} do not align with document candidates; missing={missing[:5]} extra={extra[:5]}"
            )

    profile: dict[str, Any] | None = None
    profile_sha: str | None = None
    if mev_profile is not None:
        profile = _read_json(mev_profile)
        profile_sha = sha256_file(mev_profile)

    records: list[dict[str, Any]] = []
    flat_findings: list[dict[str, Any]] = []
    flat_scores: list[dict[str, Any]] = []

    for document_id in sorted(document_ids):
        document = documents_by_id[document_id]
        evidence = evidence_by_id[document_id]
        artifact = artifacts_by_doc[document_id]
        enrichment = enrichments_by_doc[document_id]
        dossier = dossiers_by_doc[document_id]
        metadata = document.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        classification = _classification(dossier, enrichment)
        findings = _finding_candidates(document_id, enrichment)
        readiness = _core_readiness_score(
            document,
            evidence,
            artifact,
            enrichment,
            dossier,
            classification,
            findings,
        )

        base_scores: dict[str, Any] = {
            "core_readiness": asdict(readiness),
            "mev": {
                "status": "not_scored",
                "reason": "no versioned MEV profile supplied",
                "guardrail": "NutEV does not invent MEV blocks, weights, or scientific semantics.",
            },
        }

        record = NutEVCoreRecord(
            id=f"nutev-core:{document_id}",
            document_id=document_id,
            evidence_record_id=str(evidence.get("id") or "").strip() or None,
            schema_version=1,
            identity={
                "title": document.get("title"),
                "doi": document.get("doi"),
                "pmid": document.get("pmid"),
                "url": document.get("url"),
                "year": document.get("year"),
                "source_provider": document.get("source_provider"),
            },
            bibliographic={
                "abstract": dossier.get("abstract"),
                "journal": dossier.get("journal"),
                "authors": dossier.get("authors"),
                "article_type": dossier.get("article_type"),
                "keywords": metadata.get("keywords"),
            },
            reference_layer={
                "reference_rank": metadata.get("reference_rank"),
                "reference_score": metadata.get("reference_score"),
                "reference_tier": metadata.get("reference_tier"),
                "reference_taxonomy": evidence.get("taxonomy") or [],
                "audit_traceability": metadata.get("audit_traceability"),
                "guardrail": "Reference ranking is technical reading priority, not scientific quality.",
            },
            provenance={
                "evidence_record_id": evidence.get("id"),
                "source_provider": evidence.get("source_provider"),
                "source_run_id": evidence.get("source_run_id"),
                "origin_sha256": evidence.get("origin_sha256"),
                "evidence_metadata": evidence.get("metadata") or {},
                "source_files_sha256": source_shas,
            },
            acquisition={
                "artifact_id": artifact.get("id"),
                "full_text_status": artifact.get("retrieval_status"),
                "source_url": artifact.get("source_url"),
                "media_type": artifact.get("media_type"),
                "artifact_sha256": artifact.get("sha256"),
                "retrieved_at": artifact.get("retrieved_at"),
                "extraction_method": enrichment.get("extraction_method"),
                "ocr_used": bool(enrichment.get("ocr_used")),
                "ocr_engine": enrichment.get("ocr_engine"),
                "text_sha256": enrichment.get("text_sha256"),
                "text_chars": enrichment.get("text_chars"),
                "warnings": enrichment.get("warnings") or [],
            },
            structure={
                "section_coverage": classification.get("section_coverage"),
                "section_map": dossier.get("section_map") or [],
                "block_count": len(enrichment.get("blocks") or []),
                "table_mentions": classification.get("table_mentions"),
                "figure_mentions": classification.get("figure_mentions"),
                "sample_size_mentions": classification.get("sample_size_mentions"),
            },
            classification=classification,
            main_findings=findings,
            scores=base_scores,
            workflow={
                "core_status": "materialized",
                "human_review": "optional_downstream",
                "prisma": "optional_downstream",
                "screening_required_for_core": False,
                "usable_without_prisma": True,
            },
            content_refs={
                "artifact_local_path": artifact.get("local_path"),
                "private_text_path": (enrichment.get("metadata") or {}).get("private_text_path")
                if isinstance(enrichment.get("metadata"), dict)
                else None,
                "enrichment_id": enrichment.get("id"),
                "reviewer_dossier_id": dossier.get("id"),
            },
            guardrails={
                "main_findings_are_machine_candidates": True,
                "core_readiness_is_not_evidence_quality": True,
                "mev_requires_versioned_profile": True,
                "prisma_is_optional": True,
                "copyrighted_full_text_is_private_execution_material": True,
            },
        )
        record_dict = _record_dict(record)
        if profile is not None:
            mev_score = _score_configured_profile(record_dict, profile)
            record_dict["scores"]["mev"] = asdict(mev_score)

        records.append(record_dict)
        for finding in findings:
            flat = asdict(finding)
            flat["record_id"] = record.id
            flat_findings.append(flat)
        for score_kind, score in (record_dict.get("scores") or {}).items():
            if not isinstance(score, dict) or not str(score.get("status") or "").startswith("scored"):
                continue
            flat_score = dict(score)
            flat_score["record_id"] = record.id
            flat_score["score_kind"] = score_kind
            flat_scores.append(flat_score)

    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "nutev_core_records.jsonl"
    findings_path = output_dir / "finding_candidates.jsonl"
    scores_path = output_dir / "scorecards.jsonl"
    sqlite_path = output_dir / "nutev_core.sqlite"
    manifest_path = output_dir / "CORE_MANIFEST.json"

    records_sha = _write_jsonl(records_path, records)
    findings_sha = _write_jsonl(findings_path, flat_findings)
    scores_sha = _write_jsonl(scores_path, flat_scores)
    sqlite_sha = _write_sqlite(sqlite_path, records, flat_findings, flat_scores)

    mev_scored_count = sum(
        1
        for record in records
        if str(((record.get("scores") or {}).get("mev") or {}).get("status") or "").startswith("scored")
    )
    manifest = {
        "schema_version": 1,
        "core_type": "NUTEV_CORE_EVIDENCE_BANK",
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "document_candidates": str(documents_jsonl),
            "evidence_records": str(evidence_records_jsonl),
            "scientific_export_manifest": str(science_manifest),
            "full_text_artifacts": str(artifacts_jsonl),
            "document_enrichments": str(enrichments_jsonl),
            "reviewer_dossiers": str(dossiers_jsonl),
            "enrichment_manifest": str(enrichment_manifest),
            "source_sha256": source_shas,
            "mev_profile": str(mev_profile) if mev_profile else None,
            "mev_profile_sha256": profile_sha,
        },
        "counts": {
            "core_records": len(records),
            "finding_candidates": len(flat_findings),
            "scorecards": len(flat_scores),
            "mev_scored_records": mev_scored_count,
        },
        "outputs": {
            "core_records": {"path": str(records_path), "sha256": records_sha},
            "finding_candidates": {"path": str(findings_path), "sha256": findings_sha},
            "scorecards": {"path": str(scores_path), "sha256": scores_sha},
            "sqlite_bank": {"path": str(sqlite_path), "sha256": sqlite_sha},
        },
        "assertions": [
            {"name": "scientific_export_inputs_hash_verified", "status": "PASS"},
            {"name": "enrichment_inputs_hash_verified", "status": "PASS"},
            {"name": "one_core_record_per_document", "status": "PASS"},
            {"name": "core_independent_from_prisma", "status": "PASS"},
            {"name": "finding_candidates_not_upgraded_to_claims", "status": "PASS"},
            {"name": "mev_semantics_not_invented", "status": "PASS"},
        ],
        "core_guardrail": (
            "The NutEV CORE is the reusable article-information layer. PRISMA and human screening "
            "are optional downstream workflows. Machine classifications/findings remain candidates, "
            "and configured MEV scores only exist when a versioned profile is supplied."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)

    return {
        "mode": "NUTEV_CORE_EVIDENCE_BANK",
        "status": "COMPLETE",
        "records": len(records),
        "finding_candidates": len(flat_findings),
        "mev_scored_records": mev_scored_count,
        "prisma_required": False,
        "outputs": {
            "records": str(records_path),
            "findings": str(findings_path),
            "scorecards": str(scores_path),
            "sqlite": str(sqlite_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "records": records_sha,
            "findings": findings_sha,
            "scorecards": scores_sha,
            "sqlite": sqlite_sha,
            "manifest": manifest_sha,
        },
    }
