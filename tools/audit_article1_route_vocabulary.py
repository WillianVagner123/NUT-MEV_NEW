from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.science.article1_vocabulary import audit_article1_route_vocabulary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit rank-blind Article 1 route vocabulary before formal query freeze."
    )
    parser.add_argument("--search-id", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("project_output_reference"),
    )
    args = parser.parse_args()
    result = audit_article1_route_vocabulary(
        args.search_id,
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
