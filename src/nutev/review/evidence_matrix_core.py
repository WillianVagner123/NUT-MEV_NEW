"""Shared schema and SQLite initialization for evidence matrices."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.review.article_screening_ledger import get_screening_session
from nutev.review.full_text_assessment_ledger import initialize_full_text_assessment_ledger
from nutev.review.human_review import REVIEWER_ROLES

TZ = ZoneInfo("America/Sao_Paulo")
SLOTS = ("REVIEWER_1", "REVIEWER_2")
FIELD_TYPES = (
    "TEXT", "LONG_TEXT", "INTEGER", "FLOAT", "BOOLEAN", "DATE",
    "SINGLE_SELECT", "MULTI_SELECT", "JSON",
)
COMMON = "__common__"
BIBLIO = (
    "document_id", "title", "authors", "year", "publication_date", "doi",
    "pmid", "pmcid", "journal", "country", "language", "article_type",
    "url", "retrieval_artifact_path", "retrieval_artifact_sha256",
)
COMMON_FIELDS = (
    ("objective", "Objetivo", "LONG_TEXT", 1),
    ("study_design", "Desenho do estudo ou documento", "TEXT", 1),
    ("population", "População", "LONG_TEXT", 0),
    ("sample_size", "Tamanho da amostra", "INTEGER", 0),
    ("context", "Contexto", "LONG_TEXT", 0),
    ("intervention_or_exposure", "Intervenção ou exposição", "LONG_TEXT", 0),
    ("comparator", "Comparador", "LONG_TEXT", 0),
    ("duration", "Duração", "TEXT", 0),
    ("outcomes", "Desfechos", "LONG_TEXT", 1),
    ("instruments", "Instrumentos", "LONG_TEXT", 0),
    ("statistical_analysis", "Análise estatística", "LONG_TEXT", 0),
    ("main_results", "Principais resultados", "LONG_TEXT", 1),
    ("limitations", "Limitações", "LONG_TEXT", 0),
    ("conflict_of_interest", "Conflitos de interesse", "LONG_TEXT", 0),
    ("funding", "Financiamento", "LONG_TEXT", 0),
    ("country", "País", "TEXT", 0),
    ("language", "Idioma", "TEXT", 0),
    ("document_type", "Tipo de documento", "TEXT", 1),
)
DEFAULT_TOOLS = (
    ("AGREE_II", "AGREE II", ["guideline"], ["scope_and_purpose", "stakeholders", "rigour", "clarity", "applicability", "independence"], ["HIGH", "MODERATE", "LOW", "CRITICALLY_LOW", "NOT_APPLICABLE"]),
    ("AMSTAR_2", "AMSTAR 2", ["systematic review", "meta-analysis"], ["protocol", "search", "selection", "appraisal", "synthesis", "publication_bias", "conflicts"], ["HIGH", "MODERATE", "LOW", "CRITICALLY_LOW", "NOT_APPLICABLE"]),
    ("ROB_2", "RoB 2", ["randomized trial", "rct"], ["randomization", "deviations", "missing_data", "outcome_measurement", "selective_reporting"], ["LOW", "SOME_CONCERNS", "HIGH", "NOT_APPLICABLE"]),
    ("ROBINS_I", "ROBINS-I", ["non-randomized", "observational intervention"], ["confounding", "selection", "classification", "deviations", "missing_data", "measurement", "reporting"], ["LOW", "MODERATE", "SERIOUS", "CRITICAL", "NO_INFORMATION", "NOT_APPLICABLE"]),
    ("QUALITATIVE", "JBI/CASP qualitativo", ["qualitative", "implementation"], ["congruity", "participants", "collection", "analysis", "researcher_influence", "ethics", "conclusions"], ["HIGH", "MODERATE", "LOW", "INSUFFICIENT", "NOT_APPLICABLE"]),
    ("AACODS", "AACODS", ["grey literature", "technical report", "official document"], ["authority", "accuracy", "coverage", "objectivity", "currency", "significance"], ["HIGH", "MODERATE", "LOW", "INSUFFICIENT", "NOT_APPLICABLE"]),
    ("SOURCE_CREDIBILITY", "Credibilidade e transparência", ["consensus", "statement", "official source"], ["authority", "transparency", "conflicts", "currency", "relevance", "evidence_basis"], ["HIGH", "MODERATE", "LOW", "INSUFFICIENT", "NOT_APPLICABLE"]),
)
DOMAIN_LABELS = {
    "scope_and_purpose": "Escopo e propósito", "stakeholders": "Partes interessadas",
    "rigour": "Rigor do desenvolvimento", "clarity": "Clareza",
    "applicability": "Aplicabilidade", "independence": "Independência editorial",
    "protocol": "Protocolo", "search": "Estratégia de busca", "selection": "Seleção",
    "appraisal": "Avaliação crítica", "synthesis": "Síntese",
    "publication_bias": "Viés de publicação", "conflicts": "Conflitos",
    "randomization": "Randomização", "deviations": "Desvios", "missing_data": "Dados ausentes",
    "outcome_measurement": "Mensuração dos desfechos", "selective_reporting": "Relato seletivo",
    "confounding": "Confundimento", "classification": "Classificação",
    "measurement": "Mensuração", "reporting": "Relato", "congruity": "Congruência",
    "participants": "Participantes", "collection": "Coleta", "analysis": "Análise",
    "researcher_influence": "Influência do pesquisador", "ethics": "Ética",
    "conclusions": "Conclusões", "authority": "Autoridade", "accuracy": "Acurácia",
    "coverage": "Cobertura", "objectivity": "Objetividade", "currency": "Atualidade",
    "significance": "Relevância", "transparency": "Transparência", "relevance": "Aplicabilidade",
    "evidence_basis": "Base de evidências",
}
DOMAIN_JUDGMENTS = ["YES", "PARTIAL", "NO", "UNCLEAR", "NOT_APPLICABLE"]


def _now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _db(path: Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _j(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def _reviewer(name: str, role: str) -> tuple[str, str]:
    if not name.strip():
        raise ValueError("reviewer_name is required")
    if role not in REVIEWER_ROLES:
        raise ValueError(f"reviewer_role must be one of {sorted(REVIEWER_ROLES)}")
    return name.strip(), role


def _open_session(db_path: Path, session_id: str) -> dict[str, Any]:
    session = get_screening_session(db_path, session_id)
    if not session:
        raise ValueError(f"unknown session_id: {session_id}")
    if session["status"] != "OPEN":
        raise ValueError("screening session is completed")
    return session


def initialize(db_path: Path) -> None:
    initialize_full_text_assessment_ledger(db_path)
    with _db(db_path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS extraction_schema_fields(
              id TEXT PRIMARY KEY, scope TEXT NOT NULL, article_id TEXT NOT NULL DEFAULT '',
              field_key TEXT NOT NULL, label TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
              field_type TEXT NOT NULL, options_json TEXT NOT NULL DEFAULT '[]',
              required INTEGER NOT NULL DEFAULT 0, validation_json TEXT NOT NULL DEFAULT '{}',
              display_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
              revision INTEGER NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
              UNIQUE(scope,article_id,field_key,revision));
            CREATE INDEX IF NOT EXISTS idx_schema_latest ON extraction_schema_fields(scope,article_id,field_key,revision DESC);
            CREATE TABLE IF NOT EXISTS extraction_submissions(
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, document_id TEXT NOT NULL,
              article_id TEXT NOT NULL, reviewer_slot TEXT NOT NULL, reviewer_name TEXT NOT NULL,
              reviewer_role TEXT NOT NULL, schema_json TEXT NOT NULL, values_json TEXT NOT NULL,
              artifact_sha256 TEXT NOT NULL DEFAULT '', completeness TEXT NOT NULL,
              revision INTEGER NOT NULL, submitted_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,article_id,reviewer_slot,revision));
            CREATE INDEX IF NOT EXISTS idx_extract_latest ON extraction_submissions(session_id,article_id,document_id,reviewer_slot,revision DESC);
            CREATE TABLE IF NOT EXISTS extraction_adjudications(
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, document_id TEXT NOT NULL,
              article_id TEXT NOT NULL, field_key TEXT NOT NULL, reviewer_1_json TEXT NOT NULL,
              reviewer_2_json TEXT NOT NULL, final_json TEXT NOT NULL, adjudicator_name TEXT NOT NULL,
              adjudicator_role TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL,
              decided_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,article_id,field_key,revision));
            CREATE TABLE IF NOT EXISTS quality_instrument_versions(
              id TEXT PRIMARY KEY, instrument_key TEXT NOT NULL, name TEXT NOT NULL,
              version_label TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
              document_types_json TEXT NOT NULL DEFAULT '[]', overall_json TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL,
              created_by TEXT NOT NULL, created_at TEXT NOT NULL,
              UNIQUE(instrument_key,revision));
            CREATE TABLE IF NOT EXISTS quality_instrument_domains(
              id TEXT PRIMARY KEY, instrument_id TEXT NOT NULL, domain_key TEXT NOT NULL,
              label TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', judgments_json TEXT NOT NULL,
              required INTEGER NOT NULL DEFAULT 1, display_order INTEGER NOT NULL,
              FOREIGN KEY(instrument_id) REFERENCES quality_instrument_versions(id),
              UNIQUE(instrument_id,domain_key));
            CREATE TABLE IF NOT EXISTS quality_instrument_assignments(
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, document_id TEXT NOT NULL,
              article_id TEXT NOT NULL, instrument_id TEXT NOT NULL, selection_basis TEXT NOT NULL,
              rationale TEXT NOT NULL, reviewer_name TEXT NOT NULL, reviewer_role TEXT NOT NULL,
              revision INTEGER NOT NULL, assigned_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              FOREIGN KEY(instrument_id) REFERENCES quality_instrument_versions(id),
              UNIQUE(session_id,document_id,article_id,revision));
            CREATE TABLE IF NOT EXISTS quality_assessments(
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, document_id TEXT NOT NULL,
              article_id TEXT NOT NULL, instrument_id TEXT NOT NULL, reviewer_slot TEXT NOT NULL,
              domains_json TEXT NOT NULL, overall TEXT NOT NULL, rationale TEXT NOT NULL,
              artifact_sha256 TEXT NOT NULL DEFAULT '', reviewer_name TEXT NOT NULL,
              reviewer_role TEXT NOT NULL, revision INTEGER NOT NULL, assessed_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              FOREIGN KEY(instrument_id) REFERENCES quality_instrument_versions(id),
              UNIQUE(session_id,document_id,article_id,reviewer_slot,revision));
            CREATE TABLE IF NOT EXISTS quality_adjudications(
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, document_id TEXT NOT NULL,
              article_id TEXT NOT NULL, instrument_id TEXT NOT NULL, domains_json TEXT NOT NULL,
              overall TEXT NOT NULL, adjudicator_name TEXT NOT NULL, adjudicator_role TEXT NOT NULL,
              notes TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL, decided_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,article_id,revision));
            CREATE TABLE IF NOT EXISTS evidence_matrix_exports(
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created_at TEXT NOT NULL,
              included INTEGER NOT NULL, extraction_complete INTEGER NOT NULL, quality_complete INTEGER NOT NULL,
              paths_json TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id));
            """
        )
        stamp = _now()
        for order, (key, label, kind, required) in enumerate(COMMON_FIELDS, 1):
            if not con.execute("SELECT 1 FROM extraction_schema_fields WHERE scope=? AND article_id='' AND field_key=?", (COMMON, key)).fetchone():
                con.execute(
                    "INSERT INTO extraction_schema_fields VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"schema_{uuid4().hex}", COMMON, "", key, label, "", kind, "[]", required, "{}", order, 1, 1, "system", stamp),
                )
        for key, name, types, domains, overall in DEFAULT_TOOLS:
            if con.execute("SELECT 1 FROM quality_instrument_versions WHERE instrument_key=?", (key,)).fetchone():
                continue
            instrument_id = f"instrument_{uuid4().hex}"
            con.execute(
                "INSERT INTO quality_instrument_versions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (instrument_id, key, name, "configurable", "Estrutura configurável; consulte o manual oficial.", _j(types), _j(overall), 1, 1, "system", stamp),
            )
            for order, domain in enumerate(domains, 1):
                con.execute(
                    "INSERT INTO quality_instrument_domains VALUES(?,?,?,?,?,?,?,?)",
                    (f"domain_{uuid4().hex}", instrument_id, domain, DOMAIN_LABELS.get(domain, domain.replace("_", " ").title()), "", _j(DOMAIN_JUDGMENTS), 1, order),
                )
