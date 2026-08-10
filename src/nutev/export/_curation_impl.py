from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from nutev.export.excel_writer import (
    sanitize_dataframe_for_excel,
    write_excel_file,
    write_excel_sheet,
)
from nutev.export.metadata_tables import REQUIRED_METADATA_COLUMNS

CURATED_METADATA_COLUMNS = REQUIRED_METADATA_COLUMNS + [
    "document_key",
    "document_key_type",
    "doi_normalized",
    "url_normalized",
    "title_normalized",
    "year_normalized",
    "workstream_list",
    "has_full_text",
    "is_metadata_only",
    "is_prioritized",
]

UNIQUE_DOCUMENT_COLUMNS = [
    "document_key",
    "document_key_type",
    "title",
    "year",
    "doi",
    "pmid",
    "pmcid",
    "original_url",
    "final_url",
    "source_provider",
    "source_institution",
    "journal",
    "evidence_type",
    "download_status",
    "capture_status",
    "extraction_status",
    "relevance_score",
    "editorial_priority_score",
    "editorial_priority_tier",
    "workstreams",
    "document_ids",
    "source_occurrences",
    "has_full_text",
    "is_metadata_only",
    "is_prioritized",
]

TOP_A1_OPERATIONAL_COLUMNS = [
    "document_key",
    "title",
    "journal",
    "source_institution",
    "workstreams",
    "year",
    "evidence_type",
    "relevance_score",
    "editorial_priority_score",
    "editorial_priority_tier",
    "download_status",
    "capture_status",
    "extraction_status",
    "has_full_text",
    "is_metadata_only",
    "is_prioritized",
    "doi",
    "pmid",
    "pmcid",
    "final_url",
    "original_url",
]

WORKSTREAM_MAP_COLUMNS = [
    "document_key",
    "document_id",
    "workstream",
    "source_provider",
    "title",
    "year",
    "download_status",
    "extraction_status",
    "is_prioritized",
]

PRISMA_COLUMNS = [
    "registros_identificados",
    "duplicados_removidos",
    "registros_triados",
    "documentos_com_pdf_ou_html",
    "documentos_metadata_only",
    "documentos_priorizados",
]

PRISMA_NOTE_COLUMNS = ["nota"]
QA_SUMMARY_COLUMNS = ["metric", "value"]
DUPLICATE_SUMMARY_COLUMNS = [
    "document_key_type",
    "duplicate_documents",
    "duplicate_rows",
]
MISSING_BY_WORKSTREAM_COLUMNS = [
    "workstream",
    "missing_title",
    "missing_url",
    "missing_year",
    "missing_evidence_type",
]

CURATED_OUTPUT_ALIASES = {
    "curated_metadata_csv": ["curated_metadata.csv", "NUTEV_METADATA_CURATED.csv"],
    "curated_metadata_xlsx": ["curated_metadata.xlsx", "NUTEV_METADATA_CURATED.xlsx"],
    "unique_documents_csv": ["unique_documents.csv", "NUTEV_DOCUMENTS_UNIQUE.csv"],
    "unique_documents_xlsx": ["unique_documents.xlsx", "NUTEV_DOCUMENTS_UNIQUE.xlsx"],
    "workstream_map_csv": [
        "workstream_document_map.csv",
        "NUTEV_DOCUMENT_WORKSTREAM_MAP.csv",
    ],
    "workstream_map_xlsx": ["NUTEV_DOCUMENT_WORKSTREAM_MAP.xlsx"],
    "qa_report_xlsx": ["NUTEV_QA_REPORT.xlsx"],
    "prisma_flow_xlsx": ["NUTEV_PRISMA_FLOW_CORRIGIDO.xlsx"],
    "top_operational_xlsx": ["top_operational_documents.xlsx"],
}

