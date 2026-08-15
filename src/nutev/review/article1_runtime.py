"""Article 1 runtime integrated into the existing Evidence Matrix SQLite.

P2: persistent ABCD-NutEV 34/34 double extraction and adjudication.
P3: explicit relation ledger, evidence instances, review completion, calibration.
P4: family-preserving synthesis, Sheet export payload and audit manifest.

Software capability never implies PRESS/GF closure, formal execution, PRISMA
completion or scientific validity. Final scientific decisions remain human.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from nutev.analysis.article1_abcd import (
    ABCD_CODES,
    ABCD_COMPONENTS,
    ABCD_VERSION,
    assert_document_can_close,
    calibration_metrics,
    codebook_rows,
    document_completion,
    validate_component_decision,
)
from nutev.review.evidence_matrix_core import (
    SLOTS,
    _db,
    _j,
    _loads,
    _now,
    _open_session,
    _reviewer,
    initialize,
)
from nutev.review.evidence_matrix_extraction import _included, _require_included
from nutev.review.screening import validate_formal_reviewer_assignment

ARTICLE1_ID = "article_1"
EXECUTION_MODES = ("STAGING", "CALIBRATION", "FORMAL")
RELATION_DIRECTIONS = ("SOURCE_TO_TARGET", "BIDIRECTIONAL", "NON_DIRECTIONAL")
RELATION_TYPES = (
    "CONDITION",
    "MODIFIES",
    "REQUIRES",
    "TRIGGERS",
    "SUPPORTS",
    "MONITORS",
    "COORDINATES",
    "OTHER_EXPLICIT",
)
RELATION_FINAL_DECISIONS = ("INCLUDE", "EXCLUDE")
ABCD_DETAIL_FIELDS = (
    "family",
    "locator",
    "evidence",
    "action_strategy",
    "target",
    "actor_responsible",
    "frequency_sequence",
    "tool_material",
    "indicator_criterion",
    "context_condition",
    "interpretation_nature",
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _normalize_mode(value: object) -> str:
    mode = _clean(value).upper() or "STAGING"
    if mode not in EXECUTION_MODES:
        raise ValueError(f"execution_mode must be one of {EXECUTION_MODES}")
    return mode


def _normalize_slot(value: object) -> str:
    slot = _clean(value).upper()
    slot = {"R1": "REVIEWER_1", "R2": "REVIEWER_2"}.get(slot, slot)
    if slot not in SLOTS:
        raise ValueError(f"reviewer_slot must be one of {SLOTS}")
    return slot


def initialize_article1_runtime(db_path: Path) -> None:
    """Create additive Article 1 tables in the existing Evidence Matrix DB."""
    initialize(db_path)
    with _db(db_path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS article1_reviewer_assignments(
              session_id TEXT PRIMARY KEY,
              reviewer_1_name TEXT NOT NULL,
              reviewer_2_name TEXT NOT NULL,
              adjudicator_name TEXT NOT NULL,
              gf07_resolved INTEGER NOT NULL CHECK(gf07_resolved IN (0,1)),
              notes TEXT NOT NULL DEFAULT '',
              revision INTEGER NOT NULL,
              recorded_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id));

            CREATE TABLE IF NOT EXISTS article1_abcd_submissions(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              article_id TEXT NOT NULL DEFAULT 'article_1',
              execution_mode TEXT NOT NULL CHECK(execution_mode IN ('STAGING','CALIBRATION','FORMAL')),
              reviewer_slot TEXT NOT NULL CHECK(reviewer_slot IN ('REVIEWER_1','REVIEWER_2')),
              reviewer_name TEXT NOT NULL,
              reviewer_role TEXT NOT NULL,
              code TEXT NOT NULL,
              presence TEXT NOT NULL CHECK(presence IN ('YES','NO','DOUBT')),
              depth INTEGER,
              details_json TEXT NOT NULL DEFAULT '{}',
              codebook_version TEXT NOT NULL,
              revision INTEGER NOT NULL,
              submitted_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,reviewer_slot,code,revision));
            CREATE INDEX IF NOT EXISTS idx_article1_abcd_latest
              ON article1_abcd_submissions(session_id,document_id,reviewer_slot,code,revision DESC);

            CREATE TABLE IF NOT EXISTS article1_abcd_adjudications(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              code TEXT NOT NULL,
              reviewer_1_json TEXT NOT NULL,
              reviewer_2_json TEXT NOT NULL,
              final_json TEXT NOT NULL,
              adjudicator_name TEXT NOT NULL,
              adjudicator_role TEXT NOT NULL,
              notes TEXT NOT NULL DEFAULT '',
              codebook_version TEXT NOT NULL,
              revision INTEGER NOT NULL,
              decided_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,code,revision));

            CREATE TABLE IF NOT EXISTS article1_relation_submissions(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              article_id TEXT NOT NULL DEFAULT 'article_1',
              execution_mode TEXT NOT NULL CHECK(execution_mode IN ('STAGING','CALIBRATION','FORMAL')),
              reviewer_slot TEXT NOT NULL CHECK(reviewer_slot IN ('REVIEWER_1','REVIEWER_2')),
              reviewer_name TEXT NOT NULL,
              reviewer_role TEXT NOT NULL,
              relation_key TEXT NOT NULL,
              source_code TEXT NOT NULL,
              target_code TEXT NOT NULL,
              direction TEXT NOT NULL,
              relation_type TEXT NOT NULL,
              family TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL CHECK(active IN (0,1)),
              relation_codebook_version TEXT NOT NULL,
              revision INTEGER NOT NULL,
              submitted_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,reviewer_slot,relation_key,revision));
            CREATE INDEX IF NOT EXISTS idx_article1_relation_latest
              ON article1_relation_submissions(session_id,document_id,reviewer_slot,relation_key,revision DESC);

            CREATE TABLE IF NOT EXISTS article1_relation_evidence_instances(
              id TEXT PRIMARY KEY,
              relation_submission_id TEXT NOT NULL,
              locator TEXT NOT NULL DEFAULT '',
              evidence TEXT NOT NULL,
              evidence_order INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(relation_submission_id) REFERENCES article1_relation_submissions(id));

            CREATE TABLE IF NOT EXISTS article1_relation_review_status(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              reviewer_slot TEXT NOT NULL CHECK(reviewer_slot IN ('REVIEWER_1','REVIEWER_2')),
              reviewer_name TEXT NOT NULL,
              reviewer_role TEXT NOT NULL,
              complete INTEGER NOT NULL CHECK(complete IN (0,1)),
              revision INTEGER NOT NULL,
              recorded_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,reviewer_slot,revision));

            CREATE TABLE IF NOT EXISTS article1_relation_adjudications(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              relation_key TEXT NOT NULL,
              reviewer_1_json TEXT NOT NULL,
              reviewer_2_json TEXT NOT NULL,
              final_decision TEXT NOT NULL CHECK(final_decision IN ('INCLUDE','EXCLUDE')),
              final_json TEXT NOT NULL,
              adjudicator_name TEXT NOT NULL,
              adjudicator_role TEXT NOT NULL,
              notes TEXT NOT NULL DEFAULT '',
              revision INTEGER NOT NULL,
              decided_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,relation_key,revision));

            CREATE TABLE IF NOT EXISTS article1_method_characterization(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              family TEXT NOT NULL DEFAULT '',
              fields_json TEXT NOT NULL,
              reviewer_name TEXT NOT NULL,
              reviewer_role TEXT NOT NULL,
              revision INTEGER NOT NULL,
              recorded_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,revision));

            CREATE TABLE IF NOT EXISTS article1_synthesis_snapshots(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              codebook_version TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              payload_sha256 TEXT NOT NULL,
              ready INTEGER NOT NULL CHECK(ready IN (0,1)),
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id));
            """
        )


