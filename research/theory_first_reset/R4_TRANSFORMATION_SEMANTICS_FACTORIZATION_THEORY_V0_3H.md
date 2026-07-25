# R4 Transformation Semantics Factorization Theory v0.3H

## Status

`FROZEN_FOR_ZERO_PROVIDER_FORMAL_VALIDATION`

This window inherits MethodologyKernel v1.1.
If any experimental conclusion conflicts with this kernel, the conflict must be
explicitly stated and converted into a theory revision, downgrade, or caveat.

Evidence coordinate:

`SYNTHETIC_FORMAL_AUDIT`

Inherited objects:

- v0.3F claim-relative transformation equivalence;
- v0.3G exact `SourceIdentity`, `LineageCoupling`, `AddedUncertainty`, and
  `TargetClaimRelation` performance;
- v0.3G preserved `InformationRelation` 8/12 semantic failure;
- Runtime-owned deterministic relation and action authority.

Preserved caveats:

- v0.3G is immutable and cannot be relabelled or rerun;
- action safety on one corpus does not excuse semantic ambiguity;
- this formal experiment cannot validate Provider inference;
- future-claim reuse safety remains pending.

## Object Upgrading Audit

Current object:

`InformationRelation`

Observed overload:

1. transformation existence;
2. transformation verification;
3. information preservation or change;
4. global versus claim-scoped equivalence.

One enum therefore mixes transform status with information effect. The v0.3G
errors were not four unrelated exceptions; they were four projections of this
same object collision.

Proposed lift:

```text
InformationRelation
  -> TransformStatus
  + InformationEffect
```

Upper ontology chain:

```text
EvidenceTransformationSemantics
  -> TransformStatus + InformationEffect
  -> deterministic relation compilation
  -> existing Runtime action
```

The lift is accepted only if it resolves all four frozen disagreement families,
requires no case-specific branch, preserves action safety, and makes invalid
attribute combinations mechanically detectable.

## Factorized Attribute Space

### TransformStatus

- `NO_TRANSFORM`;
- `VERIFIED_TRANSFORM`;
- `ASSERTED_UNVERIFIED_TRANSFORM`;
- `UNKNOWN_TRANSFORM_APPLICABILITY`.

### InformationEffect

- `GLOBAL_EQUIVALENT`;
- `CLAIM_EQUIVALENT`;
- `INFORMATION_REDUCING`;
- `INFORMATION_AUGMENTING`;
- `UNKNOWN_EFFECT`;
- `NOT_APPLICABLE`.

### Valid Pairings

| Transform status | Admissible information effect |
| --- | --- |
| `NO_TRANSFORM` | `NOT_APPLICABLE` |
| `VERIFIED_TRANSFORM` | global, claim, reducing, or augmenting |
| `ASSERTED_UNVERIFIED_TRANSFORM` | `UNKNOWN_EFFECT` |
| `UNKNOWN_TRANSFORM_APPLICABILITY` | `UNKNOWN_EFFECT` |

All other pairings are structurally inconsistent and compile to `UNRESOLVED`.

The Cartesian surface has 24 possible pairs, but only seven are semantically
admissible. Explicit consistency rules prevent the unused combinations from
becoming free states.

## Witness Rules

Every candidate requires:

- source witness;
- lineage witness when lineage is applicable;
- transform-status witness;
- information-effect witness;
- target-claim witness;
- uncertainty witness when uncertainty is applicable.

Additional bindings:

- `GLOBAL_EQUIVALENT` requires a reversibility or full-domain preservation
  witness;
- `CLAIM_EQUIVALENT` requires a target-claim and tolerance witness;
- `IMMATERIAL_FOR_CLAIM` requires a tolerance witness;
- unknown or unverified values require a missing-fact or absence witness.

Witness presence is mechanically validated. Witness truth is not established
by this experiment.

## Formal Compilation Order

The first matching rule wins:

1. missing required witness or invalid status-effect pair -> `UNRESOLVED`;
2. materially unknown source, target, lineage, transform status, information
   effect, or uncertainty -> `UNRESOLVED`;
3. different target claim -> `SCOPE_INCOMPATIBLE`;
4. partial source identity -> `PARTIAL_OVERLAP`;
5. distinct sources plus separate pipelines -> `INDEPENDENT_DISTINCT`;
6. distinct sources plus shared pipeline -> `DEPENDENT_DISTINCT`;
7. same source plus verified global or claim equivalence, valid scope binding,
   and immaterial or non-applicable uncertainty -> `EXACT_DUPLICATE`;
