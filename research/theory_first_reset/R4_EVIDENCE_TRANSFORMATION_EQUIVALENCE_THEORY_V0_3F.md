# R4 Evidence Transformation Equivalence Theory v0.3F

## Status

`FROZEN_FOR_ZERO_PROVIDER_FORMAL_VALIDATION`

This window inherits MethodologyKernel v1.1.
If any experimental conclusion conflicts with this kernel, the conflict must be
explicitly stated and converted into a theory revision, downgrade, or caveat.

Evidence coordinate:

`SYNTHETIC_FORMAL_AUDIT`

This packet is a theory writeback from the preserved v0.3E `R43E-06`
disagreement. It does not relabel that case and does not authorize Provider
calls.

## Research Object

`EVIDENCE_TRANSFORMATION_EQUIVALENCE`

Two packets are transformation-equivalent for composition when counting both
would add no target-relevant evidence beyond one canonical packet, and this
equivalence can be established from replayable transformation and uncertainty
receipts.

Transformation equivalence is:

- relative to a target claim;
- stricter than common source identity;
- compatible with different representations;
- invalidated by material added uncertainty or target-relevant information;
- unresolved when critical attributes are unknown.

Object chain:

```text
EvidenceTransformationEquivalence
  -> typed transformation attributes
  -> deterministic relation-state compilation
  -> existing Runtime action mapping
  -> DEDUPE_AND_COMBINE or BLOCK
```

## Attribute Space

### SourceIdentity

- `SAME_SOURCE`;
- `PARTIAL_SOURCE`;
- `DISTINCT_SOURCE`;
- `UNKNOWN_SOURCE`.

### LineageCoupling

- `SAME_PIPELINE`;
- `SEPARATE_PIPELINES`;
- `UNKNOWN_PIPELINE`;
- `NOT_APPLICABLE`.

### InformationRelation

- `VERIFIED_GLOBAL_EQUIVALENCE`;
- `VERIFIED_CLAIM_EQUIVALENCE`;
- `INFORMATION_REDUCING`;
- `INFORMATION_AUGMENTING`;
- `UNVERIFIED_TRANSFORM`;
- `NOT_APPLICABLE`.

### AddedUncertainty

- `IMMATERIAL_FOR_CLAIM`;
- `MATERIAL_FOR_CLAIM`;
- `UNKNOWN_UNCERTAINTY`;
- `NOT_APPLICABLE`.

### TargetClaimRelation

- `SAME_TARGET_CLAIM`;
- `DIFFERENT_TARGET_CLAIM`;
- `UNKNOWN_TARGET_CLAIM`.

Every value must be explicit. No compiler default may infer a missing
attribute.

## Formal Compilation Order

The first matching rule wins:

1. unknown source, pipeline, transformation, uncertainty, or target claim
   needed for the decision -> `UNRESOLVED`;
2. different target claim -> `SCOPE_INCOMPATIBLE`;
3. partial source identity -> `PARTIAL_OVERLAP`;
4. distinct sources plus separate pipelines -> `INDEPENDENT_DISTINCT`;
5. distinct sources with shared pipeline -> `DEPENDENT_DISTINCT`;
6. same source plus verified global or claim equivalence, immaterial
   uncertainty, and same target claim -> `EXACT_DUPLICATE`;
7. same source with reducing or augmenting information, material uncertainty,
   and same target claim -> `DEPENDENT_DISTINCT`;
8. otherwise -> `UNRESOLVED`.

Existing Runtime action mapping remains:

| Relation | Action |
| --- | --- |
| `INDEPENDENT_DISTINCT` | `COMBINE` |
| `EXACT_DUPLICATE` | `DEDUPE_AND_COMBINE` |
| all other states | `BLOCK` |

No seventh relation state is introduced.

## Leading Model

`M1_ATTRIBUTE_COMPILATION_SUFFICIENCY`

The five attributes are sufficient to compile common evidence transformations
into the existing six relation states and three actions without a new enum.

Predictions:

- renaming, lossless compression, exact unit conversion, and verified
  claim-preserving redaction compile to `EXACT_DUPLICATE`;
- calibrated conversion compiles to `EXACT_DUPLICATE` only when its uncertainty
  is explicitly immaterial for the target claim;
- aggregation, lossy summary, stochastic transformation, and model-derived
  output compile to `DEPENDENT_DISTINCT`;
- subset versus full source compiles to `PARTIAL_OVERLAP`;
- different target claims compile to `SCOPE_INCOMPATIBLE`;
- missing critical witnesses compile to `UNRESOLVED`;
- removal of a required equivalence witness revokes deduplication.

