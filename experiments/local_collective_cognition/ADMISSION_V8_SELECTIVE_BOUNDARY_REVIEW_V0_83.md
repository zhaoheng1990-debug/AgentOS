# Selective Evidence Boundary Review v0.83

## Status

**FRESH_HOLDOUT_DIAGNOSTIC_COMPLETE -
REJECT_BOUNDARY_REVIEW_OVER_DEMOTION.**

v0.83 addresses the residual v0.82 evidence/context errors without reopening
the successful context/reject compiler.

The staged workflow is:

1. A14 produces atomic effect evidence;
2. A16 compiles non-evidence spans into context versus reject;
3. A17 independently reviews only the resulting evidence and context spans;
4. Kernel permits evidence/context mutation only with a grounded, internally
   consistent boundary witness;
5. the A16 reject partition is immutable.

Provider does not receive upstream dispositions and cannot return policy
labels. A negative witness may demote evidence to context. A complete positive
witness may promote context to evidence. Missing, conflicting, or ungrounded
witnesses preserve the upstream state.

The sixth fresh holdout contains 12 balanced Evidence Inference test objects
not used by any local admission experiment through v0.82.

- benchmark gold: secondary coverage guard only;
- external typed reference: required before acceptance;
- prompt or contract tuning after freeze: forbidden;
- holdout re-execution: forbidden;
- candidate acceptance: false;
- Core or retention write: forbidden;
- production authority: false.

## Fresh Holdout Result

The baseline returned 11/12 valid receipts with one preserved contract failure.
A14, A16, and A17 each returned 12/12 valid receipts and complete partitions.
All preregistered integrity and budget conditions passed.

| Measure | Baseline | A14 | A14 + A16 | A14 + A16 + A17 |
|---|---:|---:|---:|---:|
| Benchmark evidence precision | 0.7500 | 1.0000 | 1.0000 | 0.4167 |
| Benchmark evidence recall | 0.6667 | 0.9583 | 0.9583 | 0.3333 |
| Benchmark evidence F1 | 0.6944 | 0.9722 | 0.9722 | 0.3611 |
| Evidence/context/reject spans | 16 / 20 / 8 | 23 / 25 / 0 | 23 / 4 / 21 | 8 / 19 / 21 |
| Arm physical tokens | 20,817 | 24,264 | 21,973 | 26,947 |

The composed A14+A16+A17 system consumed 73,184 physical tokens.

A17 made 15 mutations, all from evidence to context, and no context-to-evidence
promotion. The reject partition remained exactly invariant. Two ungrounded
boundary receipts were preserved upstream and did not mutate state.

## Failure Analysis

The mutation issue ledger shows broad compound negatives:

- `OUTCOME_POOLED_NOT_ISOLATED`: 12;
- `COMPARATOR_MISMATCH`: 11;
- `INTERVENTION_MISMATCH`: 10;
- `COMPARATOR_POOLED_NOT_ISOLATED`: 8;
- `NO_INDEPENDENT_EFFECT_STATEMENT`: 8;
- `TIMEPOINT_MISMATCH`: 6;
- `OUTCOME_MISMATCH`: 5.

The review task encouraged a lexical interpretation in which target components
not repeated inside one span were treated as mismatches. Absence of an explicit
component mention was therefore conflated with an explicit contradiction.
Grounded quotes proved source presence, but did not prove that the negative
boundary interpretation was warranted.

## Decision

`REJECT_BOUNDARY_REVIEW_OVER_DEMOTION`

The candidate is not sent to a full external typed panel. The evidence collapse
is too large and the attribution is already clear enough that full annotation
has low marginal information value.

The next boundary ontology must use ternary component states:
`MATCHED`, `EXPLICITLY_CONTRADICTED`, and `NOT_STATED`. Only an explicitly
contradicted component or quoted non-separable pooling may demote evidence.
`NOT_STATED` must preserve upstream state. Positive promotion still requires a
grounded independent effect statement and no explicit contradiction.
