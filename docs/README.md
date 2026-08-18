# NutEV Reference Engine documentation

This directory contains only current software documentation for the supported Reference Engine.

- `SEARCH_PROVIDERS.md` - supported providers, credentials and failure behavior.
- `PROVENANCE_AND_LICENSE.md` - upstream provenance and release licensing boundary.
- `RELEASE_V1_0_0.md` - stable v1 product identity and release notes.
- `RELEASE_CHECKLIST.md` - technical release validation gates.
- `ZENODO_SETUP.md` - GitHub/Zenodo publication steps and DOI rule.
- `REFERENCE_ENGINE_CLEANUP_AUDIT.md` - repository cleanup scope and evidence.

The active product flow is:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

Implementation history that is not part of the current product remains available in Git history rather than being duplicated in the current documentation tree.
