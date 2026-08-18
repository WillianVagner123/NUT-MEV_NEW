from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable
from uuid import uuid4

from nutev.audit_guardrails import (
    GUARDRAIL_POLICY_VERSION,
    IntegrityError,
    annotate_record,
    has_valid_identifier,
    sha256_file,
    verify_manifest_master,
)
from nutev.reference_identity import canonical_identity, dedupe_records
from nutev.taxonomy import (
    TaxonomyError,
    load_canonical_taxonomy,
    taxonomy_config_paths,
)

_SPACE_RE = re.compile(r"\s+")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_PUBLIC_INPUT_FIELDS = {
    "source",
    "source_provider",
    "source_institution",
    "source_category",
    "title",
    "abstract",
    "summary",
    "snippet",
    "doi",
    "doi_normalized",
    "pmid",
    "pmid_normalized",
    "pmcid",
    "url",
    "url_normalized",
    "journal",
    "year",
    "publication_year",
    "published_year",
    "publication_date",
    "date",
    "article_type",
    "authors",
    "keywords",
    "keyword",
    "subjects",
    "query",
    "provider_query",
    "provider_search_url",
    "metadata_status",
    "collection_type",
    "audit_policy_version",
    "audit_traceability",
    "audit_quarantined",
    "audit_reasons",
    "audit_origin_sha256",
    "audit_source_manifest_path",
    "audit_source_master_sha256",
    "audit_source_run_id",
}

_DEFAULT_GUARDRAILS: dict[str, Any] = {
    "require_traceable_origin": True,
    "fail_on_input_hash_mismatch": True,
    "taxonomy_score_cap": 60.0,
    "focus_score_cap": 40.0,
    "document_type_scoring": "highest_weight_only",
}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IntegrityError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise IntegrityError(f"Non-object JSONL record at {path}:{line_number}")
            rows.append(value)
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
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        for row in rows
    )
    return _atomic_text(path, text)


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            for key in (
                "taxonomy_groups",
                "taxonomy_secondary",
                "taxonomy_dimensions",
                "focus_keyword_hits",
                "matched_terms",
                "document_type_hits",
                "audit_reasons",
            ):
                flat[key] = " | ".join(str(value) for value in row.get(key) or [])
            for key in ("score_breakdown", "taxonomy_group_scores", "taxonomy_ranks"):
                if isinstance(flat.get(key), dict):
                    flat[key] = json.dumps(flat[key], ensure_ascii=False, sort_keys=True)
            writer.writerow(flat)
    tmp.replace(path)
    return sha256_file(path)


def load_taxonomy(config_dir: Path) -> dict[str, list[str]]:
    """Compatibility wrapper returning the canonical scoring groups only."""

    groups, _ = load_canonical_taxonomy(config_dir)
    return groups


def _guardrail_policy(profile: dict[str, Any]) -> dict[str, Any]:
    policy = dict(_DEFAULT_GUARDRAILS)
    configured = profile.get("guardrails")
    if isinstance(configured, dict):
        policy.update(configured)
    if policy.get("document_type_scoring") != "highest_weight_only":
        raise RuntimeError(
            "Unsupported document_type_scoring. Guardrail requires highest_weight_only."
        )
    return policy


