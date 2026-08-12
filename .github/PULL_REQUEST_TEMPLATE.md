<!-- Thank you for contributing to NutEV/NutMEV. Please fill in the sections below. -->

## Summary

<!-- What does this PR change and why? -->

## Type of change

- [ ] Bug fix
- [ ] Feature / enhancement
- [ ] Documentation
- [ ] Methodology / rules / scoring / ontology change
- [ ] Search / provider / PLAY change
- [ ] Build / CI / dependencies
- [ ] Code hygiene / legacy retirement

## Scientific integrity checklist

- [ ] Generated queries are not presented as executed without attempt evidence.
- [ ] No output is presented as a final clinical recommendation (candidates only).
- [ ] Conflicts, truncation and failures are surfaced, not hidden.
- [ ] No LLM is used to define final approval.
- [ ] Methodology/rule/scoring changes are versioned where required.
- [ ] Human-only states (PRESS/FREEZE/INCLUDE/EXCLUDE/adjudication) are not invented by software.

## Safety checklist

- [ ] No secrets, tokens, `.env`, private keys or signed/authenticated URLs.
- [ ] No personal, patient or participant data.
- [ ] No protected full texts / third-party PDFs without redistribution rights.
- [ ] No real local run outputs or private databases committed.

## Testing

- [ ] `PYTHONPATH=src python -m pytest -q nutev_tests` passes (or explain).
- [ ] CLI remains usable (`nutev --help`).
- [ ] User-facing runtime changes are covered by an appropriate smoke/contract test.

## Docs

- [ ] Docs updated where relevant.
- [ ] No references to deleted legacy workstream/querypack runtime were reintroduced.

## Notes for reviewers

<!-- Anything the reviewer should focus on. -->
