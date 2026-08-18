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

## Published v1.0.0 archive

- Git tag: `v1.0.0`
- Release commit: `5728d79b05e618897f01ba93886a17584c9f215f`
- Zenodo record: `21998607`
- DOI: `10.5281/zenodo.21998607`
- Record URL: `https://zenodo.org/records/21998607`
- DOI URL: `https://doi.org/10.5281/zenodo.21998607`

The DOI patch is post-release metadata only. It must not move, recreate or otherwise modify the immutable `v1.0.0` tag. Future versions must receive their own version-specific Zenodo record and DOI.
