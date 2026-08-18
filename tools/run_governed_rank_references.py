from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from nutev.governance import governance_context, load_governance_manifest, normalize_article_scope


RANKER_PATH = Path(__file__).resolve().with_name("rank_references.py")
SPEC = importlib.util.spec_from_file_location("rank_references", RANKER_PATH)
assert SPEC and SPEC.loader
rank_references = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rank_references)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_effective_config(config_dir: Path, article_scope: str, destination: Path) -> dict[str, Any]:
    """Build a temporary article-aware ranking config without mutating canonical config files."""
    scope = normalize_article_scope(article_scope)
    if scope == "all_articles":
        raise ValueError("governed article runs require an explicit A1, A2, A3 or A4 scope")

    governance = load_governance_manifest(config_dir / "nutev_governance_manifest.json")
    profiles = _read_json(config_dir / "article_reference_profiles.json")
    if profiles.get("governance_version") != governance.get("governance_version"):
        raise ValueError("article reference profiles do not match canonical governance version")
    profile = (profiles.get("profiles") or {}).get(scope)
    if not isinstance(profile, dict):
        raise ValueError(f"missing reference profile for {scope}")

    shutil.copytree(config_dir, destination, dirs_exist_ok=True)
    base = _read_json(config_dir / "reference_mode.json")
    effective = dict(base)
    effective["article_scope"] = scope
    effective["governance_version"] = governance["governance_version"]
    effective["profile_label"] = profile.get("label")
    effective["profile_purpose"] = profile.get("purpose")
    effective["focus_keywords"] = list(profile.get("focus_keywords") or [])
    _write_json(destination / "reference_mode.json", effective)
    return effective


def run(project_root: Path, config_dir: Path, article_scope: str, top_n: int) -> dict[str, Any]:
    scope = normalize_article_scope(article_scope)
    governance_path = config_dir / "nutev_governance_manifest.json"
    context = governance_context(scope, path=governance_path)
    with tempfile.TemporaryDirectory(prefix="nutev-governance-") as temp_dir:
        effective_dir = Path(temp_dir) / "config"
        effective = build_effective_config(config_dir, scope, effective_dir)
        summary = rank_references.run(project_root, effective_dir, top_n)

    summary = dict(summary)
    summary["article_scope"] = scope
    summary["article_profile_label"] = effective.get("profile_label")
    summary["article_profile_purpose"] = effective.get("profile_purpose")
    summary["governance"] = context
    latest = project_root / "reference_ranking" / "latest.json"
    _write_json(latest, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run NutEV reference ranking with explicit canonical A1-A4 governance."
    )
    parser.add_argument("--article", required=True, choices=["A1", "A2", "A3", "A4"])
    parser.add_argument("--project-root", default="./project_output_reference")
    parser.add_argument("--config-dir", default="./config")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()
    result = run(
        Path(args.project_root),
        Path(args.config_dir),
        args.article,
        max(1, args.top_n),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
