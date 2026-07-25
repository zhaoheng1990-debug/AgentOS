# R4 Transformation Semantics Factorization Preregistration v0.3H

## Status

`PREREGISTERED_ZERO_PROVIDER_FORMAL_GRID`

## Frozen Experiment

- twenty valid or boundary cases;
- all 24 status-effect Cartesian pairs audited;
- seven pairs expected admissible;
- seventeen pairs expected invalid;
- six witness or attribute removal tests;
- no Provider calls;
- no modification of the v0.3F compiler;
- no CoreSlim, retention, or baseline writes.

## Frozen PASS Gates

All 16 gates must pass:

1. both new enums validate;
2. exactly seven status-effect pairs are admissible;
3. exactly seventeen pairs are invalid;
4. all invalid pairs compile to `UNRESOLVED -> BLOCK`;
5. all twenty cases compile to the frozen relation;
6. all twenty compile to the frozen Runtime action;
7. all four v0.3G disagreement families have non-colliding factorized
   representations;
8. subset preserves both partial-source and reducing-effect facts;
9. no-transform, unverified-transform, and unknown-applicability remain
   distinguishable;
10. global equivalence requires a full-domain witness;
11. claim equivalence requires claim and tolerance witnesses;
12. all six removal tests revoke or redirect authority as expected;
13. no new relation state or action is emitted;
14. compiler source contains no case ID, case family, or transform-name branch;
15. two complete runs produce byte-identical artifacts;
16. Provider calls and protected writes are zero.

## Frozen Removal Tests

1. remove transform-status witness from exact conversion -> `UNRESOLVED`;
2. remove information-effect witness from exact conversion -> `UNRESOLVED`;
3. remove full-domain witness from global equivalence -> `UNRESOLVED`;
4. remove tolerance witness from claim equivalence -> `UNRESOLVED`;
5. change verified transform to asserted-unverified while retaining a verified
   effect -> invalid pair and `UNRESOLVED`;
6. change subset source identity to unknown -> `UNRESOLVED`.

## Interpretation

`PASS` supports factorized formal coherence and permits a later fresh Provider
attribute-inference theory packet.

`FAIL` preserves the grid and requires object revision. It does not authorize a
prompt patch or Provider call.

## Determinism

Two complete runs must produce byte-identical:

- `result.json`;
- `hash_inventory.json`;
- `closure.json`.

## No Same-Version Repair

No expectation, rule, threshold, or test may change after first execution.
