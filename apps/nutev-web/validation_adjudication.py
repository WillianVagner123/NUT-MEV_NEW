from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from validation_server import REPO_ROOT, _audit, _connect, _db_path, _now


def _ensure_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS validation_adjudications (
            round_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            reference_id TEXT NOT NULL,
            relevance_grade INTEGER NOT NULL CHECK (relevance_grade IN (0,1,2)),
            adjudicator_id TEXT NOT NULL,
            adjudication_timestamp TEXT NOT NULL,
            notes TEXT,
            PRIMARY KEY (round_id, question_id, reference_id),
            FOREIGN KEY (round_id) REFERENCES validation_rounds(id) ON DELETE CASCADE
        );
        """
    )


def _latest_round_id(conn) -> str:
    row = conn.execute(
        "SELECT id FROM validation_rounds ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        raise FileNotFoundError("Nenhuma rodada preparada.")
    return str(row["id"])


def _round_row(conn, round_id: str | None = None):
    rid = round_id or _latest_round_id(conn)
    row = conn.execute(
        "SELECT id, status FROM validation_rounds WHERE id = ?",
        (rid,),
    ).fetchone()
    if not row:
        raise FileNotFoundError(rid)
    return row


def _locked_assessments(conn, round_id: str) -> list[dict[str, Any]]:
    unlocked = conn.execute(
        "SELECT COUNT(*) AS n FROM validation_reviewers WHERE round_id = ? AND submitted_at IS NULL",
        (round_id,),
    ).fetchone()
    if int(unlocked["n"] or 0):
        raise ValueError("A adjudicação só abre depois que todos os avaliadores enviarem e travarem suas avaliações.")

    rows = conn.execute(
        """
        SELECT a.question_id, a.reference_id, a.pool_item_id, a.assessor_id,
               a.relevance_grade, a.reason, a.decision_timestamp,
               a.title, a.abstract, a.journal, a.year, a.doi, a.pmid, a.pmcid, a.url,
               a.question_text, a.eligibility_context
        FROM validation_assignments a
        WHERE a.round_id = ?
        ORDER BY a.question_id, a.reference_id, a.assessor_id
        """,
        (round_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _group_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["question_id"]), str(row["reference_id"]))].append(row)

    result: list[dict[str, Any]] = []
    for (question_id, reference_id), judgments in sorted(grouped.items()):
        grades = {int(item["relevance_grade"]) for item in judgments if item["relevance_grade"] is not None}
        if len(grades) == 0:
            raise ValueError(f"Par sem julgamentos completos: {question_id}/{reference_id}")
        if len(judgments) < 2:
            raise ValueError(f"Par sem dois julgamentos independentes: {question_id}/{reference_id}")
        sample = judgments[0]
        result.append(
            {
                "question_id": question_id,
                "reference_id": reference_id,
                "pool_item_id": str(sample.get("pool_item_id") or ""),
                "question_text": str(sample.get("question_text") or ""),
                "eligibility_context": str(sample.get("eligibility_context") or "{}"),
                "title": str(sample.get("title") or ""),
                "abstract": str(sample.get("abstract") or ""),
                "journal": str(sample.get("journal") or ""),
                "year": str(sample.get("year") or ""),
                "doi": str(sample.get("doi") or ""),
                "pmid": str(sample.get("pmid") or ""),
                "pmcid": str(sample.get("pmcid") or ""),
                "url": str(sample.get("url") or ""),
                "agreed": len(grades) == 1,
                "agreed_grade": next(iter(grades)) if len(grades) == 1 else None,
                "judgments": [
                    {
                        "assessor_id": str(item.get("assessor_id") or ""),
                        "relevance_grade": int(item["relevance_grade"]),
                        "reason": str(item.get("reason") or ""),
                        "decision_timestamp": str(item.get("decision_timestamp") or ""),
                    }
                    for item in judgments
                ],
            }
        )
    return result


def adjudication_payload(
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
        _ensure_schema(conn)
        round_row = _round_row(conn, round_id)
        rid = str(round_row["id"])
        status = str(round_row["status"])
        if status not in {"ready_for_adjudication", "adjudicating", "adjudication_complete"}:
            raise ValueError("A rodada ainda não está pronta para adjudicação.")
        pairs = _group_pairs(_locked_assessments(conn, rid))
        saved_rows = conn.execute(
            """
            SELECT question_id, reference_id, relevance_grade, adjudicator_id,
                   adjudication_timestamp, notes
            FROM validation_adjudications
            WHERE round_id = ?
            """,
            (rid,),
        ).fetchall()
        saved = {
            (str(row["question_id"]), str(row["reference_id"])): dict(row)
            for row in saved_rows
        }

        agreements = [pair for pair in pairs if pair["agreed"]]
        conflicts: list[dict[str, Any]] = []
        for pair in pairs:
            if pair["agreed"]:
                continue
            item = dict(pair)
            decision = saved.get((pair["question_id"], pair["reference_id"]))
            item["adjudication"] = decision
            conflicts.append(item)

        resolved = sum(1 for item in conflicts if item["adjudication"] is not None)
        return {
            "round_id": rid,
            "status": status,
            "total_pairs": len(pairs),
            "agreed_pairs": len(agreements),
            "conflict_pairs": len(conflicts),
            "resolved_conflicts": resolved,
            "unresolved_conflicts": len(conflicts) - resolved,
            "conflicts": conflicts,
        }


def save_adjudication(
    payload: dict[str, Any],
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
    round_id: str | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    question_id = str(payload.get("question_id") or "").strip()
    reference_id = str(payload.get("reference_id") or "").strip()
    adjudicator_id = str(payload.get("adjudicator_id") or "").strip()
    notes = str(payload.get("notes") or "").strip()
    try:
        grade = int(payload.get("relevance_grade"))
    except (TypeError, ValueError) as exc:
        raise ValueError("A adjudicação exige nota final 0, 1 ou 2.") from exc
    if grade not in {0, 1, 2}:
        raise ValueError("A adjudicação exige nota final 0, 1 ou 2.")
    if not question_id or not reference_id:
        raise ValueError("Identidade do conflito inválida.")
    if not adjudicator_id:
        raise ValueError("Identifique o adjudicador humano.")

    with _connect(path) as conn:
        _ensure_schema(conn)
        round_row = _round_row(conn, round_id)
        rid = str(round_row["id"])
        status = str(round_row["status"])
        if status not in {"ready_for_adjudication", "adjudicating"}:
            raise ValueError("A rodada não aceita novas decisões de adjudicação.")

        pairs = _group_pairs(_locked_assessments(conn, rid))
        conflict = next(
            (
                pair
                for pair in pairs
                if pair["question_id"] == question_id
                and pair["reference_id"] == reference_id
                and not pair["agreed"]
            ),
            None,
        )
        if conflict is None:
            raise ValueError("Este par não é um conflito adjudicável.")

        timestamp = _now()
        conn.execute(
            """
            INSERT INTO validation_adjudications(
                round_id, question_id, reference_id, relevance_grade,
                adjudicator_id, adjudication_timestamp, notes
            ) VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(round_id, question_id, reference_id) DO UPDATE SET
                relevance_grade = excluded.relevance_grade,
                adjudicator_id = excluded.adjudicator_id,
                adjudication_timestamp = excluded.adjudication_timestamp,
                notes = excluded.notes
            """,
            (rid, question_id, reference_id, grade, adjudicator_id, timestamp, notes or None),
        )
        conn.execute(
            "UPDATE validation_rounds SET status = 'adjudicating', updated_at = ? WHERE id = ?",
            (timestamp, rid),
        )
        _audit(
            conn,
            rid,
            "conflict_adjudicated",
            details={
                "question_id": question_id,
                "reference_id": reference_id,
                "adjudicator_id": adjudicator_id,
            },
        )
        conn.commit()

    return adjudication_payload(repo_root=root, db_path=path, round_id=rid)


def finalize_adjudication(
    *,
    repo_root: Path | None = None,
    db_path: Path | None = None,
    round_id: str | None = None,
) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    path = _db_path(root, db_path)
    current = adjudication_payload(repo_root=root, db_path=path, round_id=round_id)
    if int(current["unresolved_conflicts"]) != 0:
        raise ValueError(
            f"Ainda existem {current['unresolved_conflicts']} conflitos sem decisão humana."
        )

    with _connect(path) as conn:
        _ensure_schema(conn)
        rid = str(current["round_id"])
        timestamp = _now()
        conn.execute(
            "UPDATE validation_rounds SET status = 'adjudication_complete', updated_at = ? WHERE id = ?",
            (timestamp, rid),
        )
        _audit(
            conn,
            rid,
            "adjudication_complete",
            details={
                "agreed_pairs": int(current["agreed_pairs"]),
                "resolved_conflicts": int(current["resolved_conflicts"]),
            },
        )
        conn.commit()

    return adjudication_payload(repo_root=root, db_path=path, round_id=str(current["round_id"]))