_PRIORITY_TERMS = [
    "obesity",
    "obesidade",
    "overweight",
    "cardiometabolic",
    "diabetes",
    "hypertension",
    "dyslipidemia",
    "dyslipidaemia",
    "hyperlipidemia",
    "hyperlipidaemia",
    "hypercholesterolemia",
    "hypercholesterolaemia",
    "hypertriglyceridemia",
    "hypertriglyceridaemia",
    "metabolic syndrome",
    "prediabetes",
    "insulin resistance",
    "apolipoprotein b",
    "apo b",
    "masld",
    "nafld",
    "mafld",
    "mash",
    "nash",
    "fatty liver",
    "steatotic liver disease",
    "steatohepatitis",
    "metabolic dysfunction-associated steatotic liver disease",
    "metabolic dysfunction associated steatotic liver disease",
    "metabolic dysfunction-associated fatty liver disease",
    "metabolic dysfunction associated fatty liver disease",
    "metabolic dysfunction-associated steatohepatitis",
    "metabolic dysfunction associated steatohepatitis",
    "nonalcoholic fatty liver disease",
    "non-alcoholic fatty liver disease",
    "nonalcoholic steatohepatitis",
    "non-alcoholic steatohepatitis",
    "mediterranean",
    "dash",
    "mind",
    "plant-based",
    "eat-lancet",
    "diet quality",
    "diet quality score",
    "diet quality index",
    "dietary quality",
    "dietary diversity",
    "healthy eating index",
    "alternate healthy eating index",
    "ahei",
    "dietary inflammatory index",
    "mediterranean diet score",
    "plant-based diet index",
    "plant based diet index",
    "dietary pattern score",
    "dietary guideline",
    "food-based dietary guideline",
    "guideline",
    "guidelines",
    "clinical practice guideline",
    "practice advisory",
    "practice guidance",
    "guidance statement",
    "guideline update",
    "clinical practice update",
    "best practice advice",
    "living guideline",
    "consensus",
    "consensus statement",
    "consensus report",
    "consensus guidance",
    "consensus update",
    "scientific statement",
    "scientific advisory",
    "policy statement",
    "position statement",
    "position paper",
    "joint statement",
    "joint guideline",
    "clinical guidance",
    "clinical decision pathway",
    "decision pathway",
    "clinical practice recommendation",
    "clinical practice recommendations",
    "standards of care",
    "standards of medical care",
    "standards of medical care in diabetes",
    "nutrition practice guideline",
    "dietetic practice guideline",
    "systematic review",
    "meta-analysis",
    "meta analysis",
    "network meta-analysis",
    "network meta analysis",
    "umbrella review",
    "overview of reviews",
    "review of reviews",
    "living systematic review",
    "rapid review",
    "scoping review",
    "integrative review",
    "randomized controlled trial",
    "controlled trial",
    "pragmatic trial",
    "lifestyle medicine",
    "culinary medicine",
    "food literacy",
    "food and nutrition literacy",
    "nutrition literacy",
    "food agency",
    "food is medicine",
    "food as medicine",
    "produce prescription",
    "produce prescriptions",
    "produce prescription program",
    "produce rx",
    "fruit and vegetable prescription",
    "healthy food prescription",
    "food prescription program",
    "healthy food incentive",
    "healthy food incentives",
    "nutrition incentive",
    "nutrition incentives",
    "produce voucher",
    "produce vouchers",
    "fruit and vegetable voucher",
    "fruit and vegetable vouchers",
    "medically tailored meal",
    "medically tailored meals",
    "medically tailored grocery",
    "medically tailored groceries",
    "medically tailored pantry",
    "medically tailored pantries",
    "medically tailored food package",
    "medically tailored food packages",
    "teaching kitchen",
    "teaching kitchens",
    "nutrition security",
    "food environment",
    "retail food environment",
    "healthy food access",
    "healthy food procurement",
    "front-of-pack labeling",
    "front-of-pack labelling",
    "menu labeling",
    "menu labelling",
    "adherence",
    "implementation",
    "implementation trial",
    "implementation evaluation",
    "implementation science",
    "implementation strategy",
    "implementation strategies",
    "implementation framework",
    "implementation frameworks",
    "implementation outcomes",
    "implementation outcomes framework",
    "proctor implementation outcomes",
    "implementation fidelity",
    "implementation determinant",
    "implementation determinants",
    "implementation barrier",
    "implementation barriers",
    "implementation facilitator",
    "implementation facilitators",
    "implementation climate",
    "organizational readiness",
    "readiness for implementation",
    "acceptability",
    "feasibility",
    "penetration",
    "sustainment",
    "hybrid effectiveness-implementation",
    "hybrid effectiveness implementation",
    "hybrid type 1",
    "hybrid type 2",
    "hybrid type 3",
    "cfir",
    "re-aim",
    "normalization process theory",
    "theoretical domains framework",
    "motivational interviewing",
    "behavior change technique",
    "behavior change techniques",
    "behaviour change technique",
    "behaviour change techniques",
    "behavior change taxonomy",
    "behaviour change taxonomy",
    "behavior change wheel",
    "behaviour change wheel",
    "behavior change intervention",
    "behaviour change intervention",
    "behavior change intervention functions",
    "behaviour change intervention functions",
    "com-b",
    "com b",
    "capability opportunity motivation behavior",
    "capability opportunity motivation behaviour",
    "intervention mapping",
    "implementation mapping",
    "process evaluation",
    "quality improvement",
    "quality improvement study",
    "real-world implementation",
    "real world implementation",
    "real-world evidence",
    "real world evidence",
    "knowledge translation",
    "practice facilitation",
    "audit and feedback",
    "care delivery",
    "service delivery",
    "health coaching",
    "telehealth",
    "telemedicine",
    "digital health",
    "mobile health",
    "mhealth",
    "ehealth",
    "virtual care",
    "remote coaching",
    "remote monitoring",
    "digital therapeutics",
    "self-management support",
    "scale-up",
    "scale up",
    "program implementation",
    "barrier",
    "facilitator",
    "commensality",
    "meal planning",
    "behavior change",
    "self-efficacy",
]