def set_article1_reviewer_assignment(
    db_path: Path,
    *,
    session_id: str,
    reviewer_1_name: str,
    reviewer_2_name: str,
    adjudicator_name: str,
    notes: str = "",
) -> dict[str, Any]:
    assignment = validate_formal_reviewer_assignment(
        reviewer_1_name, reviewer_2_name, adjudicator_name
    )
    initialize_article1_runtime(db_path)
    _open_session(db_path, session_id)
    with _db(db_path) as con:
        old = con.execute(
            "SELECT revision FROM article1_reviewer_assignments WHERE session_id=?",
            (session_id,),
        ).fetchone()
        revision = int(old[0]) + 1 if old else 1
        con.execute(
            """INSERT INTO article1_reviewer_assignments VALUES(?,?,?,?,1,?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET
                 reviewer_1_name=excluded.reviewer_1_name,
                 reviewer_2_name=excluded.reviewer_2_name,
                 adjudicator_name=excluded.adjudicator_name,
                 gf07_resolved=1,
                 notes=excluded.notes,
                 revision=excluded.revision,
                 recorded_at=excluded.recorded_at""",
            (
                session_id,
                assignment.reviewer_1,
                assignment.reviewer_2,
                assignment.adjudicator,
                notes.strip(),
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_reviewer_assignments WHERE session_id=?",
            (session_id,),
        ).fetchone()
    return dict(row)


def article1_reviewer_assignment(
    db_path: Path, session_id: str
) -> dict[str, Any] | None:
    initialize_article1_runtime(db_path)
    with _db(db_path) as con:
        row = con.execute(
            "SELECT * FROM article1_reviewer_assignments WHERE session_id=?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def _formal_guard(
    db_path: Path,
    *,
    session_id: str,
    execution_mode: str,
    reviewer_slot: str | None = None,
    reviewer_name: str | None = None,
) -> None:
    if execution_mode != "FORMAL":
        return
    assignment = article1_reviewer_assignment(db_path, session_id)
    if not assignment or not bool(assignment["gf07_resolved"]):
        raise ValueError(
            "FORMAL Article 1 work is blocked until GF-07 has real R1/R2/adjudicator identities"
        )
    if reviewer_slot and reviewer_name:
        expected = (
            assignment["reviewer_1_name"]
            if reviewer_slot == "REVIEWER_1"
            else assignment["reviewer_2_name"]
        )
        if _clean(reviewer_name).casefold() != _clean(expected).casefold():
            raise ValueError(
                f"{reviewer_slot} identity does not match the GF-07 assignment"
            )


def _require_formal_included(
    db_path: Path, session_id: str, document_id: str, execution_mode: str
) -> None:
    if execution_mode == "FORMAL":
        _require_included(db_path, session_id, document_id, ARTICLE1_ID)


def instantiate_article1_abcd_grid(document_id: str) -> list[dict[str, Any]]:
    return [
        {
            "document_id": document_id,
            "code": code,
            "macro": ABCD_COMPONENTS[code].macro,
            "label": ABCD_COMPONENTS[code].label,
            "codebook_version": ABCD_VERSION,
            "presence": None,
            "depth": None,
            "status": "UNASSESSED",
        }
        for code in ABCD_CODES
    ]


def submit_article1_abcd(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    reviewer_slot: str,
    reviewer_name: str,
    reviewer_role: str,
    code: str,
    presence: object,
    depth: object,
    execution_mode: str = "STAGING",
    **details: str,
) -> dict[str, Any]:
    initialize_article1_runtime(db_path)
    _open_session(db_path, session_id)
    slot = _normalize_slot(reviewer_slot)
    name, role = _reviewer(reviewer_name, reviewer_role)
    mode = _normalize_mode(execution_mode)
    _formal_guard(
        db_path,
        session_id=session_id,
        execution_mode=mode,
        reviewer_slot=slot,
        reviewer_name=name,
    )
    _require_formal_included(db_path, session_id, document_id, mode)
    normalized_code, normalized_presence, normalized_depth = validate_component_decision(
        code=code, presence=presence, depth=depth, final=False
    )
    normalized_details = {
        field: _clean(details.get(field, "")) for field in ABCD_DETAIL_FIELDS
    }
    if normalized_presence == "YES" and not normalized_details["evidence"]:
        raise ValueError("YES requires traceable supporting evidence")
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_abcd_submissions
                   WHERE session_id=? AND document_id=? AND reviewer_slot=? AND code=?""",
                (session_id, document_id, slot, normalized_code),
            ).fetchone()[0]
        )
        row_id = f"article1_abcd_{uuid4().hex}"
        con.execute(
            "INSERT INTO article1_abcd_submissions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                ARTICLE1_ID,
                mode,
                slot,
                name,
                role,
                normalized_code,
                normalized_presence,
                normalized_depth,
                _j(normalized_details),
                ABCD_VERSION,
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_abcd_submissions WHERE id=?", (row_id,)
        ).fetchone()
    output = dict(row)
    output["details"] = _loads(output["details_json"], {})
    return output


def _latest_abcd(
    db_path: Path,
    *,
    session_id: str,
    document_id: str | None = None,
    reviewer_slot: str | None = None,
) -> list[dict[str, Any]]:
    initialize_article1_runtime(db_path)
    clauses = ["a.session_id=?"]
    params: list[object] = [session_id]
    if document_id:
        clauses.append("a.document_id=?")
        params.append(document_id)
    if reviewer_slot:
        clauses.append("a.reviewer_slot=?")
        params.append(_normalize_slot(reviewer_slot))
    with _db(db_path) as con:
        rows = con.execute(
            f"""SELECT a.* FROM article1_abcd_submissions a JOIN(
                  SELECT session_id,document_id,reviewer_slot,code,MAX(revision) revision
                  FROM article1_abcd_submissions
                  GROUP BY session_id,document_id,reviewer_slot,code) x
                ON x.session_id=a.session_id AND x.document_id=a.document_id
                AND x.reviewer_slot=a.reviewer_slot AND x.code=a.code
                AND x.revision=a.revision
                WHERE {' AND '.join(clauses)}""",
            params,
        ).fetchall()
    output = []
    for raw in rows:
        row = dict(raw)
        row["details"] = _loads(row["details_json"], {})
        output.append(row)
    return output


def _latest_abcd_adjudications(
    db_path: Path, session_id: str, document_id: str
) -> dict[str, dict[str, Any]]:
    initialize_article1_runtime(db_path)
    with _db(db_path) as con:
        rows = con.execute(
            """SELECT a.* FROM article1_abcd_adjudications a JOIN(
                 SELECT code,MAX(revision) revision FROM article1_abcd_adjudications
                 WHERE session_id=? AND document_id=? GROUP BY code) x
               ON x.code=a.code AND x.revision=a.revision
               WHERE a.session_id=? AND a.document_id=?""",
            (session_id, document_id, session_id, document_id),
        ).fetchall()
    output = {}
    for raw in rows:
        row = dict(raw)
        row["reviewer_1"] = _loads(row["reviewer_1_json"], None)
        row["reviewer_2"] = _loads(row["reviewer_2_json"], None)
        row["final"] = _loads(row["final_json"], None)
        output[row["code"]] = row
    return output


def _compact_abcd(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    output = {
        "code": row.get("code"),
        "presence": row.get("presence"),
        "depth": row.get("depth"),
    }
    output.update(dict(row.get("details") or {}))
    return output


def compare_article1_abcd(
    db_path: Path, *, session_id: str, document_id: str
) -> list[dict[str, Any]]:
    latest = _latest_abcd(
        db_path, session_id=session_id, document_id=document_id
    )
    by_slot: dict[str, dict[str, dict[str, Any]]] = {slot: {} for slot in SLOTS}
    for row in latest:
        by_slot[row["reviewer_slot"]][row["code"]] = row
    adjudications = _latest_abcd_adjudications(db_path, session_id, document_id)
    output = []
    for code in ABCD_CODES:
        r1 = by_slot["REVIEWER_1"].get(code)
        r2 = by_slot["REVIEWER_2"].get(code)
        c1, c2 = _compact_abcd(r1), _compact_abcd(r2)
        if not r1 and not r2:
            status = "MISSING_BOTH"
        elif not r1:
            status = "MISSING_REVIEWER_1"
        elif not r2:
            status = "MISSING_REVIEWER_2"
        elif r1["presence"] == r2["presence"] and r1["depth"] == r2["depth"]:
            status = "AGREED"
        elif "DOUBT" in {r1["presence"], r2["presence"]}:
            status = "UNRESOLVED_DOUBT"
        else:
            status = "DIVERGENT"
        adjudication = adjudications.get(code)
        final = c1 if status == "AGREED" else adjudication.get("final") if adjudication else None
        output.append(
            {
                "code": code,
                "label": ABCD_COMPONENTS[code].label,
                "reviewer_1": c1,
                "reviewer_2": c2,
                "status": status,
                "final": final,
                "final_status": (
                    "AGREED"
                    if status == "AGREED"
                    else "ADJUDICATED"
                    if adjudication
                    else "PENDING"
                ),
            }
        )
    return output


def adjudicate_article1_abcd(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    code: str,
    final_presence: object,
    final_depth: object,
    adjudicator_name: str,
    adjudicator_role: str,
    notes: str = "",
    **details: str,
) -> dict[str, Any]:
    initialize_article1_runtime(db_path)
    _open_session(db_path, session_id)
    name, role = _reviewer(adjudicator_name, adjudicator_role)
    assignment = article1_reviewer_assignment(db_path, session_id)
    if assignment and _clean(name).casefold() != _clean(
        assignment["adjudicator_name"]
    ).casefold():
        raise ValueError("adjudicator identity does not match the GF-07 assignment")
    normalized_code, presence, depth = validate_component_decision(
        code=code, presence=final_presence, depth=final_depth, final=True
    )
    comparison = {
        row["code"]: row
        for row in compare_article1_abcd(
            db_path, session_id=session_id, document_id=document_id
        )
    }[normalized_code]
    if comparison["status"] not in {"DIVERGENT", "UNRESOLVED_DOUBT"}:
        raise ValueError(
            "only divergent or unresolved-DOUBT ABCD components require adjudication"
        )
    final = {"code": normalized_code, "presence": presence, "depth": depth}
    for field in ABCD_DETAIL_FIELDS:
        final[field] = _clean(details.get(field, ""))
    if presence == "YES" and not final["evidence"]:
        for reviewer in (comparison["reviewer_1"], comparison["reviewer_2"]):
            if reviewer and reviewer.get("evidence"):
                final["evidence"] = _clean(reviewer["evidence"])
                break
    if presence == "YES" and not final["evidence"]:
        raise ValueError("final YES adjudication requires traceable evidence")
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_abcd_adjudications
                   WHERE session_id=? AND document_id=? AND code=?""",
                (session_id, document_id, normalized_code),
            ).fetchone()[0]
        )
        row_id = f"article1_abcd_adj_{uuid4().hex}"
        con.execute(
            "INSERT INTO article1_abcd_adjudications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                normalized_code,
                _j(comparison["reviewer_1"]),
                _j(comparison["reviewer_2"]),
                _j(final),
                name,
                role,
                notes.strip(),
                ABCD_VERSION,
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_abcd_adjudications WHERE id=?", (row_id,)
        ).fetchone()
    return dict(row)