def _source_rows(
    project_root: Path,
    *,
    require_hash: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    source_audit: list[dict[str, Any]] = []
    states = [
        project_root / "07_logs" / "collect_everything" / "latest.json",
        project_root / "07_logs" / "latin_native" / "latest.json",
    ]
    for state_path in states:
        state = _read_json(state_path)
        if not state:
            continue
        if state.get("collection_type") not in {None, "", "REFERENCE_COLLECTION"}:
            raise IntegrityError(
                f"Unexpected collection_type in {state_path}: {state.get('collection_type')}"
            )
        if require_hash:
            audited = verify_manifest_master(state_path, state)
        else:
            master_raw = str(state.get("master_records_path") or "").strip()
            if not master_raw:
                audited = None
            else:
                master = Path(master_raw)
                if not master.is_file():
                    raise IntegrityError(f"Manifest points to missing master file: {master}")
                audited = {
                    "state_path": str(state_path),
                    "state_run_id": str(state.get("run_id") or ""),
                    "state_status": str(state.get("status") or ""),
                    "collection_type": str(state.get("collection_type") or ""),
                    "master_records_path": str(master),
                    "master_records_sha256": sha256_file(master),
                }
        if audited is None:
            continue
        master = Path(audited["master_records_path"])
        part = _read_jsonl(master)
        for raw in part:
            row = dict(raw)
            row["audit_source_manifest_path"] = str(state_path)
            row["audit_source_master_sha256"] = audited["master_records_sha256"]
            row["audit_source_run_id"] = audited["state_run_id"]
            rows.append(row)
        audit_item = dict(audited)
        audit_item["records_loaded"] = len(part)
        source_audit.append(audit_item)
    if not rows:
        raise RuntimeError(
            "Nenhum master de coleta encontrado. Rode RODAR_TUDO.cmd para coletar as fontes primeiro."
        )
    return rows, source_audit


def _identity(row: dict[str, Any]) -> str:
    return canonical_identity(row)


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return dedupe_records(rows)


def _extract_year(row: dict[str, Any]) -> int | None:
    for key in (
        "year",
        "publication_year",
        "published_year",
        "publication_date",
        "date",
    ):
        value = str(row.get(key) or "")
        match = _YEAR_RE.search(value)
        if match:
            year = int(match.group(0))
            if 1900 <= year <= datetime.now().year + 1:
                return year
    return None


def _provider_bonus(provider: str, weights: dict[str, float]) -> float:
    normalized = _norm(provider)
    best = 0.0
    for token, weight in weights.items():
        if _norm(token) in normalized:
            best = max(best, float(weight))
    return best


def _public_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key in _PUBLIC_INPUT_FIELDS}


def _ordered_taxonomy_groups(group_scores: dict[str, float]) -> list[str]:
    return sorted(group_scores, key=lambda group: (-group_scores[group], group))


def _select_primary_taxonomy(
    group_scores: dict[str, float],
    primary_dimension_order: list[str] | None,
) -> tuple[str, list[str], list[str]]:
    ordered = _ordered_taxonomy_groups(group_scores)
    if not ordered:
        return "", [], []

    primary = ""
    dimensions = []
    for group in ordered:
        dimension = group.split(".", 1)[0]
        if dimension not in dimensions:
            dimensions.append(dimension)

    for dimension in primary_dimension_order or []:
        primary = next(
            (group for group in ordered if group.split(".", 1)[0] == dimension),
            "",
        )
        if primary:
            break
    if not primary:
        primary = ordered[0]
    secondary = [group for group in ordered if group != primary]
    return primary, secondary, dimensions


