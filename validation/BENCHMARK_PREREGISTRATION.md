# NutEV Scientific Benchmark — Pre-registration

Status: **PRE-RESULTS / NO HUMAN LABELS OBSERVED**  
Frozen NutEV runtime: `6aa7a5fe6009776e611ca3e1506486606b05f4f6`  
Scientific verdict at pre-registration: **B — DEMOTE**

## 1. Scope of this pre-registration

This document pre-specifies the first testable claim: **prioritization within a common candidate pool**.

It does not pre-register a claim of exhaustive literature discovery. Discovery coverage requires a separate benchmark with relevant references that may be outside the NutEV pool.

## 2. Primary question

Among references already present in the frozen eligible NutEV output, does `nutev_full` place independently judged relevant references nearer the top than a simple question-conditioned lexical baseline?

## 3. Primary comparator

`lexical_baseline`, implemented as label-blind BM25 over title + available abstract/summary/snippet + keywords/subjects with:

- `k1 = 1.2`;
- `b = 0.75`;
- query = frozen `question_text`;
- no relevance labels;
- no NutEV score/taxonomy input.

The lexical baseline is deliberately simple. Failure to beat it materially would weaken the case for maintaining a more complex NutEV ranking heuristic.

## 4. Primary endpoint

Primary endpoint:

```text
paired delta nDCG@20 = nDCG@20(nutev_full) - nDCG@20(lexical_baseline)
```

The comparison unit is the **question**, not the individual reference.

Secondary endpoints:

- `precision@20`;
- `recall@100` within the judged/common-pool universe;
- `average_precision@100` within the completely judged depth;
- full-list average precision only when the complete ranked list being evaluated is judged;
- reciprocal rank;
- records required to reach 80%, 90% and 95% of judged relevant references;
- nDCG@10/50/100.

## 5. Directional success rule before external_test

Development data may be used only to debug the benchmark pipeline. It must not determine the final claim.

Validation data may justify retaining the frozen candidate for external testing only if all of the following are observed:

1. median paired delta `nDCG@20 > 0` versus `lexical_baseline`;
2. the number of questions won on `nDCG@20` is greater than the number lost;
3. median paired delta `recall@100 >= -0.05` within the common-pool judged universe;
4. no single large aggregate gain is used to hide a systematic subgroup failure without reporting it.

These are operational continuation criteria, not universal scientific thresholds.

Failure on the validation split does not automatically prove the software useless, but it blocks promotion above `B — DEMOTE` for the tested prioritization claim unless a new candidate is developed using only permitted development/validation information and then frozen again.

## 6. External-test criterion for defined-use validation

A claim of `D — VALIDATED_FOR_DEFINED_USE` for **common-pool prioritization only** requires the frozen candidate to satisfy, on the sealed external test set:

1. at least **12 independent external-test questions** with benchmark-grade judgments; this is an operational minimum evidence floor, not a claim of universal statistical sufficiency;
2. positive median paired delta `nDCG@20`;
3. more question-level wins than losses versus the lexical baseline;
4. a deterministic 95% question-level bootstrap confidence interval for the **mean paired delta nDCG@20** whose lower bound is greater than 0;
5. median paired delta `recall@100 >= -0.05`;
6. transparent reporting of all questions, including failures.

If fewer than 12 benchmark-grade external questions are available, the correct status is `INSUFFICIENT_EVIDENCE_SAMPLE_SIZE`, not automatic validation. Meeting the minimum sample count does not guarantee promotion: every other criterion above must also pass.

Passing this criterion would support only a statement equivalent to:

> Validado para priorização de referências dentro do common pool e do domínio/população de perguntas representados pelo benchmark.

It would **not** establish discovery recall, methodological quality assessment or clinical validity.

## 7. Ablation hypotheses

Each ablation removes one frozen score component without re-tuning remaining weights.

Components:

- taxonomy;
- focus keywords;
- provider weight;
- recency;
- document type;
- identifier bonus.

If an ablation has equal or better median `nDCG@20` than `nutev_full` and wins at least as many questions as it loses, the removed component has **no demonstrated incremental value in that split** and must be examined before a future candidate preserves it.

This does not permit changing the currently frozen candidate after seeing `external_test`.

## 8. Common-pool construction

For each question, the judgment pool is the union of the top 100 results from every common-pool system unless feasibility forces a smaller depth **before labeling begins**.

Default:

```text
pool depth per system = 100
```

The pool is shuffled deterministically and presented without system/rank fields. A separate audit file records membership and must remain hidden from assessors until initial labels are locked.

If the depth is changed for feasibility, the change and rationale must be committed before any relevance label is collected for the affected benchmark round.

## 9. Human labeling

Benchmark-grade final labels require at least two independent assessors blind to NutEV score/rank/system origin.

Scale:

- 0 = irrelevant;
- 1 = relevant/peripheral;
- 2 = directly relevant/key reference.

Disagreements require human adjudication. Scripts may validate the process but may not choose the final scientific label.

## 10. Unjudged documents and judgment coverage

Unjudged documents must never be silently converted to relevance grade `0`.

For the preregistered primary comparison:

- every candidate and baseline result through rank 20 must be judged to calculate the primary `nDCG@20` comparison;
- every candidate and baseline result through rank 100 must be judged to calculate the `recall@100` guard;
- incomplete judgment coverage at a required endpoint causes the paired comparison to fail closed;
- evaluation output must report judgment coverage by depth and the completely judged prefix;
- full-list AP is omitted when the list extends beyond the judged universe; `average_precision@100` is the bounded common-pool alternative when depth 100 is completely judged.

For the common-pool benchmark, recall is bounded by the judged pool and must not be described as global literature recall.

Any later discovery benchmark must add independently discovered relevant references outside the NutEV common pool.

## 11. Statistical analysis

The primary comparison is paired at the question level.

Pre-specified implementation parameters:

- candidate: `nutev_full`;
- baseline: `lexical_baseline`;
- paired effect: candidate metric minus baseline metric for each `question_id`;
- bootstrap statistic: mean paired delta `nDCG@20`;
- bootstrap resampling unit: question;
- bootstrap iterations: `10000`;
- fixed seed: `nutev-paired-bootstrap-v1`;
- interval: deterministic percentile 95% interval;
- wins/losses/ties: sign of the paired `nDCG@20` delta;
- recall non-inferiority floor: median paired delta `recall@100 >= -0.05`.

The bootstrap interval is evidence about the represented question set; it must not be interpreted as proof of universal generalization.

## 12. Leakage prohibition

Before external-test labels are opened, do not change the frozen candidate based on:

- external relevance grades;
- external question-level performance;
- external taxonomy agreement;
- external provider contribution;
- external error analysis.

Any runtime change creates a new candidate and requires a new freeze.

## 13. Verdict mapping

- `A — KILL`: requires broader evidence of material inferiority/lack of value; common-pool failure alone is strong negative evidence but does not automatically establish total uselessness.
- `B — DEMOTE`: default until evidence supports promotion.
- `C — SCIENTIFIC_CANDIDATE`: validation split shows pre-specified positive signal sufficient to justify sealed external testing.
- `D — VALIDATED_FOR_DEFINED_USE`: external-test criterion passes for the explicitly bounded use.

## 14. Current evidence

No human relevance labels have been observed or generated in this pre-registration. All scientific performance metrics remain `NOT_TESTED`.
