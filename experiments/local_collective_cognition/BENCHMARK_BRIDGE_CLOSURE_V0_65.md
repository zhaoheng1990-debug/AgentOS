# Benchmark Bridge v0.65 Closure

## Decision

**CLOSED: calibration passed; frozen test-split transfer rejected.**

v0.65 establishes a real but bounded benefit from staged evidence
objectification. It does not establish that the staged mechanism transfers as
a complete replacement for one-pass inference.

## What Was Built

- Pinned Evidence Inference source adapter and external cache boundary.
- ERASER-compatible hard-rationale and token-overlap scoring semantics.
- Nine-case balanced validation calibration panel.
- Thirty-six-case balanced, hash-selected test-split holdout.
- `A0_ONE_PASS` evidence partition and label receipt.
- `A1_SPAN_ADMISSION -> A1_STAGED_BINDING` receipt chain.
- Hash-bound preregistration, source lock, replay, rollback, and no-write gates.

All modules remain local to
`experiments/local_collective_cognition`. Raw benchmark CSV and split files are
absent from the repository. AgentOS CoreSlim was not modified.

## Calibration

| Metric | A0 one-pass | A1 staged |
| --- | ---: | ---: |
| Valid receipts | 9/9 | 9/9 |
| Contract failures | 0 | 0 |
| Cross-type overlap | 0 | 0 |
| Label accuracy | 0.8889 | 1.0000 |
| Object-binding proxy | 1.0000 | 1.0000 |
| Evidence F1 | 0.9556 | 0.9630 |
| Rationale token F1 | 0.9739 | 0.9896 |
| Effective Cbit | 0.9395 | 0.9842 |
| Tokens | 13,853 | 30,135 |
| Cbit / 1k tokens | 0.6103 | 0.2939 |

Staging corrected the `p=0.06` trend case that one-pass had promoted to an
effect. It also removed two irrelevant admissions. The cost was 2.175 times
more tokens and lower Cbit efficiency per token.

## Test-Split Holdout

| Metric | A0 one-pass | A1 staged |
| --- | ---: | ---: |
| Valid receipts | 36/36 | 35/36 |
| Contract failures | 0 | 1 |
| Cross-type overlap | 0 | 0 |
| Label accuracy | 0.9444 | 0.9167 |
| Object-binding proxy | 1.0000 | 0.9722 |
| Evidence precision | 0.8796 | 0.9630 |
| Evidence recall | 0.9722 | 0.9722 |
| Evidence F1 | 0.9120 | 0.9667 |
| Rationale token F1 | 0.9126 | 0.9641 |
| Effective Cbit | 0.9230 | 0.9491 |
| Tokens | 57,768 | 122,063 |
| Cbit / 1k tokens | 0.5752 | 0.2799 |

A1 improved evidence precision, rationale quality, and aggregate effective
Cbit, but it failed the frozen transfer gate:

1. `EI-CAL-13793` omitted two admitted contextual spans from the final
   partition, so the receipt was rejected.
2. `EI-CAL-11179` treated a directional trend at `p=0.07` as a significant
   decrease, changing a correct one-pass null label into an error.
3. `EI-CAL-5842` failed to reverse the relation when the passage stated the
   effect of the low-control comparator rather than the high-control
   intervention.

The `13793` case also mixes significant self-report and borderline
accelerometer results at the same timepoint. This exposes a benchmark-derived
material-ambiguity boundary rather than a clean single-label object.

## Interpretation

The staged mechanism is useful for **evidence hygiene**, especially excluding
same-article passages about a different object. More cognitive work did
increase aggregate Cbit, consistent with the working hypothesis that extra
iterations can compensate for a weaker single pass.

The experiment also shows why evidence admission alone is insufficient.
Correct evidence can still be converted into the wrong claim when the runtime
lacks explicit semantic coordinates for significance, comparator orientation,
measurement method, and timepoint. The next gain should come from making those
coordinates first-class receipts, not from adding another generic review
round.

## Claim Boundary

- Supported: staged admission improved evidence F1 and aggregate effective
  Cbit on this frozen candidate-rationale test panel.
- Not supported: full test-split transfer of the staged mechanism.
- Not claimed: benchmark-native Evidence Inference performance.
- Not claimed: pretraining-fresh generalization.
- Not authorized: Core, memory, retention, baseline, or global pointer writes.

## Verification

- Focused v0.65 tests: 12 passed.
- Full local collective cognition pack: 427 passed.
- AgentOS CoreSlim: 394 passed.
- Raw benchmark files in repository: 0.
- Largest v0.65 runtime/data module: 294 lines.
- CoreSlim version: `0.4.0-alpha.21`.

## Next Candidate

v0.66 should test a typed semantic-basis chain:

`Object/Timepoint Binding -> Comparator Orientation -> Significance Basis ->
Material Ambiguity -> Outcome Label`

Every admitted span should receive its own typed record so completeness is
structural rather than dependent on parallel arrays. This is a new candidate
experiment and must not overwrite the v0.65 negative transfer result.
