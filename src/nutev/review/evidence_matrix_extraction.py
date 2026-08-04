"""Configurable double data extraction and field adjudication."""
from __future__ import annotations

from datetime import date
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.review.article_screening_ledger import ARTICLE_IDS, list_article_catalog
from nutev.review.full_text_assessment import full_text_assessment_queue
from nutev.review.evidence_matrix_core import (
    BIBLIO, COMMON, FIELD_TYPES, SLOTS, _db, _j, _loads, _now, _open_session,
    _reviewer, initialize,
)


def _included(db_path: Path, session_id: str, article_id: str | None = None) -> list[dict[str, Any]]:
    articles = [article_id] if article_id else list(ARTICLE_IDS)
    out: list[dict[str, Any]] = []
    for article in articles:
        for row in full_text_assessment_queue(db_path, session_id=session_id, article_id=article, status_filter="INCLUDE"):
            if row.get("artifact_integrity") in {"MISSING", "MISMATCH"}:
                raise ValueError(f"full-text artifact integrity is {str(row['artifact_integrity']).lower()}")
            out.append({**row, "article_id": article})
    return out


def included_documents(db_path: Path, session_id: str, article_id: str | None = None) -> list[dict[str, Any]]:
    initialize(db_path)
    labels = {row["article_id"]: row["label"] for row in list_article_catalog(db_path, active_only=False)}
    return [{**row, "article_label": labels.get(row["article_id"], row["article_id"])} for row in _included(db_path, session_id, article_id)]


def _require_included(db_path: Path, session_id: str, document_id: str, article_id: str) -> dict[str, Any]:
    for row in _included(db_path, session_id, article_id):
        if row["document_id"] == document_id:
            return row
    raise ValueError("document is not finally included for this article")


def list_schema(db_path: Path, article_id: str) -> list[dict[str, Any]]:
    if article_id not in ARTICLE_IDS:
        raise ValueError(f"article_id must be one of {ARTICLE_IDS}")
    initialize(db_path)
    with _db(db_path) as con:
        rows = con.execute(
            """SELECT f.* FROM extraction_schema_fields f JOIN(
                 SELECT scope,article_id,field_key,MAX(revision) revision
                 FROM extraction_schema_fields WHERE (scope=? AND article_id='') OR (scope='ARTICLE' AND article_id=?)
                 GROUP BY scope,article_id,field_key) x
               ON x.scope=f.scope AND x.article_id=f.article_id AND x.field_key=f.field_key AND x.revision=f.revision
               WHERE f.active=1""", (COMMON, article_id),
        ).fetchall()
    by_key: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        row["options"] = _loads(row.pop("options_json"), [])
        row["validation"] = _loads(row.pop("validation_json"), {})
        row["required"] = bool(row["required"])
        row["active"] = bool(row["active"])
        if row["field_key"] not in by_key or row["scope"] == "ARTICLE":
            by_key[row["field_key"]] = row
    return sorted(by_key.values(), key=lambda row: (row["display_order"], row["field_key"]))


