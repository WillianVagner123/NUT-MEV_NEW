from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_snapshot_builder_hashes_only_safe_canonical_surfaces() -> None:
    js = read(WEB / "scientific-snapshot.js")

    assert "crypto.subtle.digest('SHA-256'" in js
    assert "SEARCH_STATE.json" in js
    assert "CONTEXT_MANIFEST.json" in js
    assert "ARTICLE_SUMMARIES.jsonl" in js
    assert "article1_query_draft_v1.json" in js
    assert "build-info.json" in js
    assert "snapshot_id" in js
    assert "generated_at" in js
    assert "snapshot_is_not_prisma:true" in js
    assert "snapshot_does_not_change_scientific_state:true" in js
    assert "reference_rank" not in js
    assert "reference_score" not in js
    assert "machine_relevance_score" not in js
    assert "method:'POST'" not in js.replace(" ", "")


def test_presentation_v2_has_five_snapshot_backed_screens_and_print_export() -> None:
    html = read(WEB / "presentation.html")
    js = read(WEB / "presentation.js")
    css = read(WEB / "presentation.css")

    assert html.count('class="presentation-slide') == 5
    assert "Scientific Question" not in html  # title is the actual loaded question, not a fake fixture
    assert "CORPUS" in html
    assert "EVIDENCE LANDSCAPE" in html
    assert "B-NORM × C-STRUCT" in html
    assert "FORMAL SEARCH READINESS" in html
    assert "Snapshot ≠ PRISMA" in html
    assert "buildScientificSnapshot" in js
    assert "downloadSnapshot" in js
    assert "window.print()" in js
    assert "@media print" in css
    assert "page-break-after:always" in css


def test_production_image_embeds_verified_target_sha_without_git_directory() -> None:
    dockerfile = read(ROOT / "deploy" / "hetzner" / "Dockerfile")
    workflow = read(ROOT / ".github" / "workflows" / "deploy-hetzner.yml")
    dockerignore = read(ROOT / ".dockerignore")

    assert "ARG NUTEV_BUILD_COMMIT=unknown" in dockerfile
    assert "NUTEV_BUILD_COMMIT=${NUTEV_BUILD_COMMIT}" in dockerfile
    assert "build-info.json" in dockerfile
    assert '--build-arg NUTEV_BUILD_COMMIT="$TARGET_SHA"' in workflow
    assert ".git" in dockerignore
