from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.science.article1_press import build_press_package, load_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFT = ROOT / "config" / "nutev" / "article1_query_draft_v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic pre-freeze provider query candidates and Article 1 PRESS delta-test queries. "
            "This does not validate provider syntax, approve PRESS, authorize GF-10, freeze queries, run a formal search, or emit PRISMA."
        )
    )
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    package = build_press_package(load_json(args.draft))
    text = json.dumps(
        package,
        ensure_ascii=False,
        indent=None if args.compact else 2,
        separators=(",", ":") if args.compact else None,
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(str(args.output))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
