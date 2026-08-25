#!/usr/bin/env python3
"""Article 1 PubMed PILOT runner.

Scientific status: PILOT / QA only. Outputs MUST NOT feed PRISMA denominators.
Captures PubMed ESearch translation/warnings, counts, sentinel recovery and
prospectively defined noise samples for B-NORM-PUBMED v0.5 and
C-STRUCT-PUBMED v0.3.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

OUT = Path(os.environ.get("A1_PILOT_OUT", "a1_pubmed_pilot_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "NutEV-A1-Pilot/2026-08-25 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)",
    "Accept": "application/json,text/plain,*/*",
})

CORE_B = '("Diet"[Mesh] OR "Nutrition Policy"[Mesh] OR "Nutrition Therapy"[Mesh] OR "Diet Therapy"[Mesh] OR diet*[tiab] OR dietary[tiab] OR nutrition*[tiab] OR "medical nutrition therapy"[tiab] OR "nutrition care"[tiab] OR "dietary care"[tiab] OR "healthy eating"[tiab] OR "dietary pattern*"[tiab])'
NORM_B = '(guideline[pt] OR "practice guideline"[pt] OR guideline*[tiab] OR "clinical practice guideline*"[tiab] OR consensus[tiab] OR "consensus statement*"[tiab] OR "position statement*"[tiab] OR "scientific statement*"[tiab] OR "professional statement*"[tiab] OR "expert consensus"[tiab] OR "clinical guidance"[tiab] OR advisory[tiab] OR "standards of care"[tiab] OR "practice standard*"[tiab] OR "professional standard*"[tiab] OR "clinical recommendation*"[tiab] OR "practice recommendation*"[tiab] OR recommendation*[ti])'
RESCUE_B = '(guideline[pt] OR "practice guideline"[pt] OR guideline*[ti] OR "clinical practice guideline*"[ti] OR consensus[ti] OR "consensus statement*"[ti] OR "position statement*"[ti] OR "scientific statement*"[ti] OR "professional statement*"[ti] OR "standards of care"[ti])'
EXCL_B = '(hasabstract OR comment[pt] OR editorial[pt] OR letter[pt] OR "published erratum"[pt])'

B = {
    "#1": CORE_B,
    "#2": NORM_B,
    "#3": f"({CORE_B}) AND ({NORM_B})",
    "#4": RESCUE_B,
    "#5": EXCL_B,
}
B["#6"] = f"({B['#4']}) NOT ({B['#5']})"
B["#7"] = f"({B['#3']}) OR ({B['#6']})"
B_RESCUE_ONLY = f"({B['#6']}) NOT ({B['#3']})"

C1 = '("Diet"[Mesh] OR "Nutrition Therapy"[Mesh] OR "Diet Therapy"[Mesh] OR diet*[tiab] OR dietary[tiab] OR nutrition*[tiab] OR "medical nutrition therapy"[tiab] OR "nutrition care"[tiab] OR "dietary care"[tiab] OR "healthy eating"[tiab] OR "dietary pattern*"[tiab])'
C2 = '(framework*[tiab] OR "conceptual framework*"[tiab] OR "theoretical framework*"[tiab] OR "clinical decision framework*"[tiab] OR "nutrition care framework*"[tiab] OR "practice framework*"[tiab] OR "model of care"[tiab] OR "care model*"[tiab] OR "nutrition care process"[tiab] OR "nutrition care model*"[tiab] OR "nutrition care pathway*"[tiab] OR "clinical pathway*"[tiab] OR "care pathway*"[tiab] OR "nutrition pathway*"[tiab] OR "clinical protocol*"[tiab] OR "care protocol*"[tiab] OR toolkit*[tiab] OR algorithm*[tiab] OR "practice standard*"[tiab] OR "professional standard*"[tiab] OR "scope of practice"[tiab] OR "professional role*"[tiab] OR "interprofessional care"[tiab] OR "diet prescription*"[tiab] OR "dietary prescription*"[tiab] OR "nutrition prescription*"[tiab] OR "food prescription*"[tiab] OR "meal plan*"[tiab] OR "patient care planning"[tiab])'
C3 = '("Health Literacy"[Mesh] OR "Cooking"[Mesh] OR "food literacy"[tiab] OR "nutrition literacy"[tiab] OR "culinary literacy"[tiab] OR "food skill*"[tiab] OR "cooking skill*"[tiab] OR "meal planning skill*"[tiab] OR "food competenc*"[tiab] OR "culinary competenc*"[tiab] OR "food agency"[tiab] OR "food resource management"[tiab] OR "meal preparation skill*"[tiab] OR "shopping skill*"[tiab])'
C4 = '(framework*[tiab] OR model*[tiab] OR standard*[tiab] OR guideline*[tiab])'
C6 = '("Professional Competence"[Mesh] OR "Clinical Competence"[Mesh] OR "nutrition competenc*"[tiab] OR "dietitian competenc*"[tiab] OR "nutritionist competenc*"[tiab] OR "clinical nutrition skill*"[tiab] OR "competency framework*"[tiab] OR "professional framework*"[tiab] OR "practice standard*"[tiab] OR "scope of competence"[tiab] OR "nutrition counseling skill*"[tiab])'
C7 = '(framework*[tiab] OR standard*[tiab] OR guideline*[tiab] OR "scope of practice"[tiab] OR "scope of competence"[tiab])'
C9A = '(implement*[tiab] OR adoption[tiab] OR uptake[tiab] OR integration[tiab] OR sustain*[tiab] OR "scale-up"[tiab] OR fidelity[tiab] OR reach[tiab])'
C9B = '(feasibility[tiab] OR acceptability[tiab] OR monitoring[tiab] OR "implementation strateg*"[tiab] OR "implementation framework*"[tiab] OR "implementation guide*"[tiab] OR audit[tiab] OR feedback[tiab] OR "quality improvement"[tiab])'
C10 = '(framework*[tiab] OR model*[tiab] OR strateg*[tiab] OR guide*[tiab] OR toolkit*[tiab] OR blueprint*[tiab])'
C12 = '("dietary pattern*"[tiab] OR "food pattern*"[tiab] OR "healthy eating pattern*"[tiab] OR "dietary approach*"[tiab] OR "dietary strateg*"[tiab] OR "eating pattern*"[tiab] OR "meal pattern*"[tiab] OR "dietary model*"[tiab] OR "food-based approach*"[tiab])'
C13 = '(guideline*[tiab] OR framework*[tiab] OR model*[tiab] OR prescription*[tiab] OR recommendation*[tiab])'

C = {
    "#1": C1,
    "#2": C2,
    "#3": C3,
    "#4": C4,
    "#5": f"({C3}) AND ({C4})",
    "#6": C6,
    "#7": C7,
    "#8": f"({C6}) AND ({C7})",
    "#9A": C9A,
    "#9B": C9B,
    "#10": C10,
    "#11": f"(({C9A}) OR ({C9B})) AND ({C10})",
    "#12": C12,
    "#13": C13,
    "#14": f"({C12}) AND ({C13})",
}
C["#15"] = f"({C['#2']}) OR ({C['#5']}) OR ({C['#8']}) OR ({C['#11']}) OR ({C['#14']})"
C["#16"] = f"({C['#1']}) AND ({C['#15']})"

C_BRANCHES = {
    "F4_F7": f"({C['#1']}) AND ({C['#2']})",
    "F5A": f"({C['#1']}) AND ({C['#5']})",
    "F5B": f"({C['#1']}) AND ({C['#8']})",
    "F6": f"({C['#1']}) AND ({C['#11']})",
    "F3": f"({C['#1']}) AND ({C['#14']})",
}

SENTINELS = [
    {"id":"NORM-018","label":"ACLM Lifestyle Interventions 2025","locator":"40546761[pmid]","b_norm_pubmed":"ESPERADA"},
    {"id":"NORM-040","label":"Brazilian obesity/CVD guideline 2025","locator":"PMC12625227[pmc]","b_norm_pubmed":"ESPERADA"},
    {"id":"NORM-044","label":"KDA/KNS SSB/ASB consensus 2026","locator":"PMC12813387[pmc]","b_norm_pubmed":"ESPERADA"},
    {"id":"NORM-046","label":"Diabetes Canada Remission T2D 2022","locator":"36567079[pmid]","b_norm_pubmed":"A TESTAR"},
    {"id":"NORM-049","label":"Obesity Canada Adult CPG living guideline","locator":None,"b_norm_pubmed":"NÃO ESSENCIAL"},
    {"id":"NORM-051","label":"AACE obesity/ABCD algorithm 2025","locator":"10.1016/j.eprac.2025.07.017[aid]","b_norm_pubmed":"A TESTAR"},
    {"id":"NORM-056","label":"GLP-1 nutritional/lifestyle consensus","locator":"10.1016/j.obpill.2025.100228[aid]","b_norm_pubmed":"ESPERADA"},
    {"id":"NORM-057","label":"Prevention of Obesity among Adults guideline 2025","locator":"10.1159/000546415[aid]","b_norm_pubmed":"A TESTAR"},
    {"id":"NORM-035","label":"French multisociety dyslipidemia consensus 2026","locator":"10.1016/j.acvd.2026.01.001[aid]","b_norm_pubmed":"A TESTAR"},
    {"id":"NORM-059","label":"Joint Advisory GLP-1 nutrition priorities 2025","locator":"10.1016/j.ajcnut.2025.04.023[aid]","b_norm_pubmed":"A TESTAR"},
    {"id":"NORM-060","label":"ADA Standards of Care 2026 obesity/weight","locator":"10.2337/dc26-S008[aid]","b_norm_pubmed":"ESPERADA"},
    {"id":"NORM-061","label":"Academy Diabetes T1/T2 EBNPG 2015","locator":None,"b_norm_pubmed":"NÃO ESSENCIAL"},
    {"id":"NORM-062","label":"Academy Adult Weight Management EBPG 2022","locator":"10.1016/j.jand.2022.11.014[aid]","b_norm_pubmed":"A TESTAR"},
    {"id":"NORM-063","label":"AIIMS-DST full obesity guideline 2022","locator":"10.4103/jfmpc.jfmpc_51_22[aid]","b_norm_pubmed":"ESPERADA"},
    {"id":"NORM-064","label":"Japanese CPG Diabetes JDS 2024","locator":None,"b_norm_pubmed":"NÃO ESSENCIAL"},
    {"id":"NORM-065","label":"ADA/EASD hyperglycemia T2D 2022","locator":"10.2337/dci22-0034[aid]","b_norm_pubmed":"ESPERADA"},
]


def _params(extra: dict[str, Any]) -> dict[str, Any]:
    p = {"db": "pubmed", "retmode": "json", "tool": "nutev_a1_pilot"}
    p.update(extra)
    email = os.environ.get("NCBI_EMAIL") or os.environ.get("ENTREZ_EMAIL")
    key = os.environ.get("NCBI_API_KEY")
    if email:
        p["email"] = email
    if key:
        p["api_key"] = key
    return p


def _request(endpoint: str, params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    url = f"{BASE}/{endpoint}"
    last: Exception | None = None
    for attempt in range(1, 5):
        try:
            time.sleep(0.13 if os.environ.get("NCBI_API_KEY") else 0.40)
            r = SESSION.get(url, params=_params(params), timeout=(10, 90))
            r.raise_for_status()
            return r.json(), r.url
        except Exception as exc:
            last = exc
            if attempt < 4:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"NCBI request failed after retries: {last}")


def esearch(term: str, retmax: int = 0, sort: str | None = None) -> dict[str, Any]:
    payload, resolved_url = _request("esearch.fcgi", {
        "term": term,
        "retmax": retmax,
        **({"sort": sort} if sort else {}),
    })
    result = payload.get("esearchresult", {})
    return {
        "query": term,
        "query_sha256": hashlib.sha256(term.encode()).hexdigest(),
        "count": int(result.get("count") or 0),
        "idlist": [str(x) for x in result.get("idlist", [])],
        "querytranslation": result.get("querytranslation"),
        "translationset": result.get("translationset"),
        "translationstack": result.get("translationstack"),
        "warninglist": result.get("warninglist"),
        "errorlist": result.get("errorlist"),
        "resolved_url": resolved_url,
        "raw_esearchresult": result,
    }


def esummary(pmids: list[str]) -> list[dict[str, Any]]:
    if not pmids:
        return []
    payload, _ = _request("esummary.fcgi", {"id": ",".join(pmids)})
    result = payload.get("result", {})
    rows: list[dict[str, Any]] = []
    for pmid in pmids:
        item = result.get(pmid, {}) or {}
        ids = {str(x.get("idtype")): str(x.get("value")) for x in item.get("articleids", []) if isinstance(x, dict)}
        rows.append({
            "pmid": pmid,
            "title": item.get("title"),
            "pubdate": item.get("pubdate"),
            "source": item.get("source"),
            "pubtype": item.get("pubtype"),
            "doi": ids.get("doi"),
            "pmc": ids.get("pmc"),
        })
    return rows


def write_json(name: str, obj: Any) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run_counts(label: str, queries: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line, query in queries.items():
        print(f"[{label}] {line}", flush=True)
        out[line] = esearch(query)
    return out


def run_sentinels(final_query: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in SENTINELS:
        row = dict(s)
        locator = s["locator"]
        if not locator:
            row.update({"pubmed_resolvable": False, "recovered_by_b_norm_v0_5": None, "reason": "No PubMed locator required/available in frozen sentinel map"})
            out.append(row)
            continue
        resolve = esearch(locator, retmax=5)
        pmids = resolve["idlist"]
        test = esearch(f"({final_query}) AND ({locator})", retmax=5)
        row.update({
            "pubmed_resolvable": bool(pmids),
            "resolved_pmids": pmids,
            "recovered_by_b_norm_v0_5": bool(test["count"]),
            "intersection_count": test["count"],
            "intersection_pmids": test["idlist"],
            "locator_translation": resolve.get("querytranslation"),
            "intersection_translation": test.get("querytranslation"),
            "intersection_warnings": test.get("warninglist"),
        })
        out.append(row)
    return out


def run_rescue_sample() -> dict[str, Any]:
    search = esearch(B_RESCUE_ONLY, retmax=20, sort="pub_date")
    return {"rule":"#6 NOT #3; first 20 by publication date descending; no manual substitution", "search":search, "records":esummary(search["idlist"])}


def run_c_samples() -> dict[str, Any]:
    out: dict[str, Any] = {}
    names = list(C_BRANCHES)
    for name in names:
        q = C_BRANCHES[name]
        others = [C_BRANCHES[n] for n in names if n != name]
        exclusive_q = f"({q}) NOT ({' OR '.join(f'({x})' for x in others)})"
        ex = esearch(exclusive_q, retmax=10, sort="pub_date")
        ids = list(ex["idlist"])
        source = "exclusive"
        supplement = None
        if len(ids) < 10:
            full = esearch(q, retmax=10, sort="pub_date")
            for pmid in full["idlist"]:
                if pmid not in ids:
                    ids.append(pmid)
                if len(ids) == 10:
                    break
            supplement = full
            source = "exclusive_then_branch_fill"
        out[name] = {
            "rule":"up to 10 by publication date descending; prioritize branch-exclusive records when reproducible; record overlap",
            "branch_query": q,
            "exclusive_search": ex,
            "supplement_search": supplement,
            "sampling_mode": source,
            "records": esummary(ids[:10]),
        }
    return out


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    manifest = {
        "scientific_status":"PILOT_QA_NOT_PRISMA",
        "article":"Article 1 scoping review — FBDG/normative operationalization",
        "started_at_utc":started,
        "strategy_versions":{"B_NORM_PUBMED":"v0.5","C_STRUCT_PUBMED":"v0.3"},
        "git_sha":os.environ.get("GITHUB_SHA"),
        "git_ref":os.environ.get("GITHUB_REF"),
        "workflow":os.environ.get("GITHUB_WORKFLOW"),
        "run_id":os.environ.get("GITHUB_RUN_ID"),
        "runner":"GitHub Actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "local",
        "guardrail":"Do not import these counts or records into formal PRISMA. Re-run formal searches from zero only after GF-10 authorization.",
    }
    write_json("manifest.json", manifest)
    try:
        b_counts = run_counts("B-NORM v0.5", B)
        write_json("b_norm_v0_5_counts_search_details.json", b_counts)
        rescue = run_rescue_sample()
        write_json("b_norm_v0_5_rescue_only_sample.json", rescue)
        sentinels = run_sentinels(B["#7"])
        write_json("b_norm_v0_5_sentinels.json", sentinels)

        c_counts = run_counts("C-STRUCT v0.3", C)
        write_json("c_struct_v0_3_counts_search_details.json", c_counts)
        c_samples = run_c_samples()
        write_json("c_struct_v0_3_branch_samples.json", c_samples)

        expected = [x for x in sentinels if x["b_norm_pubmed"] == "ESPERADA" and x.get("pubmed_resolvable")]
        summary = {
            "b_norm_counts": {k:v["count"] for k,v in b_counts.items()},
            "c_struct_counts": {k:v["count"] for k,v in c_counts.items()},
            "sentinel_pubmed_expected_n": len(expected),
            "sentinel_pubmed_expected_recovered_n": sum(bool(x.get("recovered_by_b_norm_v0_5")) for x in expected),
            "sentinel_expected_misses": [x["id"] for x in expected if not x.get("recovered_by_b_norm_v0_5")],
            "all_resolvable_sentinels": [{"id":x["id"],"expected":x["b_norm_pubmed"],"recovered":x.get("recovered_by_b_norm_v0_5"),"pmids":x.get("resolved_pmids",[])} for x in sentinels if x.get("pubmed_resolvable")],
            "rescue_only_sample_n": len(rescue["records"]),
            "c_branch_sample_n": {k:len(v["records"]) for k,v in c_samples.items()},
            "completed_at_utc":datetime.now(timezone.utc).isoformat(),
            "scientific_status":"PILOT_QA_NOT_PRISMA",
        }
        write_json("summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        error = {"error":repr(exc),"failed_at_utc":datetime.now(timezone.utc).isoformat(),"scientific_status":"PILOT_QA_NOT_PRISMA"}
        write_json("ERROR.json", error)
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