def final_article1_abcd(
    db_path: Path, *, session_id: str, document_id: str
) -> list[dict[str, Any]]:
    comparison = compare_article1_abcd(
        db_path, session_id=session_id, document_id=document_id
    )
    pending = [row["code"] for row in comparison if row["final_status"] == "PENDING"]
    if pending:
        raise ValueError(
            "ABCD extraction is not closed; pending components: "
            + ", ".join(pending)
        )
    rows = [dict(row["final"] or {}) for row in comparison]
    assert_document_can_close(rows)
    return rows


def article1_abcd_document_status(
    db_path: Path, *, session_id: str, document_id: str
) -> dict[str, Any]:
    comparison = compare_article1_abcd(
        db_path, session_id=session_id, document_id=document_id
    )
    finals = [row["final"] for row in comparison if row["final"]]
    raw_status = document_completion(finals)
    pending = [row["code"] for row in comparison if row["final_status"] == "PENDING"]
    return {
        **raw_status,
        "pending_codes": pending,
        "agreed_components": sum(
            row["final_status"] == "AGREED" for row in comparison
        ),
        "adjudicated_components": sum(
            row["final_status"] == "ADJUDICATED" for row in comparison
        ),
        "closed": not pending and bool(raw_status["closed"]),
    }


def article1_abcd_calibration_report(
    db_path: Path,
    *,
    session_id: str,
    document_ids: Sequence[str],
    recurrent_critical_divergence: bool = False,
) -> dict[str, Any]:
    if not document_ids:
        raise ValueError("document_ids cannot be empty")
    pairs = []
    for document_id in document_ids:
        for row in compare_article1_abcd(
            db_path, session_id=session_id, document_id=document_id
        ):
            r1, r2 = row["reviewer_1"] or {}, row["reviewer_2"] or {}
            pairs.append(
                {
                    "code": row["code"],
                    "r1_presence": r1.get("presence"),
                    "r1_depth": r1.get("depth"),
                    "r2_presence": r2.get("presence"),
                    "r2_depth": r2.get("depth"),
                }
            )
    return calibration_metrics(
        pairs,
        expected_units=34 * len(document_ids),
        recurrent_critical_divergence=recurrent_critical_divergence,
    )


