from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "verify_benchmark_freeze_chain.py"
SPEC = importlib.util.spec_from_file_location("verify_benchmark_freeze_chain", MODULE_PATH)
assert SPEC and SPEC.loader
chain = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = chain
SPEC.loader.exec_module(chain)


def _write_manifests(tmp_path: Path):
    questions = tmp_path / "QUESTIONS.csv"
    questions.write_text("question_id,question_text\nq1,Question?\n", encoding="utf-8")
    questions_sha = sha256(questions.read_bytes()).hexdigest()
    question_manifest = tmp_path / "QUESTIONS_FREEZE_MANIFEST.json"
    question_manifest.write_text(
        json.dumps({"status": "PASS", "questions_sha256": questions_sha}),
        encoding="utf-8",
    )
    benchmark_manifest = tmp_path / "BENCHMARK_RANKINGS_MANIFEST.json"
    benchmark_manifest.write_text(
        json.dumps(
            {
                "questions_sha256": questions_sha,
                "candidate_runtime_sha": chain.FROZEN_RUNTIME_SHA,
                "frozen_runtime_sha_required": chain.FROZEN_RUNTIME_SHA,
                "label_blind_build": True,
                "gold_standard_consumed": False,
            }
        ),
        encoding="utf-8",
    )
    return questions, question_manifest, benchmark_manifest


def test_exact_frozen_question_chain_passes(tmp_path: Path) -> None:
    questions, question_manifest, benchmark_manifest = _write_manifests(tmp_path)
    result = chain.verify_chain(questions, question_manifest, benchmark_manifest)
    assert result["status"] == "PASS"
    assert result["candidate_runtime_sha"] == chain.FROZEN_RUNTIME_SHA
    assert result["gold_standard_consumed"] is False


def test_modified_questions_after_freeze_fail_closed(tmp_path: Path) -> None:
    questions, question_manifest, benchmark_manifest = _write_manifests(tmp_path)
    questions.write_text(
        "question_id,question_text\nq1,Changed after freeze?\n",
        encoding="utf-8",
    )
    with pytest.raises(chain.FreezeChainError, match="no longer matches"):
        chain.verify_chain(questions, question_manifest, benchmark_manifest)


def test_benchmark_using_different_question_sha_fails_closed(tmp_path: Path) -> None:
    questions, question_manifest, benchmark_manifest = _write_manifests(tmp_path)
    data = json.loads(benchmark_manifest.read_text(encoding="utf-8"))
    data["questions_sha256"] = "0" * 64
    benchmark_manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(chain.FreezeChainError, match="different QUESTIONS.csv"):
        chain.verify_chain(questions, question_manifest, benchmark_manifest)


def test_non_frozen_runtime_fails_closed(tmp_path: Path) -> None:
    questions, question_manifest, benchmark_manifest = _write_manifests(tmp_path)
    data = json.loads(benchmark_manifest.read_text(encoding="utf-8"))
    data["candidate_runtime_sha"] = "deadbeef"
    benchmark_manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(chain.FreezeChainError, match="frozen runtime"):
        chain.verify_chain(questions, question_manifest, benchmark_manifest)


def test_gold_consumption_flag_fails_closed(tmp_path: Path) -> None:
    questions, question_manifest, benchmark_manifest = _write_manifests(tmp_path)
    data = json.loads(benchmark_manifest.read_text(encoding="utf-8"))
    data["gold_standard_consumed"] = True
    benchmark_manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(chain.FreezeChainError, match="gold-standard"):
        chain.verify_chain(questions, question_manifest, benchmark_manifest)