_PRIORITY_TEXT_FIELDS = (
    "title",
    "abstract",
    "snippet",
    "summary",
    "evidence_type",
    "domains",
    "outcomes",
    "diet_patterns",
    "clinical_conditions",
    "main_terms",
    "journal",
    "source_institution",
)

_A1_PROXY_TIERS = {"a1_proxy_high", "a1_proxy_moderate"}

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return "; ".join(_as_text(v) for v in value if _as_text(v))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def _normalize_doi(value: object) -> str:
    text = _as_text(value).lower()
    if not text:
        return ""
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    return text.strip().strip("/")


def _normalize_url(value: object) -> str:
    text = _as_text(value)
    if not text:
        return ""
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return text.strip().rstrip("/").lower().removeprefix("www.")

    netloc = parsed.netloc.lower().removeprefix("www.")
    if parsed.scheme.lower() == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    if parsed.scheme.lower() == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed.path.rstrip("/") or "/"
    return f"{netloc}{path}".rstrip("/")


def _normalize_title(value: object) -> str:
    text = _WHITESPACE_RE.sub(" ", _as_text(value).lower()).strip()
    return _NON_ALNUM_RE.sub(" ", text).strip()


def _normalize_year(value: object) -> str:
    text = _as_text(value)
    if not text:
        return ""
    try:
        year = int(float(text))
    except Exception:
        return ""
    return str(year)


def _normalize_priority_text(value: object) -> str:
    text = _WHITESPACE_RE.sub(" ", _as_text(value).lower()).strip()
    return _NON_ALNUM_RE.sub(" ", text).strip()


def _hash_fallback(row: dict) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]  # noqa: S324


def _compute_document_key(row: dict) -> tuple[str, str]:
    doi = _normalize_doi(row.get("doi"))
    if doi:
        return doi, "doi"

    pmid = _as_text(row.get("pmid"))
    if pmid:
        return pmid, "pmid"

    pmcid = _as_text(row.get("pmcid"))
    if pmcid:
        return pmcid, "pmcid"

    url = _normalize_url(
        row.get("final_url") or row.get("original_url") or row.get("url")
    )
    if url:
        return url, "url"

    title = _normalize_title(row.get("title"))
    year = _normalize_year(row.get("year"))
    if title and year:
        return f"{title}::{year}", "title_year"

    return _hash_fallback(row), "row_hash"


def _has_full_text(row: dict) -> bool:
    statuses = {
        _as_text(row.get("download_status")).lower(),
        _as_text(row.get("capture_status")).lower(),
        _as_text(row.get("extraction_status")).lower(),
    }
    if "pdf" in statuses or "html_snapshot" in statuses or "ok" in statuses:
        return True
    return bool(_as_text(row.get("file_path")) or _as_text(row.get("text_path")))


