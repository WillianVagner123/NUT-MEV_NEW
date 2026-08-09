# GitHub Public Settings Checklist

Manual configuration to apply in the GitHub UI/settings for a safe, well-presented public repository. These are repository settings, not code changes.

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
- [ ] Require the current canonical checks that are actually active for the repository, including `ci`, `security-scan`, `codeql` and, for release-changing PRs, `release-validation`.
- [ ] Require branches to be up to date before merging when appropriate.
- [ ] Block force pushes to `main`.
- [ ] Block deletion of `main`.
- [ ] Consider requiring signed commits.
- [ ] Consider applying protections to administrators.

> Do not configure required checks using historical names such as `nutev-tests`, `nutev-lint` or `nutev-smoke` if those workflows are no longer present. The current canonical CI is `.github/workflows/ci.yml`; citation-grade release validation is `.github/workflows/release-validation.yml`.

## Security & analysis

- [ ] Enable **Secret scanning** if available for the repository/account.
- [ ] Enable **Push protection** if available.
- [ ] Enable **Dependency graph** so dependency-review can operate fully.
- [ ] Keep CodeQL enabled either through GitHub default setup or the repository workflow, but avoid duplicate/conflicting configurations.
- [ ] Enable **Private vulnerability reporting** when appropriate.
- [ ] Review dependency/security alerts manually.

### Dependabot note

The current source tree does **not** rely on a `.github/dependabot.yml` configuration. Do not claim that Dependabot update automation is active unless it is intentionally re-enabled and verified in the current tree.

## Actions

- [ ] Restrict Actions to trusted/approved actions according to repository policy.
- [ ] Keep default `GITHUB_TOKEN` permissions read-only where possible; workflows should request only the scopes they require.
- [ ] Require approval for workflows from first-time/outside contributors when appropriate.
- [ ] Review workflow permissions before the citable release.
- [ ] Keep `publish-v0.2.0` limited to `workflow_run` events from a successful `release-validation` on `main`.
- [ ] Confirm the publisher has only the permissions required to create the tag/release and read the validation artifact.

## Release candidate

The citation-grade reconciled release is:

- **Software version:** `0.2.0`
- **Git tag:** `v0.2.0`
- **Maturity:** alpha

Historical tags `v0.1.0` through `v0.1.8` already exist. They must remain immutable and must not be reused, deleted or moved merely to clean up version history.

- [ ] Complete `docs/RELEASE_CHECKLIST.md` on the exact candidate SHA.
- [ ] Confirm `release-validation` succeeds on the exact final `main` SHA.
- [ ] Confirm `v0.2.0` is still unused immediately before publication.
- [ ] Let the gated publisher create the GitHub Release only after the validated `main` run succeeds.
- [ ] Title the release **NutEV Evidence Engine v0.2.0**.
- [ ] State explicitly in the release notes that scientific maturity remains alpha.
- [ ] Verify the resulting tag points to the exact validated SHA.

## Open-science archival

- [ ] Connect/enable Zenodo for `WillianVagner123/NutEV-Evidence-Engine` in the Zenodo GitHub integration.
- [ ] Confirm `.zenodo.json` contains the intended public deposit metadata for version `0.2.0`.
- [ ] Keep `CITATION.cff` synchronized for GitHub/citation tooling.
- [ ] Include ORCID and exact affiliation only when their exact values are confirmed; do not fabricate them and do not treat optional metadata as a reason to invent values.
- [ ] Archive the exact `v0.2.0` GitHub Release after the release gates pass.
- [ ] Verify the actual Zenodo record after ingestion.
- [ ] Record the **Version DOI** for use in the manuscript and the Concept DOI when applicable.
- [ ] Insert the real DOI into current repository citation/documentation only after it actually exists.
- [ ] Mirror/register on OSF only if required by the study/registration plan.

## Forks policy

- [ ] Decide whether forks are allowed; open-source/open-science projects normally permit them.
- [ ] Verify that fork PR workflows cannot access secrets.

## Final review

- [ ] `NOTICE.md` matches the current tree and provenance state.
- [ ] `.gitleaksignore` contains only manually triaged false positives, if any.
- [ ] No protected content, secrets, personal/clinical data, local DBs or real scientific outputs are present in the release.
- [ ] README/docs match the actual Python support, output paths, release identity and workflow names.
- [ ] The exact release-candidate commit has current CI/security/release-validation evidence.
- [ ] GitHub Release, Git tag and Zenodo Version record all identify the same software object.
