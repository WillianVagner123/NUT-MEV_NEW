#!/usr/bin/env python3
"""Run the Article 1 PubMed PILOT using POST for long E-utilities terms."""
from __future__ import annotations

import os
import time
from typing import Any

import article1_pubmed_pilot as pilot


def _request_post(endpoint: str, params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    url = f"{pilot.BASE}/{endpoint}"
    last: Exception | None = None
    for attempt in range(1, 5):
        try:
            time.sleep(0.13 if os.environ.get("NCBI_API_KEY") else 0.40)
            prepared = pilot._params(params)
            response = pilot.SESSION.post(url, data=prepared, timeout=(10, 90))
            response.raise_for_status()
            return response.json(), url
        except Exception as exc:
            last = exc
            if attempt < 4:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"NCBI POST request failed after retries: {last}")


pilot._request = _request_post
raise SystemExit(pilot.main())