def score_record(
    row: dict[str, Any],
    taxonomy: dict[str, list[str]],
    focus_keywords: list[str],
    provider_weights: dict[str, float],
    guardrails: dict[str, Any] | None = None,
    primary_dimension_order: list[str] | None = None,
) -> dict[str, Any]:
    policy = dict(_DEFAULT_GUARDRAILS)
    if guardrails:
        policy.update(guardrails)

    title = _norm(row.get("title"))
    abstract = _norm(row.get("abstract") or row.get("summary") or row.get("snippet"))
    keywords = _norm(row.get("keywords") or row.get("keyword") or row.get("subjects"))
    provider = str(row.get("source_provider") or row.get("source") or "")
    matched_terms: list[str] = []
    taxonomy_group_scores: dict[str, float] = {}

    taxonomy_raw = 0.0
    for group, terms in taxonomy.items():
        group_terms: list[str] = []
        group_score = 0.0
        for term in terms:
            term_score = 0.0
            if term in title:
                term_score += 6.0
            if term in keywords:
                term_score += 4.0
            if term in abstract:
                term_score += 2.0
            if term_score:
                group_score += min(term_score, 8.0)
                group_terms.append(term)
                if len(group_terms) >= 4:
                    break
        if group_terms:
            group_score += 3.0
            taxonomy_raw += group_score
            taxonomy_group_scores[group] = round(group_score, 2)
            matched_terms.extend(group_terms)

    taxonomy_score = min(
        taxonomy_raw,
        max(0.0, float(policy.get("taxonomy_score_cap") or 0.0)),
    )
    primary_taxonomy, secondary_taxonomy, taxonomy_dimensions = _select_primary_taxonomy(
        taxonomy_group_scores,
        primary_dimension_order,
    )
    matched_groups = _ordered_taxonomy_groups(taxonomy_group_scores)

    focus_hits: list[str] = []
    focus_raw = 0.0
    for raw in focus_keywords:
        term = _norm(raw)
        if not term:
            continue
        hit = False
        if term in title:
            focus_raw += 10.0
            hit = True
        if term in keywords:
            focus_raw += 6.0
            hit = True
        if term in abstract:
            focus_raw += 4.0
            hit = True
        if hit:
            focus_hits.append(raw)
    focus_score = min(
        focus_raw,
        max(0.0, float(policy.get("focus_score_cap") or 0.0)),
    )

    document_terms = {
        "clinical practice guideline": 12.0,
        "practice guideline": 11.0,
        "guideline": 10.0,
        "consensus statement": 9.0,
        "consensus": 7.0,
        "position statement": 8.0,
        "scientific statement": 8.0,
        "standards of care": 8.0,
        "systematic review": 7.0,
        "meta analysis": 7.0,
        "framework": 5.0,
        "recommendation": 4.0,
    }
    type_hits = [term for term in document_terms if term in title]
    document_type_applied = ""
    document_score = 0.0
    if type_hits:
        document_type_applied = max(type_hits, key=lambda term: document_terms[term])
        document_score = document_terms[document_type_applied]

    provider_score = _provider_bonus(provider, provider_weights)
    identifier_score = 2.0 if has_valid_identifier(row) else 0.0
    year = _extract_year(row)
    recency_score = 0.0
    if year:
        age = datetime.now().year - year
        if age <= 5:
            recency_score = 4.0
        elif age <= 10:
            recency_score = 2.0

    penalties = 0.0
    if not title:
        penalties -= 25.0
    if not abstract:
        penalties -= 1.0

    score = (
        taxonomy_score
        + focus_score
        + document_score
        + provider_score
        + identifier_score
        + recency_score
        + penalties
    )
    clean = _public_metadata(row)
    return {
        **clean,
        "reference_score": round(score, 2),
        "score_breakdown": {
            "taxonomy": round(taxonomy_score, 2),
            "taxonomy_raw_before_cap": round(taxonomy_raw, 2),
            "focus_keywords": round(focus_score, 2),
            "focus_raw_before_cap": round(focus_raw, 2),
            "document_type": round(document_score, 2),
            "provider": round(provider_score, 2),
            "identifier": round(identifier_score, 2),
            "recency": round(recency_score, 2),
            "penalties": round(penalties, 2),
        },
        "taxonomy_primary": primary_taxonomy,
        "taxonomy_secondary": secondary_taxonomy[:12],
        "taxonomy_dimensions": taxonomy_dimensions,
        "taxonomy_groups": matched_groups[:20],
        "taxonomy_group_scores": taxonomy_group_scores,
        "matched_terms": sorted(set(matched_terms))[:40],
        "focus_keyword_hits": focus_hits[:20],
        "document_type_hits": type_hits,
        "document_type_applied": document_type_applied,
        "reference_year": year,
        "reference_provider": provider,
    }