def _is_prioritized(row: dict) -> bool:
    try:
        score = float(row.get("relevance_score") or row.get("score") or 0)
    except Exception:
        score = 0.0
    text = " ".join(_as_text(row.get(field)) for field in _PRIORITY_TEXT_FIELDS)
    normalized_text = _normalize_priority_text(text)
    editorial_tier = _as_text(row.get("editorial_priority_tier")).lower()
    high_value_editorial = editorial_tier in _A1_PROXY_TIERS
    matches_priority_scope = any(
        _normalize_priority_text(term) in normalized_text for term in _PRIORITY_TERMS
    )
    return (score >= 8 and matches_priority_scope) or (score >= 7 and high_value_editorial)


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    text = _as_text(value).lower()
    return text in {"1", "true", "yes", "y", "sim"}


def _count_truthy(series: pd.Series) -> int:
    return int(sum(_is_truthy(value) for value in series.tolist()))


def _write_csv_aliases(df: pd.DataFrame, output_dir: Path, names: list[str]) -> None:
    safe_df = sanitize_dataframe_for_excel(df)
    for name in names:
        safe_df.to_csv(output_dir / name, index=False, encoding="utf-8-sig")


def _write_excel_aliases(df: pd.DataFrame, output_dir: Path, names: list[str]) -> None:
    safe_df = sanitize_dataframe_for_excel(df)
    for name in names:
        write_excel_file(safe_df, output_dir / name)


def _build_qa_summary_df(curated_df: pd.DataFrame, unique_df: pd.DataFrame) -> pd.DataFrame:
    duplicate_rows = max(len(curated_df) - len(unique_df), 0)
    rows = [
        {"metric": "curated_rows", "value": len(curated_df)},
        {"metric": "unique_documents", "value": len(unique_df)},
        {"metric": "duplicate_rows_removed", "value": duplicate_rows},
        {
            "metric": "documents_with_full_text",
            "value": _count_truthy(unique_df["has_full_text"]) if not unique_df.empty else 0,
        },
        {
            "metric": "metadata_only_documents",
            "value": _count_truthy(unique_df["is_metadata_only"]) if not unique_df.empty else 0,
        },
        {
            "metric": "prioritized_documents",
            "value": _count_truthy(unique_df["is_prioritized"]) if not unique_df.empty else 0,
        },
    ]
    return pd.DataFrame(rows, columns=QA_SUMMARY_COLUMNS)


def _build_duplicate_summary_df(unique_df: pd.DataFrame) -> pd.DataFrame:
    if unique_df.empty:
        return pd.DataFrame(columns=DUPLICATE_SUMMARY_COLUMNS)

    working = unique_df.copy()
    working["source_occurrences"] = pd.to_numeric(
        working["source_occurrences"],
        errors="coerce",
    ).fillna(0)
    duplicates_only = working[working["source_occurrences"] > 1].copy()
    if duplicates_only.empty:
        return pd.DataFrame(columns=DUPLICATE_SUMMARY_COLUMNS)

    grouped = (
        duplicates_only.groupby("document_key_type", dropna=False)
        .agg(
            duplicate_documents=("document_key", "count"),
            duplicate_rows=("source_occurrences", lambda s: int(s.sum() - len(s))),
        )
        .reset_index()
    )
    return _ensure_columns(grouped, DUPLICATE_SUMMARY_COLUMNS)


def _build_missing_by_workstream_df(curated_df: pd.DataFrame) -> pd.DataFrame:
    if curated_df.empty:
        return pd.DataFrame(columns=MISSING_BY_WORKSTREAM_COLUMNS)

    rows: list[dict[str, object]] = []
    for workstream, group in curated_df.groupby("workstream", dropna=False):
        workstream_name = _as_text(workstream) or "unknown"
        missing_url = (
            (group["original_url"].fillna("") == "")
            & (group["final_url"].fillna("") == "")
        ).sum()
        rows.append(
            {
                "workstream": workstream_name,
                "missing_title": int((group["title"].fillna("") == "").sum()),
                "missing_url": int(missing_url),
                "missing_year": int((group["year"].fillna("") == "").sum()),
                "missing_evidence_type": int(
                    (group["evidence_type"].fillna("") == "").sum()
                ),
            }
        )
    return pd.DataFrame(rows, columns=MISSING_BY_WORKSTREAM_COLUMNS)


