# Runtime Participant Identity and Custody Protocol

Status: **canonical validation identity/custody contract**.

## Normative rule

NutEV freezes the scientific object being tested, **not the identities of the humans who test it**.

Scientific constraints such as minimum independent assessors, blinding, adjudication and custody may be fixed by protocol. Real participant names, e-mail addresses, account identifiers, credentials, tokens, contact details and the mapping between a human and an operational assessor slot are private runtime data and must not be committed to Git or embedded in public benchmark artifacts.

## Operational identity model

Validation packets use opaque operational identifiers such as:

```text
assessor_4ec0d5c9150a
assessor_19ac6fc22f41
```

The canonical packet builder generates those slots at runtime from the blinded pool digest, packet seed and ordinal:

```bash
python tools/build_assessor_packets.py \
  --pool validation/data/VALIDATION_BLINDED_POOL.csv \
  --assessor-count 2 \
  --output-dir validation/data/validation_assessor_packets \
  --manifest validation/data/VALIDATION_ASSESSOR_PACKETS_MANIFEST.json
```

If neither `--assessor-count` nor compatibility `--assessor-id` values are supplied, the scientific minimum of two independent assessor slots is generated.

`--assessor-count` must be at least 2. Increasing the number of assessors is an operational decision and does not require changing application source code.

## Compatibility path

Repeated `--assessor-id` remains available only for already-opaque operational IDs. Do not pass names, e-mail addresses, usernames or other person identifiers. E-mail-like or whitespace-bearing values fail closed.

## Private custody boundary

The following must remain outside Git and outside public benchmark artifacts:

- real assessor identity and contact details;
- mapping from each real participant to `assessor_<digest>`;
- reviewer credentials or private-link tokens;
- real adjudicator/custodian identity unless separately disclosed through an approved scientific reporting process;
- sealed external-test participant mappings.

A private operational registry may hold this mapping. Its access and retention policy are outside the public NutEV repository.

## Manifest contract

The packet manifest may record:

- `assessor_count`;
- `assessor_identity_mode` (`generated_opaque_ids` or `explicit_opaque_ids`);
- opaque `assessor_ids`;
- frozen pool SHA-256;
- packet hashes and row counts;
- the scientific blinding boundary.

It must not record the real-person mapping.

## Independence and blinding

Opaque identity does not prove independence by itself. Operators remain responsible for ensuring that:

- at least two genuinely independent humans assess each required item;
- assessors do not receive ranking/system membership, another assessor's decisions or the pool audit before initial judgments are locked;
- `blind_to_nutev = true` is retained only while the assessor was actually blind;
- disagreements are resolved by an authorized human adjudicator, never by an automatic winner-selection rule.

## Scientific boundary

This protocol changes participant identity/custody only. It does not modify or authorize:

- ranking weights or reference scores;
- queries, taxonomy or providers;
- gold-standard labels;
- benchmark metrics;
- PRESS/C4/GF-10/query-freeze/formal-search/PRISMA states;
- eligibility, risk of bias, certainty or recommendations.

## Fail-closed rules

Packet preparation must fail when:

- fewer than two assessor slots are requested;
- a generated slot lacks a valid frozen-pool SHA-256;
- explicit and generated identity modes are mixed;
- an explicit assessor ID is blank or obviously person-identifying (for example an e-mail-like value);
- blinded input exposes prohibited system/ranking fields.

## Definition of done

The runtime identity contract is satisfied when a benchmark round can be prepared with `--assessor-count >= 2`, produces unique opaque slots and independently shuffled packets, preserves the exact pool hash, keeps the human mapping private, and passes the repository regression tests without changing the frozen scientific candidate.
