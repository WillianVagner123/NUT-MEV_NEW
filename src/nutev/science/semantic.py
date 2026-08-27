"""Structured semantic deconstruction for NutEV CORE records.

This module turns document-enrichment blocks into traceable semantic candidates.
It is deliberately conservative: every extracted value keeps a source excerpt,
section/locator, and SHA-256. Candidates are indexing/reading aids and are never
automatically promoted to EvidenceClaim, eligibility, quality, or recommendation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


class SemanticDeconstructionError(RuntimeError):
    """Raised when semantic deconstruction cannot prove source integrity."""


@dataclass(frozen=True, slots=True)
class SemanticFactCandidate:
    id: str
    document_id: str
    field: str
    value: str
    section: str
    locator: str | None
    source_excerpt: str
    source_sha256: str
    extraction_method: str
    extraction_confidence: float
    status: str = "machine_candidate"


@dataclass(frozen=True, slots=True)
class SemanticCoverageBlock:
    id: str
    label: str
    score: float
    max_score: float
    rationale: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticCoverageScore:
    profile_id: str
    profile_version: str
    semantic_kind: str
    total_score: float
    max_score: float
    normalized_score: float
    blocks: tuple[SemanticCoverageBlock, ...]
    guardrail: str


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9À-ÖØ-Þ])")
_SAMPLE_RE = re.compile(
    r"\b(?:n\s*=\s*|sample\s+(?:of|included)\s+|enrolled\s+|included\s+|recruited\s+)"
    r"(\d{1,7})\b",
    re.I,
)
_DURATION_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(day|days|week|weeks|month|months|year|years)\b",
    re.I,
)
_P_VALUE_RE = re.compile(r"\bp\s*(?:=|<|>|≤|≥)\s*0?\.\d+(?:e[-+]?\d+)?\b", re.I)
_CI_RE = re.compile(
    r"\b(?:95\s*%\s*(?:CI|confidence interval)|confidence interval)\s*[:=]?\s*"
    r"(?:\[|\()?\s*(-?\d+(?:\.\d+)?)\s*(?:,|to|–|—|-)\s*"
    r"(-?\d+(?:\.\d+)?)\s*(?:\]|\))?",
    re.I,
)
_EFFECT_RE = re.compile(
    r"\b(OR|RR|HR|SMD|MD|IRR|aOR|aRR|beta|β)\s*[:=]?\s*"
    r"(-?\d+(?:\.\d+)?)\b",
    re.I,
)
_TABLE_RE = re.compile(r"\bTable\s+\d+[A-Za-z]?\b", re.I)
_FIGURE_RE = re.compile(r"\b(?:Figure|Fig\.)\s*\d+[A-Za-z]?\b", re.I)

_POPULATION_TERMS = (
    "participants",
    "patients",
    "adults",
    "children",
    "adolescents",
    "athletes",
    "women",
    "men",
    "subjects",
    "individuals",
)
_INTERVENTION_TERMS = (
    "intervention",
    "assigned to",
    "randomized to",
    "randomised to",
    "received",
    "supplement",
    "treatment",
    "program",
    "programme",
    "diet",
    "training",
)
_EXPOSURE_TERMS = (
    "exposure",
    "exposed",
    "associated with",
    "association between",
    "dietary intake",
    "consumption",
    "behavior",
    "behaviour",
)
_COMPARATOR_TERMS = (
    "control group",
    "control",
    "placebo",
    "usual care",
    "versus",
    "compared with",
    "comparison group",
)
_OUTCOME_TERMS = (
    "primary outcome",
    "secondary outcome",
    "outcome",
    "endpoint",
    "measured",
    "assessed",
    "change in",
)
_OBJECTIVE_TERMS = (
    "objective",
    "aim",
    "purpose",
    "we investigated",
    "we evaluated",
    "we assessed",
    "this study examined",
)
_LIMITATION_TERMS = (
    "limitation",
    "limitations",
    "limited by",
    "small sample",
    "single-center",
    "single centre",
    "self-reported",
    "generalizability",
    "generalisability",
)
_FUNDING_TERMS = (
    "funded by",
    "funding",
    "financial support",
    "supported by",
    "grant from",
    "grant number",
)
_CONFLICT_TERMS = (
    "conflict of interest",
    "conflicts of interest",
    "competing interest",
    "competing interests",
    "no conflict",
    "no competing",
    "declare no",
)
_ELIGIBILITY_TERMS = (
    "inclusion criteria",
    "exclusion criteria",
    "eligible if",
    "eligibility criteria",
    "were eligible",
    "participants were required",
)
_FOLLOWUP_TERMS = ("follow-up", "follow up", "followed for", "followed up")

_METHOD_SECTIONS = {
    "method",
    "methods",
    "methodology",
    "materials and methods",
    "participants",
    "population",
    "intervention",
    "interventions",
    "procedures",
}
_RESULT_SECTIONS = {"result", "results", "findings"}
_CONTEXT_SECTIONS = {"abstract", "introduction", "background", "objective", "objectives"}
_DISCUSSION_SECTIONS = {"discussion", "limitation", "limitations", "conclusion", "conclusions"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SemanticDeconstructionError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SemanticDeconstructionError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SemanticDeconstructionError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SemanticDeconstructionError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SemanticDeconstructionError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise SemanticDeconstructionError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    if not rows:
        raise SemanticDeconstructionError(f"{label} JSONL is empty: {path}")
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
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        for row in rows
    )
    return _atomic_text(path, payload)


def _heading(value: Any) -> str:
    return str(value or "").strip().casefold().rstrip(":.")


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(normalized) if part.strip()]


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    lower = text.casefold()
    return any(term.casefold() in lower for term in terms)


def _fact(
    document_id: str,
    field: str,
    value: str,
    section: str,
    locator: str | None,
    sentence: str,
    confidence: float,
    *,
    method: str = "rule_v1",
) -> SemanticFactCandidate:
    digest = sha256(sentence.encode("utf-8")).hexdigest()
    identity = sha256(f"{field}|{value}|{digest}".encode("utf-8")).hexdigest()[:18]
    return SemanticFactCandidate(
        id=f"semantic:{document_id}:{identity}",
        document_id=document_id,
        field=field,
        value=value[:500].strip(),
        section=section,
        locator=locator,
        source_excerpt=sentence[:420].strip(),
        source_sha256=digest,
        extraction_method=method,
        extraction_confidence=round(max(0.0, min(confidence, 1.0)), 2),
    )


def extract_semantic_facts(
    document_id: str,
    enrichment: Mapping[str, Any],
    classification: Mapping[str, Any] | None = None,
    *,
    per_field_limit: int = 12,
) -> tuple[SemanticFactCandidate, ...]:
    """Extract conservative semantic candidates from traceable text blocks."""

    candidates: list[SemanticFactCandidate] = []
    document_class = str((classification or {}).get("document_class") or "")

    for block in enrichment.get("blocks") or []:
        if not isinstance(block, Mapping):
            continue
        section = str(block.get("heading") or "Document text").strip()
        section_key = _heading(section)
        locator = str(block.get("locator") or "").strip() or None
        text = str(block.get("text") or "")

        for sentence in _sentences(text):
            if len(sentence) < 25 or len(sentence) > 1400:
                continue

            if section_key in _CONTEXT_SECTIONS and _contains_any(sentence, _OBJECTIVE_TERMS):
                candidates.append(_fact(document_id, "objective", sentence, section, locator, sentence, 0.78))

            population_signal = _contains_any(sentence, _POPULATION_TERMS)
            if population_signal and (section_key in _METHOD_SECTIONS or section_key in _CONTEXT_SECTIONS):
                candidates.append(_fact(document_id, "population", sentence, section, locator, sentence, 0.68))

            for match in _SAMPLE_RE.finditer(sentence):
                candidates.append(_fact(document_id, "sample_size", match.group(1), section, locator, sentence, 0.9))

            if section_key in _METHOD_SECTIONS:
                intervention_signal = _contains_any(sentence, _INTERVENTION_TERMS)
                exposure_signal = _contains_any(sentence, _EXPOSURE_TERMS)
                if intervention_signal:
                    candidates.append(_fact(document_id, "intervention", sentence, section, locator, sentence, 0.66))
                if exposure_signal and not intervention_signal:
                    candidates.append(_fact(document_id, "exposure", sentence, section, locator, sentence, 0.64))
                if _contains_any(sentence, _COMPARATOR_TERMS):
                    candidates.append(_fact(document_id, "comparator", sentence, section, locator, sentence, 0.72))
                if _contains_any(sentence, _OUTCOME_TERMS):
                    candidates.append(_fact(document_id, "outcome", sentence, section, locator, sentence, 0.66))
                if _contains_any(sentence, _ELIGIBILITY_TERMS):
                    candidates.append(_fact(document_id, "eligibility_criteria", sentence, section, locator, sentence, 0.74))

            if _contains_any(sentence, _FOLLOWUP_TERMS):
                candidates.append(_fact(document_id, "follow_up", sentence, section, locator, sentence, 0.76))
            elif section_key in _METHOD_SECTIONS and _contains_any(sentence, ("trial", "study", "intervention", "treatment", "program", "programme")):
                duration_matches = list(_DURATION_RE.finditer(sentence))
                for match in duration_matches[:3]:
                    candidates.append(
                        _fact(
                            document_id,
                            "duration",
                            f"{match.group(1)} {match.group(2).lower()}",
                            section,
                            locator,
                            sentence,
                            0.7,
                        )
                    )

            if section_key in _RESULT_SECTIONS or section_key in _DISCUSSION_SECTIONS or section_key == "abstract":
                if _contains_any(sentence, _OUTCOME_TERMS):
                    candidates.append(_fact(document_id, "outcome", sentence, section, locator, sentence, 0.62))
                for match in _EFFECT_RE.finditer(sentence):
                    candidates.append(
                        _fact(
                            document_id,
                            "effect_measure",
                            f"{match.group(1)}={match.group(2)}",
                            section,
                            locator,
                            sentence,
                            0.9,
                        )
                    )
                for match in _P_VALUE_RE.finditer(sentence):
                    candidates.append(_fact(document_id, "p_value", match.group(0), section, locator, sentence, 0.94))
                for match in _CI_RE.finditer(sentence):
                    candidates.append(
                        _fact(
                            document_id,
                            "confidence_interval",
                            f"95% CI {match.group(1)} to {match.group(2)}",
                            section,
                            locator,
                            sentence,
                            0.9,
                        )
                    )

            if section_key in _DISCUSSION_SECTIONS and _contains_any(sentence, _LIMITATION_TERMS):
                candidates.append(_fact(document_id, "limitation", sentence, section, locator, sentence, 0.8))

            if _contains_any(sentence, _FUNDING_TERMS):
                candidates.append(_fact(document_id, "funding", sentence, section, locator, sentence, 0.8))
            if _contains_any(sentence, _CONFLICT_TERMS):
                candidates.append(_fact(document_id, "conflict_of_interest", sentence, section, locator, sentence, 0.82))

            for match in _TABLE_RE.finditer(sentence):
                candidates.append(_fact(document_id, "table_reference", match.group(0), section, locator, sentence, 0.96))
            for match in _FIGURE_RE.finditer(sentence):
                candidates.append(_fact(document_id, "figure_reference", match.group(0), section, locator, sentence, 0.96))

    # If a randomized primary study has explicit intervention text but no comparator
    # sentence, do not fabricate a comparator. The same rule applies to PECO/PCC fields.
    unique: dict[tuple[str, str, str], SemanticFactCandidate] = {}
    for item in sorted(candidates, key=lambda fact: fact.extraction_confidence, reverse=True):
        key = (item.field, item.value.casefold(), item.source_sha256)
        unique.setdefault(key, item)

    by_field: dict[str, list[SemanticFactCandidate]] = defaultdict(list)
    for item in unique.values():
        by_field[item.field].append(item)

    limited: list[SemanticFactCandidate] = []
    for field_name in sorted(by_field):
        items = sorted(
            by_field[field_name],
            key=lambda fact: (fact.extraction_confidence, bool(fact.locator)),
            reverse=True,
        )[:per_field_limit]
        limited.extend(items)

    return tuple(sorted(limited, key=lambda fact: (fact.field, -fact.extraction_confidence)))


def _framework_candidates(
    facts: Iterable[SemanticFactCandidate], classification: Mapping[str, Any]
) -> list[dict[str, Any]]:
    fields = {fact.field for fact in facts}
    candidates: list[dict[str, Any]] = []
    if "intervention" in fields and "outcome" in fields:
        basis = ["intervention", "outcome"]
        if "comparator" in fields:
            basis.append("comparator")
        if "population" in fields:
            basis.append("population")
        candidates.append({"framework": "PICO", "basis": basis, "status": "candidate"})
    if "exposure" in fields and "outcome" in fields:
        basis = ["exposure", "outcome"]
        if "comparator" in fields:
            basis.append("comparator")
        if "population" in fields:
            basis.append("population")
        candidates.append({"framework": "PECO", "basis": basis, "status": "candidate"})
    if (
        str(classification.get("document_class") or "") in {"review", "evidence_synthesis"}
        and "population" in fields
        and "intervention" not in fields
        and "exposure" not in fields
    ):
        candidates.append(
            {
                "framework": "PCC",
                "basis": ["population", "review_classification"],
                "status": "weak_candidate",
                "warning": "concept/context were not explicitly resolved by rule_v1",
            }
        )
    return candidates


def _coverage_block(
    block_id: str,
    label: str,
    max_score: float,
    checks: Iterable[tuple[float, str, bool]],
) -> SemanticCoverageBlock:
    score = 0.0
    rationale: list[str] = []
    for points, reason, condition in checks:
        if condition:
            score += points
            rationale.append(f"+{points:g} {reason}")
    return SemanticCoverageBlock(
        id=block_id,
        label=label,
        score=round(min(score, max_score), 2),
        max_score=max_score,
        rationale=tuple(rationale),
    )


def semantic_coverage_score(facts: Iterable[SemanticFactCandidate]) -> SemanticCoverageScore:
    fields = Counter(fact.field for fact in facts)
    context = _coverage_block(
        "question_context",
        "Question and population context",
        20.0,
        ((8.0, "objective candidate", fields["objective"] > 0), (12.0, "population candidate", fields["population"] > 0)),
    )
    design = _coverage_block(
        "design_sample",
        "Design, sample and time",
        20.0,
        (
            (8.0, "sample size candidate", fields["sample_size"] > 0),
            (6.0, "duration candidate", fields["duration"] > 0),
            (6.0, "follow-up candidate", fields["follow_up"] > 0),
        ),
    )
    exposure = _coverage_block(
        "exposure_comparator",
        "Intervention/exposure and comparator",
        20.0,
        (
            (12.0, "intervention or exposure candidate", fields["intervention"] > 0 or fields["exposure"] > 0),
            (8.0, "comparator candidate", fields["comparator"] > 0),
        ),
    )
    results = _coverage_block(
        "outcomes_results",
        "Outcomes and quantitative results",
        25.0,
        (
            (10.0, "outcome candidate", fields["outcome"] > 0),
            (7.0, "effect measure candidate", fields["effect_measure"] > 0),
            (4.0, "p-value candidate", fields["p_value"] > 0),
            (4.0, "confidence interval candidate", fields["confidence_interval"] > 0),
        ),
    )
    reporting = _coverage_block(
        "reporting_context",
        "Limitations and disclosure context",
        15.0,
        (
            (6.0, "limitation candidate", fields["limitation"] > 0),
            (5.0, "funding candidate", fields["funding"] > 0),
            (4.0, "conflict-of-interest candidate", fields["conflict_of_interest"] > 0),
        ),
    )
    blocks = (context, design, exposure, results, reporting)
    total = round(sum(block.score for block in blocks), 2)
    maximum = round(sum(block.max_score for block in blocks), 2)
    normalized = round((total / maximum) * 100.0, 2) if maximum else 0.0
    return SemanticCoverageScore(
        profile_id="NUTEV_SEMANTIC_COVERAGE",
        profile_version="1",
        semantic_kind="technical_semantic_coverage",
        total_score=total,
        max_score=maximum,
        normalized_score=normalized,
        blocks=blocks,
        guardrail=(
            "This score measures whether common semantic fields were traceably extracted. "
            "It is not evidence quality, risk of bias, certainty, eligibility, or effect credibility."
        ),
    )


def build_semantic_layer(
    document_id: str,
    enrichment: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    facts = extract_semantic_facts(document_id, enrichment, classification)
    field_counts = Counter(fact.field for fact in facts)
    return {
        "schema_version": 1,
        "status": "machine_candidates_materialized",
        "framework_candidates": _framework_candidates(facts, classification),
        "field_counts": dict(sorted(field_counts.items())),
        "facts": [asdict(fact) for fact in facts],
        "coverage_score": asdict(semantic_coverage_score(facts)),
        "guardrails": {
            "facts_are_machine_candidates": True,
            "no_fact_is_an_accepted_evidence_claim": True,
            "no_missing_field_is_inferred": True,
            "every_fact_requires_source_excerpt_and_hash": True,
            "extraction_confidence_is_rule_strength_not_probability": True,
            "prisma_not_required": True,
        },
    }


def _verify_inputs(
    core_records_jsonl: Path,
    core_manifest_path: Path,
    enrichments_jsonl: Path,
    enrichment_manifest_path: Path,
) -> dict[str, str]:
    core_manifest = _read_json(core_manifest_path)
    if core_manifest.get("core_type") != "NUTEV_CORE_EVIDENCE_BANK" or core_manifest.get("status") != "PASS":
        raise SemanticDeconstructionError("CORE manifest is not a passing NUTEV CORE evidence-bank manifest")
    enrichment_manifest = _read_json(enrichment_manifest_path)
    if enrichment_manifest.get("enrichment_type") != "NUTEV_PRE_SCREENING_DOCUMENT_ENRICHMENT" or enrichment_manifest.get("status") != "PASS":
        raise SemanticDeconstructionError("enrichment manifest is not PASS")

    expected_core = str((((core_manifest.get("outputs") or {}).get("core_records") or {}).get("sha256")) or "").strip().lower()
    expected_enrichment = str((((enrichment_manifest.get("outputs") or {}).get("document_enrichments") or {}).get("sha256")) or "").strip().lower()
    if not expected_core or not expected_enrichment:
        raise SemanticDeconstructionError("required source SHA-256 missing from manifest")
    actual_core = sha256_file(core_records_jsonl)
    actual_enrichment = sha256_file(enrichments_jsonl)
    if actual_core != expected_core:
        raise SemanticDeconstructionError(f"CORE records SHA-256 mismatch: expected {expected_core}, got {actual_core}")
    if actual_enrichment != expected_enrichment:
        raise SemanticDeconstructionError(
            f"document enrichments SHA-256 mismatch: expected {expected_enrichment}, got {actual_enrichment}"
        )
    return {
        "core_records": actual_core,
        "core_manifest": sha256_file(core_manifest_path),
        "enrichments": actual_enrichment,
        "enrichment_manifest": sha256_file(enrichment_manifest_path),
    }


def run_semantic_deconstruction(
    core_records_jsonl: Path,
    core_manifest: Path,
    enrichments_jsonl: Path,
    enrichment_manifest: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Materialize schema-v2 macro records with traceable semantic candidates."""

    source_shas = _verify_inputs(
        core_records_jsonl, core_manifest, enrichments_jsonl, enrichment_manifest
    )
    records = _read_jsonl(core_records_jsonl, label="CORE records")
    enrichments = _read_jsonl(enrichments_jsonl, label="document enrichments")
    records_by_doc = {str(row.get("document_id") or ""): row for row in records}
    enrichments_by_doc = {str(row.get("document_id") or ""): row for row in enrichments}
    if not records_by_doc or "" in records_by_doc or "" in enrichments_by_doc:
        raise SemanticDeconstructionError("records/enrichments contain missing document_id")
    if len(records_by_doc) != len(records) or len(enrichments_by_doc) != len(enrichments):
        raise SemanticDeconstructionError("duplicate document_id in records/enrichments")
    if set(records_by_doc) != set(enrichments_by_doc):
        raise SemanticDeconstructionError("CORE records and enrichments do not contain the same document IDs")

    enriched_records: list[dict[str, Any]] = []
    flat_facts: list[dict[str, Any]] = []
    flat_scores: list[dict[str, Any]] = []
    for document_id in sorted(records_by_doc):
        record = dict(records_by_doc[document_id])
        classification = record.get("classification") or {}
        if not isinstance(classification, Mapping):
            classification = {}
        semantic = build_semantic_layer(document_id, enrichments_by_doc[document_id], classification)
        record["schema_version"] = max(2, int(record.get("schema_version") or 1))
        record["semantic"] = semantic
        record.setdefault("workflow", {})
        if isinstance(record["workflow"], dict):
            record["workflow"]["semantic_deconstruction"] = "materialized"
            record["workflow"]["prisma"] = "optional_downstream"
        record.setdefault("guardrails", {})
        if isinstance(record["guardrails"], dict):
            record["guardrails"]["semantic_facts_are_machine_candidates"] = True
            record["guardrails"]["prisma_is_optional"] = True
        enriched_records.append(record)
        for fact in semantic["facts"]:
            flat = dict(fact)
            flat["record_id"] = record.get("id")
            flat_facts.append(flat)
        coverage = dict(semantic["coverage_score"])
        coverage["record_id"] = record.get("id")
        coverage["document_id"] = document_id
        coverage["score_kind"] = "semantic_coverage"
        flat_scores.append(coverage)

    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "nutev_core_records_semantic.jsonl"
    facts_path = output_dir / "semantic_fact_candidates.jsonl"
    scores_path = output_dir / "semantic_scorecards.jsonl"
    manifest_path = output_dir / "SEMANTIC_MANIFEST.json"

    records_sha = _write_jsonl(records_path, enriched_records)
    facts_sha = _write_jsonl(facts_path, flat_facts)
    scores_sha = _write_jsonl(scores_path, flat_scores)
    field_counts = Counter(str(fact.get("field") or "") for fact in flat_facts)
    manifest = {
        "schema_version": 1,
        "semantic_type": "NUTEV_CORE_SEMANTIC_DECONSTRUCTION",
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "core_records": str(core_records_jsonl),
            "core_manifest": str(core_manifest),
            "document_enrichments": str(enrichments_jsonl),
            "enrichment_manifest": str(enrichment_manifest),
            "source_sha256": source_shas,
        },
        "counts": {
            "records": len(enriched_records),
            "semantic_fact_candidates": len(flat_facts),
            "field_counts": dict(sorted(field_counts.items())),
        },
        "outputs": {
            "semantic_core_records": {"path": str(records_path), "sha256": records_sha},
            "semantic_fact_candidates": {"path": str(facts_path), "sha256": facts_sha},
            "semantic_scorecards": {"path": str(scores_path), "sha256": scores_sha},
        },
        "assertions": [
            {"name": "core_hash_verified", "status": "PASS"},
            {"name": "enrichment_hash_verified", "status": "PASS"},
            {"name": "document_sets_align", "status": "PASS"},
            {"name": "every_fact_has_source_excerpt_hash", "status": "PASS"},
            {"name": "semantic_candidates_not_upgraded_to_claims", "status": "PASS"},
            {"name": "prisma_not_required", "status": "PASS"},
        ],
        "guardrail": (
            "Semantic facts are traceable machine candidates. Absence is not inferred, extraction confidence "
            "is rule strength rather than a calibrated probability, and PRISMA remains optional downstream."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)
    return {
        "mode": "NUTEV_CORE_SEMANTIC_DECONSTRUCTION",
        "status": "COMPLETE",
        "records": len(enriched_records),
        "semantic_fact_candidates": len(flat_facts),
        "prisma_required": False,
        "outputs": {
            "records": str(records_path),
            "facts": str(facts_path),
            "scorecards": str(scores_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "records": records_sha,
            "facts": facts_sha,
            "scorecards": scores_sha,
            "manifest": manifest_sha,
        },
    }