def normalize_relation(
    *, source_code: object, target_code: object, direction: object, relation_type: object
) -> tuple[str, str, str, str, str]:
    source = _clean(source_code).upper()
    target = _clean(target_code).upper()
    if source not in ABCD_COMPONENTS or target not in ABCD_COMPONENTS:
        raise ValueError(
            "source_code and target_code must be valid ABCD component codes"
        )
    if source == target:
        raise ValueError("source_code and target_code must be different components")
    normalized_direction = _clean(direction).upper()
    normalized_type = _clean(relation_type).upper()
    if normalized_direction not in RELATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {RELATION_DIRECTIONS}")
    if normalized_type not in RELATION_TYPES:
        raise ValueError(f"relation_type must be one of {RELATION_TYPES}")
    key = "|".join((source, target, normalized_direction, normalized_type))
    return key, source, target, normalized_direction, normalized_type


def submit_article1_relation(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    reviewer_slot: str,
    reviewer_name: str,
    reviewer_role: str,
    source_code: str,
    target_code: str,
    direction: str,
    relation_type: str,
    evidence_instances: Sequence[Mapping[str, object]] = (),
    execution_mode: str = "STAGING",
    family: str = "",
    active: bool = True,
) -> dict[str, Any]:
    initialize_article1_runtime(db_path)
    _open_session(db_path, session_id)
    slot = _normalize_slot(reviewer_slot)
    name, role = _reviewer(reviewer_name, reviewer_role)
    mode = _normalize_mode(execution_mode)
    _formal_guard(
        db_path,
        session_id=session_id,
        execution_mode=mode,
        reviewer_slot=slot,
        reviewer_name=name,
    )
    _require_formal_included(db_path, session_id, document_id, mode)
    relation_key, source, target, normalized_direction, normalized_type = (
        normalize_relation(
            source_code=source_code,
            target_code=target_code,
            direction=direction,
            relation_type=relation_type,
        )
    )
    cleaned_evidence = [
        {"locator": _clean(item.get("locator")), "evidence": _clean(item.get("evidence"))}
        for item in evidence_instances
        if _clean(item.get("evidence"))
    ]
    if active and not cleaned_evidence:
        raise ValueError(
            "an explicit relation requires at least one traceable evidence passage"
        )
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_relation_submissions
                   WHERE session_id=? AND document_id=? AND reviewer_slot=?
                   AND relation_key=?""",
                (session_id, document_id, slot, relation_key),
            ).fetchone()[0]
        )
        row_id = f"article1_relation_{uuid4().hex}"
        con.execute(
            "INSERT INTO article1_relation_submissions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                ARTICLE1_ID,
                mode,
                slot,
                name,
                role,
                relation_key,
                source,
                target,
                normalized_direction,
                normalized_type,
                family.strip(),
                int(bool(active)),
                ABCD_VERSION,
                revision,
                _now(),
            ),
        )
        if active:
            for order, item in enumerate(cleaned_evidence, 1):
                con.execute(
                    "INSERT INTO article1_relation_evidence_instances VALUES(?,?,?,?,?,?)",
                    (
                        f"article1_relation_ev_{uuid4().hex}",
                        row_id,
                        item["locator"],
                        item["evidence"],
                        order,
                        _now(),
                    ),
                )
        row = dict(
            con.execute(
                "SELECT * FROM article1_relation_submissions WHERE id=?", (row_id,)
            ).fetchone()
        )
        evidence_rows = con.execute(
            """SELECT locator,evidence,evidence_order
               FROM article1_relation_evidence_instances
               WHERE relation_submission_id=? ORDER BY evidence_order""",
            (row_id,),
        ).fetchall()
    row["active"] = bool(row["active"])
    row["evidence_instances"] = [dict(item) for item in evidence_rows]
    return row


def complete_article1_relation_review(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    reviewer_slot: str,
    reviewer_name: str,
    reviewer_role: str,
    complete: bool = True,
) -> dict[str, Any]:
    initialize_article1_runtime(db_path)
    _open_session(db_path, session_id)
    slot = _normalize_slot(reviewer_slot)
    name, role = _reviewer(reviewer_name, reviewer_role)
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_relation_review_status
                   WHERE session_id=? AND document_id=? AND reviewer_slot=?""",
                (session_id, document_id, slot),
            ).fetchone()[0]
        )
        row_id = f"article1_relation_review_{uuid4().hex}"
        con.execute(
            "INSERT INTO article1_relation_review_status VALUES(?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                slot,
                name,
                role,
                int(bool(complete)),
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_relation_review_status WHERE id=?", (row_id,)
        ).fetchone()
    output = dict(row)
    output["complete"] = bool(output["complete"])
    return output


