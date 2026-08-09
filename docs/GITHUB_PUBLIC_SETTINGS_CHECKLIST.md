# GitHub Public Settings Checklist

Manual configuration to apply in the GitHub UI/settings for a safe, well-presented public repository. These are repository settings, not code changes.

The `v0.2.0` release was published on 2026-08-09. The one-shot `v0.2.0` publisher has been retired; future releases must use the reusable release process/checklist rather than instructions tied to that historical publisher.

## Repository presentation

- [ ] **Description:** e.g. "Reproducible evidence engine for lifestyle nutrition research — produces RecommendationCandidates (not final clinical advice)."
- [ ] **Topics:** `nutrition`, `lifestyle-medicine`, `evidence-synthesis`, `scoping-review`, `open-science`, `reproducible-research`, `python`.
- [ ] **Website:** project/docs page if desired.
- [ ] Enable **Issues** if they are intended for public use.
- [ ] Enable **Discussions** only if the project will actively maintain them.

## Branch protection (`main`)

Use the **current workflow names**, not removed historical workflows.

- [ ] Require a pull request before merging.
- [ ] Require at least 1 approving review when collaboration policy requires it.
- [ ] Dismiss stale approvals on new commits.
- [ ] Require active canonical checks such as `ci`, `security-scan`, `codeql` and any current release-validation workflow used by the candidate.
- [ ] Require branches to be up to date before merging when appropriate.
- [ ] Block force pushes to `main`.
- [ ] Block deletion of `main`.
- [ ] Consider requiring signed commits.
- [ ] Consider applying protections to administrators.

> Do not configure required checks using removed historical names. The canonical CI is `.github/workflows/ci.yml`.

## Security & analysis — blocking manual action

- [ ] Enable **Secret scanning** if available for the repository/account.
- [ ] Enable **Push protection** if available.
- [ ] **Enable Dependency Graph.** This is currently required before dependency-review can be treated as a real security gate.
- [ ] After enabling Dependency Graph, confirm the `dependency-review` action actually executes successfully on a PR.
- [ ] Require dependency review for release/security-sensitive changes only after a true execution has been demonstrated.
- [ ] Keep CodeQL enabled either through GitHub default setup or the repository workflow, avoiding duplicate/conflicting setups.
- [ ] Enable **Private vulnerability reporting** when appropriate.
- [ ] Review dependency/security alerts manually.

### Why Dependency Graph is explicitly required

The complete 2026-08-09 audit found that the dependency-review workflow could appear green even though GitHub reported dependency review as unsupported while Dependency Graph was disabled. The workflow has since been changed to make this condition blocking. Therefore a future green dependency-review must represent a real successful action execution.

The historical `v0.2.0` release record is correctly classified as **dependency review NOT VALIDATED**, not PASS.

### Dependabot / dependency-update policy

The current development tree includes `.github/dependabot.yml` for the `github-actions` package ecosystem on a weekly Monday schedule. Its purpose is to open reviewable PRs for Action updates instead of leaving SHA-pinned workflows permanently frozen.

- [x] automated GitHub Actions update policy added to the development branch;
- [ ] verify the first Dependabot GitHub-Actions PR after this configuration reaches `main`;
- [ ] review every Action update through the same CI/security gates before merge;
- [ ] decide separately whether Python dependency version updates should also be automated.

## Actions / supply-chain hardening

Critical Action references in the active development security/CI paths are pinned to full immutable commit SHAs, including:

- `actions/checkout`;
- `actions/setup-python`;
- `github/codeql-action`;
- `actions/dependency-review-action`;
- `gitleaks/gitleaks-action`.

The official GitHub/Actions pins use revisions already exercised by the remediation validation path. The gitleaks scan was separately reviewed and migrated from v2 to the signed **v3.0.0** release commit because v3 moves the runtime from Node 20 to Node 24 without changing the declared inputs/outputs/behavior. Dependabot is configured to propose later GitHub Actions updates for review rather than relying on mutable major-version references.

- [ ] Restrict Actions to trusted/approved actions according to repository policy.
- [ ] Keep default `GITHUB_TOKEN` permissions read-only where possible; workflows should request only the scopes they require.
- [ ] Require approval for workflows from first-time/outside contributors when appropriate.
- [ ] Review workflow permissions before every citable release.
- [x] Pin critical Action references in the active development branch to immutable commit SHAs.
- [x] Migrate gitleaks to the Node-24 v3 release line and pin its signed release commit.
- [ ] Confirm no retired one-shot release workflow is still treated as the canonical publication path.

## Current release state

The citation-grade reconciled release currently recorded is:

- **Software version:** `0.2.0`
- **Git tag:** `v0.2.0`
- **Release date:** `2026-08-09`
- **Maturity:** alpha

The post-release source tree is on the development package line `0.3.0.dev0`; this does not replace or move the published `v0.2.0` object.

Historical tags `v0.1.0` through `v0.1.8` and the published `v0.2.0` tag must remain immutable.

For a future release:

- [ ] use `docs/RELEASE_CHECKLIST.md` as the reusable template;
- [ ] validate the exact candidate SHA;
- [ ] create a new unused tag only after every blocking gate passes;
- [ ] preserve a post-release record with tag/SHA/date/validation evidence;
- [ ] never move an existing tag to repair metadata.

## Article 1 scientific execution settings

Repository settings do not by themselves prove a scientific run, but the repository should protect the code used for a definitive Article 1 execution.

- [ ] definitive execution occurs from a reviewed/protected commit;
- [ ] generated and executed query artifacts are distinct;
- [ ] `query_execution_ledger.json/.csv` is present for generic-pipeline execution;
- [ ] frozen indexed-database strategy executions preserve snapshots/checksums;
- [ ] `scientific_readiness` remains separate from execution completion;
- [ ] final manuscript readiness requires explicit human/manuscript gates.

See `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md`.

## Open-science archival

- [ ] Connect/enable Zenodo for `WillianVagner123/NutEV-Evidence-Engine` if Zenodo archival is part of the dissemination plan.
- [ ] Keep `.zenodo.json` and `CITATION.cff` synchronized with the release identity.
- [ ] Include ORCID and exact affiliation only when their exact values are confirmed.
- [ ] Verify the actual Zenodo record after ingestion.
- [ ] Record the **Version DOI** only after it exists publicly.
- [ ] Record a Concept DOI only when applicable and verified.
- [ ] Never add a guessed DOI to the manuscript or repository.

## Forks policy

- [ ] Decide whether forks are allowed; open-source/open-science projects normally permit them.
- [ ] Verify that fork PR workflows cannot access secrets.

## Final review

- [ ] `NOTICE.md` matches the current tree and provenance state.
- [ ] `.gitleaksignore` contains only manually triaged false positives, if any.
- [ ] No protected content, secrets, personal/clinical data, local DBs or real scientific outputs are present in a software release.
- [ ] README/docs match the actual Python support, output paths, release identity and workflow names.
- [ ] Exact candidate commit has current CI/security evidence.
- [ ] Dependency review is reported as PASS only after the action truly executes.
- [ ] GitHub Release, Git tag and any Zenodo Version record identify the same software object.