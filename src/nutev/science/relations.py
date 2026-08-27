"""Traceable relational mapping for NutEV semantic candidates.

The semantic layer extracts facts. This module links only sufficiently grounded
facts into candidate scientific relations such as study-arm comparisons,
outcome/timepoint links, and effect-estimate bundles. Relations remain machine
candidates and are never promoted automatically to EvidenceClaim, eligibility,
quality, certainty, recommendation, or PRISMA decisions.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


class RelationalMappingError(RuntimeError):
    """Raised when relational mapping cannot prove source integrity."""


@dataclass(frozen=True, slots=True)
class ScientificEntityCandidate:
    id: str
    document_id: str
    entity_type: str
    label: str
    normalized: Mapping[str, Any]
    source_fact_ids: tuple[str, ...]
    source_sha256: tuple[str, ...]
    locators: tuple[str, ...]
    status: str = "machine_candidate"


@dataclass(frozen=True, slots=True)
class ScientificRelationCandidate:
    id: str
    document_id: str
    relation_type: str
    source_entity_id: str
    target_entity_id: str
    basis: str
    source_fact_ids: tuple[str, ...]
    source_sha256: tuple[str, ...]
    locators: tuple[str, ...]
    relation_confidence: float
    status: str = "machine_candidate"


@dataclass(frozen=True, slots=True)
class RelationalCoverageBlock:
    id: str
    label: str
    score: float
    max_score: float
    rationale: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationalCoverageScore:
    profile_id: str
    profile_version: str
    semantic_kind: str
    total_score: float
    max_score: float
    normalized_score: float
    blocks: tuple[RelationalCoverageBlock, ...]
    guardrail: str


_EFFECT_RE = re.compile(
    r"^(?P<kind>a?OR|a?RR|HR|SMD|MD|IRR|beta|β)=(?P<value>-?\d+(?:\.\d+)?)$",
    re.I,
)
_P_VALUE_RE = re.compile(
    r"^p\s*(?P<operator>=|<|>|≤|≥)\s*(?P<value>0?\.\d+(?:e[-+]?\d+)?)$",
    re.I,
)
_CI_RE = re.compile(
    r"^95% CI\s+(?P<lower>-?\d+(?:\.\d+)?)\s+to\s+"
    r"(?P<upper>-?\d+(?:\.\d+)?)$",
    re.I,
)
_DURATION_RE = re.compile(
    r"^(?P<value>\d+(?:\.\d+)?)\s+"
    r"(?P<unit>day|days|week|weeks|month|months|year|years)$",
    re.I,
)
_SAMPLE_RE = re.compile(r"^\d{1,7}$")
_TABLE_RE = re.compile(r"^Table\s+(?P<id>\d+[A-Za-z]?)$", re.I)
_FIGURE_RE = re.compile(r"^(?:Figure|Fig\.)\s*(?P<id>\d+[A-Za-z]?)$", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RelationalMappingError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RelationalMappingError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RelationalMappingError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str, allow_empty: bool = False) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RelationalMappingError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RelationalMappingError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise RelationalMappingError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    if not rows and not allow_empty:
        raise RelationalMappingError(f"{label} JSONL is empty: {path}")
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


def _fact_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _normalized_for_fact(fact: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    field = str(fact.get("field") or "").strip()
    value = str(fact.get("value") or "").strip()
    if not field or not value:
        raise RelationalMappingError("semantic fact requires field and value")

    if field == "intervention":
        return "study_arm", {"role": "intervention", "description": value}
    if field == "comparator":
        return "study_arm", {"role": "comparator", "description": value}
    if field == "exposure":
        return "exposure", {"description": value}
    if field == "population":
        return "population", {"description": value}
    if field == "outcome":
        return "outcome", {"description": value}
    if field == "sample_size":
        match = _SAMPLE_RE.fullmatch(value)
        return "sample", {"n": int(value) if match else None, "raw": value}
    if field in {"duration", "follow_up"}:
        match = _DURATION_RE.fullmatch(value)
        normalized: dict[str, Any] = {
            "time_kind": "study_duration" if field == "duration" else "follow_up",
            "raw": value,
        }
        if match:
            normalized["value"] = float(match.group("value"))
            normalized["unit"] = match.group("unit").lower()
        return "timepoint", normalized
    if field == "effect_measure":
        match = _EFFECT_RE.fullmatch(value)
        normalized = {"raw": value}
        if match:
            normalized.update(
                {
                    "measure": match.group("kind"),
                    "value": float(match.group("value")),
                }
            )
        return "effect_estimate", normalized
    if field == "p_value":
        match = _P_VALUE_RE.fullmatch(value)
        normalized = {"raw": value}
        if match:
            normalized.update(
                {
                    "operator": match.group("operator"),
                    "value": float(match.group("value")),
                }
            )
        return "p_value", normalized
    if field == "confidence_interval":
        match = _CI_RE.fullmatch(value)
        normalized = {"raw": value, "level": 0.95}
        if match:
            normalized.update(
                {
                    "lower": float(match.group("lower")),
                    "upper": float(match.group("upper")),
                }
            )
        return "confidence_interval", normalized
    if field == "table_reference":
        match = _TABLE_RE.fullmatch(value)
        return "table", {"identifier": match.group("id") if match else value}
    if field == "figure_reference":
        match = _FIGURE_RE.fullmatch(value)
        return "figure", {"identifier": match.group("id") if match else value}
    if field in {
        "objective",
        "eligibility_criteria",
        "limitation",
        "funding",
        "conflict_of_interest",
    }:
        return field, {"description": value}
    return "semantic_fact", {"field": field, "value": value}


def _entity_from_fact(fact: Mapping[str, Any]) -> ScientificEntityCandidate:
    document_id = str(fact.get("document_id") or "").strip()
    fact_id = str(fact.get("id") or "").strip()
    source_sha = str(fact.get("source_sha256") or "").strip().lower()
    locator = str(fact.get("locator") or "").strip()
    value = str(fact.get("value") or "").strip()
    if not document_id or not fact_id or len(source_sha) != 64 or not value:
        raise RelationalMappingError(
            "semantic fact requires document_id, id, value, and 64-char source_sha256"
        )
    entity_type, normalized = _normalized_for_fact(fact)
    digest = sha256(f"{fact_id}|{entity_type}".encode("utf-8")).hexdigest()[:18]
    return ScientificEntityCandidate(
        id=f"entity:{document_id}:{digest}",
        document_id=document_id,
        entity_type=entity_type,
        label=value[:500],
        normalized=normalized,
        source_fact_ids=(fact_id,),
        source_sha256=(source_sha,),
        locators=(locator,) if locator else (),
    )


def build_entity_candidates(
    document_id: str, facts: Iterable[Mapping[str, Any]]
) -> tuple[ScientificEntityCandidate, ...]:
    entities: list[ScientificEntityCandidate] = []
    seen_fact_ids: set[str] = set()
    for fact in facts:
        if str(fact.get("document_id") or "") != document_id:
            raise RelationalMappingError(
                f"fact document_id does not match record: {fact.get('document_id')} != {document_id}"
            )
        fact_id = str(fact.get("id") or "").strip()
        if fact_id in seen_fact_ids:
            raise RelationalMappingError(f"duplicate semantic fact id: {fact_id}")
        seen_fact_ids.add(fact_id)
        entities.append(_entity_from_fact(fact))
    return tuple(entities)


def _relation(
    document_id: str,
    relation_type: str,
    source: ScientificEntityCandidate,
    target: ScientificEntityCandidate,
    *,
    basis: str,
    confidence: float,
) -> ScientificRelationCandidate:
    fact_ids = tuple(dict.fromkeys(source.source_fact_ids + target.source_fact_ids))
    source_shas = tuple(dict.fromkeys(source.source_sha256 + target.source_sha256))
    locators = tuple(dict.fromkeys(source.locators + target.locators))
    digest = sha256(
        f"{relation_type}|{source.id}|{target.id}".encode("utf-8")
    ).hexdigest()[:18]
    return ScientificRelationCandidate(
        id=f"relation:{document_id}:{digest}",
        document_id=document_id,
        relation_type=relation_type,
        source_entity_id=source.id,
        target_entity_id=target.id,
        basis=basis,
        source_fact_ids=fact_ids,
        source_sha256=source_shas,
        locators=locators,
        relation_confidence=round(max(0.0, min(confidence, 1.0)), 2),
    )


def _entities_by_type(
    entities: Iterable[ScientificEntityCandidate],
) -> dict[str, list[ScientificEntityCandidate]]:
    grouped: dict[str, list[ScientificEntityCandidate]] = defaultdict(list)
    for entity in entities:
        grouped[entity.entity_type].append(entity)
    return grouped


def _arm_role(entity: ScientificEntityCandidate) -> str:
    if entity.entity_type != "study_arm":
        return ""
    return str(entity.normalized.get("role") or "")


def _sentence_relations(
    document_id: str,
    entities: Iterable[ScientificEntityCandidate],
) -> list[ScientificRelationCandidate]:
    by_sha: dict[str, list[ScientificEntityCandidate]] = defaultdict(list)
    for entity in entities:
        for digest in entity.source_sha256:
            by_sha[digest].append(entity)

    relations: list[ScientificRelationCandidate] = []
    for group in by_sha.values():
        typed = _entities_by_type(group)
        intervention_arms = [
            item for item in typed.get("study_arm", []) if _arm_role(item) == "intervention"
        ]
        comparator_arms = [
            item for item in typed.get("study_arm", []) if _arm_role(item) == "comparator"
        ]
        outcomes = typed.get("outcome", [])
        timepoints = typed.get("timepoint", [])
        effects = typed.get("effect_estimate", [])
        p_values = typed.get("p_value", [])
        cis = typed.get("confidence_interval", [])
        tables = typed.get("table", [])
        figures = typed.get("figure", [])

        for source in intervention_arms:
            for target in comparator_arms:
                relations.append(
                    _relation(
                        document_id,
                        "compared_with",
                        source,
                        target,
                        basis="same_sentence",
                        confidence=0.94,
                    )
                )
        for outcome in outcomes:
            for effect in effects:
                relations.append(
                    _relation(
                        document_id,
                        "effect_estimate_for",
                        effect,
                        outcome,
                        basis="same_sentence",
                        confidence=0.96,
                    )
                )
            for p_value in p_values:
                relations.append(
                    _relation(
                        document_id,
                        "p_value_for",
                        p_value,
                        outcome,
                        basis="same_sentence",
                        confidence=0.94,
                    )
                )
            for ci in cis:
                relations.append(
                    _relation(
                        document_id,
                        "confidence_interval_for",
                        ci,
                        outcome,
                        basis="same_sentence",
                        confidence=0.92,
                    )
                )
            for timepoint in timepoints:
                relations.append(
                    _relation(
                        document_id,
                        "measured_at",
                        outcome,
                        timepoint,
                        basis="same_sentence",
                        confidence=0.9,
                    )
                )
            for table in tables:
                relations.append(
                    _relation(
                        document_id,
                        "reported_in",
                        outcome,
                        table,
                        basis="same_sentence",
                        confidence=0.97,
                    )
                )
            for figure in figures:
                relations.append(
                    _relation(
                        document_id,
                        "reported_in",
                        outcome,
                        figure,
                        basis="same_sentence",
                        confidence=0.97,
                    )
                )
        for effect in effects:
            for p_value in p_values:
                relations.append(
                    _relation(
                        document_id,
                        "effect_has_p_value",
                        effect,
                        p_value,
                        basis="same_sentence",
                        confidence=0.98,
                    )
                )
            for ci in cis:
                relations.append(
                    _relation(
                        document_id,
                        "effect_has_confidence_interval",
                        effect,
                        ci,
                        basis="same_sentence",
                        confidence=0.97,
                    )
                )
            for timepoint in timepoints:
                relations.append(
                    _relation(
                        document_id,
                        "estimated_at",
                        effect,
                        timepoint,
                        basis="same_sentence",
                        confidence=0.9,
                    )
                )
    return relations


def _locator_fallback_relations(
    document_id: str,
    entities: Iterable[ScientificEntityCandidate],
) -> list[ScientificRelationCandidate]:
    by_locator: dict[str, list[ScientificEntityCandidate]] = defaultdict(list)
    for entity in entities:
        for locator in entity.locators:
            by_locator[locator].append(entity)

    relations: list[ScientificRelationCandidate] = []
    for group in by_locator.values():
        typed = _entities_by_type(group)
        intervention_arms = [
            item for item in typed.get("study_arm", []) if _arm_role(item) == "intervention"
        ]
        comparator_arms = [
            item for item in typed.get("study_arm", []) if _arm_role(item) == "comparator"
        ]
        outcomes = typed.get("outcome", [])
        timepoints = typed.get("timepoint", [])
        effects = typed.get("effect_estimate", [])

        if len(intervention_arms) == 1 and len(comparator_arms) == 1:
            relations.append(
                _relation(
                    document_id,
                    "compared_with",
                    intervention_arms[0],
                    comparator_arms[0],
                    basis="same_locator_unique_candidates",
                    confidence=0.72,
                )
            )
        if len(outcomes) == 1 and len(timepoints) == 1:
            relations.append(
                _relation(
                    document_id,
                    "measured_at",
                    outcomes[0],
                    timepoints[0],
                    basis="same_locator_unique_candidates",
                    confidence=0.68,
                )
            )
        if len(outcomes) == 1 and len(effects) == 1:
            relations.append(
                _relation(
                    document_id,
                    "effect_estimate_for",
                    effects[0],
                    outcomes[0],
                    basis="same_locator_unique_candidates",
                    confidence=0.7,
                )
            )
    return relations


def build_relation_candidates(
    document_id: str,
    entities: Iterable[ScientificEntityCandidate],
) -> tuple[ScientificRelationCandidate, ...]:
    entity_tuple = tuple(entities)
    candidates = _sentence_relations(document_id, entity_tuple)
    candidates.extend(_locator_fallback_relations(document_id, entity_tuple))

    best: dict[tuple[str, str, str], ScientificRelationCandidate] = {}
    for relation in sorted(
        candidates,
        key=lambda item: item.relation_confidence,
        reverse=True,
    ):
        key = (
            relation.relation_type,
            relation.source_entity_id,
            relation.target_entity_id,
        )
        best.setdefault(key, relation)
    return tuple(
        sorted(
            best.values(),
            key=lambda item: (
                item.relation_type,
                item.source_entity_id,
                item.target_entity_id,
            ),
        )
    )


def _coverage_block(
    block_id: str,
    label: str,
    max_score: float,
    checks: Iterable[tuple[float, str, bool]],
) -> RelationalCoverageBlock:
    score = 0.0
    rationale: list[str] = []
    for points, reason, condition in checks:
        if condition:
            score += points
            rationale.append(f"+{points:g} {reason}")
    return RelationalCoverageBlock(
        id=block_id,
        label=label,
        score=round(min(score, max_score), 2),
        max_score=max_score,
        rationale=tuple(rationale),
    )


def relational_coverage_score(
    entities: Iterable[ScientificEntityCandidate],
    relations: Iterable[ScientificRelationCandidate],
) -> RelationalCoverageScore:
    entity_tuple = tuple(entities)
    relation_tuple = tuple(relations)
    entity_types = Counter(item.entity_type for item in entity_tuple)
    relation_types = Counter(item.relation_type for item in relation_tuple)
    arms = [item for item in entity_tuple if item.entity_type == "study_arm"]
    intervention_arm = any(_arm_role(item) == "intervention" for item in arms)
    comparator_arm = any(_arm_role(item) == "comparator" for item in arms)

    entities_block = _coverage_block(
        "entity_normalization",
        "Entity normalization",
        20.0,
        (
            (5.0, "population entity", entity_types["population"] > 0),
            (5.0, "study-arm or exposure entity", bool(arms) or entity_types["exposure"] > 0),
            (5.0, "outcome entity", entity_types["outcome"] > 0),
            (5.0, "timepoint or quantitative entity", entity_types["timepoint"] > 0 or entity_types["effect_estimate"] > 0),
        ),
    )
    arms_block = _coverage_block(
        "arm_comparison",
        "Study-arm comparison mapping",
        20.0,
        (
            (6.0, "intervention arm candidate", intervention_arm),
            (6.0, "comparator arm candidate", comparator_arm),
            (8.0, "explicit arm comparison relation", relation_types["compared_with"] > 0),
        ),
    )
    outcome_block = _coverage_block(
        "outcome_time",
        "Outcome and time mapping",
        20.0,
        (
            (8.0, "outcome entity", entity_types["outcome"] > 0),
            (5.0, "timepoint entity", entity_types["timepoint"] > 0),
            (7.0, "outcome/time relation", relation_types["measured_at"] > 0),
        ),
    )
    quantitative_block = _coverage_block(
        "quantitative_bundle",
        "Quantitative estimate bundle",
        30.0,
        (
            (10.0, "effect estimate linked to outcome", relation_types["effect_estimate_for"] > 0),
            (7.0, "effect estimate linked to confidence interval", relation_types["effect_has_confidence_interval"] > 0),
            (7.0, "effect estimate linked to p-value", relation_types["effect_has_p_value"] > 0),
            (6.0, "result linked to table or figure", relation_types["reported_in"] > 0),
        ),
    )
    provenance_block = _coverage_block(
        "relation_provenance",
        "Relation provenance",
        10.0,
        (
            (5.0, "all relations retain source hashes", bool(relation_tuple) and all(item.source_sha256 for item in relation_tuple)),
            (5.0, "all relations retain source fact IDs", bool(relation_tuple) and all(item.source_fact_ids for item in relation_tuple)),
        ),
    )
    blocks = (
        entities_block,
        arms_block,
        outcome_block,
        quantitative_block,
        provenance_block,
    )
    total = round(sum(block.score for block in blocks), 2)
    maximum = round(sum(block.max_score for block in blocks), 2)
    normalized = round((total / maximum) * 100.0, 2) if maximum else 0.0
    return RelationalCoverageScore(
        profile_id="NUTEV_RELATIONAL_COVERAGE",
        profile_version="1",
        semantic_kind="technical_relational_coverage",
        total_score=total,
        max_score=maximum,
        normalized_score=normalized,
        blocks=blocks,
        guardrail=(
            "This score measures whether traceable semantic candidates could be linked "
            "without ambiguous inference. It is not evidence quality, risk of bias, certainty, "
            "eligibility, effect credibility, or recommendation strength."
        ),
    )


def build_relational_layer(
    document_id: str,
    facts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    entities = build_entity_candidates(document_id, facts)
    relations = build_relation_candidates(document_id, entities)
    coverage = relational_coverage_score(entities, relations)
    return {
        "schema_version": 1,
        "status": "machine_relations_materialized",
        "entities": [asdict(item) for item in entities],
        "relations": [asdict(item) for item in relations],
        "coverage_score": asdict(coverage),
        "entity_counts": dict(sorted(Counter(item.entity_type for item in entities).items())),
        "relation_counts": dict(sorted(Counter(item.relation_type for item in relations).items())),
        "guardrails": {
            "entities_are_machine_candidates": True,
            "relations_are_machine_candidates": True,
            "same_sentence_relations_are_preferred": True,
            "locator_fallback_requires_unique_candidates": True,
            "relation_confidence_is_rule_strength_not_probability": True,
            "no_relation_is_an_accepted_evidence_claim": True,
            "prisma_not_required": True,
        },
    }


def _verify_inputs(
    semantic_records_jsonl: Path,
    semantic_facts_jsonl: Path,
    semantic_manifest_path: Path,
) -> dict[str, str]:
    manifest = _read_json(semantic_manifest_path)
    if (
        manifest.get("semantic_type") != "NUTEV_CORE_SEMANTIC_DECONSTRUCTION"
        or manifest.get("status") != "PASS"
    ):
        raise RelationalMappingError("semantic manifest is not a passing NutEV semantic manifest")
    outputs = manifest.get("outputs") or {}
    expected_records = str(
        ((outputs.get("semantic_core_records") or {}).get("sha256")) or ""
    ).strip().lower()
    expected_facts = str(
        ((outputs.get("semantic_fact_candidates") or {}).get("sha256")) or ""
    ).strip().lower()
    if not expected_records or not expected_facts:
        raise RelationalMappingError("semantic manifest is missing required output SHA-256 values")
    actual_records = sha256_file(semantic_records_jsonl)
    actual_facts = sha256_file(semantic_facts_jsonl)
    if actual_records != expected_records:
        raise RelationalMappingError(
            f"semantic CORE records SHA-256 mismatch: expected {expected_records}, got {actual_records}"
        )
    if actual_facts != expected_facts:
        raise RelationalMappingError(
            f"semantic fact candidates SHA-256 mismatch: expected {expected_facts}, got {actual_facts}"
        )
    return {
        "semantic_records": actual_records,
        "semantic_facts": actual_facts,
        "semantic_manifest": sha256_file(semantic_manifest_path),
    }


def _index_records(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        document_id = str(row.get("document_id") or "").strip()
        if not document_id:
            raise RelationalMappingError("semantic CORE record missing document_id")
        if document_id in indexed:
            raise RelationalMappingError(f"duplicate semantic CORE document_id: {document_id}")
        indexed[document_id] = row
    return indexed


def _facts_by_document(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for row in rows:
        document_id = str(row.get("document_id") or "").strip()
        fact_id = str(row.get("id") or "").strip()
        if not document_id or not fact_id:
            raise RelationalMappingError("semantic fact row missing document_id or id")
        if fact_id in seen_ids:
            raise RelationalMappingError(f"duplicate semantic fact id: {fact_id}")
        seen_ids.add(fact_id)
        grouped[document_id].append(row)
    return grouped


def _write_sqlite(
    path: Path,
    entities: Iterable[dict[str, Any]],
    relations: Iterable[dict[str, Any]],
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
            CREATE TABLE entities (
                entity_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                label TEXT NOT NULL,
                normalized_json TEXT NOT NULL,
                source_fact_ids_json TEXT NOT NULL,
                source_sha256_json TEXT NOT NULL,
                locators_json TEXT NOT NULL,
                status TEXT NOT NULL,
                entity_json TEXT NOT NULL
            );
            CREATE INDEX idx_entities_document ON entities(document_id);
            CREATE INDEX idx_entities_type ON entities(entity_type);

            CREATE TABLE relations (
                relation_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                basis TEXT NOT NULL,
                relation_confidence REAL NOT NULL,
                status TEXT NOT NULL,
                relation_json TEXT NOT NULL,
                FOREIGN KEY(source_entity_id) REFERENCES entities(entity_id),
                FOREIGN KEY(target_entity_id) REFERENCES entities(entity_id)
            );
            CREATE INDEX idx_relations_document ON relations(document_id);
            CREATE INDEX idx_relations_type ON relations(relation_type);
            CREATE INDEX idx_relations_source ON relations(source_entity_id);
            CREATE INDEX idx_relations_target ON relations(target_entity_id);

            CREATE TABLE relation_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO relation_meta(key, value) VALUES (?, ?)",
            ("schema", "NUTEV_RELATIONAL_BANK_V1"),
        )
        connection.execute(
            "INSERT INTO relation_meta(key, value) VALUES (?, ?)",
            ("prisma_dependency", "optional_downstream"),
        )
        for entity in entities:
            connection.execute(
                """
                INSERT INTO entities(
                    entity_id, document_id, entity_type, label, normalized_json,
                    source_fact_ids_json, source_sha256_json, locators_json, status, entity_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity["id"],
                    entity["document_id"],
                    entity["entity_type"],
                    entity["label"],
                    json.dumps(entity.get("normalized") or {}, sort_keys=True),
                    json.dumps(entity.get("source_fact_ids") or []),
                    json.dumps(entity.get("source_sha256") or []),
                    json.dumps(entity.get("locators") or []),
                    entity["status"],
                    json.dumps(entity, ensure_ascii=False, sort_keys=True, default=str),
                ),
            )
        for relation in relations:
            connection.execute(
                """
                INSERT INTO relations(
                    relation_id, document_id, relation_type, source_entity_id,
                    target_entity_id, basis, relation_confidence, status, relation_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relation["id"],
                    relation["document_id"],
                    relation["relation_type"],
                    relation["source_entity_id"],
                    relation["target_entity_id"],
                    relation["basis"],
                    relation["relation_confidence"],
                    relation["status"],
                    json.dumps(relation, ensure_ascii=False, sort_keys=True, default=str),
                ),
            )
        connection.commit()
    finally:
        connection.close()
    tmp.replace(path)
    return sha256_file(path)


def run_relational_mapping(
    semantic_records_jsonl: Path,
    semantic_facts_jsonl: Path,
    semantic_manifest: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Materialize schema-v3 CORE records with traceable candidate relations."""

    source_shas = _verify_inputs(
        semantic_records_jsonl,
        semantic_facts_jsonl,
        semantic_manifest,
    )
    records = _read_jsonl(semantic_records_jsonl, label="semantic CORE records")
    flat_facts = _read_jsonl(
        semantic_facts_jsonl,
        label="semantic fact candidates",
        allow_empty=True,
    )
    records_by_doc = _index_records(records)
    facts_by_doc = _facts_by_document(flat_facts)
    if not set(facts_by_doc).issubset(records_by_doc):
        extras = sorted(set(facts_by_doc) - set(records_by_doc))
        raise RelationalMappingError(
            f"semantic facts reference unknown documents: {extras[:5]}"
        )

    output_records: list[dict[str, Any]] = []
    flat_entities: list[dict[str, Any]] = []
    flat_relations: list[dict[str, Any]] = []
    flat_scores: list[dict[str, Any]] = []

    for document_id in sorted(records_by_doc):
        record = dict(records_by_doc[document_id])
        semantic = record.get("semantic") or {}
        if not isinstance(semantic, Mapping):
            raise RelationalMappingError(
                f"semantic CORE record lacks semantic mapping: {document_id}"
            )
        embedded_facts = semantic.get("facts") or []
        if not isinstance(embedded_facts, list):
            raise RelationalMappingError(
                f"semantic facts must be a list for {document_id}"
            )
        embedded_ids = {
            str(item.get("id") or "")
            for item in embedded_facts
            if isinstance(item, Mapping)
        }
        flat_ids = {
            str(item.get("id") or "") for item in facts_by_doc.get(document_id, [])
        }
        if embedded_ids != flat_ids:
            raise RelationalMappingError(
                f"embedded and flat semantic facts disagree for {document_id}"
            )

        relational = build_relational_layer(document_id, embedded_facts)
        record["schema_version"] = max(3, int(record.get("schema_version") or 1))
        record["relational"] = relational
        record.setdefault("workflow", {})
        if isinstance(record["workflow"], dict):
            record["workflow"]["relational_mapping"] = "materialized"
            record["workflow"]["prisma"] = "optional_downstream"
        record.setdefault("guardrails", {})
        if isinstance(record["guardrails"], dict):
            record["guardrails"]["scientific_relations_are_machine_candidates"] = True
            record["guardrails"]["prisma_is_optional"] = True
        output_records.append(record)

        for entity in relational["entities"]:
            flat = dict(entity)
            flat["record_id"] = record.get("id")
            flat_entities.append(flat)
        for relation in relational["relations"]:
            flat = dict(relation)
            flat["record_id"] = record.get("id")
            flat_relations.append(flat)
        coverage = dict(relational["coverage_score"])
        coverage["record_id"] = record.get("id")
        coverage["document_id"] = document_id
        coverage["score_kind"] = "relational_coverage"
        flat_scores.append(coverage)

    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "nutev_core_records_relational.jsonl"
    entities_path = output_dir / "scientific_entity_candidates.jsonl"
    relations_path = output_dir / "scientific_relation_candidates.jsonl"
    scores_path = output_dir / "relational_scorecards.jsonl"
    sqlite_path = output_dir / "nutev_relations.sqlite"
    manifest_path = output_dir / "RELATIONS_MANIFEST.json"

    records_sha = _write_jsonl(records_path, output_records)
    entities_sha = _write_jsonl(entities_path, flat_entities)
    relations_sha = _write_jsonl(relations_path, flat_relations)
    scores_sha = _write_jsonl(scores_path, flat_scores)
    sqlite_sha = _write_sqlite(sqlite_path, flat_entities, flat_relations)

    entity_counts = Counter(str(row.get("entity_type") or "") for row in flat_entities)
    relation_counts = Counter(str(row.get("relation_type") or "") for row in flat_relations)
    manifest = {
        "schema_version": 1,
        "relations_type": "NUTEV_CORE_RELATIONAL_MAPPING",
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "semantic_core_records": str(semantic_records_jsonl),
            "semantic_fact_candidates": str(semantic_facts_jsonl),
            "semantic_manifest": str(semantic_manifest),
            "source_sha256": source_shas,
        },
        "counts": {
            "records": len(output_records),
            "entities": len(flat_entities),
            "relations": len(flat_relations),
            "entity_counts": dict(sorted(entity_counts.items())),
            "relation_counts": dict(sorted(relation_counts.items())),
        },
        "outputs": {
            "relational_core_records": {"path": str(records_path), "sha256": records_sha},
            "scientific_entity_candidates": {"path": str(entities_path), "sha256": entities_sha},
            "scientific_relation_candidates": {"path": str(relations_path), "sha256": relations_sha},
            "relational_scorecards": {"path": str(scores_path), "sha256": scores_sha},
            "relations_sqlite": {"path": str(sqlite_path), "sha256": sqlite_sha},
        },
        "assertions": [
            {"name": "semantic_inputs_hash_verified", "status": "PASS"},
            {"name": "embedded_flat_fact_sets_align", "status": "PASS"},
            {"name": "same_sentence_relations_preferred", "status": "PASS"},
            {"name": "ambiguous_locator_cross_products_blocked", "status": "PASS"},
            {"name": "relations_not_upgraded_to_claims", "status": "PASS"},
            {"name": "prisma_not_required", "status": "PASS"},
        ],
        "guardrail": (
            "Relations are traceable machine candidates. Same-sentence evidence is preferred, "
            "locator fallback requires unique candidates, relation confidence is rule strength "
            "rather than a calibrated probability, and PRISMA remains optional downstream."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)
    return {
        "mode": "NUTEV_CORE_RELATIONAL_MAPPING",
        "status": "COMPLETE",
        "records": len(output_records),
        "entities": len(flat_entities),
        "relations": len(flat_relations),
        "prisma_required": False,
        "outputs": {
            "records": str(records_path),
            "entities": str(entities_path),
            "relations": str(relations_path),
            "scorecards": str(scores_path),
            "sqlite": str(sqlite_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "records": records_sha,
            "entities": entities_sha,
            "relations": relations_sha,
            "scorecards": scores_sha,
            "sqlite": sqlite_sha,
            "manifest": manifest_sha,
        },
    }