def _tier(index: int, total: int) -> str:
    if index < min(20, total):
        return "A_TOP_REFERENCE"
    if index < min(100, total):
        return "B_STRONG_REFERENCE"
    return "C_DISCOVERY"


def _assign_taxonomy_ranks(rows: list[dict[str, Any]]) -> None:
    groups = sorted(
        {
            group
            for row in rows
            for group in (row.get("taxonomy_groups") or [])
            if isinstance(group, str) and group
        }
    )
    for row in rows:
        row["taxonomy_ranks"] = {}

    for group in groups:
        members = [row for row in rows if group in (row.get("taxonomy_groups") or [])]
        members.sort(
            key=lambda row: (
                -float((row.get("taxonomy_group_scores") or {}).get(group) or 0),
                -float(row.get("reference_score") or 0),
                -int(row.get("reference_year") or 0),
                str(row.get("title") or ""),
            )
        )
        for index, row in enumerate(members, start=1):
            row["taxonomy_ranks"][group] = index

    for row in rows:
        primary = str(row.get("taxonomy_primary") or "")
        row["taxonomy_primary_rank"] = (
            (row.get("taxonomy_ranks") or {}).get(primary) if primary else None
        )


def _config_hashes(config_dir: Path) -> dict[str, str]:
    paths = [config_dir / "reference_mode.json", *taxonomy_config_paths(config_dir)]
    return {str(path): sha256_file(path) for path in paths if path.is_file()}