def _build_prisma_df(curated_df: pd.DataFrame, unique_df: pd.DataFrame) -> pd.DataFrame:
    registros_identificados = len(curated_df)
    registros_triados = len(unique_df)
    documentos_com_pdf_ou_html = (
        _count_truthy(unique_df["has_full_text"]) if not unique_df.empty else 0
    )
    documentos_metadata_only = (
        _count_truthy(unique_df["is_metadata_only"]) if not unique_df.empty else 0
    )
    documentos_priorizados = (
        _count_truthy(unique_df["is_prioritized"]) if not unique_df.empty else 0
    )
    row = {
        "registros_identificados": registros_identificados,
        "duplicados_removidos": max(registros_identificados - registros_triados, 0),
        "registros_triados": registros_triados,
        "documentos_com_pdf_ou_html": documentos_com_pdf_ou_html,
        "documentos_metadata_only": documentos_metadata_only,
        "documentos_priorizados": documentos_priorizados,
    }
    return pd.DataFrame([row], columns=PRISMA_COLUMNS)


def _build_prisma_notes_df() -> pd.DataFrame:
    note = (
        "PRISMA operacional derivado da camada curada. "
        "registros_identificados = linhas brutas curadas; "
        "duplicados_removidos = linhas curadas - documentos únicos; "
        "documentos_com_pdf_ou_html = documentos únicos com has_full_text verdadeiro; "
        "documentos_metadata_only = documentos únicos sem texto completo; "
        "documentos_priorizados = documentos únicos priorizados pela regra operacional."
    )
    return pd.DataFrame([{"nota": note}], columns=PRISMA_NOTE_COLUMNS)


def _write_qa_report(
    output_dir: Path,
    summary_df: pd.DataFrame,
    duplicate_df: pd.DataFrame,
    missing_df: pd.DataFrame,
) -> None:
    for name in CURATED_OUTPUT_ALIASES["qa_report_xlsx"]:
        path = output_dir / name
        try:
            with pd.ExcelWriter(path) as writer:
                write_excel_sheet(writer, summary_df, "qa_summary")
                write_excel_sheet(writer, duplicate_df, "duplicate_summary")
                write_excel_sheet(writer, missing_df, "missing_by_workstream")
        except Exception:
            summary_df.to_csv(path.with_suffix(".qa_summary.csv"), index=False, encoding="utf-8-sig")
            duplicate_df.to_csv(path.with_suffix(".duplicate_summary.csv"), index=False, encoding="utf-8-sig")
            missing_df.to_csv(path.with_suffix(".missing_by_workstream.csv"), index=False, encoding="utf-8-sig")
            path.touch()


def _write_prisma_report(
    output_dir: Path,
    prisma_df: pd.DataFrame,
    notes_df: pd.DataFrame,
) -> None:
    for name in CURATED_OUTPUT_ALIASES["prisma_flow_xlsx"]:
        path = output_dir / name
        try:
            with pd.ExcelWriter(path) as writer:
                write_excel_sheet(writer, prisma_df, "prisma_flow")
                write_excel_sheet(writer, notes_df, "notes")
        except Exception:
            prisma_df.to_csv(path.with_suffix(".prisma_flow.csv"), index=False, encoding="utf-8-sig")
            notes_df.to_csv(path.with_suffix(".notes.csv"), index=False, encoding="utf-8-sig")
            path.touch()


