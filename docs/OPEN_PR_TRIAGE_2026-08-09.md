# Open Pull Request Triage — 2026-08-09

## Purpose

This document converts the open-PR backlog into an auditable governance queue. It does **not** authorize blind mass merge or deletion of historical scientific ideas.

Current connector inventory on 2026-08-09 returned **20 open pull requests**, including the active remediation PR #976. The remaining 19 PRs were created on July 13–14, 2026 against substantially older `main` states; most report that the full canonical test suite was not run in their original environment.

## Governance rule

> No July-era methodological/query-expansion PR should be merged into current `main` as-is.

Each old PR must first be treated as a **scientific proposal**, not as a ready code patch:

1. extract the proposed concepts/terms;
2. compare them with the current canonical taxonomy/querypacks and Article 1/2/4 scope;
3. remove duplicates and obsolete numbering/architecture assumptions;
4. justify expected recall/precision impact;
5. reimplement only the still-needed delta on current `main`;
6. run current CI, provenance tests and search-contract checks;
7. close the historical PR as `SUPERSEDED` with a pointer to the canonical replacement or decision record.

This preserves scientific history while preventing stale code from re-entering the runtime.

## A. Current remediation

| PR | Topic | Classification | Action |
|---|---|---|---|
| #976 | P0 scientific provenance/readiness + P1 hardening | **CURRENT MERGE CANDIDATE** | Keep draft until Dependency Graph is enabled and dependency-review truly passes; then final re-audit. |

## B. GLP-1 / anti-obesity medication family

| PR | Proposal | Current classification | Reason / next action |
|---|---|---|---|
| #912 | GLP-1 nutrition Global Watch terms | **HISTORICAL — CONSOLIDATE** | Overlaps #906/#902 and later Global Watch work. Extract only unique nutrition-care terms after comparing with current watch extensions. |
| #906 | GLP-1 nutrition semantic query expansion | **HISTORICAL — CONSOLIDATE** | Overlaps #912 and #902. Re-evaluate unique diet/protein/lean-mass concepts against current querypacks. |
| #902 | GLP-1 discontinuation nutrition/watch terms | **HISTORICAL — REVIEW UNIQUE DELTA** | Potentially distinct discontinuation/weight-regain concept; retain as a scientific idea, but reimplement on current architecture only if still absent. |

**Canonical next step:** one evidence-based GLP-1 nutrition gap review, not three independent stale merges.

## C. Food access / Food is Medicine / nutrition security family

| PR | Proposal | Current classification | Reason / next action |
|---|---|---|---|
| #913 | food access navigation/referral terms | **HISTORICAL — CONSOLIDATE** | Strong overlap with #900/#901/#894. |
| #901 | Food Is Medicine program variants | **HISTORICAL — CONSOLIDATE** | Consolidate program/voucher/incentive/medically tailored terminology. |
| #900 | food access navigation/referral terms | **HISTORICAL — DUPLICATE FAMILY** | Material thematic overlap with #913. Compare unique terms only. |
| #894 | food security/access query terms | **HISTORICAL — CONSOLIDATE** | Preserve nutrition-security concepts but align with current equity/access methodology. |

**Canonical next step:** one current-main `food_access / food_is_medicine / nutrition_security` gap matrix with duplicate-term removal and explicit workstream ownership.

## D. Cardiometabolic / liver / kidney / lipid family

| PR | Proposal | Current classification | Reason / next action |
|---|---|---|---|
| #921 | Portfolio diet / lipid semantic extension | **HISTORICAL — REVIEW UNIQUE DELTA** | Potentially useful pattern-specific evidence; verify whether current cardiometabolic taxonomy already contains Portfolio/LDL/ApoB concepts. |
| #920 | `hepatic steatosis` term | **HISTORICAL — REVIEW UNIQUE DELTA** | Small focused delta; verify against current MASLD/NAFLD terminology before reimplementation. |
| #919 | CKM/kidney nutrition extension | **HISTORICAL — CONSOLIDATE** | Consolidate with current CKM/cardiorenal architecture rather than merging stale module. |
| #917 | MASLD/NAFLD/MASH diet querypack | **HISTORICAL — CONSOLIDATE** | Evaluate with #920 and current liver/metabolic taxonomy. |
| #895 | cardiorenal semantic coverage | **HISTORICAL — CONSOLIDATE** | Overlaps CKM kidney/cardiorenal scope in #919 and later work. |

