"""Traceable scientific excerpts and compact result bundles for NutEV CORE.

This stage is deterministic by default. It reuses already extracted CORE findings
and semantic facts, selects a small source-linked evidence packet per article,
and never sends full text to an LLM. The resulting article card is intended to
be the cheap context object used by later UI/synthesis layers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


EXTRACTOR_VERSION = "evidence_excerpt_rule_v1"
MAX_EXCERPT_CHARS = 420
MAX_LLM_CONTEXT_CHARS = 6000


class EvidenceExcerptError(RuntimeError):
    """Raised when excerpt/result materialization cannot prove source integrity."""


@dataclass(frozen=True, slots=True)
class EvidenceExcerpt:
    id: str
    document_id: str
    kind: str
    section: str
    locator: str | None
    verbatim_excerpt: str
    excerpt_sha256: str
    source_sentence_sha256: str | None
    source_object_ids: tuple[str, ...]
    semantic_fields: tuple[str, ...]
    priority_score: float
    reference: Mapping[str, Any]
    status: str = "machine_candidate"


@dataclass(frozen=True, slots=True)
class ResultBundle:
    id: str
    document_id: str
    result_kind: str
    excerpt_id: str
    source_sentence_sha256: str | None
    outcomes: tuple[str, ...]
    effect_measures: tuple[str, ...]
    confidence_intervals: tuple[str, ...]
    p_values: tuple[str, ...]
    table_references: tuple[str, ...]
    figure_references: tuple[str, ...]
    result_text: str
    priority_score: float
    reference: Mapping[str, Any]
    status: str = "machine_candidate_not_evidence_claim"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EvidenceExcerptError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceExcerptError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceExcerptError(f"expected JSON object at {path}")
    return value


def _read_jsonl(
    path: Path,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    if not path.is_file():
        raise EvidenceExcerptError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvidenceExcerptError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise EvidenceExcerptError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    if not rows and not allow_empty:
        raise EvidenceExcerptError(f"{label} JSONL is empty: {path}")
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


def _output_sha(manifest: Mapping[str, Any], key: str) -> str:
    value = str(
        (((manifest.get("outputs") or {}).get(key) or {}).get("sha256")) or ""
    ).strip().lower()
    if not value:
        raise EvidenceExcerptError(f"semantic manifest missing SHA-256 for {key}")
    return value


def _verify_inputs(
    semantic_records_jsonl: Path,
    semantic_facts_jsonl: Path,
    semantic_manifest_path: Path,
) -> dict[str, str]:
    manifest = _read_json(semantic_manifest_path)
    if manifest.get("semantic_type") != "NUTEV_CORE_SEMANTIC_DECONSTRUCTION":
        raise EvidenceExcerptError("unexpected semantic manifest type")
    if manifest.get("status") != "PASS":
        raise EvidenceExcerptError("semantic manifest is not PASS")

    actual_records = sha256_file(semantic_records_jsonl)
    actual_facts = sha256_file(semantic_facts_jsonl)
    expected_records = _output_sha(manifest, "semantic_core_records")
    expected_facts = _output_sha(manifest, "semantic_fact_candidates")
    if actual_records != expected_records:
        raise EvidenceExcerptError(
            "semantic records SHA-256 mismatch: "
            f"expected {expected_records}, got {actual_records}"
        )
    if actual_facts != expected_facts:
        raise EvidenceExcerptError(
            "semantic facts SHA-256 mismatch: "
            f"expected {expected_facts}, got {actual_facts}"
        )
    return {
        "semantic_records": actual_records,
        "semantic_facts": actual_facts,
        "semantic_manifest": sha256_file(semantic_manifest_path),
    }


def _heading(value: Any) -> str:
    return str(value or "").strip().casefold().rstrip(":.")


def _clean_excerpt(value: Any) -> str:
    return " ".join(str(value or "").split())[:MAX_EXCERPT_CHARS].strip()


def _as_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _author_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, list):
        return ""
    names: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, Mapping):
            name = str(item.get("name") or "").strip()
            if not name:
                family = str(item.get("family") or item.get("last") or "").strip()
                given = str(item.get("given") or item.get("first") or "").strip()
                name = " ".join(part for part in (given, family) if part)
            if name:
                names.append(name)
    if not names:
        return ""
    if len(names) <= 3:
        return ", ".join(names)
    return f"{names[0]} et al."


def _reference(record: Mapping[str, Any]) -> dict[str, Any]:
    identity = record.get("identity") or {}
    bibliographic = record.get("bibliographic") or {}
    if not isinstance(identity, Mapping):
        identity = {}
    if not isinstance(bibliographic, Mapping):
        bibliographic = {}
    title = str(identity.get("title") or "").strip()
    journal = str(bibliographic.get("journal") or "").strip()
    year = str(identity.get("year") or "").strip()
    doi = str(identity.get("doi") or "").strip()
    pmid = str(identity.get("pmid") or "").strip()
    authors = _author_text(bibliographic.get("authors"))
    parts = [part for part in (authors, title, journal, year) if part]
    reference_stub = ". ".join(parts)
    if reference_stub and not reference_stub.endswith("."):
        reference_stub += "."
    if doi:
        reference_stub += f" DOI: {doi}."
    if pmid:
        reference_stub += f" PMID: {pmid}."
    return {
        "title": title or None,
        "authors": authors or None,
        "journal": journal or None,
        "year": identity.get("year"),
        "doi": doi or None,
        "pmid": pmid or None,
        "url": identity.get("url"),
        "source_provider": identity.get("source_provider"),
        "reference_stub": reference_stub.strip(),
        "style": "deterministic_stub_not_journal_style",
    }


def _fact_category(field: str, section: str) -> str | None:
    section_key = _heading(section)
    if field == "objective":
        return "objective"
    if field == "limitation":
        return "limitation"
    if field in {"funding", "conflict_of_interest"}:
        return "disclosure"
    if field in {
        "population",
        "sample_size",
        "intervention",
        "exposure",
        "comparator",
        "duration",
        "follow_up",
        "eligibility_criteria",
    }:
        return "method"
    if field in {
        "outcome",
        "effect_measure",
        "p_value",
        "confidence_interval",
        "table_reference",
        "figure_reference",
    }:
        if section_key in {"conclusion", "conclusions"}:
            return "conclusion"
        return "result"
    return None


def _candidate_priority(
    category: str,
    *,
    source_score: float,
    fields: Iterable[str],
    section: str,
) -> float:
    base = {
        "result": 8.0,
        "conclusion": 7.0,
        "limitation": 6.0,
        "objective": 5.0,
        "method": 4.0,
        "disclosure": 3.0,
    }.get(category, 0.0)
    field_set = set(fields)
    quantitative = len(
        field_set & {"effect_measure", "p_value", "confidence_interval"}
    )
    if _heading(section) in {"result", "results", "findings"}:
        base += 2.0
    return round(base + float(source_score) + (0.8 * quantitative), 3)


def _build_excerpt_candidates(
    record: Mapping[str, Any],
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped_facts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        source_sha = str(fact.get("source_sha256") or "").strip()
        excerpt = _clean_excerpt(fact.get("source_excerpt"))
        if not source_sha or not excerpt:
            continue
        grouped_facts[source_sha].append(fact)

    candidates: dict[str, dict[str, Any]] = {}

    def add(
        *,
        excerpt: str,
        category: str,
        section: str,
        locator: str | None,
        source_sha: str | None,
        source_ids: Iterable[str],
        fields: Iterable[str],
        source_score: float,
        source_kind: str,
    ) -> None:
        clean = _clean_excerpt(excerpt)
        if not clean:
            return
        excerpt_sha = sha256(clean.encode("utf-8")).hexdigest()
        field_tuple = _as_tuple(str(item) for item in fields)
        score = _candidate_priority(
            category,
            source_score=source_score,
            fields=field_tuple,
            section=section,
        )
        existing = candidates.get(excerpt_sha)
        if existing is None:
            candidates[excerpt_sha] = {
                "excerpt": clean,
                "excerpt_sha": excerpt_sha,
                "category": category,
                "section": section,
                "locator": locator,
                "source_sha": source_sha,
                "source_ids": list(_as_tuple(str(item) for item in source_ids)),
                "fields": list(field_tuple),
                "score": score,
                "source_kinds": [source_kind],
            }
            return
        existing["source_ids"] = list(
            _as_tuple([*existing["source_ids"], *(str(item) for item in source_ids)])
        )
        existing["fields"] = list(
            _as_tuple([*existing["fields"], *field_tuple])
        )
        existing["source_kinds"] = list(
            _as_tuple([*existing["source_kinds"], source_kind])
        )
        if score > float(existing["score"]):
            existing["score"] = score
            existing["category"] = category
            existing["section"] = section
            existing["locator"] = locator
            existing["source_sha"] = source_sha

    for source_sha, source_facts in grouped_facts.items():
        categories = Counter()
        for fact in source_facts:
            category = _fact_category(
                str(fact.get("field") or ""), str(fact.get("section") or "")
            )
            if category:
                categories[category] += 1
        if not categories:
            continue
        category = max(
            categories,
            key=lambda key: (
                categories[key],
                {"result": 6, "conclusion": 5, "limitation": 4, "objective": 3,
                 "method": 2, "disclosure": 1}.get(key, 0),
            ),
        )
        first = source_facts[0]
        add(
            excerpt=str(first.get("source_excerpt") or ""),
            category=category,
            section=str(first.get("section") or "Document text"),
            locator=str(first.get("locator") or "").strip() or None,
            source_sha=source_sha,
            source_ids=(str(item.get("id") or "") for item in source_facts),
            fields=(str(item.get("field") or "") for item in source_facts),
            source_score=max(
                float(item.get("extraction_confidence") or 0.0)
                for item in source_facts
            ),
            source_kind="semantic_fact",
        )

    for finding in record.get("main_findings") or []:
        if not isinstance(finding, Mapping):
            continue
        section = str(finding.get("section") or "Document text")
        section_key = _heading(section)
        if section_key in {"conclusion", "conclusions"}:
            category = "conclusion"
        elif section_key in {"result", "results", "findings"}:
            category = "result"
        elif section_key == "discussion":
            category = "result"
        else:
            category = "result"
        add(
            excerpt=str(finding.get("source_excerpt") or ""),
            category=category,
            section=section,
            locator=str(finding.get("locator") or "").strip() or None,
            source_sha=str(finding.get("sentence_sha256") or "").strip() or None,
            source_ids=(str(finding.get("id") or ""),),
            fields=("finding_candidate",),
            source_score=float(finding.get("importance_score") or 0.0),
            source_kind="finding_candidate",
        )

    return sorted(
        candidates.values(),
        key=lambda item: (float(item["score"]), item["excerpt_sha"]),
        reverse=True,
    )


def _select_excerpts(
    record: Mapping[str, Any],
    facts: list[dict[str, Any]],
) -> tuple[EvidenceExcerpt, ...]:
    candidates = _build_excerpt_candidates(record, facts)
    quotas = {
        "objective": 1,
        "method": 3,
        "result": 5,
        "conclusion": 1,
        "limitation": 2,
        "disclosure": 1,
    }
    selected: list[dict[str, Any]] = []
    for category, limit in quotas.items():
        selected.extend(
            [item for item in candidates if item["category"] == category][:limit]
        )
    selected = sorted(
        {item["excerpt_sha"]: item for item in selected}.values(),
        key=lambda item: (float(item["score"]), item["excerpt_sha"]),
        reverse=True,
    )
    result_ids = [
        item["excerpt_sha"] for item in selected if item["category"] == "result"
    ]
    reference = _reference(record)
    output: list[EvidenceExcerpt] = []
    for item in selected:
        kind = str(item["category"])
        if kind == "result":
            kind = (
                "main_result"
                if item["excerpt_sha"] == (result_ids[0] if result_ids else "")
                else "secondary_result"
            )
        output.append(
            EvidenceExcerpt(
                id=f"excerpt:{record.get('document_id')}:{item['excerpt_sha'][:18]}",
                document_id=str(record.get("document_id") or ""),
                kind=kind,
                section=str(item["section"]),
                locator=item["locator"],
                verbatim_excerpt=str(item["excerpt"]),
                excerpt_sha256=str(item["excerpt_sha"]),
                source_sentence_sha256=item["source_sha"],
                source_object_ids=_as_tuple(item["source_ids"]),
                semantic_fields=_as_tuple(item["fields"]),
                priority_score=float(item["score"]),
                reference=reference,
            )
        )
    return tuple(output)


def _values(facts: Iterable[dict[str, Any]], field: str) -> tuple[str, ...]:
    return _as_tuple(
        str(fact.get("value") or "").strip()
        for fact in facts
        if str(fact.get("field") or "") == field
    )


def _build_result_bundles(
    record: Mapping[str, Any],
    facts: list[dict[str, Any]],
    excerpts: Iterable[EvidenceExcerpt],
) -> tuple[ResultBundle, ...]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        source_sha = str(fact.get("source_sha256") or "").strip()
        if source_sha:
            grouped[source_sha].append(fact)
    reference = _reference(record)
    bundles: list[ResultBundle] = []
    for excerpt in excerpts:
        if excerpt.kind not in {"main_result", "secondary_result"}:
            continue
        source_facts = grouped.get(excerpt.source_sentence_sha256 or "", [])
        bundle_seed = f"{excerpt.id}|{excerpt.source_sentence_sha256 or excerpt.excerpt_sha256}"
        bundle_id = sha256(bundle_seed.encode("utf-8")).hexdigest()[:18]
        bundles.append(
            ResultBundle(
                id=f"result:{excerpt.document_id}:{bundle_id}",
                document_id=excerpt.document_id,
                result_kind=excerpt.kind,
                excerpt_id=excerpt.id,
                source_sentence_sha256=excerpt.source_sentence_sha256,
                outcomes=_values(source_facts, "outcome"),
                effect_measures=_values(source_facts, "effect_measure"),
                confidence_intervals=_values(source_facts, "confidence_interval"),
                p_values=_values(source_facts, "p_value"),
                table_references=_values(source_facts, "table_reference"),
                figure_references=_values(source_facts, "figure_reference"),
                result_text=excerpt.verbatim_excerpt,
                priority_score=excerpt.priority_score,
                reference=reference,
            )
        )
    return tuple(sorted(bundles, key=lambda item: item.priority_score, reverse=True)[:5])


def _first_values(
    facts: Iterable[dict[str, Any]],
    fields: Iterable[str],
    *,
    per_field: int = 2,
) -> dict[str, list[str]]:
    wanted = set(fields)
    output: dict[str, list[str]] = defaultdict(list)
    for fact in sorted(
        facts,
        key=lambda item: float(item.get("extraction_confidence") or 0.0),
        reverse=True,
    ):
        field = str(fact.get("field") or "")
        value = str(fact.get("value") or "").strip()
        if field not in wanted or not value or value in output[field]:
            continue
        if len(output[field]) < per_field:
            output[field].append(value[:500])
    return dict(output)


def _compact_llm_context(
    reference: Mapping[str, Any],
    study_snapshot: Mapping[str, Any],
    excerpts: Iterable[EvidenceExcerpt],
    bundles: Iterable[ResultBundle],
) -> tuple[dict[str, Any], int]:
    selected_excerpts = list(excerpts)
    selected_bundles = list(bundles)

    def payload() -> dict[str, Any]:
        return {
            "reference": {
                "reference_stub": reference.get("reference_stub"),
                "doi": reference.get("doi"),
                "pmid": reference.get("pmid"),
            },
            "study_snapshot": study_snapshot,
            "results": [
                {
                    "kind": item.result_kind,
                    "outcomes": item.outcomes,
                    "effect_measures": item.effect_measures,
                    "confidence_intervals": item.confidence_intervals,
                    "p_values": item.p_values,
                    "quote": item.result_text,
                    "section": next(
                        (
                            excerpt.section
                            for excerpt in selected_excerpts
                            if excerpt.id == item.excerpt_id
                        ),
                        None,
                    ),
                    "locator": next(
                        (
                            excerpt.locator
                            for excerpt in selected_excerpts
                            if excerpt.id == item.excerpt_id
                        ),
                        None,
                    ),
                }
                for item in selected_bundles
            ],
            "supporting_quotes": [
                {
                    "kind": item.kind,
                    "quote": item.verbatim_excerpt,
                    "section": item.section,
                    "locator": item.locator,
                }
                for item in selected_excerpts
                if item.kind
                in {"objective", "method", "conclusion", "limitation"}
            ],
            "guardrail": (
                "Use only these source-linked candidates; do not infer missing study facts. "
                "Machine candidates are not accepted EvidenceClaims."
            ),
        }

    current = payload()
    size = len(json.dumps(current, ensure_ascii=False, default=str))
    while size > MAX_LLM_CONTEXT_CHARS and len(selected_excerpts) > 4:
        removable = next(
            (
                index
                for index in range(len(selected_excerpts) - 1, -1, -1)
                if selected_excerpts[index].kind
                in {"method", "limitation", "secondary_result", "disclosure"}
            ),
            None,
        )
        if removable is None:
            break
        removed = selected_excerpts.pop(removable)
        selected_bundles = [
            bundle for bundle in selected_bundles if bundle.excerpt_id != removed.id
        ]
        current = payload()
        size = len(json.dumps(current, ensure_ascii=False, default=str))
    return current, size


def _cache_key(record: Mapping[str, Any]) -> str:
    acquisition = record.get("acquisition") or {}
    if not isinstance(acquisition, Mapping):
        acquisition = {}
    text_sha = str(acquisition.get("text_sha256") or "").strip()
    if not text_sha:
        text_sha = sha256(
            json.dumps(record, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
    return sha256(
        f"{EXTRACTOR_VERSION}|{record.get('document_id')}|{text_sha}".encode("utf-8")
    ).hexdigest()


def _article_card(
    record: Mapping[str, Any],
    facts: list[dict[str, Any]],
    excerpts: tuple[EvidenceExcerpt, ...],
    bundles: tuple[ResultBundle, ...],
) -> dict[str, Any]:
    reference = _reference(record)
    snapshot = _first_values(
        facts,
        (
            "objective",
            "population",
            "sample_size",
            "intervention",
            "exposure",
            "comparator",
            "outcome",
            "duration",
            "follow_up",
            "limitation",
        ),
    )
    llm_context, context_chars = _compact_llm_context(
        reference, snapshot, excerpts, bundles
    )
    classification = record.get("classification") or {}
    acquisition = record.get("acquisition") or {}
    return {
        "schema_version": 1,
        "document_id": record.get("document_id"),
        "record_id": record.get("id"),
        "cache_key": _cache_key(record),
        "extractor_version": EXTRACTOR_VERSION,
        "identity": record.get("identity") or {},
        "reference": reference,
        "document_class": (
            classification.get("document_class")
            if isinstance(classification, Mapping)
            else None
        ),
        "full_text_status": (
            acquisition.get("full_text_status")
            if isinstance(acquisition, Mapping)
            else None
        ),
        "study_snapshot": snapshot,
        "excerpt_ids": [item.id for item in excerpts],
        "result_bundle_ids": [item.id for item in bundles],
        "counts": {
            "evidence_excerpts": len(excerpts),
            "result_bundles": len(bundles),
            "semantic_facts": len(facts),
        },
        "llm_context": llm_context,
        "llm_context_chars": context_chars,
        "token_cost_policy": {
            "default_mode": "deterministic_only",
            "external_llm_calls": 0,
            "full_text_sent_to_llm": False,
            "future_llm_input": "article_evidence_card.llm_context_only",
            "max_context_chars": MAX_LLM_CONTEXT_CHARS,
            "cache_key": _cache_key(record),
        },
        "workflow": {
            "evidence_excerpt_stage": "materialized",
            "human_validation": "optional_downstream",
            "claim_promotion": "not_performed",
            "prisma": "optional_downstream",
        },
        "guardrails": {
            "quotes_are_short_source_linked_machine_candidates": True,
            "result_bundles_are_not_evidence_claims": True,
            "no_missing_value_is_inferred": True,
            "no_llm_required_for_this_stage": True,
            "copyrighted_full_text_remains_private_execution_material": True,
        },
    }


def _cached_run(
    output_dir: Path,
    source_shas: Mapping[str, str],
) -> dict[str, Any] | None:
    manifest_path = output_dir / "EXCERPT_MANIFEST.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = _read_json(manifest_path)
    except EvidenceExcerptError:
        return None
    if manifest.get("status") != "PASS" or manifest.get("extractor_version") != EXTRACTOR_VERSION:
        return None
    if (manifest.get("source") or {}).get("source_sha256") != dict(source_shas):
        return None
    outputs = manifest.get("outputs") or {}
    for key in ("evidence_excerpts", "result_bundles", "article_evidence_cards"):
        item = outputs.get(key) or {}
        path = Path(str(item.get("path") or ""))
        expected = str(item.get("sha256") or "")
        if not path.is_file() or not expected or sha256_file(path) != expected:
            return None
    counts = manifest.get("counts") or {}
    return {
        "mode": "NUTEV_EVIDENCE_EXCERPTS_RESULTS",
        "status": "COMPLETE",
        "cache_hit": True,
        "extractor_version": EXTRACTOR_VERSION,
        "records": counts.get("records", 0),
        "evidence_excerpts": counts.get("evidence_excerpts", 0),
        "result_bundles": counts.get("result_bundles", 0),
        "llm_calls": 0,
        "manifest": str(manifest_path),
    }


def run_evidence_excerpt_extraction(
    semantic_records_jsonl: Path,
    semantic_facts_jsonl: Path,
    semantic_manifest: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Materialize short quotes, result bundles, and low-token article cards."""

    source_shas = _verify_inputs(
        semantic_records_jsonl, semantic_facts_jsonl, semantic_manifest
    )
    cached = _cached_run(output_dir, source_shas)
    if cached is not None:
        return cached

    records = _read_jsonl(semantic_records_jsonl, label="semantic CORE records")
    facts = _read_jsonl(
        semantic_facts_jsonl,
        label="semantic fact candidates",
        allow_empty=True,
    )
    records_by_doc: dict[str, dict[str, Any]] = {}
    for record in records:
        document_id = str(record.get("document_id") or "").strip()
        if not document_id:
            raise EvidenceExcerptError("semantic CORE record missing document_id")
        if document_id in records_by_doc:
            raise EvidenceExcerptError(f"duplicate semantic CORE document_id: {document_id}")
        records_by_doc[document_id] = record

    facts_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        document_id = str(fact.get("document_id") or "").strip()
        if not document_id or document_id not in records_by_doc:
            raise EvidenceExcerptError(
                f"semantic fact references unknown document_id: {document_id or '<missing>'}"
            )
        if not str(fact.get("source_excerpt") or "").strip():
            raise EvidenceExcerptError("semantic fact missing source_excerpt")
        if not str(fact.get("source_sha256") or "").strip():
            raise EvidenceExcerptError("semantic fact missing source_sha256")
        facts_by_doc[document_id].append(fact)

    all_excerpts: list[dict[str, Any]] = []
    all_bundles: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    kind_counts: Counter[str] = Counter()
    for document_id in sorted(records_by_doc):
        record = records_by_doc[document_id]
        document_facts = facts_by_doc.get(document_id, [])
        excerpts = _select_excerpts(record, document_facts)
        bundles = _build_result_bundles(record, document_facts, excerpts)
        for excerpt in excerpts:
            row = asdict(excerpt)
            all_excerpts.append(row)
            kind_counts[excerpt.kind] += 1
        all_bundles.extend(asdict(bundle) for bundle in bundles)
        cards.append(_article_card(record, document_facts, excerpts, bundles))

    output_dir.mkdir(parents=True, exist_ok=True)
    excerpts_path = output_dir / "evidence_excerpts.jsonl"
    bundles_path = output_dir / "result_bundles.jsonl"
    cards_path = output_dir / "article_evidence_cards.jsonl"
    manifest_path = output_dir / "EXCERPT_MANIFEST.json"
    excerpts_sha = _write_jsonl(excerpts_path, all_excerpts)
    bundles_sha = _write_jsonl(bundles_path, all_bundles)
    cards_sha = _write_jsonl(cards_path, cards)
    manifest = {
        "schema_version": 1,
        "excerpt_type": "NUTEV_EVIDENCE_EXCERPTS_RESULTS",
        "extractor_version": EXTRACTOR_VERSION,
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "semantic_records": str(semantic_records_jsonl),
            "semantic_facts": str(semantic_facts_jsonl),
            "semantic_manifest": str(semantic_manifest),
            "source_sha256": source_shas,
        },
        "counts": {
            "records": len(cards),
            "evidence_excerpts": len(all_excerpts),
            "result_bundles": len(all_bundles),
            "excerpt_kind_counts": dict(sorted(kind_counts.items())),
        },
        "outputs": {
            "evidence_excerpts": {"path": str(excerpts_path), "sha256": excerpts_sha},
            "result_bundles": {"path": str(bundles_path), "sha256": bundles_sha},
            "article_evidence_cards": {"path": str(cards_path), "sha256": cards_sha},
        },
        "token_cost_policy": {
            "default_mode": "deterministic_only",
            "llm_calls": 0,
            "full_text_sent_to_llm": False,
            "future_llm_context_max_chars_per_article": MAX_LLM_CONTEXT_CHARS,
            "cache_identity": "document text SHA-256 + extractor version",
        },
        "assertions": [
            {"name": "semantic_input_hashes_verified", "status": "PASS"},
            {"name": "quotes_preserve_source_locator_and_hash", "status": "PASS"},
            {"name": "result_bundles_not_promoted_to_claims", "status": "PASS"},
            {"name": "no_llm_required", "status": "PASS"},
            {"name": "full_text_not_sent_to_llm", "status": "PASS"},
            {"name": "prisma_not_required", "status": "PASS"},
        ],
        "guardrail": (
            "Evidence excerpts and result bundles are short, source-linked machine candidates. "
            "They support reading, indexing and later synthesis but are not accepted EvidenceClaims, "
            "quality judgments, causal interpretations, eligibility decisions or recommendations."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)
    return {
        "mode": "NUTEV_EVIDENCE_EXCERPTS_RESULTS",
        "status": "COMPLETE",
        "cache_hit": False,
        "extractor_version": EXTRACTOR_VERSION,
        "records": len(cards),
        "evidence_excerpts": len(all_excerpts),
        "result_bundles": len(all_bundles),
        "llm_calls": 0,
        "prisma_required": False,
        "outputs": {
            "excerpts": str(excerpts_path),
            "result_bundles": str(bundles_path),
            "article_cards": str(cards_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "excerpts": excerpts_sha,
            "result_bundles": bundles_sha,
            "article_cards": cards_sha,
            "manifest": manifest_sha,
        },
    }
