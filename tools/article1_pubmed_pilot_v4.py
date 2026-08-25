#!/usr/bin/env python3
"""Syntax-clean micro-PILOT for Article 1.

B-NORM v0.7 is unchanged from the successful third pilot. C-STRUCT v0.5.1
implements only the five prospectively frozen syntax corrections in D-131.
Outputs remain PILOT/QA and MUST NOT feed PRISMA.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import article1_pubmed_pilot_v3 as v3

OUT = Path(os.environ.get("A1_PILOT_OUT", "a1_pubmed_pilot_v4_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

# Exact D-131 syntax-clean replacements. All other v0.5 logic is retained.
C1 = v3.C1
C2A = '("nutrition care process"[tiab] OR "nutrition care model*"[tiab] OR ("nutrition care"[tiab] AND framework*[tiab]) OR "nutrition care pathway*"[tiab] OR "nutrition pathway*"[tiab] OR "medical nutrition therapy"[tiab] OR "diet prescription*"[tiab] OR "dietary prescription*"[tiab] OR "nutrition prescription*"[tiab] OR "food prescription*"[tiab] OR "meal plan*"[tiab] OR "nutrition counseling"[tiab] OR "nutrition counselling"[tiab] OR "dietetic care"[tiab] OR "dietitian-led"[tiab] OR "dietitian led"[tiab] OR "scope of practice"[tiab] OR "professional standard*"[tiab] OR "practice standard*"[tiab] OR "clinical decision framework*"[tiab] OR "model of care"[tiab] OR "lifestyle medicine"[tiab])'
C2B = v3.C2B
C3 = '("food literacy"[tiab] OR "nutrition literacy"[tiab] OR "culinary literacy"[tiab] OR "food skill*"[tiab] OR "cooking skill*"[tiab] OR "meal planning skill*"[tiab] OR (food[tiab] AND (competence[tiab] OR competency[tiab] OR competencies[tiab])) OR "culinary competenc*"[tiab] OR "food agency"[tiab] OR "food resource management"[tiab] OR "meal preparation skill*"[tiab] OR "shopping skill*"[tiab])'
C4 = v3.C4
C6 = '("nutrition competenc*"[tiab] OR (dietitian*[tiab] AND (competence[tiab] OR competency[tiab] OR competencies[tiab])) OR (nutritionist*[tiab] AND (competence[tiab] OR competency[tiab] OR competencies[tiab])) OR ("clinical nutrition"[tiab] AND (skill[tiab] OR skills[tiab])) OR "competency framework*"[tiab] OR "nutrition counseling skill*"[tiab] OR "nutrition counselling skill*"[tiab] OR "dietetic competenc*"[tiab])'
C7 = v3.C7
C9A = v3.C9A
C9B = v3.C9B
C12 = v3.C12
C13 = v3.C13
C17 = v3.C17

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

# Repoint inherited QA helpers to syntax-clean globals.
v3.C = C
v3.C_BRANCHES = C_BRANCHES


def write_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    write_json("manifest.json", {
        "scientific_status":"PILOT_QA_NOT_PRISMA",
        "article":"Article 1 scoping review — syntax-clean equivalence check",
        "started_at_utc":datetime.now(timezone.utc).isoformat(),
        "prospective_freeze":"D-131 / 02I_PRESS_ESTRATEGIAS recorded before execution",
        "strategy_versions":{"B_NORM_PUBMED":"v0.7_UNCHANGED","C_STRUCT_PUBMED":"v0.5.1_SYNTAX_CLEAN"},
        "git_sha":os.environ.get("GITHUB_SHA"), "git_ref":os.environ.get("GITHUB_REF"), "run_id":os.environ.get("GITHUB_RUN_ID"),
        "guardrail":"PILOT only. Do not feed PRISMA."
    })

    # B is unchanged; rerun final only to confirm same environment/date behavior.
    print("[B-NORM v0.7 unchanged] #3", flush=True)
    b_final = v3.base.esearch(v3.B["#3"])
    write_json("b_norm_v0_7_final_confirmation.json", b_final)

    c_counts = v3.run_counts("C-STRUCT v0.5.1", C)
    write_json("c_struct_v0_5_1_counts_search_details.json", c_counts)
    c_samples = v3.branch_samples()
    write_json("c_struct_v0_5_1_branch_samples.json", c_samples)
    sentinels = v3.sentinel_matrix()
    write_json("sentinel_matrix_v0_7_v0_5_1.json", sentinels)

    all_warnings = {k:v.get("warninglist") for k,v in c_counts.items() if v.get("warninglist")}
    expected_b = [x for x in sentinels if x["b_expect"] in {"EXPECTED", "EXPECTED_FAMILY_LINK"}]
    expected_c = [x for x in sentinels if x["c_expect"] == "EXPECTED"]
    summary = {
        "scientific_status":"PILOT_QA_NOT_PRISMA",
        "b_final_count":b_final["count"],
        "c_counts":{k:v["count"] for k,v in c_counts.items()},
        "c_warning_entries":all_warnings,
        "c_warning_free":not bool(all_warnings),
        "b_expected_n":len(expected_b),
        "b_expected_recovered_n":sum(bool(x["b_v0_7"]["recovered"]) for x in expected_b),
        "b_expected_misses":[x["id"] for x in expected_b if not x["b_v0_7"]["recovered"]],
        "c_expected_n":len(expected_c),
        "c_expected_recovered_n":sum(bool(x["c_v0_5"]["recovered"]) for x in expected_c),
        "c_expected_misses":[x["id"] for x in expected_c if not x["c_v0_5"]["recovered"]],
        "c_branch_sample_n":{k:len(v["records"]) for k,v in c_samples.items()},
        "completed_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    write_json("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
