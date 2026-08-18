# NutEV Reference Engine documentation

This directory contains current documentation for the supported NutEV Reference Engine.

## Start here

- `POP_USO_NUTEV_REFERENCE_ENGINE.md` — complete Portuguese Standard Operating Procedure for installation, updating, execution, collection profiles, credentials, outputs, interpretation and troubleshooting.
- `VALIDATED_WINDOWS_RUN_2026-08-18.md` — observed evidence from a real successful Windows execution: 8,702 ranking inputs, 115 taxonomy groups, TOP 100 and all three pipeline stages exiting with code 0.
- `SEARCH_PROVIDERS.md` — supported providers, operational/deep limits, credentials and failure/unavailable behavior.

## Release, provenance and archive

- `PROVENANCE_AND_LICENSE.md` — upstream provenance and release licensing boundary.
- `RELEASE_V1_0_0.md` — stable v1.0.0 product identity and release notes.
- `RELEASE_CHECKLIST.md` — technical release validation gates.
- `ZENODO_SETUP.md` — GitHub/Zenodo publication record and DOI rules.
- `REFERENCE_ENGINE_CLEANUP_AUDIT.md` — repository cleanup scope and evidence.

## Product flow

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

Windows day-to-day entry point:

```text
Iniciar-NutEV-Windows.bat
```

Primary outputs:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/latest.json
```

The ranking is a reading-priority/information-retrieval output, not scientific screening, methodological appraisal or a clinical recommendation.

Implementation history that is not part of the current product remains available in Git history rather than being duplicated in the active documentation tree.