## Rival Models

### M0_SOURCE_IDENTITY_SUFFICIENCY

One source item is enough to classify every transformation as exact duplicate.

Rejected if same-source cases legitimately compile to different relations or
actions.

### M2_REPRESENTATION_IDENTITY_REQUIRED

Only byte-identical or text-identical packets may be deduplicated.

Rejected if verified lossless or exact unit transformations remain
claim-equivalent and safely deduplicate.

### M3_NEW_RELATION_STATE_REQUIRED

Transformed-equivalent evidence cannot be represented by the existing
`EXACT_DUPLICATE` state without semantic distortion.

Supported if the five attributes produce cases whose safe action is
deduplication but whose relation cannot coherently compile to an existing state.

### M4_TARGET_RELATIVE_EQUIVALENCE_UNSAFE

Claim-relative equivalence is too permissive because globally lossy
transformations may hide future information needs.

Signature:

- a redacted or coarsened packet passes the current claim gate but creates
  negative transfer when reused for a broader claim.

This zero-Provider experiment can expose the scope boundary but cannot measure
future negative transfer.

### M5_UNCERTAINTY_THRESHOLD_UNDERDEFINED

`IMMATERIAL_FOR_CLAIM` cannot be validated without an explicit claim tolerance
or uncertainty witness.

Supported if the compiler accepts the label without requiring a witness
reference and tolerance binding.

## Required Witnesses

Every candidate must include:

- source witness reference;
- transformation witness reference when a transform is present;
- target-claim witness reference;
- uncertainty witness reference when uncertainty is not `NOT_APPLICABLE`;
- claim-tolerance witness reference for `VERIFIED_CLAIM_EQUIVALENCE` or
  `IMMATERIAL_FOR_CLAIM`.

Missing required witnesses block compilation to `EXACT_DUPLICATE`.

The compiler validates witness presence and binding, not their real-world
truth.

## Discriminating Predictions

| Case family | M1 | M0 | M2 | M3 |
| --- | --- | --- | --- | --- |
| rename or lossless compression | deduplicate | deduplicate | rename only | new state |
| exact unit conversion | deduplicate | deduplicate | block | new state |
| calibrated, immaterial error | deduplicate | deduplicate | block | new state |
| calibrated, material error | block | deduplicate | block | block |
| aggregate or model output | block | deduplicate | block | block |
| missing transform witness | unresolved | deduplicate | block | unresolved |

## Engineering Derivation Contract

| Engineering object | Frozen variable | Minimality | Removal test | Authority |
| --- | --- | --- | --- | --- |
| `TransformationRelationCandidate` | five typed attributes plus witnesses | one immutable contract | removal returns to source-only ambiguity | candidate only |
| `TransformationRelationCompiler` | ordered formal rules | pure deterministic function | removal leaves action unresolved | mechanical compiler |
| `TransformationGrid` | rival-discriminating cases | finite 18-case surface | removal hides boundary families | fixture only |
| `TransformationRemovalAudit` | witness and attribute necessity | reuses same cases | removal cannot test dedupe revocation | diagnostic only |

The existing relation graph compiler and composition action mapping remain
unchanged.

## Proxy Validity Limits

Passing establishes only internal coherence of the attribute compiler on the
frozen grid.

It does not establish:

- real transform correctness;
- calibration validity;
- actual information equivalence;
- Provider ability to infer the attributes;
- natural evidence safety;
- CoreSlim integration readiness.

## Falsification Conditions

Reject M1 for this construction if:

- any frozen grid case compiles to the wrong relation or action;
- a required witness can be removed without revoking deduplication;
- source identity alone determines all same-source cases;
- a new relation state is required to express a safe action;
- two complete runs differ.

Revise the object if target-relative equivalence cannot be represented without
future-scope metadata.

## Anti-Additive Audit

Object upgrade:

```text
telemetry calibration exception
  -> evidence transformation equivalence attributes
```

Not added:

- a telemetry branch;
- a seventh relation enum;
- Provider prompt fields;
- a second composition runtime;
- a production policy.

Added:

- one candidate contract;
- one pure compiler;
- one formal grid;
- one removal audit.

## Stop And Rollback

Stop if:

- a frozen case expectation changes after execution;
- a special-case transform name enters compiler logic;
- Provider calls occur;
- CoreSlim, retention, or baseline writes occur;
- the experiment requires modifying the existing relation graph compiler.

Rollback deletes only the standalone v0.3F candidate modules and ignored
outputs.

