"""Configurable methodological appraisal with double review and adjudication."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.review.evidence_matrix_core import (
    BIBLIO, SLOTS, _db, _j, _loads, _now, _open_session, _reviewer, initialize,
)
from nutev.review.evidence_matrix_extraction import _require_included


def _instrument(db_path: Path, instrument_id: str) -> dict[str, Any] | None:
    initialize(db_path)
    with _db(db_path) as con:
        raw = con.execute(
            "SELECT * FROM quality_instrument_versions WHERE id=?",
            (instrument_id,),
        ).fetchone()
        if not raw:
            return None
        domains = con.execute(
            "SELECT * FROM quality_instrument_domains WHERE instrument_id=? "
            "ORDER BY display_order",
            (instrument_id,),
        ).fetchall()
    row = dict(raw)
    row["document_types"] = _loads(row.pop("document_types_json"), [])
    row["overall_values"] = _loads(row.pop("overall_json"), [])
    row["active"] = bool(row["active"])
    row["domains"] = []
    for item in domains:
        domain = dict(item)
        domain["judgments"] = _loads(domain.pop("judgments_json"), [])
        domain["required"] = bool(domain["required"])
        row["domains"].append(domain)
    return row


def list_instruments(
    db_path: Path,
    document_type: str = "",
) -> list[dict[str, Any]]:
    initialize(db_path)
    with _db(db_path) as con:
        rows = con.execute(
            """
            SELECT q.id
            FROM quality_instrument_versions q
            JOIN (
                SELECT instrument_key, MAX(revision) revision
                FROM quality_instrument_versions
                GROUP BY instrument_key
            ) x
              ON x.instrument_key=q.instrument_key
             AND x.revision=q.revision
            WHERE q.active=1
            """
        ).fetchall()
    needle = document_type.casefold()
    output: list[dict[str, Any]] = []
    for raw in rows:
        item = _instrument(db_path, raw["id"])
        if item is None:
            continue
        item["suggestion_score"] = sum(
            term.casefold() in needle or needle in term.casefold()
            for term in item["document_types"]
            if needle
        )
        output.append(item)
    return sorted(output, key=lambda row: (-row["suggestion_score"], row["name"]))


def save_instrument(
    db_path: Path,
    *,
    instrument_key: str,
    name: str,
    version_label: str,
    description: str,
    document_types: list[str],
    overall_values: list[str],
    domains: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    key = instrument_key.strip().upper()
    if (
        not key
        or not key.replace("_", "").isalnum()
        or not name.strip()
        or not version_label.strip()
        or not created_by.strip()
    ):
        raise ValueError("instrument key, name, version, and created_by are required")
    if not overall_values or not domains:
        raise ValueError("overall values and domains are required")
    keys = [str(row.get("domain_key", "")).strip().lower() for row in domains]
    if (
        any(not item or not item.replace("_", "").isalnum() for item in keys)
        or len(keys) != len(set(keys))
    ):
        raise ValueError(
            "domain keys must be unique and use letters, numbers, and underscores"
        )
    initialize(db_path)
    with _db(db_path) as con:
        revision = con.execute(
            "SELECT COALESCE(MAX(revision),0)+1 "
            "FROM quality_instrument_versions WHERE instrument_key=?",
            (key,),
        ).fetchone()[0]
        instrument_id = f"instrument_{uuid4().hex}"
        con.execute(
            "INSERT INTO quality_instrument_versions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                instrument_id,
                key,
                name.strip(),
                version_label.strip(),
                description.strip(),
                _j(document_types),
                _j([item.upper() for item in overall_values]),
                1,
                revision,
                created_by.strip(),
                _now(),
            ),
        )
        for order, row in enumerate(domains, 1):
            judgments = [
                str(item).strip().upper()
                for item in row.get("judgments", [])
                if str(item).strip()
            ]
            if not judgments:
                raise ValueError(f"domain {keys[order - 1]} requires judgments")
            con.execute(
                "INSERT INTO quality_instrument_domains VALUES(?,?,?,?,?,?,?,?)",
                (
                    f"domain_{uuid4().hex}",
                    instrument_id,
                    keys[order - 1],
                    str(row.get("label") or keys[order - 1]),
                    str(row.get("description") or ""),
                    _j(judgments),
                    int(row.get("required", True)),
                    int(row.get("display_order", order)),
                ),
            )
        return dict(
            con.execute(
                "SELECT * FROM quality_instrument_versions WHERE id=?",
                (instrument_id,),
            ).fetchone()
        )


def _latest_assignment(
    db_path: Path,
    session_id: str,
    document_id: str,
    article_id: str,
) -> dict[str, Any] | None:
    initialize(db_path)
    with _db(db_path) as con:
        row = con.execute(
            "SELECT * FROM quality_instrument_assignments "
            "WHERE session_id=? AND document_id=? AND article_id=? "
            "ORDER BY revision DESC LIMIT 1",
            (session_id, document_id, article_id),
        ).fetchone()
    return dict(row) if row else None


def assign_instrument(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
    instrument_id: str,
    selection_basis: str,
    rationale: str,
    reviewer_name: str,
    reviewer_role: str,
) -> dict[str, Any]:
    _require_included(db_path, session_id, document_id, article_id)
    name, role = _reviewer(reviewer_name, reviewer_role)
    _open_session(db_path, session_id)
    if selection_basis not in {"HUMAN", "RULE_SUGGESTION"} or not rationale.strip():
        raise ValueError("valid selection basis and rationale are required")
    if not _instrument(db_path, instrument_id):
        raise ValueError("unknown instrument")
    with _db(db_path) as con:
        revision = con.execute(
            "SELECT COALESCE(MAX(revision),0)+1 "
            "FROM quality_instrument_assignments "
            "WHERE session_id=? AND document_id=? AND article_id=?",
            (session_id, document_id, article_id),
        ).fetchone()[0]
        row_id = f"assignment_{uuid4().hex}"
        con.execute(
            "INSERT INTO quality_instrument_assignments "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                article_id,
                instrument_id,
                selection_basis,
                rationale.strip(),
                name,
                role,
                revision,
                _now(),
            ),
        )
        return dict(
            con.execute(
                "SELECT * FROM quality_instrument_assignments WHERE id=?",
                (row_id,),
            ).fetchone()
        )


def _latest_assessments(
    db_path: Path,
    session_id: str,
    document_id: str,
    article_id: str,
    instrument_id: str,
) -> dict[str, dict[str, Any]]:
    initialize(db_path)
    with _db(db_path) as con:
        rows = con.execute(
            """
            SELECT q.*
            FROM quality_assessments q
            JOIN (
                SELECT reviewer_slot, MAX(revision) revision
                FROM quality_assessments
                WHERE session_id=? AND document_id=?
                  AND article_id=? AND instrument_id=?
                GROUP BY reviewer_slot
            ) x
              ON x.reviewer_slot=q.reviewer_slot
             AND x.revision=q.revision
            WHERE q.session_id=? AND q.document_id=?
              AND q.article_id=? AND q.instrument_id=?
            """,
            (
                session_id,
                document_id,
                article_id,
                instrument_id,
                session_id,
                document_id,
                article_id,
                instrument_id,
            ),
        ).fetchall()
    output: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        row["domains"] = _loads(row.pop("domains_json"), {})
        output[row["reviewer_slot"]] = row
    return output


def submit_quality(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
    reviewer_slot: str,
    domains: dict[str, dict[str, str]],
    overall: str,
    rationale: str,
    reviewer_name: str,
    reviewer_role: str,
) -> dict[str, Any]:
    source = _require_included(db_path, session_id, document_id, article_id)
    assignment = _latest_assignment(db_path, session_id, document_id, article_id)
    if not assignment:
        raise ValueError("select a quality instrument first")
    tool = _instrument(db_path, assignment["instrument_id"])
    if tool is None:
        raise ValueError("assigned instrument is missing")
    name, role = _reviewer(reviewer_name, reviewer_role)
    slot = reviewer_slot.upper()
    if slot not in SLOTS or not rationale.strip():
        raise ValueError("valid reviewer slot and rationale are required")
    if overall.upper() not in tool["overall_values"]:
        raise ValueError("invalid overall judgment")
    normalized: dict[str, dict[str, str]] = {}
    for definition in tool["domains"]:
        key = definition["domain_key"]
        supplied = domains.get(key)
        if not supplied and definition["required"]:
            raise ValueError(f"missing quality domain: {key}")
        if not supplied:
            continue
        judgment = str(supplied.get("judgment", "")).upper()
        justification = str(supplied.get("justification", "")).strip()
        if judgment not in definition["judgments"] or not justification:
            raise ValueError(f"invalid judgment or missing justification for {key}")
        normalized[key] = {
            "judgment": judgment,
            "justification": justification,
        }
    _open_session(db_path, session_id)
    with _db(db_path) as con:
        revision = con.execute(
            "SELECT COALESCE(MAX(revision),0)+1 FROM quality_assessments "
            "WHERE session_id=? AND document_id=? AND article_id=? "
            "AND reviewer_slot=?",
            (session_id, document_id, article_id, slot),
        ).fetchone()[0]
        row_id = f"quality_{uuid4().hex}"
        con.execute(
            "INSERT INTO quality_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                article_id,
                tool["id"],
                slot,
                _j(normalized),
                overall.upper(),
                rationale.strip(),
                source.get("retrieval_artifact_sha256", ""),
                name,
                role,
                revision,
                _now(),
            ),
        )
        return dict(
            con.execute(
                "SELECT * FROM quality_assessments WHERE id=?",
                (row_id,),
            ).fetchone()
        )


def _latest_quality_adjudication(
    db_path: Path,
    session_id: str,
    document_id: str,
    article_id: str,
    instrument_id: str,
) -> dict[str, Any] | None:
    initialize(db_path)
    with _db(db_path) as con:
        raw = con.execute(
            "SELECT * FROM quality_adjudications "
            "WHERE session_id=? AND document_id=? AND article_id=? "
            "AND instrument_id=? ORDER BY revision DESC LIMIT 1",
            (session_id, document_id, article_id, instrument_id),
        ).fetchone()
    if not raw:
        return None
    row = dict(raw)
    row["domains"] = _loads(row.pop("domains_json"), {})
    return row


def compare_quality(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
) -> dict[str, Any]:
    assignment = _latest_assignment(db_path, session_id, document_id, article_id)
    if not assignment:
        raise ValueError("select a quality instrument first")
    tool = _instrument(db_path, assignment["instrument_id"])
    if tool is None:
        raise ValueError("assigned instrument is missing")
    slots = _latest_assessments(
        db_path,
        session_id,
        document_id,
        article_id,
        tool["id"],
    )
    one = slots.get("REVIEWER_1")
    two = slots.get("REVIEWER_2")
    adjudication = _latest_quality_adjudication(
        db_path,
        session_id,
        document_id,
        article_id,
        tool["id"],
    )
    domain_rows: list[dict[str, Any]] = []
    for definition in tool["domains"]:
        key = definition["domain_key"]
        value_one = (one or {}).get("domains", {}).get(key)
        value_two = (two or {}).get("domains", {}).get(key)
        if not one and not two:
            status = "MISSING_BOTH"
        elif not one:
            status = "MISSING_REVIEWER_1"
        elif not two:
            status = "MISSING_REVIEWER_2"
        elif _j(value_one) == _j(value_two):
            status = "AGREED"
        else:
            status = "DIVERGENT"
        final = (
            value_one
            if status == "AGREED"
            else (adjudication or {}).get("domains", {}).get(key)
        )
        domain_rows.append(
            {
                "domain_key": key,
                "label": definition["label"],
                "reviewer_1": value_one,
                "reviewer_2": value_two,
                "status": status,
                "final": final,
            }
        )
    overall_one = (one or {}).get("overall")
    overall_two = (two or {}).get("overall")
    if not one and not two:
        overall_status = "MISSING_BOTH"
    elif not one:
        overall_status = "MISSING_REVIEWER_1"
    elif not two:
        overall_status = "MISSING_REVIEWER_2"
    elif overall_one == overall_two:
        overall_status = "AGREED"
    else:
        overall_status = "DIVERGENT"
    final_overall = (
        overall_one
        if overall_status == "AGREED"
        else (adjudication or {}).get("overall")
    )
    return {
        "instrument": tool,
        "reviewer_1": one,
        "reviewer_2": two,
        "domains": domain_rows,
        "overall_status": overall_status,
        "reviewer_1_overall": overall_one,
        "reviewer_2_overall": overall_two,
        "final_overall": final_overall,
        "adjudication": adjudication,
        "complete": (
            all(row["final"] is not None for row in domain_rows)
            and final_overall is not None
        ),
    }


def adjudicate_quality(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
    domains: dict[str, dict[str, str]],
    overall: str,
    adjudicator_name: str,
    adjudicator_role: str,
    notes: str = "",
) -> dict[str, Any]:
    comparison = compare_quality(
        db_path,
        session_id=session_id,
        document_id=document_id,
        article_id=article_id,
    )
    name, role = _reviewer(adjudicator_name, adjudicator_role)
    _open_session(db_path, session_id)
    if not comparison["reviewer_1"] or not comparison["reviewer_2"]:
        raise ValueError("quality adjudication requires both reviewers")
    tool = comparison["instrument"]
    expected = {row["domain_key"]: row for row in tool["domains"]}
    if set(domains) != set(expected):
        raise ValueError("final domains must contain every instrument domain")
    normalized: dict[str, dict[str, str]] = {}
    for key, definition in expected.items():
        judgment = str(domains[key].get("judgment", "")).upper()
        justification = str(domains[key].get("justification", "")).strip()
        if judgment not in definition["judgments"] or not justification:
            raise ValueError(f"invalid final judgment or justification for {key}")
        normalized[key] = {
            "judgment": judgment,
            "justification": justification,
        }
    if overall.upper() not in tool["overall_values"]:
        raise ValueError("invalid final overall judgment")
    with _db(db_path) as con:
        revision = con.execute(
            "SELECT COALESCE(MAX(revision),0)+1 FROM quality_adjudications "
            "WHERE session_id=? AND document_id=? AND article_id=?",
            (session_id, document_id, article_id),
        ).fetchone()[0]
        row_id = f"quality_adjudication_{uuid4().hex}"
        con.execute(
            "INSERT INTO quality_adjudications VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row_id,
                session_id,
                document_id,
                article_id,
                tool["id"],
                _j(normalized),
                overall.upper(),
                name,
                role,
                notes.strip(),
                revision,
                _now(),
            ),
        )
        return dict(
            con.execute(
                "SELECT * FROM quality_adjudications WHERE id=?",
                (row_id,),
            ).fetchone()
        )


def final_quality(
    db_path: Path,
    session_id: str,
    document_id: str,
    article_id: str,
) -> dict[str, Any]:
    source = _require_included(db_path, session_id, document_id, article_id)
    try:
        comparison = compare_quality(
            db_path,
            session_id=session_id,
            document_id=document_id,
            article_id=article_id,
        )
    except ValueError:
        comparison = None
    output = {key: source.get(key, "") for key in BIBLIO}
    output.update(
        {
            "session_id": session_id,
            "article_id": article_id,
            "quality_complete": bool(comparison and comparison["complete"]),
            "quality_instrument": (
                comparison["instrument"]["name"] if comparison else ""
            ),
            "quality_instrument_version": (
                comparison["instrument"]["version_label"] if comparison else ""
            ),
            "quality_overall": comparison["final_overall"] if comparison else None,
        }
    )
    if comparison:
        for row in comparison["domains"]:
            value = row["final"] or {}
            output[f"quality__{row['domain_key']}__judgment"] = value.get(
                "judgment"
            )
            output[f"quality__{row['domain_key']}__justification"] = value.get(
                "justification"
            )
    return output