def save_schema_field(db_path: Path, *, field_key: str, label: str, field_type: str, created_by: str, article_id: str | None = None, description: str = "", options: list[str] | None = None, required: bool = False, validation: dict[str, Any] | None = None, display_order: int = 0, active: bool = True) -> dict[str, Any]:
    key = field_key.strip().lower()
    kind = field_type.strip().upper()
    if not key or not key.replace("_", "").isalnum():
        raise ValueError("field_key must use letters, numbers, and underscores")
    if not label.strip() or not created_by.strip():
        raise ValueError("label and created_by are required")
    if kind not in FIELD_TYPES:
        raise ValueError(f"field_type must be one of {FIELD_TYPES}")
    article = (article_id or "").strip().lower()
    if article and article not in ARTICLE_IDS:
        raise ValueError(f"article_id must be one of {ARTICLE_IDS}")
    clean_options = [str(item).strip() for item in (options or []) if str(item).strip()]
    if kind in {"SINGLE_SELECT", "MULTI_SELECT"} and not clean_options:
        raise ValueError("select fields require options")
    initialize(db_path)
    scope = "ARTICLE" if article else COMMON
    with _db(db_path) as con:
        revision = con.execute("SELECT COALESCE(MAX(revision),0)+1 FROM extraction_schema_fields WHERE scope=? AND article_id=? AND field_key=?", (scope, article, key)).fetchone()[0]
        row_id = f"schema_{uuid4().hex}"
        con.execute(
            "INSERT INTO extraction_schema_fields VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (row_id, scope, article, key, label.strip(), description.strip(), kind, _j(clean_options), int(required), _j(validation or {}), int(display_order), int(active), revision, created_by.strip(), _now()),
        )
        return dict(con.execute("SELECT * FROM extraction_schema_fields WHERE id=?", (row_id,)).fetchone())


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _value(field: dict[str, Any], raw: Any) -> Any:
    if _empty(raw):
        if field["required"]:
            raise ValueError(f"required field is missing: {field['field_key']}")
        return None
    kind = field["field_type"]
    if kind in {"TEXT", "LONG_TEXT"}:
        value: Any = str(raw).strip()
    elif kind == "INTEGER":
        value = int(raw)
    elif kind == "FLOAT":
        value = float(raw)
    elif kind == "BOOLEAN":
        if isinstance(raw, bool): value = raw
        elif str(raw).lower() in {"true", "1", "sim", "yes"}: value = True
        elif str(raw).lower() in {"false", "0", "não", "nao", "no"}: value = False
        else: raise ValueError(f"{field['field_key']} must be boolean")
    elif kind == "DATE":
        value = str(raw).strip(); date.fromisoformat(value)
    elif kind == "SINGLE_SELECT":
        value = str(raw).strip()
        if value not in field["options"]: raise ValueError(f"invalid option for {field['field_key']}")
    elif kind == "MULTI_SELECT":
        if not isinstance(raw, (list, tuple, set)): raise ValueError(f"{field['field_key']} must be a list")
        value = [str(item).strip() for item in raw if str(item).strip()]
        if set(value) - set(field["options"]): raise ValueError(f"invalid options for {field['field_key']}")
    elif kind == "JSON":
        value = json.loads(raw) if isinstance(raw, str) else raw
    else:
        raise ValueError(f"unsupported field type: {kind}")
    rules = field["validation"]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "min" in rules and value < float(rules["min"]): raise ValueError(f"{field['field_key']} is below minimum")
        if "max" in rules and value > float(rules["max"]): raise ValueError(f"{field['field_key']} is above maximum")
    if isinstance(value, str):
        if "min_length" in rules and len(value) < int(rules["min_length"]): raise ValueError(f"{field['field_key']} is too short")
        if "max_length" in rules and len(value) > int(rules["max_length"]): raise ValueError(f"{field['field_key']} is too long")
        if rules.get("pattern") and not re.search(str(rules["pattern"]), value): raise ValueError(f"{field['field_key']} has invalid format")
    return value