def _latest_relation_review_status(
    db_path: Path, *, session_id: str, document_id: str
) -> dict[str, bool]:
    initialize_article1_runtime(db_path)
    with _db(db_path) as con:
        rows = con.execute(
            """SELECT s.* FROM article1_relation_review_status s JOIN(
                 SELECT reviewer_slot,MAX(revision) revision
                 FROM article1_relation_review_status
                 WHERE session_id=? AND document_id=? GROUP BY reviewer_slot) x
               ON x.reviewer_slot=s.reviewer_slot AND x.revision=s.revision
               WHERE s.session_id=? AND s.document_id=?""",
            (session_id, document_id, session_id, document_id),
        ).fetchall()
    return {row["reviewer_slot"]: bool(row["complete"]) for row in rows}


def _latest_relations(
    db_path: Path,
    *,
    session_id: str,
    document_id: str | None = None,
    reviewer_slot: str | None = None,
) -> list[dict[str, Any]]:
    initialize_article1_runtime(db_path)
    clauses = ["r.session_id=?", "r.active=1"]
    params: list[object] = [session_id]
    if document_id:
        clauses.append("r.document_id=?")
        params.append(document_id)
    if reviewer_slot:
        clauses.append("r.reviewer_slot=?")
        params.append(_normalize_slot(reviewer_slot))
    with _db(db_path) as con:
        rows = con.execute(
            f"""SELECT r.* FROM article1_relation_submissions r JOIN(
                  SELECT session_id,document_id,reviewer_slot,relation_key,MAX(revision) revision
                  FROM article1_relation_submissions
                  GROUP BY session_id,document_id,reviewer_slot,relation_key) x
                ON x.session_id=r.session_id AND x.document_id=r.document_id
                AND x.reviewer_slot=r.reviewer_slot
                AND x.relation_key=r.relation_key AND x.revision=r.revision
                WHERE {' AND '.join(clauses)}""",
            params,
        ).fetchall()
        output = []
        for raw in rows:
            row = dict(raw)
            row["active"] = bool(row["active"])
            evidence = con.execute(
                """SELECT locator,evidence,evidence_order
                   FROM article1_relation_evidence_instances
                   WHERE relation_submission_id=? ORDER BY evidence_order""",
                (row["id"],),
            ).fetchall()
            row["evidence_instances"] = [dict(item) for item in evidence]
            output.append(row)
    return output


def _latest_relation_adjudications(
    db_path: Path, session_id: str, document_id: str
) -> dict[str, dict[str, Any]]:
    initialize_article1_runtime(db_path)
    with _db(db_path) as con:
        rows = con.execute(
            """SELECT a.* FROM article1_relation_adjudications a JOIN(
                 SELECT relation_key,MAX(revision) revision
                 FROM article1_relation_adjudications
                 WHERE session_id=? AND document_id=? GROUP BY relation_key) x
               ON x.relation_key=a.relation_key AND x.revision=a.revision
               WHERE a.session_id=? AND a.document_id=?""",
            (session_id, document_id, session_id, document_id),
        ).fetchall()
    output = {}
    for raw in rows:
        row = dict(raw)
        row["final"] = _loads(row["final_json"], {})
        output[row["relation_key"]] = row
    return output


def compare_article1_relations(
    db_path: Path, *, session_id: str, document_id: str
) -> list[dict[str, Any]]:
    latest = _latest_relations(
        db_path, session_id=session_id, document_id=document_id
    )
    by_slot: dict[str, dict[str, dict[str, Any]]] = {slot: {} for slot in SLOTS}
    for row in latest:
        by_slot[row["reviewer_slot"]][row["relation_key"]] = row
    adjudicated = _latest_relation_adjudications(db_path, session_id, document_id)
    keys = sorted(set(by_slot["REVIEWER_1"]) | set(by_slot["REVIEWER_2"]))
    output = []
    for key in keys:
        r1 = by_slot["REVIEWER_1"].get(key)
        r2 = by_slot["REVIEWER_2"].get(key)
        if r1 and r2:
            status = "AGREED_RELATION"
            final = {
                "relation_key": key,
                "source_code": r1["source_code"],
                "target_code": r1["target_code"],
                "direction": r1["direction"],
                "relation_type": r1["relation_type"],
                "family": r1.get("family", ""),
                "evidence_instances": (
                    (r1.get("evidence_instances") or [])
                    + (r2.get("evidence_instances") or [])
                ),
            }
            final_status = "AGREED"
        else:
            status = "REVIEWER_SET_DIVERGENCE"
            adj = adjudicated.get(key)
            if adj and adj["final_decision"] == "INCLUDE":
                final, final_status = adj.get("final"), "ADJUDICATED_INCLUDE"
            elif adj:
                final, final_status = None, "ADJUDICATED_EXCLUDE"
            else:
                final, final_status = None, "PENDING"
        output.append(
            {
                "relation_key": key,
                "reviewer_1": r1,
                "reviewer_2": r2,
                "status": status,
                "final": final,
                "final_status": final_status,
            }
        )
    return output


