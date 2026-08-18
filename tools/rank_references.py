from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

_SPACE_RE = re.compile(r"\s+")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


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
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _taxonomy_files(config_dir: Path) -> list[Path]:
    return sorted(config_dir.glob("keyword_taxonomy*.json"))


def _flatten_terms(value: Any, path: tuple[str, ...] = ()) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "version":
                continue
            child_out = _flatten_terms(child, path + (str(key),))
            for group, terms in child_out.items():
                out.setdefault(group, set()).update(terms)
    elif isinstance(value, list):
        group = ".".join(path) or "taxonomy"
        for item in value:
            if isinstance(item, str):
                term = _norm(item)
                if len(term) >= 3:
                    out.setdefault(group, set()).add(term)
            elif isinstance(item, (dict, list)):
                child_out = _flatten_terms(item, path)
                for child_group, terms in child_out.items():
                    out.setdefault(child_group, set()).update(terms)
    elif isinstance(value, str):
        term = _norm(value)
        if len(term) >= 3:
            out.setdefault(".".join(path) or "taxonomy", set()).add(term)
    return out


def load_taxonomy(config_dir: Path) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = {}
    for path in _taxonomy_files(config_dir):
        data = _read_json(path)
        for group, terms in _flatten_terms(data).items():
            merged.setdefault(group, set()).update(terms)
    return {group: sorted(terms, key=lambda term: (-len(term), term)) for group, terms in sorted(merged.items())}


