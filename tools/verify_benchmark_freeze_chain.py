from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


FROZEN_RUNTIME_SHA = "6aa7a5fe6009776e611ca3e1506486606b05f4f6"


class FreezeChainError(RuntimeError):
    """Raised when benchmark inputs no longer match their pre-label freeze records."""


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FreezeChainError(f"{label} not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FreezeChainError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise FreezeChainError(f"{label} must contain a JSON object")
    return value


def verify_chain(
    questions_path: Path,
    question_freeze_manifest_path: Path,
    benchmark_manifest_path: Path,
) -> dict[str, Any]:
    if not questions_path.is_file():
        raise FreezeChainError(f"QUESTIONS.csv not found: {questions_path}")
    question_freeze = _load_json(
        question_freeze_manifest_path,
        label="question freeze manifest",
    )
    benchmark = _load_json(
        benchmark_manifest_path,
        label="benchmark ranking manifest",
    )

    live_questions_sha = sha256(questions_path.read_bytes()).hexdigest()
    freeze_sha = str(question_freeze.get("questions_sha256") or "").strip()
    benchmark_sha = str(benchmark.get("questions_sha256") or "").strip()

    if question_freeze.get("status") != "PASS":
        raise FreezeChainError("Question freeze manifest status is not PASS")
    if not freeze_sha or freeze_sha != live_questions_sha:
        raise FreezeChainError(
            "QUESTIONS.csv no longer matches the question freeze manifest"
        )
    if benchmark_sha != freeze_sha:
        raise FreezeChainError(
            "Benchmark ranking manifest used a different QUESTIONS.csv SHA-256"
        )
    if benchmark.get("candidate_runtime_sha") != FROZEN_RUNTIME_SHA:
        raise FreezeChainError(
            "Benchmark ranking manifest does not reference the frozen runtime candidate"
        )
    if benchmark.get("frozen_runtime_sha_required") != FROZEN_RUNTIME_SHA:
        raise FreezeChainError(
            "Benchmark ranking manifest frozen-runtime contract is inconsistent"
        )
    if benchmark.get("label_blind_build") is not True:
        raise FreezeChainError("Benchmark ranking manifest is not declared label-blind")
    if benchmark.get("gold_standard_consumed") is not False:
        raise FreezeChainError(
            "Benchmark ranking build consumed or ambiguously records gold-standard input"
        )

    return {
        "status": "PASS",
        "artifact_type": "NUTEV_BENCHMARK_FREEZE_CHAIN",
        "questions_sha256": live_questions_sha,
        "question_freeze_manifest_sha256": sha256(
            question_freeze_manifest_path.read_bytes()
        ).hexdigest(),
        "benchmark_manifest_sha256": sha256(
            benchmark_manifest_path.read_bytes()
        ).hexdigest(),
        "candidate_runtime_sha": FROZEN_RUNTIME_SHA,
        "label_blind_build": True,
        "gold_standard_consumed": False,
        "scientific_boundary": (
            "PASS proves the benchmark ranking build used the exact frozen question file and "
            "declared frozen runtime without gold labels. It does not verify scientific quality, "
            "human independence, relevance judgments or benchmark representativeness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that benchmark rankings used the exact human-approved frozen question set and frozen NutEV runtime."
        )
    )
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--question-freeze-manifest", required=True, type=Path)
    parser.add_argument("--benchmark-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        result = verify_chain(
            args.questions,
            args.question_freeze_manifest,
            args.benchmark_manifest,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except FreezeChainError as exc:
        print(f"Freeze-chain failure: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
