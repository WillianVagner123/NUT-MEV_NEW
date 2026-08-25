#!/usr/bin/env python3
"""Supplemental A1 PILOT probe: sentinel recovery by B-NORM and C-STRUCT.

QA only; never PRISMA. Uses POST to avoid URL-length limits.
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import article1_pubmed_pilot as p

OUT = Path(os.environ.get("A1_PILOT_OUT", "a1_pubmed_pilot_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)


def request_post(endpoint: str, params: dict[str, Any]):
    url = f"{p.BASE}/{endpoint}"
    last = None
    for attempt in range(1, 5):
        try:
            time.sleep(0.40)
            r = p.SESSION.post(url, data=p._params(params), timeout=(10, 90))
            r.raise_for_status()
            return r.json(), url
        except Exception as exc:
            last = exc
            if attempt < 4:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"NCBI POST failed: {last}")

p._request = request_post

rows = []
for s in p.SENTINELS:
    row = {"id": s["id"], "label": s["label"], "expected_b": s["b_norm_pubmed"], "locator": s["locator"]}
    if not s["locator"]:
        row.update({"pubmed_resolvable": False, "b_norm": None, "c_struct": None, "c_branches": {}})
    else:
        resolve = p.esearch(s["locator"], retmax=5)
        row["pubmed_resolvable"] = bool(resolve["idlist"])
        row["pmids"] = resolve["idlist"]
        row["b_norm"] = bool(p.esearch(f"({p.B['#7']}) AND ({s['locator']})", retmax=5)["count"])
        row["c_struct"] = bool(p.esearch(f"({p.C['#16']}) AND ({s['locator']})", retmax=5)["count"])
        row["c_branches"] = {
            name: bool(p.esearch(f"({query}) AND ({s['locator']})", retmax=5)["count"])
            for name, query in p.C_BRANCHES.items()
        }
    rows.append(row)

summary = {
    "scientific_status": "PILOT_QA_NOT_PRISMA",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "git_sha": os.environ.get("GITHUB_SHA"),
    "sentinels": rows,
}
(OUT / "sentinel_route_probe.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