def _curate_row(row: dict) -> dict:
    curated = {
        column: _as_text(row.get(column)) for column in REQUIRED_METADATA_COLUMNS
    }
    curated["document_id"] = _as_text(row.get("document_id") or row.get("id"))
    curated["title"] = _as_text(row.get("title"))
    curated["doi"] = _as_text(row.get("doi"))
    curated["pmid"] = _as_text(row.get("pmid"))
    curated["pmcid"] = _as_text(row.get("pmcid"))
    curated["abstract"] = _as_text(row.get("abstract") or row.get("summary"))
    curated["snippet"] = _as_text(row.get("snippet"))
    curated["summary"] = _as_text(row.get("summary"))
    curated["original_url"] = _as_text(row.get("original_url") or row.get("url"))
    curated["final_url"] = _as_text(
        row.get("final_url") or row.get("resolved_url") or row.get("url")
    )
    curated["artifact_paths"] = _as_text(
        row.get("artifact_paths") or row.get("file_path")
    )
    curated["source_provider"] = _as_text(
        row.get("source_provider") or row.get("source")
    )
    curated["workstream"] = _as_text(row.get("workstream"))
    curated["capture_status"] = _as_text(row.get("capture_status") or "missing")
    curated["download_status"] = _as_text(
        row.get("download_status") or ("pdf" if row.get("file_path") else "metadata_only")
    )
    curated["extraction_status"] = _as_text(
        row.get("extraction_status") or "missing"
    )
    curated["relevance_score"] = row.get("relevance_score") or row.get("score") or ""
    curated["novelty_score"] = row.get("novelty_score") or ""
    curated["domains"] = _as_text(row.get("domains"))
    curated["outcomes"] = _as_text(row.get("outcomes"))
    curated["diet_patterns"] = _as_text(
        row.get("diet_patterns") or row.get("diet_pattern")
    )
    curated["clinical_conditions"] = _as_text(
        row.get("clinical_conditions") or row.get("clinical_condition")
    )
    curated["journal"] = _as_text(row.get("journal"))
    curated["source_institution"] = _as_text(row.get("source_institution"))
    curated["editorial_priority_score"] = row.get("editorial_priority_score") or ""
    curated["editorial_priority_tier"] = _as_text(
        row.get("editorial_priority_tier")
    )

    document_key, document_key_type = _compute_document_key(curated)
    curated["document_key"] = document_key
    curated["document_key_type"] = document_key_type
    curated["doi_normalized"] = _normalize_doi(curated.get("doi"))
    curated["url_normalized"] = _normalize_url(
        curated.get("final_url") or curated.get("original_url")
    )
    curated["title_normalized"] = _normalize_title(curated.get("title"))
    curated["year_normalized"] = _normalize_year(curated.get("year"))
    curated["workstream_list"] = curated.get("workstream", "")
    curated["has_full_text"] = _has_full_text(curated)
    curated["is_metadata_only"] = not curated["has_full_text"]
    curated["is_prioritized"] = _is_prioritized(curated)
    return curated


def _rank_row(row: dict) -> tuple[int, int, float, float, int, str]:
    try:
        score = float(row.get("relevance_score") or 0)
    except Exception:
        score = 0.0
    try:
        editorial_score = float(row.get("editorial_priority_score") or 0)
    except Exception:
        editorial_score = 0.0
    try:
        year = int(row.get("year_normalized") or 0)
    except Exception:
        year = 0
    return (
        int(bool(row.get("has_full_text"))),
        int(bool(row.get("is_prioritized"))),
        editorial_score,
        score,
        year,
        _as_text(row.get("title")),
    )


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = ""
    return out[columns]