8. same source plus verified reducing or augmenting effect, or material
   uncertainty -> `DEPENDENT_DISTINCT`;
9. otherwise -> `UNRESOLVED`.

The existing relation states and action mapping remain unchanged.

## Leading Model

`M1_FACTORIZED_TRANSFORMATION_SEMANTICS`

The two-axis object is sufficient to represent the v0.3G disagreement families
without semantic collision and to compile a finite formal grid into the
existing Runtime relation and action surface.

Predictions:

- registered-but-unverified calibration is distinguishable from verified
  claim-equivalent calibration;
- strict subset can be both `PARTIAL_SOURCE` and
  `INFORMATION_REDUCING`;
- no transform is distinguishable from unknown transform applicability and
  asserted unverified transform;
- global equivalence requires a stronger witness than claim equivalence;
- both global and claim equivalence may safely compile to exact duplicate under
  their respective witnesses;
- invalid cross-axis combinations fail closed.

## Rival Models

### M0_SINGLE_ENUM_SUFFICIENT

The v0.3G failures can be removed by sharper definitions inside the original
enum. Factorization adds no discriminating information.

Rejected if one case legitimately needs simultaneous transform-status and
information-effect facts or if absence, unknown applicability, and unverified
assertion require distinct states.

### M2_FULL_TRANSFORMATION_GRAPH_REQUIRED

Two axes are still insufficient; safe judgment requires an unrestricted
transformation graph or domain-specific model.

Supported if frozen cases remain ambiguous after explicit status, effect,
scope, uncertainty, and witnesses are supplied.

### M3_ACTION_EQUIVALENCE_MAKES_SPLIT_REDUNDANT

Because several distinctions compile to the same action, the semantic split
has no Runtime value.

Rejected if the split changes relation, revalidation need, explanation, or
future-scope binding even when immediate action is unchanged.

### M4_FACTORIZATION_COMPLEXITY_EXCEEDS_CBIT

The split merely expands vocabulary. It is supported if it requires
case-specific branches, increases unresolved cases without exposing missing
facts, or cannot resolve all four v0.3G disagreement families.

## Formal Grid

Twenty cases must cover:

- all seven valid status-effect pairings;
- invalid pairings;
- global versus claim equivalence;
- material versus immaterial uncertainty;
- same, partial, distinct, and unknown source identity;
- separate, shared, and unknown lineage;
- same, different, and unknown target claim;
- the four v0.3G disagreement families;
- witness removals.

No transform name or case family may appear in compiler branches.

## Complexity Criterion

The factorization passes the anti-additive gate only if:

1. all four disagreement families obtain non-colliding representations;
2. seven valid status-effect pairs are generated by generic consistency rules;
3. all seventeen invalid Cartesian pairs fail closed;
4. no new relation state or action is introduced;
5. compiler decision branches do not depend on case identity;
6. removal of either axis or a scope witness changes or revokes the intended
   semantic authority.

## Falsification Conditions

Reject M1 for this construction if:

- any frozen case compiles incorrectly;
- any invalid status-effect pair becomes actionable;
- the subset case cannot preserve both partial-source and reducing-effect facts;
- global equivalence is admitted without full-domain witness;
- claim equivalence is admitted without claim and tolerance binding;
- a case-specific branch is required;
- a seventh relation state or new action is required;
- two complete runs differ.

## Anti-Additive Boundary

Added:

- one factorized candidate contract;
- one pure compiler;
- one finite grid and invalid-pair audit;
- one removal audit.

Not added:

- Provider prompt repair;
- Provider call;
- domain transform registry;
- second Runtime;
- new relation state;
- CoreSlim or retention integration.

## Claim Ceiling

Passing establishes only:

`FACTORIZED_TRANSFORMATION_SEMANTICS_FORMAL_COHERENCE`

It does not establish Provider inferability, witness truth, real-world
equivalence, future reuse safety, or production readiness.

## Stop And Rollback

Stop if any expectation changes after first execution, any Provider call
occurs, a special-case branch is needed, or a protected write occurs.

Rollback removes only standalone v0.3H candidate modules and ignored outputs.