def adjudicate_article1_relation(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    relation_key: str,
    final_decision: str,
    adjudicator_name: str,
    adjudicator_role: str,
    notes: str = "",
) -> dict[str, Any]:
    initialize_article1_runtime(db_path)
    _open_session(db_path, session_id)
    name, role = _reviewer(adjudicator_name, adjudicator_role)
    assignment = article1_reviewer_assignment(db_path, session_id)
    if assignment and _clean(name).casefold() != _clean(
        assignment["adjudicator_name"]
    ).casefold():
        raise ValueError("adjudicator identity does not match the GF-07 assignment")
    decision = _clean(final_decision).upper()
    if decision not in RELATION_FINAL_DECISIONS:
        raise ValueError(f"final_decision must be one of {RELATION_FINAL_DECISIONS}")
    comparison = {
        row["relation_key"]: row
        for row in compare_article1_relations(
            db_path, session_id=session_id, document_id=document_id
        )
    }.get(relation_key)
    if not comparison or comparison["status"] != "REVIEWER_SET_DIVERGENCE":
        raise ValueError(
            "only reviewer-set relation divergences require adjudication"
        )
    source = comparison["reviewer_1"] or comparison["reviewer_2"] or {}
    final = (
        {
            "relation_key": relation_key,
            "source_code": source.get("source_code", ""),
            "target_code": source.get("target_code", ""),
            "direction": source.get("direction", ""),
            "relation_type": source.get("relation_type", ""),
            "family": source.get("family", ""),
            "evidence_instances": source.get("evidence_instances", []),
        }
        if decision == "INCLUDE"
        else {}
    )
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_relation_adjudications
                   WHERE session_id=? AND document_id=? AND relation_key=?""",
                (session_id, document_id, relation_key),
            ).fetchone()[0]
        )
        row_id = f"article1_relation_adj_{uuid4().hex}"
        con.execute(
            "INSERT INTO article1_relation_adjudications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                relation_key,
                _j(comparison["reviewer_1"]),
                _j(comparison["reviewer_2"]),
                decision,
                _j(final),
                name,
                role,
                notes.strip(),
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_relation_adjudications WHERE id=?", (row_id,)
        ).fetchone()
    return dict(row)


def final_article1_relations(
    db_path: Path, *, session_id: str, document_id: str
) -> list[dict[str, Any]]:
    review_status = _latest_relation_review_status(
        db_path, session_id=session_id, document_id=document_id
    )
    if not all(review_status.get(slot, False) for slot in SLOTS):
        raise ValueError(
            "relation extraction is not closed; both reviewers must explicitly complete relation review"
        )
    comparison = compare_article1_relations(
        db_path, session_id=session_id, document_id=document_id
    )
    if any(row["final_status"] == "PENDING" for row in comparison):
        raise ValueError(
            "relation extraction is not closed; unresolved reviewer-set divergences remain"
        )
    return [dict(row["final"]) for row in comparison if row["final"]]


def article1_relation_calibration_report(
    db_path: Path,
    *,
    session_id: str,
    document_ids: Sequence[str],
    conceptual_error_flags: Sequence[str] | None = None,
) -> dict[str, Any]:
    if not document_ids:
        raise ValueError("document_ids cannot be empty")
    r1: set[tuple[str, str]] = set()
    r2: set[tuple[str, str]] = set()
    completed_pairs = 0
    for document_id in document_ids:
        status = _latest_relation_review_status(
            db_path, session_id=session_id, document_id=document_id
        )
        if all(status.get(slot, False) for slot in SLOTS):
            completed_pairs += 1
        for row in _latest_relations(
            db_path, session_id=session_id, document_id=document_id
        ):
            item = (document_id, row["relation_key"])
            (r1 if row["reviewer_slot"] == "REVIEWER_1" else r2).add(item)
    intersection, union = r1 & r2, r1 | r2
    flags = [_clean(item) for item in (conceptual_error_flags or []) if _clean(item)]
    return {
        "documents_expected": len(document_ids),
        "documents_with_both_relation_reviews_complete": completed_pairs,
        "review_completeness": completed_pairs / len(document_ids),
        "reviewer_1_relations": len(r1),
        "reviewer_2_relations": len(r2),
        "intersection": len(intersection),
        "union": len(union),
        "jaccard_descriptive": len(intersection) / len(union) if union else None,
        "conceptual_error_flags": flags,
        "requires_rule_review": bool(flags),
        "interpretation": (
            "Descriptive relation-set agreement only. No Jaccard pass threshold; "
            "absent 34x34 pairs are not negatives."
        ),
    }


def save_article1_method_characterization(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    fields: Mapping[str, object],
    reviewer_name: str,
    reviewer_role: str,
    family: str = "",
) -> dict[str, Any]:
    initialize_article1_runtime(db_path)
    _open_session(db_path, session_id)
    name, role = _reviewer(reviewer_name, reviewer_role)
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_method_characterization
                   WHERE session_id=? AND document_id=?""",
                (session_id, document_id),
            ).fetchone()[0]
        )
        row_id = f"article1_method_{uuid4().hex}"
        con.execute(
            "INSERT INTO article1_method_characterization VALUES(?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                family.strip(),
                _j(dict(fields)),
                name,
                role,
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_method_characterization WHERE id=?", (row_id,)
        ).fetchone()
    return dict(row)


def _latest_method_characterization(
    db_path: Path, session_id: str
) -> list[dict[str, Any]]:
    initialize_article1_runtime(db_path)
    with _db(db_path) as con:
        rows = con.execute(
            """SELECT m.* FROM article1_method_characterization m JOIN(
                 SELECT document_id,MAX(revision) revision
                 FROM article1_method_characterization
                 WHERE session_id=? GROUP BY document_id) x
               ON x.document_id=m.document_id AND x.revision=m.revision
               WHERE m.session_id=?""",
            (session_id, session_id),
        ).fetchall()
    output = []
    for raw in rows:
        row = dict(raw)
        row["fields"] = _loads(row["fields_json"], {})
        output.append(row)
    return output


