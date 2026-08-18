# NutEV Reference Engine v1.0.0 — identity audit

Audit date: 2026-08-18

Base branch: `main`

Base SHA: `a47299fcb944ae6d7fdac17f06102d91b51e0d17`

Release branch: `agent/release-v1.0.0`

## Classification rule

- **ACTIVE**: affects the supported v1 product identity, default execution path, release metadata, public outputs or contributor instructions.
- **LEGACY**: historical research-workflow material or compatibility code that is not part of the supported v1 runtime/output contract.

The audit does not rewrite Git history and does not move immutable historical tags.

## Active findings and action

| File/surface | Finding | Class | Release action |
|---|---|---|---|
| `src/nutev/__version__.py` | `0.3.0.dev1` development identity | ACTIVE | set `1.0.0` |
| `.zenodo.json` | v0.2.0 Evidence Engine/scoping-review/PRISMA metadata | ACTIVE | replace with Reference Engine v1 metadata; no DOI until verified |
| `CITATION.cff` | v0.2.0 Evidence Engine/scoping-review citation identity | ACTIVE | replace with Reference Engine v1 citation metadata |
| `pyproject.toml` | Evidence Engine/candidate-protocol product description | ACTIVE | replace active package description with Reference Engine identity |
| `README.md` | reference-mode product already present but no stable v1 identity/complete release docs | ACTIVE | make v1.0.0 canonical, add Quick Start/Outputs/Sources/Ranking/Limitations/Citation |
| `AGENTS.md` | scientific-review governance and PRISMA/PRESS/gate requirements still normative for contributors | ACTIVE | replace with Reference Engine product invariants |
| `CHANGELOG.md` | current source described as `0.3.0.dev1`, PILOT/GF/PRESS/FREEZE active | ACTIVE | create v1.0.0 stable section and demote pre-v1 workflow to history |
| `.github/workflows/release-artifact-validation.yml` | generic build + clean-wheel validation | ACTIVE | retain; it is release-safe and version-agnostic |
| `RODAR_TUDO.cmd` | supported one-command collection + ranking path | ACTIVE | retain; audit final public outputs for legacy control fields |
| `tools/rank_references.py` | ranking product implementation | ACTIVE | retain; test determinism/scoring/public-output contract |
| `config/reference_mode.json` | ranking configuration | ACTIVE | retain |
| `config/keyword_taxonomy*.json` | semantic taxonomy | ACTIVE | retain |

## Legacy findings

Repository search found substantial pre-v1 material containing terms such as PRISMA, PRESS, FREEZE, GF-01/GF-02/GF-03/GF-07/GF-10, FORMAL, scoping review, human screening and Evidence Engine.

Representative legacy surfaces include:

- `docs/ARTICLE1_*`
- `docs/NUTEV_COMPLETE_REVIEW_WORKFLOW.md`
- `docs/SCIENTIFIC_GOVERNANCE.md`
- `docs/PLAY.md`
- `docs/SEARCH_*`
- `docs/ENGINE_MASTER_SCOPE_AND_DEFINITION_OF_DONE.md`
- `src/nutev/review/*`
- `src/nutev/api/article1_routes.py`
- `src/nutev/control_plane.py`
- historical scientific-gate tests
- archived v0.2.0 release documentation/workflow

Classification: **LEGACY**, unless a file is explicitly imported by a supported v1 code path for compatibility.

Release action:

1. do not mass-delete compatibility code before v1;
2. do not expose legacy review/gate concepts in the supported v1 Quick Start or ranking outputs;
3. preserve historical release documents and archived v0.2.0 validation as immutable provenance;
4. identify legacy material as outside the supported v1 product scope through `docs/legacy/README.md`;
5. future physical relocation/removal requires a separate compatibility-cleanup release and is not a v1 release blocker.

## Public-output contract

The supported v1 outputs are only:

- `project_output_reference/reference_ranking/TOP_REFERENCIAS.md`
- `project_output_reference/reference_ranking/reference_ranking.csv`
- `project_output_reference/reference_ranking/reference_ranking.jsonl`
- `project_output_reference/reference_ranking/latest.json`

These outputs must not expose legacy PRISMA/FORMAL/screening-control fields.

## Release decision

This audit permits v1 release preparation without deleting historical research-workflow code, provided:

- active metadata and documentation are fully synchronized to 1.0.0;
- ranking tests pass;
- public outputs satisfy the v1 contract;
- CI/build/security checks pass on the exact release candidate SHA;
- tag and GitHub Release are created only after merge and exact-SHA verification;
- no Zenodo DOI is claimed before a real archive record is verified.
