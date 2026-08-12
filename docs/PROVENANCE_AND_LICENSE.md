# Provenance and license boundary

Status: **required reading before the next public/Zenodo release**.

## Origin

NutEV Evidence Engine evolved from the open-source **Local Deep Research** project maintained by **LearningCircuit**. The inherited project was distributed under the MIT License.

The inherited Local Deep Research runtime is no longer present in the current working tree, but its historical code remains in Git history. Upstream attribution therefore must not be erased merely because the current runtime has been rewritten/refactored under `src/nutev/**`.

## Current tree

The active NutEV implementation is under `src/nutev/**`. The current tree contains NutEV-specific search, provenance, corpus, review, extraction, UI, API and orchestration code developed after the project diverged from the inherited Local Deep Research runtime.

Do not make either of these inaccurate claims:

- that every current NutEV source line was authored by LearningCircuit; or
- that the project has no upstream MIT provenance simply because the inherited runtime has been removed.

## MIT notice

The repository currently retains the upstream MIT notice in `LICENSE` and records the provenance boundary in `NOTICE.md` and Git history.

Before the next Zenodo/public release, perform a final human-confirmed license/provenance review. At minimum verify:

1. exact upstream repository identity;
2. upstream license at the relevant derivation point;
3. the best available upstream commit/tag/derivation point, if it can be established without guessing;
4. whether any current files contain substantial inherited upstream material;
5. the copyright holder/name that should be stated for original NutEV contributions;
6. that `LICENSE`, `NOTICE.md`, `CITATION.cff`, `.zenodo.json` and release notes do not contradict one another.

## Current safe rule

Until that review is complete:

- preserve the LearningCircuit MIT notice;
- preserve Git history;
- do not invent an upstream commit;
- do not remove attribution from inherited/substantial upstream material;
- do not claim that LearningCircuit owns/authored the independent NutEV contributions;
- do not change the declared license immediately before release without a deliberate human decision.

## Zenodo gate

License/provenance is a release gate. A Zenodo release should archive an exact reviewed SHA whose software version, Git tag, license, upstream attribution, creator metadata, `CITATION.cff`, `.zenodo.json`, CHANGELOG and release notes have been reconciled.

A DOI is recorded only after Zenodo actually creates the public record. No placeholder DOI belongs in the source tree.