**Canonical next step:** one current cardiometabolic coverage audit covering lipid patterns, MASLD and CKM/kidney terms, with explicit precision/recall rationale.

## E. Adherence / competence / person-centered behavior family

| PR | Proposal | Current classification | Reason / next action |
|---|---|---|---|
| #918 | food/eating competence taxonomy | **HISTORICAL — REVIEW UNIQUE DELTA** | Potentially relevant to behavioral/framework work; reconcile with current article numbering and later NutEV behavioral architecture. |
| #916 | person-centered adherence / treatment burden / shared decision making | **HISTORICAL — REVIEW UNIQUE DELTA** | Scientifically relevant but must be mapped to current Article 2/behavioral scope before code inclusion. |
| #911 | dietary preference / acceptability / cultural tailoring | **HISTORICAL — REVIEW UNIQUE DELTA** | Retain as candidate adherence/implementation constructs; verify against current taxonomy. |
| #909 | habit formation / lapse / relapse / maintenance | **HISTORICAL — REVIEW UNIQUE DELTA** | Relevant behavior-change concepts; must be aligned with current functional-behavior framework instead of simply expanding recall. |
| #898 | dietary-pattern adherence scores/indexes | **HISTORICAL — REVIEW UNIQUE DELTA** | Distinguish evidence about dietary-pattern adherence measurement from implementation/functional adherence constructs. |

**Canonical next step:** build one construct-to-search-term matrix before adding more terms. This family is particularly vulnerable to conceptual inflation if every adherence-adjacent term is added without a construct boundary.

## F. Historical documentation / architecture proposals

| PR | Proposal | Current classification | Reason / next action |
|---|---|---|---|
| #899 | Article 3 analytical-behavioral framework + questionnaire plan | **HISTORICAL DOCUMENT — MANUAL CONTENT REVIEW** | Current project numbering/architecture evolved. Compare the scientific content with current Article 4/framework and instrument documents; migrate only still-valid material. |
| #896 | Article 1 canonical scope + CITATION preparation | **HISTORICAL DOCUMENT — LIKELY SUPERSEDED IN STRUCTURE** | Current repository now has a published `v0.2.0`, reconciled citation metadata, expanded Article 1 contracts and newer governance. Review `article1_scope.json`/protocol content for any unique scientific detail before closing. |

## Why these old PRs are not merge-ready

Common characteristics visible in their current metadata:

- created July 13–14, 2026;
- based on old `main` SHAs from before the release/audit consolidation;
- currently non-mergeable against `main` in the connector inventory;
- many explicitly state that full repository tests were not run locally;
- several overlap each other semantically;
- article numbering and methodological boundaries have evolved since creation;
- current `main` now has provenance/readiness rules that did not exist when these PRs were authored.

A stale PR can still contain a valuable scientific idea. The safe action is to preserve the proposal while rejecting the stale patch as the canonical implementation.

## Recommended closure protocol

After each thematic family is reviewed on current `main`:

### If all useful content is already present

Close old PR with classification:

`SUPERSEDED — current main already contains the relevant concept under the reconciled architecture.`

### If unique content remains useful

1. create one new current-main issue/PR for the consolidated delta;
2. cite/link all historical PRs that contributed ideas;
3. validate under current CI/search provenance contract;
4. close old PRs as superseded by the new implementation.

### If the idea is no longer in scope

Close as:

`HISTORICAL METHODOLOGY REFERENCE — not part of the current protocol/scope.`

## Backlog after this triage

The backlog is no longer an undifferentiated set of patches. It is five scientific review families plus two historical documentation reviews and the active remediation PR.

Priority after PR #976:

1. Article 1/2 search-term families that could affect the definitive search strategy;
2. adherence/behavior constructs requiring conceptual boundaries;
3. framework/questionnaire historical documents;
4. close/supersede old PRs only after the unique scientific deltas have been accounted for.

This ordering protects both repository hygiene and the audit trail of how the search strategy evolved.