def _article1_included_documents(
    db_path: Path, session_id: str
) -> list[dict[str, Any]]:
    return list(_included(db_path, session_id, ARTICLE1_ID))


def article1_runtime_status(
    db_path: Path, *, session_id: str
) -> dict[str, Any]:
    documents = _article1_included_documents(db_path, session_id)
    per_document = []
    for source in documents:
        document_id = source["document_id"]
        abcd = article1_abcd_document_status(
            db_path, session_id=session_id, document_id=document_id
        )
        review_status = _latest_relation_review_status(
            db_path, session_id=session_id, document_id=document_id
        )
        relation_comparison = compare_article1_relations(
            db_path, session_id=session_id, document_id=document_id
        )
        relation_pending = sum(
            item["final_status"] == "PENDING" for item in relation_comparison
        )
        relation_reviews_complete = all(
            review_status.get(slot, False) for slot in SLOTS
        )
        per_document.append(
            {
                "document_id": document_id,
                "family": source.get("family", source.get("document_family", "")),
                "abcd_closed": bool(abcd["closed"]),
                "abcd_pending": len(abcd["pending_codes"]),
                "relation_reviews_complete": relation_reviews_complete,
                "relation_pending": relation_pending,
                "relations_closed": relation_reviews_complete
                and relation_pending == 0,
            }
        )
    ready = bool(documents) and all(
        row["abcd_closed"] and row["relations_closed"] for row in per_document
    )
    return {
        "session_id": session_id,
        "included_documents": len(documents),
        "documents": per_document,
        "synthesis_ready": ready,
        "codebook_version": ABCD_VERSION,
    }


def article1_synthesis(
    db_path: Path, *, session_id: str, strict: bool = True
) -> dict[str, Any]:
    documents = _article1_included_documents(db_path, session_id)
    status = article1_runtime_status(db_path, session_id=session_id)
    if strict and not status["synthesis_ready"]:
        raise ValueError(
            "Article 1 synthesis is blocked until every included document has closed ABCD and relation review"
        )
    component_family: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    depth_family: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    cooccurrence_family: dict[tuple[str, str, str], int] = defaultdict(int)
    relation_family: dict[tuple[str, str], int] = defaultdict(int)
    closed_documents = 0
    for source in documents:
        document_id = source["document_id"]
        family = _clean(
            source.get("family") or source.get("document_family") or "UNSPECIFIED"
        ) or "UNSPECIFIED"
        try:
            abcd = final_article1_abcd(
                db_path, session_id=session_id, document_id=document_id
            )
        except ValueError:
            if strict:
                raise
            continue
        closed_documents += 1
        yes_codes = []
        for row in abcd:
            key = (family, row["code"])
            component_family[key][row["presence"]] += 1
            if row["presence"] == "YES":
                depth_family[key][str(row["depth"])] += 1
                yes_codes.append(row["code"])
        yes_codes = sorted(yes_codes, key=ABCD_CODES.index)
        for index, source_code in enumerate(yes_codes):
            for target_code in yes_codes[index + 1 :]:
                cooccurrence_family[(family, source_code, target_code)] += 1
        try:
            relations = final_article1_relations(
                db_path, session_id=session_id, document_id=document_id
            )
        except ValueError:
            if strict:
                raise
            relations = []
        for relation in relations:
            relation_family[(family, relation["relation_key"])] += 1
    components = []
    for (family, code), counts in sorted(component_family.items()):
        depths = depth_family[(family, code)]
        components.append(
            {
                "family": family,
                "code": code,
                "label": ABCD_COMPONENTS[code].label,
                "documents_evaluated": sum(counts.values()),
                "yes": counts.get("YES", 0),
                "no": counts.get("NO", 0),
                "depth_1": depths.get("1", 0),
                "depth_2": depths.get("2", 0),
                "depth_3": depths.get("3", 0),
            }
        )
    cooccurrence = [
        {
            "family": family,
            "source_code": source,
            "target_code": target,
            "documents_with_cooccurrence": count,
        }
        for (family, source, target), count in sorted(cooccurrence_family.items())
    ]
    explicit_relations = []
    for (family, key), count in sorted(relation_family.items()):
        source, target, direction, relation_type = key.split("|", 3)
        explicit_relations.append(
            {
                "family": family,
                "relation_key": key,
                "source_code": source,
                "target_code": target,
                "direction": direction,
                "relation_type": relation_type,
                "documents_with_explicit_relation": count,
            }
        )
    return {
        "session_id": session_id,
        "codebook_version": ABCD_VERSION,
        "included_documents": len(documents),
        "closed_documents": closed_documents,
        "ready": bool(status["synthesis_ready"]),
        "components": components,
        "cooccurrence": cooccurrence,
        "explicit_relations": explicit_relations,
        "method_characterization": _latest_method_characterization(
            db_path, session_id
        ),
        "guardrails": {
            "global_abcd_score": False,
            "mean_depth": False,
            "document_ranking": False,
            "cooccurrence_is_relation": False,
            "greater_depth_means_better_evidence": False,
            "more_relations_means_better_document": False,
        },
    }


def create_article1_synthesis_snapshot(
    db_path: Path, *, session_id: str, strict: bool = True
) -> dict[str, Any]:
    initialize_article1_runtime(db_path)
    payload = article1_synthesis(db_path, session_id=session_id, strict=strict)
    serialized = _j(payload)
    digest = sha256(serialized.encode("utf-8")).hexdigest()
    snapshot_id = f"article1_synthesis_{uuid4().hex}"
    with _db(db_path) as con:
        con.execute(
            "INSERT INTO article1_synthesis_snapshots VALUES(?,?,?,?,?,?,?)",
            (
                snapshot_id,
                session_id,
                _now(),
                ABCD_VERSION,
                serialized,
                digest,
                int(bool(payload["ready"])),
            ),
        )
    return {
        "snapshot_id": snapshot_id,
        "payload_sha256": digest,
        "payload": payload,
    }