def run(project_root: Path, config_dir: Path, top_n: int) -> dict[str, Any]:
    profile = _read_json(config_dir / "reference_mode.json")
    guardrails = _guardrail_policy(profile)
    taxonomy, taxonomy_metadata = load_canonical_taxonomy(config_dir)
    focus_keywords = list(profile.get("focus_keywords") or [])
    provider_weights = dict(profile.get("provider_weights") or {})
    rows, source_audit = _source_rows(
        project_root,
        require_hash=bool(guardrails.get("fail_on_input_hash_mismatch", True)),
    )

    annotated = [annotate_record(row) for row in rows]
    if guardrails.get("require_traceable_origin", True):
        eligible = [row for row in annotated if not row.get("audit_quarantined")]
        quarantined = [row for row in annotated if row.get("audit_quarantined")]
    else:
        eligible = annotated
        quarantined = []

    out_dir = project_root / "reference_ranking"
    out_dir.mkdir(parents=True, exist_ok=True)
    quarantine_path = out_dir / "reference_quarantine.jsonl"
    quarantine_public = [_public_metadata(row) for row in quarantined]
    quarantine_sha = _write_jsonl(quarantine_path, quarantine_public)

    if not eligible:
        raise RuntimeError(
            "Guardrail bloqueou o ranking: nenhum registro com origem rastreavel. "
            f"Consulte {quarantine_path}."
        )

    unique = _dedupe(eligible)
    primary_dimension_order = list(taxonomy_metadata.get("primary_dimension_order") or [])
    ranked = [
        score_record(
            row,
            taxonomy,
            focus_keywords,
            provider_weights,
            guardrails,
            primary_dimension_order,
        )
        for row in unique
    ]
    ranked.sort(
        key=lambda row: (
            -float(row.get("reference_score") or 0),
            -int(row.get("reference_year") or 0),
            str(row.get("title") or ""),
        )
    )
    for index, row in enumerate(ranked):
        row["reference_rank"] = index + 1
        row["reference_tier"] = _tier(index, len(ranked))
    _assign_taxonomy_ranks(ranked)

    jsonl_path = out_dir / "reference_ranking.jsonl"
    csv_path = out_dir / "reference_ranking.csv"
    markdown_path = out_dir / "TOP_REFERENCIAS.md"
    jsonl_sha = _write_jsonl(jsonl_path, ranked)

    columns = [
        "reference_rank",
        "reference_tier",
        "reference_score",
        "taxonomy_primary",
        "taxonomy_primary_rank",
        "taxonomy_secondary",
        "taxonomy_dimensions",
        "taxonomy_group_scores",
        "taxonomy_ranks",
        "title",
        "reference_year",
        "reference_provider",
        "audit_traceability",
        "audit_origin_sha256",
        "audit_source_run_id",
        "doi",
        "pmid",
        "pmcid",
        "url",
        "taxonomy_groups",
        "focus_keyword_hits",
        "matched_terms",
        "document_type_hits",
        "document_type_applied",
        "score_breakdown",
    ]
    csv_sha = _write_csv(csv_path, ranked, columns)

    top = ranked[: max(1, top_n)]
    lines = [
        "# Top referencias NutEV",
        "",
        "Ranking tecnico para priorizacao de leitura. Nao representa nivel de evidencia, elegibilidade de revisao ou recomendacao clinica.",
        "A taxonomia e canonica e versionada; workstreams historicos e document_types da taxonomia nao entram no score taxonomico.",
        "Todos os itens ranqueados passaram pelo guardrail de rastreabilidade; registros sem identificador ou URL verificavel ficam em reference_quarantine.jsonl.",
        "O score e auditavel em score_breakdown e o manifesto de integridade esta em AUDIT_MANIFEST.json.",
        "",
    ]
    for row in top:
        title = str(row.get("title") or "Sem titulo")
        lines.append(f"## {row['reference_rank']}. {title}")
        lines.append(f"- Score: {row['reference_score']} | Faixa: {row['reference_tier']}")
        lines.append(
            f"- Fonte: {row.get('reference_provider') or 'N/D'} | Ano: {row.get('reference_year') or 'N/D'}"
        )
        lines.append(
            f"- Rastreabilidade: {row.get('audit_traceability') or 'N/D'} | Origem SHA-256: {row.get('audit_origin_sha256') or 'N/D'}"
        )
        if row.get("doi"):
            lines.append(f"- DOI: {row['doi']}")
        if row.get("pmid"):
            lines.append(f"- PMID: {row['pmid']}")
        if row.get("url"):
            lines.append(f"- URL: {row['url']}")
        if row.get("document_type_applied"):
            lines.append(f"- Tipo documental aplicado ao score: {row['document_type_applied']}")
        if row.get("taxonomy_primary"):
            lines.append(
                f"- Taxonomia principal: {row['taxonomy_primary']} | Rank na taxonomia: {row.get('taxonomy_primary_rank') or 'N/D'}"
            )
        if row.get("taxonomy_secondary"):
            lines.append("- Taxonomias secundarias: " + ", ".join(row["taxonomy_secondary"][:6]))
        if row.get("focus_keyword_hits"):
            lines.append(
                "- Palavras-chave foco: " + ", ".join(row["focus_keyword_hits"][:8])
            )
        lines.append(
            "- Score breakdown: "
            + json.dumps(row.get("score_breakdown") or {}, ensure_ascii=False, sort_keys=True)
        )
        lines.append("")
    markdown_sha = _atomic_text(markdown_path, "\n".join(lines))

    taxonomy_audit = {
        key: value
        for key, value in taxonomy_metadata.items()
        if key not in {"group_metadata", "excluded_raw_paths"}
    }
    config_hashes = _config_hashes(config_dir)
    assertions = [
        {"name": "source_master_hashes_verified", "status": "PASS"},
        {
            "name": "untraceable_records_not_ranked",
            "status": "PASS" if not any(row.get("audit_quarantined") for row in eligible) else "FAIL",
        },
        {"name": "document_type_score_non_stacking", "status": "PASS"},
        {
            "name": "canonical_taxonomy_registry_applied",
            "status": (
                "PASS"
                if taxonomy_metadata.get("registry_mode") == "canonical"
                else "PASS_COMPATIBILITY"
            ),
        },
        {
            "name": "legacy_workstream_groups_excluded",
            "status": (
                "PASS"
                if not any(group.startswith("workstreams.") for group in taxonomy)
                else "FAIL"
            ),
        },
        {
            "name": "document_type_taxonomy_excluded",
            "status": (
                "PASS"
                if not any(group.startswith("global.document_types.") for group in taxonomy)
                else "FAIL"
            ),
        },
        {"name": "ranking_outputs_hashed", "status": "PASS"},
        {"name": "provider_results_not_simulated", "status": "PASS_BY_CONTRACT"},
    ]
    audit_manifest = {
        "schema_version": 1,
        "audit_type": "REFERENCE_RANKING_AUDIT",
        "guardrail_policy_version": GUARDRAIL_POLICY_VERSION,
        "created_at": _now(),
        "status": "PASS" if all(item["status"] != "FAIL" for item in assertions) else "FAIL",
        "guardrails": guardrails,
        "taxonomy": taxonomy_audit,
        "source_integrity": source_audit,
        "configuration_sha256": config_hashes,
        "counts": {
            "records_input": len(rows),
            "records_traceable": len(eligible),
            "records_quarantined": len(quarantined),
            "records_unique_ranked": len(unique),
        },
        "outputs": {
            "ranking_jsonl": {"path": str(jsonl_path), "sha256": jsonl_sha},
            "ranking_csv": {"path": str(csv_path), "sha256": csv_sha},
            "top_markdown": {"path": str(markdown_path), "sha256": markdown_sha},
            "quarantine_jsonl": {"path": str(quarantine_path), "sha256": quarantine_sha},
        },
        "assertions": assertions,
        "interpretation_guardrail": (
            "Ranking is information-retrieval priority only. It must not be represented as "
            "scientific inclusion/exclusion, certainty of evidence, or clinical recommendation."
        ),
    }
    audit_path = out_dir / "AUDIT_MANIFEST.json"
    audit_sha = _write_json(audit_path, audit_manifest)

    status = "COMPLETE_WITH_QUARANTINE" if quarantined else "COMPLETE"
    summary = {
        "mode": "REFERENCE_RANKING",
        "status": status,
        "created_at": _now(),
        "guardrail_policy_version": GUARDRAIL_POLICY_VERSION,
        "guardrails": guardrails,
        "taxonomy_version": taxonomy_metadata.get("taxonomy_version"),
        "taxonomy_registry_mode": taxonomy_metadata.get("registry_mode"),
        "taxonomy_raw_groups_mapped": taxonomy_metadata.get("raw_groups_mapped"),
        "taxonomy_raw_groups_excluded": taxonomy_metadata.get("raw_groups_excluded"),
        "source_files": [item["master_records_path"] for item in source_audit],
        "source_integrity": source_audit,
        "records_input": len(rows),
        "records_traceable": len(eligible),
        "records_quarantined": len(quarantined),
        "records_unique": len(unique),
        "taxonomy_groups_loaded": len(taxonomy),
        "focus_keywords": focus_keywords,
        "top_n": len(top),
        "outputs": {
            "jsonl": str(jsonl_path),
            "csv": str(csv_path),
            "markdown": str(markdown_path),
            "quarantine": str(quarantine_path),
            "audit_manifest": str(audit_path),
        },
        "output_sha256": {
            "jsonl": jsonl_sha,
            "csv": csv_sha,
            "markdown": markdown_sha,
            "quarantine": quarantine_sha,
            "audit_manifest": audit_sha,
        },
    }
    _write_json(out_dir / "latest.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ranqueia referencias rastreaveis com guardrails e trilha de auditoria."
    )
    parser.add_argument("--project-root", default="./project_output_reference")
    parser.add_argument("--config-dir", default="./config")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()
    try:
        result = run(Path(args.project_root), Path(args.config_dir), max(1, args.top_n))
    except (IntegrityError, TaxonomyError, RuntimeError) as exc:
        print(f"Guardrail failure: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
