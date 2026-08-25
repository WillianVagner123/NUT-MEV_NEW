#!/usr/bin/env python3
"""Third Article 1 PubMed PILOT QA: B-NORM v0.7 + C-STRUCT v0.5.

Strategies were prospectively frozen in the canonical Article 1 sheet
(D-127 / 02I) before execution. Outputs are PILOT/QA only and MUST NOT feed
PRISMA denominators.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import article1_pubmed_pilot as base

OUT = Path(os.environ.get("A1_PILOT_OUT", "a1_pubmed_pilot_v3_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)


def _request_post(endpoint: str, params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    url = f"{base.BASE}/{endpoint}"
    last: Exception | None = None
    for attempt in range(1, 5):
        try:
            time.sleep(0.13 if os.environ.get("NCBI_API_KEY") else 0.40)
            r = base.SESSION.post(url, data=base._params(params), timeout=(10, 90))
            r.raise_for_status()
            return r.json(), url
        except Exception as exc:
            last = exc
            if attempt < 4:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"NCBI POST request failed after retries: {last}")


base._request = _request_post

# B-NORM-PUBMED v0.7 (exact D-127 / 02I frozen string)
B1 = '(diet*[ti] OR dietary[ti] OR nutrition*[ti] OR "healthy eating"[ti] OR "medical nutrition therapy"[ti] OR "nutrition care"[ti] OR "dietary care"[ti] OR "dietary pattern*"[ti] OR "food-based"[ti] OR "food based"[ti] OR "Nutrition Therapy"[Majr] OR "Diet Therapy"[Majr] OR "Nutrition Policy"[Majr] OR ((diet*[tiab] OR dietary[tiab] OR "healthy eating"[tiab] OR "medical nutrition therapy"[tiab] OR "nutrition care"[tiab] OR "dietary care"[tiab] OR "dietary pattern*"[tiab] OR "food-based"[tiab] OR "food based"[tiab]) AND (nutrition*[tiab] OR recommend*[tiab] OR prescrib*[tiab] OR counsel*[tiab] OR guideline*[tiab])))'
B2 = '(guideline[pt] OR "practice guideline"[pt] OR guideline*[ti] OR consensus[ti] OR "consensus statement*"[ti] OR "position statement*"[ti] OR "scientific statement*"[ti] OR "professional statement*"[ti] OR "expert consensus"[ti] OR "clinical guidance"[ti] OR "standards of care"[ti] OR "practice standard*"[ti] OR "professional standard*"[ti] OR "clinical recommendation*"[ti] OR "practice recommendation*"[ti] OR "dietary recommendation*"[ti])'
B = {"#1": B1, "#2": B2, "#3": f"({B1}) AND ({B2})"}

# C-STRUCT-PUBMED v0.5 (exact D-127 / 02I frozen strings)
C1 = '("Diet"[Mesh] OR "Nutrition Therapy"[Mesh] OR "Diet Therapy"[Mesh] OR diet*[tiab] OR dietary[tiab] OR nutrition*[tiab] OR "medical nutrition therapy"[tiab] OR "nutrition care"[tiab] OR "dietary care"[tiab] OR "healthy eating"[tiab] OR "dietary pattern*"[tiab] OR "food-based"[tiab] OR "food based"[tiab])'
C2A = '("nutrition care process"[tiab] OR "nutrition care model*"[tiab] OR "nutrition care framework*"[tiab] OR "nutrition care pathway*"[tiab] OR "nutrition pathway*"[tiab] OR "medical nutrition therapy"[tiab] OR "diet prescription*"[tiab] OR "dietary prescription*"[tiab] OR "nutrition prescription*"[tiab] OR "food prescription*"[tiab] OR "meal plan*"[tiab] OR "nutrition counseling"[tiab] OR "nutrition counselling"[tiab] OR "dietetic care"[tiab] OR "dietitian-led"[tiab] OR "dietitian led"[tiab] OR "scope of practice"[tiab] OR "professional standard*"[tiab] OR "practice standard*"[tiab] OR "clinical decision framework*"[tiab] OR "model of care"[tiab] OR "lifestyle medicine"[tiab])'
C2B = '(framework*[ti] OR model*[ti] OR process*[ti] OR pathway*[ti] OR standard*[ti] OR guideline*[ti] OR consensus[ti] OR statement*[ti] OR protocol*[ti] OR "practice point*"[ti] OR "scope of practice"[ti] OR "lifestyle medicine"[ti])'
C3 = '("food literacy"[tiab] OR "nutrition literacy"[tiab] OR "culinary literacy"[tiab] OR "food skill*"[tiab] OR "cooking skill*"[tiab] OR "meal planning skill*"[tiab] OR "food competenc*"[tiab] OR "culinary competenc*"[tiab] OR "food agency"[tiab] OR "food resource management"[tiab] OR "meal preparation skill*"[tiab] OR "shopping skill*"[tiab])'
C4 = '(framework*[ti] OR model*[ti] OR standard*[ti] OR guideline*[ti] OR curriculum[ti] OR toolkit*[ti] OR consensus[ti] OR statement*[ti])'
C6 = '("nutrition competenc*"[tiab] OR "dietitian competenc*"[tiab] OR "nutritionist competenc*"[tiab] OR "clinical nutrition skill*"[tiab] OR "competency framework*"[tiab] OR "nutrition counseling skill*"[tiab] OR "nutrition counselling skill*"[tiab] OR "dietetic competenc*"[tiab])'
C7 = '(framework*[ti] OR standard*[ti] OR guideline*[ti] OR consensus[ti] OR statement*[ti] OR curriculum[ti] OR "scope of practice"[ti] OR "scope of competence"[ti])'
C9A = '("implementation framework*"[ti] OR "implementation strateg*"[ti] OR "implementation guide*"[ti] OR "implementation toolkit*"[ti] OR "implementation plan*"[ti] OR "implementation model*"[ti] OR "implementation project*"[ti] OR "dissemination framework*"[ti] OR "dissemination strateg*"[ti] OR "guideline implementation"[ti] OR "practice implementation"[ti])'
C9B = '("quality improvement framework*"[ti] OR "quality improvement strateg*"[ti] OR "monitoring framework*"[ti] OR "monitoring system*"[ti] OR "implementation monitoring"[ti] OR "implementation evaluation"[ti])'
C12 = '("dietary pattern*"[ti] OR "food pattern*"[ti] OR "healthy eating pattern*"[ti] OR "dietary approach*"[ti] OR "dietary strateg*"[ti] OR "eating pattern*"[ti] OR "meal pattern*"[ti] OR "dietary model*"[ti] OR "food-based approach*"[ti])'
C13 = '(guideline*[ti] OR recommendation*[ti] OR prescription*[ti] OR standard*[ti] OR consensus[ti] OR "practice point*"[ti])'
C17 = '("2000/01/01"[Date - Publication] : "2026/08/25"[Date - Publication])'

C = {
    "#1": C1,
    "#2A": C2A,
    "#2B": C2B,
    "#2": f"({C2A}) AND ({C2B})",
    "#3": C3,
    "#4": C4,
    "#5": f"({C3}) AND ({C4})",
    "#6": C6,
    "#7": C7,
    "#8": f"({C6}) AND ({C7})",
    "#9A": C9A,
    "#9B": C9B,
    "#11": f"({C9A}) OR ({C9B})",
    "#12": C12,
    "#13": C13,
    "#14": f"({C12}) AND ({C13})",
}
C["#15"] = f"({C['#2']}) OR ({C['#5']}) OR ({C['#8']}) OR ({C['#11']}) OR ({C['#14']})"
C["#16"] = f"({C['#1']}) AND ({C['#15']})"
C["#17"] = C17
C["#18"] = f"({C['#16']}) AND ({C17})"

C_BRANCHES = {
    "F4_F7": f"({C1}) AND ({C['#2']}) AND ({C17})",
    "F5A": f"({C1}) AND ({C['#5']}) AND ({C17})",
    "F5B": f"({C1}) AND ({C['#8']}) AND ({C17})",
    "F6": f"({C1}) AND ({C['#11']}) AND ({C17})",
    "F3": f"({C1}) AND ({C['#14']}) AND ({C17})",
}

SENTINELS = [
    {"id":"NORM-018","locator":"40546761[pmid]","b_expect":"EXPECTED","c_expect":"TEST"},
    {"id":"NORM-040","locator":"41254791[pmid]","b_expect":"ALT_ROUTE","c_expect":"ALT_ROUTE"},
    {"id":"NORM-044","locator":"41531289[pmid]","b_expect":"EXPECTED","c_expect":"TEST"},
    {"id":"NORM-046","locator":"36567079[pmid]","b_expect":"TEST","c_expect":"TEST"},
    {"id":"NORM-051","locator":"40956256[pmid]","b_expect":"ALT_ROUTE","c_expect":"ALT_ROUTE"},
    {"id":"NORM-056","locator":"41502845[pmid]","b_expect":"EXPECTED","c_expect":"TEST"},
    {"id":"NORM-057","locator":"40403714[pmid]","b_expect":"TEST","c_expect":"TEST"},
    {"id":"NORM-035","locator":"41651774[pmid]","b_expect":"ALT_ROUTE","c_expect":"ALT_ROUTE"},
    {"id":"NORM-059","locator":"40450457[pmid]","b_expect":"TEST","c_expect":"TEST"},
    {"id":"NORM-060","locator":"41358882[pmid]","b_expect":"ALT_ROUTE","c_expect":"ALT_ROUTE"},
    {"id":"NORM-062","locator":"36462613[pmid]","b_expect":"TEST","c_expect":"EXPECTED"},
    {"id":"NORM-063_MAIN","locator":"36994026[pmid]","b_expect":"ALT_ROUTE_OR_LINKED","c_expect":"TEST"},
    {"id":"NORM-063_LINKED_SUMMARY","locator":"35707299[pmid]","b_expect":"EXPECTED_FAMILY_LINK","c_expect":"TEST"},
    {"id":"NORM-065","locator":"36148880[pmid]","b_expect":"ALT_ROUTE","c_expect":"ALT_ROUTE"},
]


def write_json(name: str, obj: Any) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run_counts(label: str, queries: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line, query in queries.items():
        print(f"[{label}] {line}", flush=True)
        out[line] = base.esearch(query)
    return out


def sample_query(query: str, n: int) -> dict[str, Any]:
    s = base.esearch(query, retmax=n, sort="pub_date")
    return {"rule":f"first {n} by publication date descending; no manual substitution", "search":s, "records":base.esummary(s["idlist"])}


def branch_samples() -> dict[str, Any]:
    out: dict[str, Any] = {}
    names = list(C_BRANCHES)
    for name in names:
        q = C_BRANCHES[name]
        others = [C_BRANCHES[x] for x in names if x != name]
        exclusive = f"({q}) NOT ({' OR '.join(f'({x})' for x in others)})"
        ex = base.esearch(exclusive, retmax=10, sort="pub_date")
        ids = list(ex["idlist"])
        supplement = None
        mode = "exclusive"
        if len(ids) < 10:
            full = base.esearch(q, retmax=10, sort="pub_date")
            for pmid in full["idlist"]:
                if pmid not in ids:
                    ids.append(pmid)
                if len(ids) >= 10:
                    break
            supplement = full
            mode = "exclusive_then_branch_fill"
        out[name] = {"rule":"up to 10 by publication date descending; prioritize branch-exclusive; no opportunistic substitution", "branch_query":q, "exclusive_search":ex, "supplement_search":supplement, "sampling_mode":mode, "records":base.esummary(ids[:10])}
    return out


def sentinel_matrix() -> list[dict[str, Any]]:
    out = []
    for item in SENTINELS:
        b = base.esearch(f"({B['#3']}) AND ({item['locator']})", retmax=5)
        c = base.esearch(f"({C['#18']}) AND ({item['locator']})", retmax=5)
        branches = {}
        if c["count"]:
            for name, q in C_BRANCHES.items():
                hit = base.esearch(f"({q}) AND ({item['locator']})", retmax=5)
                branches[name] = {"recovered":bool(hit["count"]), "count":hit["count"], "pmids":hit["idlist"]}
        out.append({**item, "b_v0_7":{"recovered":bool(b["count"]),"count":b["count"],"pmids":b["idlist"],"translation":b.get("querytranslation"),"warnings":b.get("warninglist")}, "c_v0_5":{"recovered":bool(c["count"]),"count":c["count"],"pmids":c["idlist"],"translation":c.get("querytranslation"),"warnings":c.get("warninglist")}, "c_branches":branches})
    return out


def main() -> int:
    write_json("manifest.json", {
        "scientific_status":"PILOT_QA_NOT_PRISMA",
        "article":"Article 1 scoping review — normative/operational food and nutrition care ecosystem",
        "started_at_utc":datetime.now(timezone.utc).isoformat(),
        "prospective_freeze":"D-127 / 02I_PRESS_ESTRATEGIAS recorded and verified before execution",
        "strategy_versions":{"B_NORM_PUBMED":"v0.7","C_STRUCT_PUBMED":"v0.5"},
        "git_sha":os.environ.get("GITHUB_SHA"), "git_ref":os.environ.get("GITHUB_REF"), "run_id":os.environ.get("GITHUB_RUN_ID"),
        "guardrail":"PILOT only. Formal PRISMA remains zero until PRESS, human gates, freeze, and fresh FORMAL searches."
    })
    b_counts = run_counts("B-NORM v0.7", B)
    write_json("b_norm_v0_7_counts_search_details.json", b_counts)
    b_sample = sample_query(B["#3"], 20)
    write_json("b_norm_v0_7_final_sample.json", b_sample)
    c_counts = run_counts("C-STRUCT v0.5", C)
    write_json("c_struct_v0_5_counts_search_details.json", c_counts)
    c_samples = branch_samples()
    write_json("c_struct_v0_5_branch_samples.json", c_samples)
    sentinels = sentinel_matrix()
    write_json("sentinel_matrix_v0_7_v0_5.json", sentinels)
    expected_b = [x for x in sentinels if x["b_expect"] in {"EXPECTED", "EXPECTED_FAMILY_LINK"}]
    expected_c = [x for x in sentinels if x["c_expect"] == "EXPECTED"]
    summary = {
        "scientific_status":"PILOT_QA_NOT_PRISMA",
        "b_counts":{k:v["count"] for k,v in b_counts.items()},
        "c_counts":{k:v["count"] for k,v in c_counts.items()},
        "b_expected_n":len(expected_b), "b_expected_recovered_n":sum(bool(x["b_v0_7"]["recovered"]) for x in expected_b),
        "b_expected_misses":[x["id"] for x in expected_b if not x["b_v0_7"]["recovered"]],
        "c_expected_n":len(expected_c), "c_expected_recovered_n":sum(bool(x["c_v0_5"]["recovered"]) for x in expected_c),
        "c_expected_misses":[x["id"] for x in expected_c if not x["c_v0_5"]["recovered"]],
        "b_sample_n":len(b_sample["records"]), "c_branch_sample_n":{k:len(v["records"]) for k,v in c_samples.items()},
        "sentinel_matrix":[{"id":x["id"],"b_expect":x["b_expect"],"b":x["b_v0_7"]["recovered"],"c_expect":x["c_expect"],"c":x["c_v0_5"]["recovered"],"c_branches":[k for k,v in x["c_branches"].items() if v["recovered"]]} for x in sentinels],
        "completed_at_utc":datetime.now(timezone.utc).isoformat()
    }
    write_json("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
