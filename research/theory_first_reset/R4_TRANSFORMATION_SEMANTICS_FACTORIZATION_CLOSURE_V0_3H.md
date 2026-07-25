# R4 Transformation Semantics Factorization Closure v0.3H

## Formal Status

`FAIL_CONSTRUCTION_INVALID_GATE_IMPLEMENTATION`

Evidence coordinate:

`INTERNAL_EXPERIMENT_INSTRUMENT_AUDIT`

No factorization-coherence conclusion is scorable.

## What Happened

The first test execution reported:

`65 passed`

However, post-execution source inspection found that two frozen gates were not
implemented as real audits:

1. `invalid_pairs_fail_closed` counted the seventeen pairs labelled invalid but
   did not compile those pairs and inspect their relation, action, and error;
2. `compiler_has_no_case_surface` was emitted as a constant `True` rather than
   derived from compiler source or an independent test.

The test suite therefore established that the frozen examples passed their
expected outputs, but not that all invalid Cartesian combinations fail closed
or that case-specific shortcuts are absent.

## Why The Apparent PASS Is Invalid

The preregistration required executable evidence for both gates. A boolean
whose value is assumed by the evaluator is not an audit witness.

This is not:

- evidence against the factorized theory;
- evidence for the factorized theory;
- a Provider failure;
- a semantic corpus failure.

It is:

`EXPERIMENT_INSTRUMENT_CONSTRUCTION_FAILURE`

## Preserved Boundary

No Provider call, CoreSlim write, retention write, baseline write, or relation
surface change occurred.

The v0.3H source and the invalid first result remain preserved in Git. The
version is not repaired or rerun.

## Next Version

v0.3I may inherit the frozen theory without changing its semantic expectations.
It must change only the validation instrument:

1. instantiate and compile all 24 status-effect pairs;
2. assert `UNRESOLVED -> BLOCK` plus
   `STATUS_EFFECT_INCONSISTENT` for all seventeen invalid pairs;
3. derive the no-case-shortcut and no-Provider-import gates from source;
4. preserve all twenty cases, six removals, thresholds, and theory rules;
5. freeze the corrected implementation before first v0.3I execution.