def _source_rows(project_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    sources: list[str] = []
    states = [
        project_root / "07_logs" / "collect_everything" / "latest.json",
        project_root / "07_logs" / "latin_native" / "latest.json",
    ]
    for state_path in states:
        state = _read_json(state_path)
        master = Path(str(state.get("master_records_path") or ""))
        if master.is_file():
            part = _read_jsonl(master)
            rows.extend(part)
            sources.append(str(master))
    if not rows:
        raise RuntimeError("Nenhum master de coleta encontrado. Rode RODAR_TUDO.cmd para coletar as fontes primeiro.")
    return rows, sources


def _identity(row: dict[str, Any]) -> str:
    doi = _norm(row.get("doi") or row.get("doi_normalized"))
    if doi:
        return "doi:" + doi
    pmid = _norm(row.get("pmid") or row.get("pmid_normalized"))
    if pmid:
        return "pmid:" + pmid
    url = _norm(row.get("url") or row.get("url_normalized"))
    if url:
        return "url:" + url
    title = _norm(row.get("title"))
    return "title:" + title


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _identity(row)
        if not key or key == "title:":
            continue
        current = best.get(key)
        if current is None:
            best[key] = dict(row)
            continue
        current_text = str(current.get("abstract") or current.get("summary") or current.get("snippet") or "")
        new_text = str(row.get("abstract") or row.get("summary") or row.get("snippet") or "")
        if len(new_text) > len(current_text):
            best[key] = dict(row)
    return list(best.values())


def _extract_year(row: dict[str, Any]) -> int | None:
    for key in ("year", "publication_year", "published_year", "publication_date", "date"):
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


def score_record(
    row: dict[str, Any],
    taxonomy: dict[str, list[str]],
    focus_keywords: list[str],
    provider_weights: dict[str, float],
) -> dict[str, Any]:
    title = _norm(row.get("title"))
    abstract = _norm(row.get("abstract") or row.get("summary") or row.get("snippet"))
    keywords = _norm(row.get("keywords") or row.get("keyword") or row.get("subjects"))
    provider = str(row.get("source_provider") or row.get("source") or "")
    score = 0.0
    matched_groups: list[str] = []
    matched_terms: list[str] = []

    for group, terms in taxonomy.items():
        group_hit = False
        group_terms: list[str] = []
        for term in terms:
            term_score = 0.0
            if term in title:
                term_score += 6.0
            if term in keywords:
                term_score += 4.0
            if term in abstract:
                term_score += 2.0
            if term_score:
                score += min(term_score, 8.0)
                group_hit = True
                group_terms.append(term)
                if len(group_terms) >= 4:
                    break
        if group_hit:
            score += 3.0
            matched_groups.append(group)
            matched_terms.extend(group_terms)

    focus_hits: list[str] = []
    for raw in focus_keywords:
        term = _norm(raw)
        if not term:
            continue
        hit = False
        if term in title:
            score += 10.0
            hit = True
        if term in keywords:
            score += 6.0
            hit = True
        if term in abstract:
            score += 4.0
            hit = True
        if hit:
            focus_hits.append(raw)

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
    type_hits: list[str] = []
    for term, weight in document_terms.items():
        if term in title:
            score += weight
            type_hits.append(term)

    score += _provider_bonus(provider, provider_weights)
    if row.get("doi") or row.get("pmid") or row.get("pmcid"):
        score += 2.0
    year = _extract_year(row)
    if year:
        age = datetime.now().year - year
        if age <= 5:
            score += 4.0
        elif age <= 10:
            score += 2.0
    if not title:
        score -= 25.0
    if not abstract:
        score -= 1.0

    return {
        **row,
        "reference_score": round(score, 2),
        "taxonomy_groups": matched_groups[:20],
        "matched_terms": sorted(set(matched_terms))[:40],
        "focus_keyword_hits": focus_hits[:20],
        "document_type_hits": type_hits,
        "reference_year": year,
        "reference_provider": provider,
    }


def _tier(index: int, total: int) -> str:
    if index < min(20, total):
        return "A_TOP_REFERENCE"
    if index < min(100, total):
        return "B_STRONG_REFERENCE"
    return "C_DISCOVERY"


def run(project_root: Path, config_dir: Path, top_n: int) -> dict[str, Any]:
    profile = _read_json(config_dir / "reference_mode.json")
    taxonomy = load_taxonomy(config_dir)
    focus_keywords = list(profile.get("focus_keywords") or [])
    provider_weights = dict(profile.get("provider_weights") or {})
    rows, sources = _source_rows(project_root)
    unique = _dedupe(rows)
    ranked = [score_record(row, taxonomy, focus_keywords, provider_weights) for row in unique]
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

    out_dir = project_root / "reference_ranking"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "reference_ranking.jsonl"
    csv_path = out_dir / "reference_ranking.csv"
    markdown_path = out_dir / "TOP_REFERENCIAS.md"
    _write_jsonl(jsonl_path, ranked)

    columns = [
        "reference_rank",
        "reference_tier",
        "reference_score",
        "title",
        "reference_year",
        "reference_provider",
        "doi",
        "pmid",
        "pmcid",
        "url",
        "taxonomy_groups",
        "focus_keyword_hits",
        "matched_terms",
        "document_type_hits",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in ranked:
            flat = dict(row)
            for key in ("taxonomy_groups", "focus_keyword_hits", "matched_terms", "document_type_hits"):
                flat[key] = " | ".join(str(value) for value in row.get(key) or [])
            writer.writerow(flat)

    top = ranked[: max(1, top_n)]
    lines = [
        "# Top referencias NutEV",
        "",
        "Ranking tecnico por aderencia a taxonomia, palavras-chave, tipo documental, fonte e recencia.",
        "Nao e decisao de inclusao/exclusao e nao produz PRISMA.",
        "",
    ]
    for row in top:
        title = str(row.get("title") or "Sem titulo")
        lines.append(f"## {row['reference_rank']}. {title}")
        lines.append(f"- Score: {row['reference_score']} | Faixa: {row['reference_tier']}")
        lines.append(f"- Fonte: {row.get('reference_provider') or 'N/D'} | Ano: {row.get('reference_year') or 'N/D'}")
        if row.get("doi"):
            lines.append(f"- DOI: {row['doi']}")
        if row.get("pmid"):
            lines.append(f"- PMID: {row['pmid']}")
        if row.get("url"):
            lines.append(f"- URL: {row['url']}")
        if row.get("taxonomy_groups"):
            lines.append("- Taxonomia: " + ", ".join(row["taxonomy_groups"][:8]))
        if row.get("focus_keyword_hits"):
            lines.append("- Palavras-chave foco: " + ", ".join(row["focus_keyword_hits"][:8]))
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "mode": "REFERENCE_RANKING",
        "status": "COMPLETE",
        "created_at": _now(),
        "source_files": sources,
        "records_input": len(rows),
        "records_unique": len(unique),
        "taxonomy_groups_loaded": len(taxonomy),
        "focus_keywords": focus_keywords,
        "top_n": len(top),
        "outputs": {
            "jsonl": str(jsonl_path),
            "csv": str(csv_path),
            "markdown": str(markdown_path),
        },
        "scientific_review_workflow": False,
        "prisma": False,
        "screening": False,
        "press": False,
        "freeze": False,
    }
    _write_json(out_dir / "latest.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Ranqueia as melhores referencias por taxonomia e palavras-chave.")
    parser.add_argument("--project-root", default="./project_output_reference")
    parser.add_argument("--config-dir", default="./config")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()
    result = run(Path(args.project_root), Path(args.config_dir), max(1, args.top_n))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
