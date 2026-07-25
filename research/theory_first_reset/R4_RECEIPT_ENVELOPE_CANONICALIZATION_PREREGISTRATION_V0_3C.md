# R4 Receipt Envelope Canonicalization Preregistration v0.3C

## Status

`PREREGISTERED_ZERO_PROVIDER_REPRESENTATION_TEST`

## Objective

Test whether a key-agnostic, shape-bound canonicalizer can recover unique
homogeneous receipt collections while preserving all existing item-level
semantic, authority, and exact-coverage gates.

## Frozen Implementation Boundary

The standalone implementation must separate:

- envelope shape detection and provenance;
- existing semantic item validation;
- adversarial fixtures;
- preserved-response replay;
- evaluation and artifact writing.

The envelope module may inspect only:

- JSON root type;
- root-level container count and type;
- non-emptiness;
- item object type;
- presence of a caller-supplied required-key set.

It may not inspect:

- private relation truth;
- relation-state correctness;
- evidence correctness;
- case coverage;
- Provider identity;
- decision or candidate state.

## Frozen Accepted Shapes

1. non-empty root array of receipt-shaped objects;
2. direct receipt-shaped root object;
3. object with one `receipts` list;
4. object with one `cases` list;
5. object with one unseen `payload` list plus scalar root metadata.

## Frozen Rejected Shapes

1. scalar root;
2. empty root array;
3. object with an empty list;
4. object with no receipt-shaped collection;
5. list containing non-objects;
6. list mixing receipt-shaped and non-receipt-shaped objects;
7. object containing two list-valued fields;
8. object containing one candidate list plus separate list metadata;
9. object containing one candidate list plus nested object metadata.

## Frozen End-To-End Item Gates

After successful envelope canonicalization:

1. a forbidden authority field still blocks;
2. missing expected-case coverage still blocks;
3. an unknown case ID still blocks;
4. extra non-authority item fields are recorded and excluded from canonical
   state.

## Preserved Replay

Inputs:

```text
outputs/r4_provider_semantic_relation_v0_3b/raw_attempts/
  batch_A_attempt_1.json.txt
  batch_A_attempt_2.json.txt
```

The replay must:

- read both files without modification;
- record their source SHA-256 values;
- identify root type `object_collection`;
- record source key `cases`;
- pass the unchanged semantic item validator;
- recover 12/12 receipts in each response;
- retain 12/12 relation-state agreement;
- retain zero false Runtime action in the diagnostic;
- grant no scoring or promotion authority to v0.3B.

## Frozen PASS Gates

All 15 gates must pass:

1. all five accepted shapes canonicalize;
2. all nine rejected shapes block;
3. accepted items are value-preserving;
4. root type, source key, and scalar metadata fields are recorded;
5. no key allowlist exists in the canonicalizer;
6. ambiguous root collections block;
7. heterogeneous collections block;
8. nested root containers block;
9. forbidden item authority remains blocked;
10. exact expected-case coverage remains enforced;
11. unknown case identity remains blocked;
12. both preserved v0.3B responses replay without modification;
13. each replay recovers 12/12 exact relations and zero harmful Runtime action;
14. two complete experiment runs are byte-identical;
15. Provider calls and CoreSlim, retention, and baseline writes are zero.

## Failure Interpretation

`PASS`:

- supports M1 for this bounded representation surface;
- closes the v0.3B envelope anomaly mechanically;
- permits drafting a new Provider experiment version;
- does not repair v0.3B or establish semantic generalization.

`FAIL_AMBIGUITY`:

- supports M0;
- reject key-agnostic canonicalization.

`FAIL_METADATA`:

- supports M2;
- revise the root metadata boundary before any Provider call.

`FAIL_ITEM_VALIDATION`:

- supports M3;
- envelope recovery is insufficient.

## Determinism

Two complete runs must produce byte-identical:

- `result.json`;
- `closure.json`;
- `hash_inventory.json`.

Source response hashes must remain unchanged.

## Stop Rule

Stop without same-version repair if:

- any frozen shape expectation is changed after test reveal;
- a preserved response is edited or normalized on disk;
- an alias-specific branch is required;
- a Provider call occurs;
- output is written outside the ignored experiment directory.

