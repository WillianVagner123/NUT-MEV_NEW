from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any
from uuid import uuid4

from validation_readiness import (
    MANIFEST_NAME,
    REPO_ROOT,
    _packet_dir,
    get_validation_readiness,
)

DEFAULT_DB_RELATIVE = Path("project_output_reference") / "16_validation_server" / "validation.sqlite3"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _db_path(repo_root: Path, db_path: Path | None = None) -> Path:
    return (db_path or (repo_root / DEFAULT_DB_RELATIVE)).resolve()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS validation_rounds (
            id TEXT PRIMARY KEY,
            source_fingerprint TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS validation_reviewers (
            round_id TEXT NOT NULL,
            assessor_id TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            submitted_at TEXT,
            PRIMARY KEY (round_id, assessor_id),
            FOREIGN KEY (round_id) REFERENCES validation_rounds(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS validation_assignments (
            round_id TEXT NOT NULL,
            assessor_id TEXT NOT NULL,
            pool_item_id TEXT NOT NULL,
            assessor_order INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            question_text TEXT NOT NULL,
            eligibility_context TEXT NOT NULL,
            reference_id TEXT NOT NULL,
            title TEXT NOT NULL,
            abstract TEXT NOT NULL,
            journal TEXT NOT NULL,
            year TEXT NOT NULL,
            doi TEXT NOT NULL,
            pmid TEXT NOT NULL,
            pmcid TEXT NOT NULL,
            url TEXT NOT NULL,
            relevance_grade INTEGER,
            reason TEXT,
            decision_timestamp TEXT,
            blind_to_nutev INTEGER NOT NULL DEFAULT 1,
            review_later INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            PRIMARY KEY (round_id, assessor_id, pool_item_id),
            FOREIGN KEY (round_id, assessor_id)
              REFERENCES validation_reviewers(round_id, assessor_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS validation_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id TEXT NOT NULL,
            assessor_id TEXT,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            details_json TEXT NOT NULL,
            FOREIGN KEY (round_id) REFERENCES validation_rounds(id) ON DELETE CASCADE
        );
        """
    )
    return conn


def _audit(
    conn: sqlite3.Connection,
    round_id: str,
    event_type: str,
    *,
    assessor_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        "INSERT INTO validation_audit_events(round_id, assessor_id, event_type, created_at, details_json) VALUES(?,?,?,?,?)",
        (round_id, assessor_id, event_type, _now(), json.dumps(details or {}, sort_keys=True)),
    )


def _questions(repo_root: Path) -> dict[str, dict[str, str]]:
    path = repo_root / "validation" / "data" / "QUESTIONS.csv"
    result: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("split") or "").strip() != "validation":
                continue
            question_id = str(row.get("question_id") or "").strip()
            context = {
                key: str(row.get(key) or "").strip()
                for key in (
                    "population_context",
                    "intervention_exposure",
                    "comparator",
                    "outcome_construct",
                    "time_window",
                    "languages",
                    "document_types",
                )
                if str(row.get(key) or "").strip()
            }
            result[question_id] = {
                "question_text": str(row.get("question_text") or "").strip(),
                "eligibility_context": json.dumps(context, ensure_ascii=False, sort_keys=True),
            }
    return result


def _manifest_and_packets(repo_root: Path) -> tuple[dict[str, Any], Path]:
    packet_dir = _packet_dir(repo_root)
    manifest_path = packet_dir / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifesto privado inválido.")
    return manifest, packet_dir


def _source_fingerprint(repo_root: Path, manifest: dict[str, Any]) -> str:
    questions_path = repo_root / "validation" / "data" / "QUESTIONS.csv"
    digest = sha256()
    digest.update(questions_path.read_bytes())
    digest.update(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


def _load_packet(path: Path, questions: dict[str, dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    assessor_ids: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            assessor_id = str(raw.get("assessor_id") or "").strip()
            question_id = str(raw.get("question_id") or "").strip()
            if question_id not in questions:
                raise ValueError("Packet contém pergunta fora do split validation.")
            assessor_ids.add(assessor_id)
            try:
                assessor_order = int(str(raw.get("assessor_order") or "0"))
            except ValueError as exc:
                raise ValueError("assessor_order inválido no packet privado.") from exc
            q = questions[question_id]
            rows.append(
                {
                    "assessor_id": assessor_id,
                    "pool_item_id": str(raw.get("pool_item_id") or "").strip(),
                    "assessor_order": assessor_order,
                    "question_id": question_id,
                    "question_text": q["question_text"],
                    "eligibility_context": q["eligibility_context"],
                    "reference_id": str(raw.get("reference_id") or "").strip(),
                    "title": str(raw.get("title") or "").strip(),
                    "abstract": str(raw.get("abstract") or "").strip(),
                    "journal": str(raw.get("journal") or "").strip(),
                    "year": str(raw.get("year") or "").strip(),
                    "doi": str(raw.get("doi") or "").strip(),
                    "pmid": str(raw.get("pmid") or "").strip(),
                    "pmcid": str(raw.get("pmcid") or "").strip(),
                    "url": str(raw.get("url") or "").strip(),
                }
            )
    assessor_ids.discard("")
    if len(assessor_ids) != 1 or not rows:
        raise ValueError("Packet privado deve conter exatamente um assessor e pelo menos um item.")
    return next(iter(assessor_ids)), rows


def prepare_round(
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    readiness = get_validation_readiness(root)
    if readiness.get("ready") is not True:
        raise ValueError(str(readiness.get("message") or "Rodada científica não está pronta."))

    manifest, packet_dir = _manifest_and_packets(root)
    fingerprint = _source_fingerprint(root, manifest)
    path = _db_path(root, db_path)
    questions = _questions(root)

    with _connect(path) as conn:
        existing = conn.execute(
            "SELECT id FROM validation_rounds WHERE source_fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if existing:
            return round_status(repo_root=root, db_path=path, round_id=str(existing["id"]))

        round_id = "vr_" + uuid4().hex
        now = _now()
        conn.execute(
            "INSERT INTO validation_rounds(id, source_fingerprint, status, created_at, updated_at) VALUES(?,?,?,?,?)",
            (round_id, fingerprint, "assessment", now, now),
        )

        outputs = manifest.get("outputs") or []
        seen_assessors: set[str] = set()
        for output in outputs:
            if not isinstance(output, dict):
                continue
            packet_path = packet_dir / Path(str(output.get("path") or "")).name
            assessor_id, rows = _load_packet(packet_path, questions)
            if assessor_id in seen_assessors:
                raise ValueError("Assessor duplicado nos packets privados.")
            seen_assessors.add(assessor_id)
            declared = str(output.get("assessor_id") or "").strip()
            if declared and declared != assessor_id:
                raise ValueError("assessor_id do manifesto não corresponde ao packet.")

            token = secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO validation_reviewers(round_id, assessor_id, token, submitted_at) VALUES(?,?,?,NULL)",
                (round_id, assessor_id, token),
            )
            conn.executemany(
                """
                INSERT INTO validation_assignments(
                    round_id, assessor_id, pool_item_id, assessor_order, question_id,
                    question_text, eligibility_context, reference_id, title, abstract,
                    journal, year, doi, pmid, pmcid, url
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        round_id,
                        assessor_id,
                        row["pool_item_id"],
                        row["assessor_order"],
                        row["question_id"],
                        row["question_text"],
                        row["eligibility_context"],
                        row["reference_id"],
                        row["title"],
                        row["abstract"],
                        row["journal"],
                        row["year"],
                        row["doi"],
                        row["pmid"],
                        row["pmcid"],
                        row["url"],
                    )
                    for row in rows
                ],
            )
        if len(seen_assessors) < 2:
            raise ValueError("A rodada exige pelo menos dois assessores independentes.")
        _audit(conn, round_id, "round_prepared", details={"assessor_count": len(seen_assessors)})
        conn.commit()

    return round_status(repo_root=root, db_path=path, round_id=round_id)


def _latest_round_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT id FROM validation_rounds ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return str(row["id"]) if row else None


def round_status(
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
    round_id: str | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    if not path.is_file():
        raise FileNotFoundError("Nenhuma rodada preparada.")
    with _connect(path) as conn:
        rid = round_id or _latest_round_id(conn)
        if not rid:
            raise FileNotFoundError("Nenhuma rodada preparada.")
        round_row = conn.execute(
            "SELECT id, status, created_at, updated_at FROM validation_rounds WHERE id = ?",
            (rid,),
        ).fetchone()
        if not round_row:
            raise FileNotFoundError(rid)
        reviewers = conn.execute(
            """
            SELECT r.assessor_id, r.token, r.submitted_at,
                   COUNT(a.pool_item_id) AS total_items,
                   SUM(CASE WHEN a.relevance_grade IS NOT NULL AND TRIM(COALESCE(a.reason,'')) <> '' THEN 1 ELSE 0 END) AS completed_items,
                   SUM(CASE WHEN a.review_later = 1 THEN 1 ELSE 0 END) AS flagged_items,
                   SUM(CASE WHEN a.blind_to_nutev = 0 THEN 1 ELSE 0 END) AS blind_broken_items
            FROM validation_reviewers r
            JOIN validation_assignments a ON a.round_id = r.round_id AND a.assessor_id = r.assessor_id
            WHERE r.round_id = ?
            GROUP BY r.assessor_id, r.token, r.submitted_at
            ORDER BY r.assessor_id
            """,
            (rid,),
        ).fetchall()
        return {
            "round_id": str(round_row["id"]),
            "status": str(round_row["status"]),
            "created_at": str(round_row["created_at"]),
            "updated_at": str(round_row["updated_at"]),
            "reviewers": [
                {
                    "assessor_id": str(row["assessor_id"]),
                    "token": str(row["token"]),
                    "submitted": row["submitted_at"] is not None,
                    "submitted_at": row["submitted_at"],
                    "total_items": int(row["total_items"] or 0),
                    "completed_items": int(row["completed_items"] or 0),
                    "flagged_items": int(row["flagged_items"] or 0),
                    "blind_broken_items": int(row["blind_broken_items"] or 0),
                }
                for row in reviewers
            ],
        }


def _reviewer_by_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT round_id, assessor_id, submitted_at FROM validation_reviewers WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise PermissionError("Link privado inválido ou expirado.")
    return row


def reviewer_payload(
    token: str,
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    if not token or len(token) < 32:
        raise PermissionError("Link privado inválido.")
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    with _connect(path) as conn:
        reviewer = _reviewer_by_token(conn, token)
        rows = conn.execute(
            """
            SELECT pool_item_id, assessor_order, question_id, question_text, eligibility_context,
                   reference_id, title, abstract, journal, year, doi, pmid, pmcid, url,
                   relevance_grade, reason, decision_timestamp, blind_to_nutev, review_later, notes
            FROM validation_assignments
            WHERE round_id = ? AND assessor_id = ?
            ORDER BY assessor_order
            """,
            (reviewer["round_id"], reviewer["assessor_id"]),
        ).fetchall()
        assignments: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["eligibility_context"] = json.loads(item["eligibility_context"] or "{}")
            except json.JSONDecodeError:
                item["eligibility_context"] = {}
            item["blind_to_nutev"] = bool(item["blind_to_nutev"])
            item["review_later"] = bool(item["review_later"])
            assignments.append(item)
        completed = sum(
            1 for item in assignments if item["relevance_grade"] is not None and str(item["reason"] or "").strip()
        )
        return {
            "round_id": str(reviewer["round_id"]),
            "assessor_id": str(reviewer["assessor_id"]),
            "locked": reviewer["submitted_at"] is not None,
            "submitted_at": reviewer["submitted_at"],
            "completed_items": completed,
            "total_items": len(assignments),
            "assignments": assignments,
        }


def save_decision(
    token: str,
    payload: dict[str, Any],
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    pool_item_id = str(payload.get("pool_item_id") or "").strip()
    try:
        grade = int(payload.get("relevance_grade"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Escolha uma nota 0, 1 ou 2.") from exc
    reason = str(payload.get("reason") or "").strip()
    blind = payload.get("blind_to_nutev") is True
    review_later = payload.get("review_later") is True
    notes = str(payload.get("notes") or "").strip()
    if grade not in {0, 1, 2}:
        raise ValueError("Escolha uma nota 0, 1 ou 2.")
    if not reason:
        raise ValueError("A justificativa é obrigatória.")
    if not pool_item_id:
        raise ValueError("Item de avaliação inválido.")

    with _connect(path) as conn:
        reviewer = _reviewer_by_token(conn, token)
        if reviewer["submitted_at"] is not None:
            raise ValueError("A avaliação já foi enviada e está travada.")
        decision_timestamp = _now()
        cursor = conn.execute(
            """
            UPDATE validation_assignments
            SET relevance_grade = ?, reason = ?, decision_timestamp = ?, blind_to_nutev = ?, review_later = ?, notes = ?
            WHERE round_id = ? AND assessor_id = ? AND pool_item_id = ?
            """,
            (
                grade,
                reason,
                decision_timestamp,
                1 if blind else 0,
                1 if review_later else 0,
                notes or None,
                reviewer["round_id"],
                reviewer["assessor_id"],
                pool_item_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("Item não pertence a este avaliador.")
        _audit(
            conn,
            str(reviewer["round_id"]),
            "decision_saved",
            assessor_id=str(reviewer["assessor_id"]),
            details={"pool_item_id": pool_item_id},
        )
        conn.commit()
    return reviewer_payload(token, repo_root=root, db_path=path)


def submit_reviewer(
    token: str,
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    with _connect(path) as conn:
        reviewer = _reviewer_by_token(conn, token)
        if reviewer["submitted_at"] is not None:
            return reviewer_payload(token, repo_root=root, db_path=path)
        stats = conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN relevance_grade IS NOT NULL AND TRIM(COALESCE(reason,'')) <> '' AND decision_timestamp IS NOT NULL THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN blind_to_nutev = 0 THEN 1 ELSE 0 END) AS blind_broken
            FROM validation_assignments
            WHERE round_id = ? AND assessor_id = ?
            """,
            (reviewer["round_id"], reviewer["assessor_id"]),
        ).fetchone()
        total = int(stats["total"] or 0)
        completed = int(stats["completed"] or 0)
        blind_broken = int(stats["blind_broken"] or 0)
        if total <= 0 or completed != total:
            raise ValueError(f"Complete todos os itens antes de enviar ({completed}/{total}).")
        if blind_broken:
            raise ValueError("A cegueira foi declarada como quebrada em pelo menos um item; esta avaliação não pode ser submetida como evidência válida.")

        submitted_at = _now()
        conn.execute(
            "UPDATE validation_reviewers SET submitted_at = ? WHERE round_id = ? AND assessor_id = ?",
            (submitted_at, reviewer["round_id"], reviewer["assessor_id"]),
        )
        _audit(
            conn,
            str(reviewer["round_id"]),
            "assessment_submitted_locked",
            assessor_id=str(reviewer["assessor_id"]),
            details={"items": total},
        )
        remaining = conn.execute(
            "SELECT COUNT(*) AS n FROM validation_reviewers WHERE round_id = ? AND submitted_at IS NULL",
            (reviewer["round_id"],),
        ).fetchone()
        if int(remaining["n"] or 0) == 0:
            conn.execute(
                "UPDATE validation_rounds SET status = 'ready_for_adjudication', updated_at = ? WHERE id = ?",
                (_now(), reviewer["round_id"]),
            )
            _audit(conn, str(reviewer["round_id"]), "initial_assessment_complete")
        else:
            conn.execute(
                "UPDATE validation_rounds SET updated_at = ? WHERE id = ?",
                (_now(), reviewer["round_id"]),
            )
        conn.commit()
    return reviewer_payload(token, repo_root=root, db_path=path)
