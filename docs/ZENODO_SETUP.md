# Zenodo publication setup

This repository keeps archive metadata in `.zenodo.json` and citation metadata in `CITATION.cff`.

## Before publication

1. Verify the exact candidate SHA and release version.
2. Confirm all required CI/security/build checks are green at that SHA.
3. Confirm `.zenodo.json`, `CITATION.cff`, README and release notes use the same title/version/creator/license.
4. Confirm the repository is enabled in the GitHub-Zenodo integration for the account that owns the repository.
5. Do not add or guess a DOI before an actual archive record exists.

## GitHub Release

Create an immutable release tag only after the exact `main` SHA has been validated. Publish a GitHub Release from that tag with the matching software title/version.

## Archive verification

After publication, verify the archive record contains:

- the expected release tag/version;
- correct title and creator;
- MIT license;
- expected description and keywords;
- archived source files corresponding to the release;
- a real DOI issued by the archive service.

Only after the DOI is visible and verified should the repository add that DOI to current citation/documentation metadata. Such a documentation patch must not move or alter the already-published release tag.
