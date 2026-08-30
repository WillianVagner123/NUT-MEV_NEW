#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from nutev.science.article1_agent_context import build_article1_agent_context


_SAFE_WEB_FILES = (
    "CONTEXT_MANIFEST.json",
    "SEARCH_STATE.json",
    "SEARCH_SUMMARY.md",
    "ARTICLE_SUMMARIES.jsonl",
)


def _mirror_safe_context(source: Path, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in _SAFE_WEB_FILES:
        src = source / name
        if not src.is_file():
            raise FileNotFoundError(src)
        target = destination / name
        tmp = destination / f".{name}.tmp"
        shutil.copyfile(src, tmp)
        tmp.replace(target)
        copied.append(str(target))
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the verified, rank-blind Article 1 AI/agent context bundle."
    )
    parser.add_argument("--search-id", default=None)
    parser.add_argument("--output-root", type=Path, default=Path("project_output_reference"))
    parser.add_argument(
        "--web-mirror-root",
        type=Path,
        default=None,
        help=(
            "Optional static-web destination for the four safe context files. "
            "No full text, Bank rank/score/tier or machine relevance is mirrored."
        ),
    )
    args = parser.parse_args()

    result = build_article1_agent_context(
        args.search_id,
        output_root=args.output_root,
    )
    if args.web_mirror_root is not None:
        result["web_mirror_files"] = _mirror_safe_context(
            Path(result["output_dir"]),
            args.web_mirror_root.resolve(),
        )
        result["web_mirror_full_text_included"] = False
        result["web_mirror_rank_blind"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
