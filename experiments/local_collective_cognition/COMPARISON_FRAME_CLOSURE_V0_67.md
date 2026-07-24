# Comparison Frame v0.67 Closure

## Decision

**CLOSED: calibration rejected; fresh holdout not executed.**

v0.67 successfully removed free Provider synthesis from the label-authority
path, but the Provider-facing relational vocabulary remained under-specified.
The result is a useful architectural separation and a failed end-to-end
mechanism.

## Calibration

| Metric | A1 direct binding | A3 frame + compiler |
| --- | ---: | ---: |
| Valid final receipts | 11/12 | 10/12 |
| Total candidate failures | 1 | 2 |
| Label accuracy | 0.7500 | 0.5000 |
| Evidence F1 | 0.9000 | 0.6667 |
| Rationale token F1 | 0.8922 | 0.6667 |
| Effective Cbit | 0.8474 | 0.6111 |
| Provider tasks | 23 | 22 |
| Tokens | 41,101 | 57,088 |
| Cbit / 1k tokens | 0.2474 | 0.1285 |

The candidate produced ten valid frames, ten valid bases, and ten compiled
receipts. The deterministic compiler had zero failures. Calibration corrected
`EI-CAL-5842`, harmed four previously correct cases, and abstained on
`EI-CAL-11179` and `EI-CAL-13793`.

## Layer Diagnosis

### Frame Contract

`EI-CAL-3189` correctly represented Kuntai, Tibolone, and Control as grouped
arms compared with baseline, but omitted the abstract baseline from
`study_arms`. `EI-CAL-8861` used descriptive arm names while focal members used
short aliases. Both were semantically plausible and failed only the exact
string-subset contract. Object identity needs explicit aliases or stable local
IDs rather than display-string equality.

### Basis Semantics

`EI-CAL-13790` and `EI-CAL-5791` were direct statements about the intervention
relative to control, yet the Provider labeled them
`COMPARATOR_VS_INTERVENTION`. The enum conflated grammatical mention order with
the mathematical subject/reference relation. The compiler correctly obeyed
the supplied coordinate and therefore produced the wrong normalized labels.

`EI-CAL-11179` and `EI-CAL-13793` correctly recorded non-significant or
borderline results, but marked those spans `REJECT_AFTER_BASIS`. This erased
the exact evidence needed to compile `NO_DIFFERENCE`. Evidence relevance,
statistical significance, and final effect state must remain separate axes.

### Deterministic Compiler

The compiler corrected the known comparator-first failure in `EI-CAL-5842`,
preserved the unconstrained-timepoint case `EI-CAL-9330`, emitted no
contract failures, and replayed deterministically. It should remain the final
label authority in the next candidate.

## Holdout Boundary

- Frozen holdout hash:
  `5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1`
- Fresh holdout Provider calls: **0**
- Raw benchmark files in repository: **0**
- CoreSlim changes: **none**

## Next Candidate

v0.68 should keep the compiler and replace the Provider-facing basis with:

1. stable local arm IDs plus Provider-issued aliases;
2. explicit `subject_group_id` and `reference_group_id` per evidence span;
3. direction bound to those IDs, with no orientation enum;
4. evidence relevance/admissibility independent from significance;
5. local alias and relation checks that do not perform semantic extraction.

This is a new preregistered mechanism. v0.67 must not be retroactively tuned or
rerun under the same version.