def _build_unique_documents(curated_rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in curated_rows:
        key = _as_text(row.get("document_key")) or _hash_fallback(row)
        groups.setdefault(key, []).append(row)

    unique_rows: list[dict] = []
    for key, rows in groups.items():
        best = sorted(rows, key=_rank_row, reverse=True)[0]
        item = {column: best.get(column, "") for column in UNIQUE_DOCUMENT_COLUMNS}
        item["document_key"] = key
        item["document_key_type"] = best.get("document_key_type", "")
        item["workstreams"] = "; ".join(
            sorted(
                {
                    _as_text(row.get("workstream"))
                    for row in rows
                    if _as_text(row.get("workstream"))
                }
            )
        )
        item["document_ids"] = "; ".join(
            sorted(
                {
                    _as_text(row.get("document_id"))
                    for row in rows
                    if _as_text(row.get("document_id"))
                }
            )
        )
        item["source_occurrences"] = len(rows)
        item["has_full_text"] = any(bool(row.get("has_full_text")) for row in rows)
        item["is_metadata_only"] = not item["has_full_text"]
        item["is_prioritized"] = any(bool(row.get("is_prioritized")) for row in rows)
        unique_rows.append(item)

    return sorted(unique_rows, key=_rank_row, reverse=True)


def curate_outputs(rows: list[dict], output_dir: Path) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    curated_rows = [_curate_row(row) for row in rows]
    curated_df = pd.DataFrame(curated_rows)
    if curated_df.empty:
        curated_df = pd.DataFrame(columns=CURATED_METADATA_COLUMNS)
    else:
        curated_df = _ensure_columns(curated_df, CURATED_METADATA_COLUMNS)

    _write_csv_aliases(
        curated_df,
        output_dir,
        CURATED_OUTPUT_ALIASES["curated_metadata_csv"],
    )
    _write_excel_aliases(
        curated_df,
        output_dir,
        CURATED_OUTPUT_ALIASES["curated_metadata_xlsx"],
    )

    unique_rows = _build_unique_documents(curated_rows)
    unique_df = pd.DataFrame(unique_rows)
    if unique_df.empty:
        unique_df = pd.DataFrame(columns=UNIQUE_DOCUMENT_COLUMNS)
    else:
        unique_df = _ensure_columns(unique_df, UNIQUE_DOCUMENT_COLUMNS)

    _write_csv_aliases(
        unique_df,
        output_dir,
        CURATED_OUTPUT_ALIASES["unique_documents_csv"],
    )
    _write_excel_aliases(
        unique_df,
        output_dir,
        CURATED_OUTPUT_ALIASES["unique_documents_xlsx"],
    )

    top_df = unique_df.head(100).copy()
    if not top_df.empty:
        top_df = _ensure_columns(top_df, TOP_A1_OPERATIONAL_COLUMNS)
    else:
        top_df = pd.DataFrame(columns=TOP_A1_OPERATIONAL_COLUMNS)
    _write_excel_aliases(
        top_df,
        output_dir,
        CURATED_OUTPUT_ALIASES["top_operational_xlsx"],
    )

    workstream_rows = []
    for row in curated_rows:
        workstream_rows.append(
            {
                "document_key": row.get("document_key", ""),
                "document_id": row.get("document_id", ""),
                "workstream": row.get("workstream", ""),
                "source_provider": row.get("source_provider", ""),
                "title": row.get("title", ""),
                "year": row.get("year", ""),
                "download_status": row.get("download_status", ""),
                "extraction_status": row.get("extraction_status", ""),
                "is_prioritized": row.get("is_prioritized", False),
            }
        )

    workstream_df = pd.DataFrame(workstream_rows)
    if workstream_df.empty:
        workstream_df = pd.DataFrame(columns=WORKSTREAM_MAP_COLUMNS)
    else:
        workstream_df = _ensure_columns(workstream_df, WORKSTREAM_MAP_COLUMNS)
    _write_csv_aliases(
        workstream_df,
        output_dir,
        CURATED_OUTPUT_ALIASES["workstream_map_csv"],
    )
    _write_excel_aliases(
        workstream_df,
        output_dir,
        CURATED_OUTPUT_ALIASES["workstream_map_xlsx"],
    )

    qa_summary_df = _build_qa_summary_df(curated_df, unique_df)
    duplicate_summary_df = _build_duplicate_summary_df(unique_df)
    missing_by_workstream_df = _build_missing_by_workstream_df(curated_df)
    _write_qa_report(
        output_dir,
        qa_summary_df,
        duplicate_summary_df,
        missing_by_workstream_df,
    )

    prisma_df = _build_prisma_df(curated_df, unique_df)
    prisma_notes_df = _build_prisma_notes_df()
    _write_prisma_report(output_dir, prisma_df, prisma_notes_df)

    summary = {
        "input_rows": len(rows),
        "curated_rows": len(curated_rows),
        "unique_documents": len(unique_rows),
        "metadata_only_documents": _count_truthy(unique_df["is_metadata_only"]) if not unique_df.empty else 0,
        "prioritized_documents": _count_truthy(unique_df["is_prioritized"]) if not unique_df.empty else 0,
        "canonical_outputs": [
            "10_curated/NUTEV_METADATA_CURATED.csv",
            "10_curated/NUTEV_METADATA_CURATED.xlsx",
            "10_curated/NUTEV_DOCUMENTS_UNIQUE.csv",
            "10_curated/NUTEV_DOCUMENTS_UNIQUE.xlsx",
            "10_curated/NUTEV_DOCUMENT_WORKSTREAM_MAP.csv",
            "10_curated/NUTEV_DOCUMENT_WORKSTREAM_MAP.xlsx",
            "10_curated/NUTEV_QA_REPORT.xlsx",
            "10_curated/NUTEV_PRISMA_FLOW_CORRIGIDO.xlsx",
        ],
    }

    (output_dir / "curation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary
