## Summary

<!-- What does this PR change and why? -->

## Type of change

- [ ] Provider / search
- [ ] Ranking / taxonomy
- [ ] Output contract
- [ ] Bug fix
- [ ] Documentation
- [ ] Build / CI / dependencies
- [ ] Code cleanup / refactor

## Reference Engine integrity

- [ ] Provider failures and unavailable sources remain explicit.
- [ ] No provider result, identifier or execution evidence is fabricated.
- [ ] Ranking remains reading/reference priority only.
- [ ] Source/provider identity is preserved.
- [ ] Licensed databases are not simulated when access is unavailable.
- [ ] Public ranking outputs contain only supported metadata/ranking fields.

## Safety

- [ ] No secrets, tokens, private keys or committed `.env` file.
- [ ] No personal, patient or participant data.
- [ ] No protected third-party full text without redistribution rights.
- [ ] No local generated output directory or private database committed.

## Testing

- [ ] `PYTHONPATH=src python -m pytest -q nutev_tests`
- [ ] `python -m compileall -q src tools nutev_tests`
- [ ] `ruff check src tools nutev_tests --select F,E9`
- [ ] User-visible changes are documented.

## Reviewer notes

<!-- Anything that deserves focused review. -->
