from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse
from uuid import uuid4

import requests

COLLECTION_TYPE = "REFERENCE_COLLECTION"
USER_AGENT = "NutEV Reference Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"
_SPACE_RE = re.compile(r"\s+")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip())


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    return _atomic_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    return _atomic_text(
        path,
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n" for row in rows),
    )


class _AnchorParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._href = ""
        self._parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = _clean(dict(attrs).get("href"))
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href:
            return
        title = _clean(" ".join(self._parts))
        url = urljoin(self.base_url, self._href)
        if title and url:
            self.anchors.append((url, title))
        self._href = ""
        self._parts = []


def lilacs_search_url(query: str) -> str:
    params = [("lang", "pt"), ("q", query), ("filter[db_cluster][]", "LILACS")]
    return "https://pesquisa.bvsalud.org/portal/?" + urlencode(params)


def scielo_search_url(query: str) -> str:
    return "https://search.scielo.org/?" + urlencode({"lang": "en", "q": f"subject:({query})"})


def _candidate(provider: str, search_url: str, url: str, title: str, query: str) -> dict[str, Any] | None:
    parsed = urlparse(url)
    title = _clean(title)
    if len(title) < 20:
        return None
    if provider == "lilacs_bvs_native":
        if "bvsalud.org" not in parsed.netloc:
            return None
        if "/resource/" not in parsed.path and "id=" not in parsed.query and "biblio-" not in url:
            return None
    elif provider == "scielo_native":
        if "scielo" not in parsed.netloc:
            return None
        if not any(token in url.lower() for token in ("article", "script=sci_arttext", "pid=", "doi.org")):
            return None
    else:
        return None
    return {
        "source": provider,
        "source_provider": provider,
        "title": title,
        "abstract": "",
        "snippet": "",
        "doi": "",
        "pmid": "",
        "pmcid": "",
        "url": url,
        "query": query,
        "provider_query": query,
        "provider_search_url": search_url,
        "collection_type": COLLECTION_TYPE,
        "metadata_status": "native_search_html_candidate",
    }


def _run_provider(provider: str, search_url: str, query: str, run_dir: Path) -> dict[str, Any]:
    started = _now()
    try:
        response = requests.get(search_url, timeout=60, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        html = response.text
        raw_path = run_dir / "raw" / f"{provider}.html"
        raw_sha = _atomic_text(raw_path, html)
        parser = _AnchorParser(search_url)
        parser.feed(html)
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for url, title in parser.anchors:
            row = _candidate(provider, search_url, url, title, query)
            if row is None:
                continue
            key = str(row.get("url") or row.get("title") or "").casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(row)
        records_path = run_dir / "providers" / f"{provider}.jsonl"
        records_sha = _atomic_jsonl(records_path, rows)
        return {
            "provider": provider,
            "status": "completed" if rows else "completed_no_candidates_parsed",
            "started_at": started,
            "finished_at": _now(),
            "search_url": search_url,
            "query": query,
            "http_status": response.status_code,
            "raw_html_path": str(raw_path),
            "raw_html_sha256": raw_sha,
            "records_path": str(records_path),
            "records_sha256": records_sha,
            "records": len(rows),
            "parser_note": "Official search HTML is retained as retrieval evidence; parsed anchors are reference candidates.",
        }
    except Exception as exc:
        return {
            "provider": provider,
            "status": "failed",
            "started_at": started,
            "finished_at": _now(),
            "search_url": search_url,
            "query": query,
            "records": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run(project_root: Path, query: str) -> dict[str, Any]:
    run_id = "latin_" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    run_dir = project_root / "14_latin_native" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    providers = [
        _run_provider("lilacs_bvs_native", lilacs_search_url(query), query, run_dir),
        _run_provider("scielo_native", scielo_search_url(query), query, run_dir),
    ]

    master_rows: list[dict[str, Any]] = []
    for provider in providers:
        path = Path(str(provider.get("records_path") or ""))
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    master_rows.append(value)

    master_path = run_dir / "latin_native_records.jsonl"
    master_sha = _atomic_jsonl(master_path, master_rows)
    summary = {
        "schema_version": 1,
        "collection_type": COLLECTION_TYPE,
        "run_id": run_id,
        "created_at": _now(),
        "query": query,
        "providers": providers,
        "master_records_path": str(master_path),
        "master_records_sha256": master_sha,
        "records": len(master_rows),
        "method_note": "LILACS/BVS and SciELO use their native public search interfaces and retain provider identity.",
    }
    summary_path = run_dir / "summary.json"
    summary_sha = _atomic_json(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = summary_sha
    _atomic_json(project_root / "07_logs" / "latin_native" / "latest.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect reference candidates from native LILACS/BVS and SciELO routes.")
    parser.add_argument("--project-root", default="./project_output_reference")
    parser.add_argument(
        "--query",
        default='(diet OR dietary OR nutrition OR "healthy eating") AND (guideline OR guidance OR recommendation OR consensus OR statement OR standard)',
    )
    args = parser.parse_args()
    result = run(Path(args.project_root), args.query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(p.get("status") != "failed" for p in result["providers"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