def assert_article1_prisma_eligible(
    *,
    execution_mode: str,
    freeze_authorized: bool,
    screening_calibration_released: bool,
    unresolved_title_abstract: int = 0,
    unresolved_full_text: int = 0,
) -> None:
    mode = _normalize_mode(execution_mode)
    if mode != "FORMAL":
        raise ValueError(
            "PILOT/STAGING/CALIBRATION contribute zero formal PRISMA counts"
        )
    if not freeze_authorized:
        raise ValueError("formal PRISMA is blocked until GF-10 freeze authorization")
    if not screening_calibration_released:
        raise ValueError(
            "formal PRISMA is blocked until screening calibration is released"
        )
    if int(unresolved_title_abstract) or int(unresolved_full_text):
        raise ValueError(
            "final PRISMA included counts are blocked by unresolved screening decisions"
        )


def article1_sheet_payload(
    db_path: Path, *, session_id: str, strict: bool = False
) -> dict[str, Any]:
    status = article1_runtime_status(db_path, session_id=session_id)
    comparisons = []
    relation_comparisons = []
    final_abcd = []
    final_relations = []
    for document in status["documents"]:
        document_id = document["document_id"]
        comparisons.extend(
            {"document_id": document_id, **row}
            for row in compare_article1_abcd(
                db_path, session_id=session_id, document_id=document_id
            )
        )
        relation_comparisons.extend(
            {"document_id": document_id, **row}
            for row in compare_article1_relations(
                db_path, session_id=session_id, document_id=document_id
            )
        )
        if document["abcd_closed"]:
            final_abcd.extend(
                {"document_id": document_id, **row}
                for row in final_article1_abcd(
                    db_path, session_id=session_id, document_id=document_id
                )
            )
        if document["relations_closed"]:
            final_relations.extend(
                {"document_id": document_id, **row}
                for row in final_article1_relations(
                    db_path, session_id=session_id, document_id=document_id
                )
            )
    synthesis = article1_synthesis(
        db_path, session_id=session_id, strict=strict
    )
    return {
        "sync_direction": "ENGINE_TO_SHEET",
        "runtime_is_authoritative": True,
        "tabs": {
            "08_CODEBOOK_ABCD": codebook_rows(),
            "10_EXTRACAO_ABCD": final_abcd,
            "10A_RELACOES_ABCD": final_relations,
            "11_DIVERGENCIAS": [
                row for row in comparisons if row["final_status"] == "PENDING"
            ]
            + [
                row
                for row in relation_comparisons
                if row["final_status"] == "PENDING"
            ],
            "13_SINTESE": synthesis,
        },
        "audit": {
            "codebook_version": ABCD_VERSION,
            "session_id": session_id,
            "status": status,
            "raw_abcd_submissions": len(
                _latest_abcd(db_path, session_id=session_id)
            ),
            "raw_relation_submissions": len(
                _latest_relations(db_path, session_id=session_id)
            ),
            "generated_at": _now(),
        },
    }


def article1_manifest(
    db_path: Path,
    *,
    session_id: str,
    config_digest: str = "",
    git_sha: str = "",
) -> dict[str, Any]:
    status = article1_runtime_status(db_path, session_id=session_id)
    assignment = article1_reviewer_assignment(db_path, session_id)
    payload = {
        "article_id": ARTICLE1_ID,
        "session_id": session_id,
        "generated_at": _now(),
        "codebook_version": ABCD_VERSION,
        "git_sha": _clean(git_sha) or _clean(os.environ.get("GITHUB_SHA")),
        "config_digest": _clean(config_digest),
        "gf07": {
            "resolved": bool(assignment and assignment.get("gf07_resolved")),
            "reviewer_1": assignment.get("reviewer_1_name", "")
            if assignment
            else "",
            "reviewer_2": assignment.get("reviewer_2_name", "")
            if assignment
            else "",
            "adjudicator": assignment.get("adjudicator_name", "")
            if assignment
            else "",
        },
        "runtime_status": status,
        "scientific_claims_not_implied": [
            "PRESS approved",
            "GF-01/02/03/10 closed",
            "formal search executed",
            "formal PRISMA complete",
            "scientific results valid",
            "human decisions automated",
        ],
    }
    payload["manifest_digest"] = sha256(_j(payload).encode("utf-8")).hexdigest()
    return payload


def article1_export_bundle(
    db_path: Path, *, session_id: str
) -> dict[str, Any]:
    status = article1_runtime_status(db_path, session_id=session_id)
    abcd_comparison = []
    relation_comparison = []
    final_abcd = []
    final_relations = []
    for document in status["documents"]:
        document_id = document["document_id"]
        abcd_comparison.extend(
            {"document_id": document_id, **row}
            for row in compare_article1_abcd(
                db_path, session_id=session_id, document_id=document_id
            )
        )
        relation_comparison.extend(
            {"document_id": document_id, **row}
            for row in compare_article1_relations(
                db_path, session_id=session_id, document_id=document_id
            )
        )
        if document["abcd_closed"]:
            final_abcd.extend(
                {"document_id": document_id, **row}
                for row in final_article1_abcd(
                    db_path, session_id=session_id, document_id=document_id
                )
            )
        if document["relations_closed"]:
            final_relations.extend(
                {"document_id": document_id, **row}
                for row in final_article1_relations(
                    db_path, session_id=session_id, document_id=document_id
                )
            )
    return {
        "status": status,
        "codebook": codebook_rows(),
        "abcd_submissions": _latest_abcd(db_path, session_id=session_id),
        "abcd_comparison": abcd_comparison,
        "final_abcd": final_abcd,
        "relation_submissions": _latest_relations(db_path, session_id=session_id),
        "relation_comparison": relation_comparison,
        "final_relations": final_relations,
        "method_characterization": _latest_method_characterization(
            db_path, session_id
        ),
        "synthesis": article1_synthesis(
            db_path, session_id=session_id, strict=False
        ),
        "sheet_payload": article1_sheet_payload(
            db_path, session_id=session_id, strict=False
        ),
        "manifest": article1_manifest(db_path, session_id=session_id),
    }
