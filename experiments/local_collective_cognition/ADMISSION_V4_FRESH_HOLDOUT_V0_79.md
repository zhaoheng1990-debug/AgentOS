# Minimal Semantic Witness Admission v0.79

## Decision

**REJECT_RUNTIME_INTEGRITY_WITH_POSITIVE_VALID-SUBSET_SIGNAL.**

v0.79 preserved the v0.76 baseline and the rejected v0.78 result. It replaced
Provider-authored policy labels with minimal semantic facts and deterministic
local policy derivation.

The Provider returned only:

1. target outcome scope;
2. independent target-effect support;
3. effect-basis codes;
4. non-effect contextual relevance;
5. rationale.

The Runtime derived object relation and handled receipt conflicts. The local
compiler derived evidence utility, disposition, admission state, the complete
partition, and downstream authorization.

## Freshness Boundary

The 12-case balanced holdout used a second set of locally unseen Evidence
Inference test-split objects. It did not overlap v0.65/v0.75, v0.77, or v0.78
objects.

- panel hash:
  `7b26828f64e4f31433a65ad5a98e41fd7384e0b72611a175d8c7598dba596b66`;
- preregistration hash:
  `16117ec3a6f11b0826a70af9963551790efb7d90dc80e4e139e818b1de38bd30`;
- Provider calls at freeze: 0;
- holdout re-execution allowed: false;
- pretraining contamination excluded: false.

The benchmark rationale set remained a secondary coverage guard. A new
external typed reference was required for semantic acceptance.

## Full Result

| Measure | v0.76 baseline | v0.79 candidate |
|---|---:|---:|
| Valid receipts | 12/12 | 9/12 |
| Contract failures | 0 | 3 |
| Complete partitions | 12/12 | 9/12 |
| Benchmark evidence precision | 0.8194 | 0.7222 |
| Benchmark evidence recall | 0.9167 | 0.7500 |
| Benchmark evidence F1 | 0.8556 | 0.7333 |
| Provider tasks | 12 | 12 |
| Physical attempts | 12 | 12 |
| Physical tokens | 21,393 | 24,847 |

The candidate added 3,454 tokens, a 16.1% increase. The full score includes
three failed candidate cases as zero and therefore cannot establish semantic
improvement.

## Valid-Subset Signal

On the nine cases where both arms produced valid partitions:

| Measure | v0.76 baseline | v0.79 candidate |
|---|---:|---:|
| Mean benchmark evidence F1 | 0.8074 | 0.9778 |
| Improved cases | 0 | 3 |
| Harmed cases | 0 | 0 |

The candidate:

- removed two false-positive admissions from `EI-CAL-11031`;
- removed one false-positive admission from `EI-CAL-3295`;
- corrected `EI-CAL-7252` from no admitted evidence to both benchmark
  rationale spans, which reported a valid no-difference result.

This is a positive diagnostic signal, not an acceptance result. It shows that
separating Provider semantic facts from Runtime policy can improve evidence
hygiene and recover null evidence when the receipt is valid.

## Failure Anatomy

All three failures were `ADMISSION_V4_SUPPORT_SCOPE_CONFLICT`.

In every failed receipt, the Provider selected
`TARGET_COMPONENT_OF_COMPOSITE` while also stating that the target had its own
separate values or statement and independently supported the target effect.
The rationales explicitly distinguished the target evidence, but the
categorical scope label used "component" to describe membership in a
multi-outcome list.

The remaining problem is therefore not duplicated policy fields. It is that
`TARGET_COMPONENT_OF_COMPOSITE` still bundles two independent questions:

1. is the target mentioned within a larger passage or outcome list?
2. is the target effect separately extractable?

A multi-outcome list with separate target numbers is not a non-separable
composite, but the category name encouraged that interpretation.

## v0.80 Design Constraint

The next receipt should replace outcome-scope categories with atomic facts:

1. exact target object mentioned: true or false;
2. target effect separately extractable: true or false;
3. independent target-effect support: true or false;
4. effect-basis codes;
5. non-effect contextual relevance: true or false;
6. bounded rationale.

Independent support must imply exact-target binding and separate
extractability. The Runtime should handle conflicts explicitly, while the
local compiler continues to derive all policy labels and state.

v0.79 must not be repaired and rerun on this holdout. A third unused-source
holdout is available for v0.80 and requires a new preregistration.

## Authority Boundary

- operational decision: `REJECT_RUNTIME_INTEGRITY`;
- external typed panel: not authorized;
- semantic acceptance: not established;
- runtime tuning, Core, retention, and production writes: not authorized.
