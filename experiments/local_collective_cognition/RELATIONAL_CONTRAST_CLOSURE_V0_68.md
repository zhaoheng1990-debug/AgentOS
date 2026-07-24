# Relational Contrast v0.68 Closure

## Decision

**CLOSED: calibration rejected; fresh holdout not executed.**

v0.68 replaced comparison orientation with stable arm IDs and explicit
subject/reference relations. It is positive mechanism evidence, but not a
calibration pass.

## Result

| Metric | Direct baseline | v0.68 candidate |
| --- | ---: | ---: |
| Valid receipts | 11/12 | 12/12 |
| Label accuracy | 0.7500 | 0.8333 |
| Evidence F1 | 0.9000 | 0.9556 |
| Rationale token F1 | 0.8922 | 0.9443 |
| Effective Cbit | 0.8474 | 0.9111 |
| Tokens | 41,101 | 69,124 |

All 12 frames, bases, and compiler receipts were valid. There were zero
Provider contract failures and zero compiler failures. `EI-CAL-11179` and
`EI-CAL-13793` were corrected. `EI-CAL-8555` regressed to an explicit
abstention, and `EI-CAL-5842` remained wrong.

## Observed Mechanisms

Stable arm IDs eliminated the two alias/string failures in v0.67. Separating
evidence role from significance preserved exact non-significant evidence and
allowed the compiler to produce `NO_DIFFERENCE`.

For `EI-CAL-5842`, the Provider rationale correctly said the intervention was
lower than the comparator, but the structured field said `SUBJECT_HIGHER`.
Schema completeness cannot detect a semantic contradiction between prose and
its enum.

For `EI-CAL-8555`, the evidence reported no cell-related serious adverse
effects but did not provide a comparative statistic. The compiler abstained
instead of inventing significance. A future benchmark bridge must explicitly
represent `NO_COMPARATIVE_EFFECT_REPORTED` or justify a benchmark-specific
mapping rather than smuggling it through `SUBJECT_LOWER`.

## Boundary

- Fresh holdout Provider calls: **0**
- Frozen holdout hash:
  `5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1`
- CoreSlim changes: **none**
- Raw benchmark files in repository: **0**

## Next Candidate

v0.69 should add span-anchored relation witnesses:

1. exact quoted subject surface bound to a frame alias and local arm ID;
2. exact quoted relation surface;
3. local substring and alias-membership checks;
4. an explicit non-comparative absence state;
5. no Provider authority over the deterministic label.

This must be a new preregistered version. v0.68 remains frozen.
