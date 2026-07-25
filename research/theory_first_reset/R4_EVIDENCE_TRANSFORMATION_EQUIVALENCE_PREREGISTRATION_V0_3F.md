# R4 Evidence Transformation Equivalence Preregistration v0.3F

## Status

`PREREGISTERED_ZERO_PROVIDER_FORMAL_GRID`

## Frozen Grid

Eighteen cases:

1. renamed identical source -> `EXACT_DUPLICATE`;
2. lossless compressed source -> `EXACT_DUPLICATE`;
3. exact Celsius/Fahrenheit conversion -> `EXACT_DUPLICATE`;
4. claim-preserving redaction -> `EXACT_DUPLICATE`;
5. calibrated conversion with bounded immaterial error ->
   `EXACT_DUPLICATE`;
6. calibrated conversion with material error -> `DEPENDENT_DISTINCT`;
7. full source versus aggregate mean -> `DEPENDENT_DISTINCT`;
8. full source versus lossy summary -> `DEPENDENT_DISTINCT`;
9. raw inputs versus model-derived score -> `DEPENDENT_DISTINCT`;
10. source versus stochastic transformed output -> `DEPENDENT_DISTINCT`;
11. two distinct statistics from one full source -> `DEPENDENT_DISTINCT`;
12. subset versus full source -> `PARTIAL_OVERLAP`;
13. one source used for different target claims -> `SCOPE_INCOMPATIBLE`;
14. distinct sources and separate pipelines -> `INDEPENDENT_DISTINCT`;
15. same source with unverified transform -> `UNRESOLVED`;
16. unknown source identity -> `UNRESOLVED`;
17. distinct sources with one shared pipeline -> `DEPENDENT_DISTINCT`;
18. unknown target-claim relation -> `UNRESOLVED`.

No case-specific transform name may appear in compiler branches.

## Frozen Removal Tests

1. remove transform witness from rename case -> `UNRESOLVED`;
2. remove claim-tolerance witness from exact unit conversion -> `UNRESOLVED`;
3. change calibrated immaterial uncertainty to material ->
   `DEPENDENT_DISTINCT`;
4. change claim-preserving redaction target to different ->
   `SCOPE_INCOMPATIBLE`;
5. remove separate-pipeline witness from independent case -> `UNRESOLVED`;
6. change subset source identity to unknown -> `UNRESOLVED`.

## Frozen PASS Gates

All 14 gates must pass:

1. all five attribute enums validate;
2. all required witness rules validate;
3. all 18 frozen cases compile to expected relation states;
4. all 18 compile to expected Runtime actions;
5. all five intended exact-duplicate cases deduplicate;
6. no other case deduplicates;
7. same-source cases produce both deduplicate and block outcomes;
8. all six removal tests revoke or redirect the original action as expected;
9. missing critical attributes resolve to `UNRESOLVED`;
10. different target claims resolve to `SCOPE_INCOMPATIBLE`;
11. partial source resolves to `PARTIAL_OVERLAP`;
12. no new relation state or action is emitted;
13. two complete runs produce byte-identical artifacts;
14. Provider calls and CoreSlim, retention, and baseline writes are zero.

## Modularity

Separate:

- contracts;
- frozen grid;
- compiler;
- removal audit and evaluation;
- CLI and artifact writing;
- tests.

No module may import Provider clients, CoreSlim, retention, or baseline code.

## Outcome Interpretation

`PASS`:

- supports attribute compilation sufficiency on the formal grid;
- permits a later semantic attribute-inference experiment;
- does not authorize CoreSlim integration.

`FAIL`:

- preserve the failed grid;
- revise the ontology before adding states or Provider calls.

## Determinism

Two runs must produce byte-identical:

- `result.json`;
- `hash_inventory.json`;
- `closure.json`.

## Stop Rule

No same-version repair after first execution.