def submit_extraction(db_path: Path, *, session_id: str, document_id: str, article_id: str, reviewer_slot: str, reviewer_name: str, reviewer_role: str, values: dict[str, Any]) -> dict[str, Any]:
    source = _require_included(db_path, session_id, document_id, article_id)
    name, role = _reviewer(reviewer_name, reviewer_role)
    slot = reviewer_slot.upper()
    if slot not in SLOTS: raise ValueError(f"reviewer_slot must be one of {SLOTS}")
    schema = list_schema(db_path, article_id)
    unknown = set(values) - {row["field_key"] for row in schema}
    if unknown: raise ValueError(f"unknown extraction fields: {sorted(unknown)}")
    normalized = {row["field_key"]: _value(row, values.get(row["field_key"])) for row in schema}
    complete = all(not _empty(normalized[row["field_key"]]) for row in schema if row["required"])
    _open_session(db_path, session_id)
    with _db(db_path) as con:
        revision = con.execute("SELECT COALESCE(MAX(revision),0)+1 FROM extraction_submissions WHERE session_id=? AND document_id=? AND article_id=? AND reviewer_slot=?", (session_id, document_id, article_id, slot)).fetchone()[0]
        row_id = f"extraction_{uuid4().hex}"
        con.execute("INSERT INTO extraction_submissions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (row_id, session_id, document_id, article_id, slot, name, role, _j(schema), _j(normalized), source.get("retrieval_artifact_sha256", ""), "COMPLETE" if complete else "INCOMPLETE", revision, _now()))
        return dict(con.execute("SELECT * FROM extraction_submissions WHERE id=?", (row_id,)).fetchone())


def _latest_extractions(db_path: Path, session_id: str, article_id: str | None = None, document_id: str | None = None) -> list[dict[str, Any]]:
    initialize(db_path)
    clauses, params = ["e.session_id=?"], [session_id]
    if article_id: clauses.append("e.article_id=?"); params.append(article_id)
    if document_id: clauses.append("e.document_id=?"); params.append(document_id)
    with _db(db_path) as con:
        rows = con.execute(f"""SELECT e.* FROM extraction_submissions e JOIN(
          SELECT session_id,document_id,article_id,reviewer_slot,MAX(revision) revision FROM extraction_submissions GROUP BY session_id,document_id,article_id,reviewer_slot) x
          ON x.session_id=e.session_id AND x.document_id=e.document_id AND x.article_id=e.article_id AND x.reviewer_slot=e.reviewer_slot AND x.revision=e.revision
          WHERE {' AND '.join(clauses)}""", params).fetchall()
    out=[]
    for raw in rows:
        row=dict(raw); row["values"]=_loads(row.pop("values_json"),{}); row["schema"]=_loads(row.pop("schema_json"),[]); out.append(row)
    return out


def _latest_adjudications(db_path: Path, session_id: str, article_id: str, document_id: str) -> dict[str, dict[str, Any]]:
    initialize(db_path)
    with _db(db_path) as con:
        rows=con.execute("""SELECT a.* FROM extraction_adjudications a JOIN(
          SELECT field_key,MAX(revision) revision FROM extraction_adjudications WHERE session_id=? AND article_id=? AND document_id=? GROUP BY field_key) x
          ON x.field_key=a.field_key AND x.revision=a.revision WHERE a.session_id=? AND a.article_id=? AND a.document_id=?""", (session_id,article_id,document_id,session_id,article_id,document_id)).fetchall()
    out={}
    for raw in rows:
        row=dict(raw); row["final"]=_loads(row["final_json"],None); out[row["field_key"]]=row
    return out


def compare_extractions(db_path: Path, *, session_id: str, document_id: str, article_id: str) -> list[dict[str, Any]]:
    slots={row["reviewer_slot"]:row for row in _latest_extractions(db_path,session_id,article_id,document_id)}
    one=slots.get("REVIEWER_1",{}).get("values",{}); two=slots.get("REVIEWER_2",{}).get("values",{})
    adjudicated=_latest_adjudications(db_path,session_id,article_id,document_id)
    out=[]
    for field in list_schema(db_path,article_id):
        key=field["field_key"]; v1=one.get(key); v2=two.get(key)
        if "REVIEWER_1" not in slots and "REVIEWER_2" not in slots: status="MISSING_BOTH"
        elif "REVIEWER_1" not in slots: status="MISSING_REVIEWER_1"
        elif "REVIEWER_2" not in slots: status="MISSING_REVIEWER_2"
        elif _j(v1)==_j(v2): status="AGREED"
        else: status="DIVERGENT"
        final=v1 if status=="AGREED" else adjudicated.get(key,{}).get("final")
        out.append({"field_key":key,"label":field["label"],"required":field["required"],"reviewer_1":v1,"reviewer_2":v2,"status":status,"final":final,"final_status":"AGREED" if status=="AGREED" else "ADJUDICATED" if key in adjudicated else "PENDING"})
    return out


def adjudicate_extraction(db_path: Path, *, session_id: str, document_id: str, article_id: str, field_key: str, final_value: Any, adjudicator_name: str, adjudicator_role: str, notes: str="") -> dict[str, Any]:
    name,role=_reviewer(adjudicator_name,adjudicator_role); _open_session(db_path,session_id)
    comparison={row["field_key"]:row for row in compare_extractions(db_path,session_id=session_id,document_id=document_id,article_id=article_id)}.get(field_key)
    if not comparison or comparison["status"]!="DIVERGENT": raise ValueError("only divergent fields require adjudication")
    field=next(row for row in list_schema(db_path,article_id) if row["field_key"]==field_key); final=_value(field,final_value)
    with _db(db_path) as con:
        revision=con.execute("SELECT COALESCE(MAX(revision),0)+1 FROM extraction_adjudications WHERE session_id=? AND document_id=? AND article_id=? AND field_key=?",(session_id,document_id,article_id,field_key)).fetchone()[0]
        row_id=f"extract_adjudication_{uuid4().hex}"
        con.execute("INSERT INTO extraction_adjudications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(row_id,session_id,document_id,article_id,field_key,_j(comparison["reviewer_1"]),_j(comparison["reviewer_2"]),_j(final),name,role,notes.strip(),revision,_now()))
        return dict(con.execute("SELECT * FROM extraction_adjudications WHERE id=?",(row_id,)).fetchone())


def final_extraction(db_path: Path, session_id: str, document_id: str, article_id: str) -> dict[str, Any]:
    source=_require_included(db_path,session_id,document_id,article_id); comparison=compare_extractions(db_path,session_id=session_id,document_id=document_id,article_id=article_id)
    out={key:source.get(key,"") for key in BIBLIO}; pending=[row["field_key"] for row in comparison if row["final_status"]=="PENDING"]
    out.update({"session_id":session_id,"article_id":article_id,"extraction_complete":not pending,"fields_pending":"|".join(pending)})
    out.update({f"extracted__{row['field_key']}":row["final"] for row in comparison}); return out
