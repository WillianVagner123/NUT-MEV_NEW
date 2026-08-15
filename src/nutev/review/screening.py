"""Canonical two-reviewer Article 1 screening flow.

Implements the D-105/D-106/D-107 contract while preserving the original
append-only human decisions. Title/abstract DOUBT is conservatively mapped to
ADVANCE without rewriting the original label; at full text, DOUBT remains
unresolved and blocks closure until consensus/adjudication.

This module contains pure decision/reconciliation/calibration rules. Persistence
and UI layers must enforce reviewer identity, blindness and immutable history.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

PHASES = ("title_abstract", "full_text")
SCREEN_DECISIONS = ("include", "exclude", "uncertain")  # compatibility labels
CANONICAL_DECISIONS = ("INCLUDE", "EXCLUDE", "DOUBT")

EXCLUSION_REASONS = (
    "wrong_population",
    "not_normative_document",
    "wrong_period",
    "wrong_language",
    "empirical_study",
    "review_or_protocol",
    "duplicate",
    "superseded_version",
    "no_full_text",
    "poor_ocr",
    "out_of_scope",
    "aggregator_or_derived",
    "other",
)

DIVERGENCE_TYPES = (
    "population",
    "concept_abcd",
    "dietary_care_context",
    "document_type",
    "family",
    "unit_version",
    "insufficient_information_content",
    "ambiguous_rule",
    "application_error",
    "other_specified",
)


@dataclass(frozen=True, slots=True)
class ReviewerAssignment:
    reviewer_1: str
    reviewer_2: str
    adjudicator: str


def normalize_decision(value: object) -> str:
    raw = str(value or "").strip().upper()
    aliases = {
        "INCLUDE": "INCLUDE", "INCLUIR": "INCLUDE",
        "EXCLUDE": "EXCLUDE", "EXCLUIR": "EXCLUDE",
        "DOUBT": "DOUBT", "DÚVIDA": "DOUBT", "DUVIDA": "DOUBT",
        "MAYBE": "DOUBT", "UNCERTAIN": "DOUBT",
    }
    if raw not in aliases:
        raise ValueError("decision must be INCLUDE, EXCLUDE or DOUBT")
    return aliases[raw]


def validate_formal_reviewer_assignment(reviewer_1: object, reviewer_2: object, adjudicator: object) -> ReviewerAssignment:
    values = [str(v or "").strip() for v in (reviewer_1, reviewer_2, adjudicator)]
    if any(not v for v in values):
        raise ValueError("formal screening requires real R1, R2 and adjudicator identities")
    if len({v.casefold() for v in values}) != 3:
        raise ValueError("R1, R2 and adjudicator must be distinct people")
    return ReviewerAssignment(*values)


def title_abstract_action(decision: object) -> str:
    """D-106: preserve DOUBT but operationally advance it to full text."""
    return "EXCLUDE" if normalize_decision(decision) == "EXCLUDE" else "ADVANCE"


def reconcile_title_abstract(r1: object, r2: object) -> dict[str, object]:
    d1, d2 = normalize_decision(r1), normalize_decision(r2)
    a1, a2 = title_abstract_action(d1), title_abstract_action(d2)
    return {
        "r1_decision": d1,
        "r2_decision": d2,
        "r1_action": a1,
        "r2_action": a2,
        "operational_agreement": a1 == a2,
        "resolution": a1 if a1 == a2 else "CONFLICT",
        "contains_doubt": "DOUBT" in (d1, d2),
    }


def reconcile_full_text(r1: object, r2: object) -> dict[str, object]:
    d1, d2 = normalize_decision(r1), normalize_decision(r2)
    if "DOUBT" in (d1, d2):
        resolution = "UNRESOLVED_DOUBT"
    elif d1 == d2 == "INCLUDE":
        resolution = "INCLUDE"
    elif d1 == d2 == "EXCLUDE":
        resolution = "EXCLUDE"
    else:
        resolution = "CONFLICT"
    return {
        "r1_decision": d1,
        "r2_decision": d2,
        "exact_agreement": d1 == d2,
        "resolution": resolution,
        "requires_consensus_or_adjudication": resolution in {"UNRESOLVED_DOUBT", "CONFLICT"},
    }


def _latest_by_reviewer(decisions: list[dict], phase: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for decision in decisions:
        if decision.get("phase") != phase:
            continue
        reviewer = str(decision.get("reviewer") or "").strip()
        if reviewer:
            out[reviewer] = decision
    return out


def reconcile_record(decisions: list[dict], phase: str) -> dict:
    """Compatibility wrapper exposing canonical stage-specific semantics."""
    if phase not in PHASES:
        raise ValueError(f"phase must be one of {PHASES}")
    by_reviewer = _latest_by_reviewer(decisions, phase)
    if len(by_reviewer) < 2:
        return {"phase": phase, "status": "needs_second_reviewer", "n_reviewers": len(by_reviewer)}
    labels = [row.get("decision") for row in by_reviewer.values()]
    if phase == "title_abstract":
        result = reconcile_title_abstract(labels[0], labels[1])
        if result["resolution"] == "ADVANCE":
            status = "agree_advance"
        elif result["resolution"] == "EXCLUDE":
            status = "agree_exclude"
        else:
            status = "conflict"
    else:
        result = reconcile_full_text(labels[0], labels[1])
        status = {
            "INCLUDE": "agree_include",
            "EXCLUDE": "agree_exclude",
            "UNRESOLVED_DOUBT": "unresolved_doubt",
            "CONFLICT": "conflict",
        }[str(result["resolution"])]
    return {"phase": phase, "status": status, "n_reviewers": len(by_reviewer), "labels": [normalize_decision(x) for x in labels]}


def adjudicate(record_id: str, phase: str, adjudicator: str, decision: str, rationale: str) -> dict:
    normalized = normalize_decision(decision)
    if normalized not in {"INCLUDE", "EXCLUDE"}:
        raise ValueError("adjudication decision must be include or exclude")
    if not str(adjudicator).strip() or not str(rationale).strip():
        raise ValueError("adjudication requires an adjudicator and a rationale")
    return {
        "record_id": record_id,
        "phase": phase,
        "adjudicator": adjudicator,
        "decision": normalized.lower(),
        "rationale": rationale,
        "kind": "adjudication",
    }


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if n == 0:
        return 0.0
    po = sum(1 for a, b in pairs if a == b) / n
    a_counts = Counter(a for a, _ in pairs)
    b_counts = Counter(b for _, b in pairs)
    categories = set(a_counts) | set(b_counts)
    pe = sum((a_counts[c] / n) * (b_counts[c] / n) for c in categories)
    if abs(1 - pe) < 1e-12:
        return 1.0 if po == 1.0 else 0.0
    return round((po - pe) / (1 - pe), 4)


def queue_reviewer_pairs(queue: list[dict]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row in queue:
        a = str(row.get("reviewer_1_decision") or "").strip().lower()
        b = str(row.get("reviewer_2_decision") or "").strip().lower()
        if a in SCREEN_DECISIONS and b in SCREEN_DECISIONS:
            pairs.append((a, b))
    return pairs


def screening_agreement(queue: list[dict]) -> dict:
    """Descriptive agreement report; no generic kappa pass/fail interpretation."""
    pairs = queue_reviewer_pairs(queue)
    n_items, n_pairs = len(queue), len(pairs)
    flags = Counter(str(row.get("screen_flag") or "unknown") for row in queue)
    agree = sum(1 for a, b in pairs if a == b)
    agree_include = sum(1 for a, b in pairs if a == b == "include")
    agree_exclude = sum(1 for a, b in pairs if a == b == "exclude")
    export_ready = sum(1 for row in queue if row.get("export_ready"))
    return {
        "n_items": n_items,
        "n_double_screened": n_pairs,
        "cohen_kappa": cohen_kappa(pairs) if n_pairs else None,
        "percent_agreement": round(agree / n_pairs, 4) if n_pairs else None,
        "agree_total": agree,
        "agree_include": agree_include,
        "agree_exclude": agree_exclude,
        "conflicts": n_pairs - agree,
        "ready_to_screen": flags.get("ready_to_screen", 0),
        "no_full_text": flags.get("no_full_text", 0),
        "poor_ocr": flags.get("poor_ocr", 0),
        "export_ready": export_ready,
        "note": (
            "No double-screened records yet; descriptive agreement is available once two reviewers record decisions."
            if not n_pairs
            else "Descriptive agreement over records independently screened by two reviewers; methodological gates are evaluated separately."
        ),
    }


def final_decision(record_decisions: list[dict], adjudications: list[dict] | None = None) -> dict:
    adjudications = adjudications or []
    reconciled = reconcile_record(record_decisions, "full_text")
    if reconciled["status"] == "agree_include":
        return {"decision": "include", "basis": "agreement"}
    if reconciled["status"] == "agree_exclude":
        return {"decision": "exclude", "basis": "agreement"}
    adj = next((row for row in adjudications if row.get("phase") == "full_text"), None)
    if adj:
        return {"decision": adj["decision"], "basis": "adjudication", "rationale": adj.get("rationale", "")}
    return {"decision": "pending", "basis": reconciled["status"]}


def is_export_ready(record_decisions: list[dict], adjudications: list[dict] | None = None) -> bool:
    return final_decision(record_decisions, adjudications).get("decision") == "include"


def export_blocked_reason(record_decisions: list[dict], adjudications: list[dict] | None = None) -> str:
    final = final_decision(record_decisions, adjudications)
    if final["decision"] == "include":
        return ""
    if final["decision"] == "exclude":
        return "excluded in full-text screening"
    return f"not validated ({final['basis']})"


def title_abstract_calibration_metrics(
    rows: Sequence[Mapping[str, object]], *, expected_units: int,
    recurrent_rule_contradiction: bool = False, gf07_resolved: bool = False,
) -> dict[str, object]:
    if expected_units <= 0:
        raise ValueError("expected_units must be > 0")
    if len(rows) > expected_units:
        raise ValueError("rows cannot exceed expected_units")
    complete = agreements = r1_doubt = r2_doubt = conflicts = 0
    invalid: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        try:
            d1, d2 = normalize_decision(row.get("r1_decision")), normalize_decision(row.get("r2_decision"))
        except ValueError as exc:
            invalid.append({"row": index, "error": str(exc)})
            continue
        complete += 1
        r1_doubt += d1 == "DOUBT"
        r2_doubt += d2 == "DOUBT"
        result = reconcile_title_abstract(d1, d2)
        agreements += bool(result["operational_agreement"])
        conflicts += result["resolution"] == "CONFLICT"
    completeness = complete / expected_units
    agreement = agreements / complete if complete else None
    release = bool(gf07_resolved and completeness == 1.0 and agreement is not None and agreement >= 0.80 and not recurrent_rule_contradiction and not invalid)
    return {
        "expected_units": expected_units, "complete_pairs": complete, "completeness": completeness,
        "agreement_denominator": complete, "advance_exclude_raw_agreement": agreement,
        "operational_conflicts": conflicts, "r1_doubt_count": r1_doubt, "r2_doubt_count": r2_doubt,
        "recurrent_rule_contradiction": bool(recurrent_rule_contradiction), "gf07_resolved": bool(gf07_resolved),
        "invalid_pairs": invalid, "release_signal": release,
        "note": "Family classification at title/abstract is descriptive and does not block conservative advancement to full text.",
    }


def full_text_calibration_metrics(
    rows: Sequence[Mapping[str, object]], *, expected_units: int,
    recurrent_rule_contradiction: bool = False, gf07_resolved: bool = False,
) -> dict[str, object]:
    if expected_units <= 0:
        raise ValueError("expected_units must be > 0")
    if len(rows) > expected_units:
        raise ValueError("rows cannot exceed expected_units")
    complete = exact = doubts = conflicts = both_include = family_den = family_matches = 0
    invalid: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        try:
            d1, d2 = normalize_decision(row.get("r1_decision")), normalize_decision(row.get("r2_decision"))
        except ValueError as exc:
            invalid.append({"row": index, "error": str(exc)})
            continue
        complete += 1
        exact += d1 == d2
        rec = reconcile_full_text(d1, d2)
        doubts += rec["resolution"] == "UNRESOLVED_DOUBT"
        conflicts += rec["resolution"] == "CONFLICT"
        if d1 == d2 == "INCLUDE":
            both_include += 1
            f1, f2 = str(row.get("r1_family") or "").strip().upper(), str(row.get("r2_family") or "").strip().upper()
            if f1 and f2:
                family_den += 1
                family_matches += f1 == f2
    completeness = complete / expected_units
    agreement = exact / complete if complete else None
    family_agreement = family_matches / family_den if family_den else None
    family_ok = family_agreement is None or family_agreement >= 0.80
    release = bool(gf07_resolved and completeness == 1.0 and agreement is not None and agreement >= 0.80 and family_ok and doubts == 0 and not recurrent_rule_contradiction and not invalid)
    return {
        "expected_units": expected_units, "complete_pairs": complete, "completeness": completeness,
        "eligibility_denominator": complete, "eligibility_exact_matches": exact, "eligibility_raw_agreement": agreement,
        "unresolved_doubt_pairs": doubts, "eligibility_conflicts": conflicts, "both_include_pairs": both_include,
        "family_denominator": family_den, "family_exact_matches": family_matches, "family_raw_agreement": family_agreement,
        "recurrent_rule_contradiction": bool(recurrent_rule_contradiction), "gf07_resolved": bool(gf07_resolved),
        "invalid_pairs": invalid, "release_signal": release,
        "note": "Exclusion-reason agreement is descriptive; no additional threshold is introduced.",
    }


def blind_reviewer_view(row: Mapping[str, object], *, reviewer_slot: str, own_submitted: bool, pair_unblinded: bool = False) -> dict[str, object]:
    slot = str(reviewer_slot or "").strip().upper()
    if slot not in {"R1", "R2"}:
        raise ValueError("reviewer_slot must be R1 or R2")
    own_key = "r1_decision" if slot == "R1" else "r2_decision"
    other_key = "r2_decision" if slot == "R1" else "r1_decision"
    view = dict(row)
    if not pair_unblinded:
        view[other_key] = None
    if not own_submitted:
        view[own_key] = row.get(own_key)
    return view


_FULLTEXT_OK = {"ok", "ok_ocr", "fake_pdf_html", "fake_pdf_text"}


def build_screening_queue(rows: list[dict]) -> list[dict]:
    queue: list[dict] = []
    for row in rows:
        status = str(row.get("extraction_status") or "")
        if status in _FULLTEXT_OK:
            flag = "ready_to_screen"
        elif status in {"pdf_needs_ocr_setup", "ocr_fail"}:
            flag = "poor_ocr"
        else:
            flag = "no_full_text"
        queue.append({
            "record_id": row.get("_guide_key") or row.get("name", ""),
            "name": row.get("name", ""),
            "country": row.get("country", row.get("reference_country", "")),
            "reference": row.get("reference", ""),
            "extraction_status": status,
            "screen_flag": flag,
            "phase": "title_abstract",
            "reviewer_1_decision": "",
            "reviewer_2_decision": "",
            "exclusion_reason": "",
            "status": "needs_second_reviewer",
            "export_ready": False,
        })
    return queue
