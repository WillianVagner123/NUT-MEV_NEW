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
- [ ] Require at least 1 approving review.
- [ ] Dismiss stale approvals on new commits.
- [ ] Require the current canonical checks that are actually active for the repository, including at minimum the canonical `ci` workflow and security checks.
- [ ] Require branches to be up to date before merging when appropriate.
- [ ] Block force pushes to `main`.
- [ ] Block deletion of `main`.
- [ ] Consider requiring signed commits.
- [ ] Consider applying protections to administrators.

> Do not configure required checks using historical names such as `nutev-tests`, `nutev-lint` or `nutev-smoke` if those workflows are no longer present. The current canonical CI is `.github/workflows/ci.yml`.

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

## Release candidate

For the first citable software release:

- **Software version:** `0.1.0`
- **Git tag:** `v0.1.0`
- **Maturity:** alpha

- [ ] Complete `docs/RELEASE_CHECKLIST.md` on the exact candidate SHA.
- [ ] Create the GitHub Release only after GO/NO-GO passes.
- [ ] Title the release **NutEV Evidence Engine v0.1.0**.
- [ ] State explicitly in the release notes that scientific maturity remains alpha.

## Open-science archival

- [ ] Connect Zenodo to the repository.
- [ ] Confirm `.zenodo.json` and `CITATION.cff` are synchronized.
- [ ] Confirm ORCID and exact affiliation before DOI minting.
- [ ] Archive the exact `v0.1.0` release only after the release gates pass.
- [ ] Verify the actual Zenodo record after ingestion.
- [ ] Record the Version DOI for use in the manuscript.
- [ ] Mirror/register on OSF only if required by the study/registration plan.

## Forks policy

- [ ] Decide whether forks are allowed; open-source/open-science projects normally permit them.
- [ ] Verify that fork PR workflows cannot access secrets.

## Final review

- [ ] `NOTICE.md` matches the current tree and provenance state.
- [ ] `.gitleaksignore` contains only manually triaged false positives, if any.
- [ ] No protected content, secrets, personal/clinical data, local DBs or real scientific outputs are present in the release.
- [ ] README/docs match the actual Python support, output paths and workflow names.
- [ ] The exact release-candidate commit has current CI/security evidence.
