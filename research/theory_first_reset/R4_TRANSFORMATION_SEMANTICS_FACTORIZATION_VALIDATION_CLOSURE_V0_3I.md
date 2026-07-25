# R4 Transformation Semantics Factorization Validation Closure v0.3I

## Formal Status

`PASS_FACTORIZED_TRANSFORMATION_SEMANTICS_FORMAL_COHERENCE`

Evidence coordinate:

`SYNTHETIC_FORMAL_AUDIT`

Claim ceiling:

`FACTORIZED_TRANSFORMATION_SEMANTICS_FORMAL_COHERENCE_ONLY`

All sixteen frozen gates passed under the corrected v0.3I instrument.

## Version Boundary

v0.3H remains:

`FAIL_CONSTRUCTION_INVALID_GATE_IMPLEMENTATION`

v0.3I inherited the same theory, twenty cases, six removals, seven valid pair
expectations, seventeen invalid pair expectations, and thresholds. It changed
only the invalid-pair execution audit and source-derived boundary audit.

Freeze commits:

- v0.3H theory: `c233c70`;
- preserved invalid v0.3H instrument: `d43cbb1`;
- v0.3I preregistration: `ee3a44c`;
- corrected instrument freeze: `8395177`.

No same-version repair or relabelling occurred.

## Formal Results

| Quantity | Result |
| --- | ---: |
| frozen gates | 16/16 |
| frozen cases | 20/20 |
| Runtime actions | 20/20 |
| Cartesian status-effect pairs | 24 |
| admissible pairs | 7/7 |
| invalid pairs | 17/17 |
| invalid pairs returning `UNRESOLVED -> BLOCK` | 17/17 |
| invalid pairs carrying inconsistency error | 17/17 |
| removal tests | 6/6 |
| v0.3G disagreement families represented | 4/4 |
| Provider calls | 0 |
| protected writes | 0 |

The compiler source contained no case ID, case-family keyword, Provider or
network dependency, or protected-write dependency.

## Four Resolved Disagreement Families

### Calibration Verification

The factorized object distinguishes:

```text
VERIFIED_TRANSFORM + CLAIM_EQUIVALENT
ASSERTED_UNVERIFIED_TRANSFORM + UNKNOWN_EFFECT
```

The first may compile to `DEPENDENT_DISTINCT` under material uncertainty. The
second compiles to `UNRESOLVED`. Both block immediately, but their explanation
and revalidation requirements differ.

### Strict Subset

The candidate can simultaneously retain:

```text
SourceIdentity = PARTIAL_SOURCE
InformationEffect = INFORMATION_REDUCING
```

No enum competition is required. Runtime relation remains
`PARTIAL_OVERLAP`.

### Absence, Unverified, And Unknown

These are now distinct:

```text
NO_TRANSFORM + NOT_APPLICABLE
ASSERTED_UNVERIFIED_TRANSFORM + UNKNOWN_EFFECT
UNKNOWN_TRANSFORM_APPLICABILITY + UNKNOWN_EFFECT
```

They can share an immediate blocking action without collapsing their semantic
state or next validation need.

### Global Versus Claim Equivalence

`GLOBAL_EQUIVALENT` requires a full-domain or reversibility witness.
`CLAIM_EQUIVALENT` requires target-claim and tolerance binding. Both can
deduplicate when their distinct witness obligations are satisfied.

## Removal Evidence

Removing any of the following revoked exact-duplicate authority:

- transform-status witness;
- information-effect witness;
- full-domain witness;
- claim-tolerance witness.

Changing a verified transform to asserted-unverified while retaining a verified
effect produced `STATUS_EFFECT_INCONSISTENT`. Changing subset source identity
to unknown produced `UNRESOLVED`.

## Anti-Additive Assessment

Cost:

- one additional typed axis;
- seven admissible status-effect combinations instead of one six-value mixed
  enum;
- a 126-line pure compiler.

Gain:

- four prior disagreement families receive non-colliding representations;
- seventeen impossible combinations are mechanically rejected;
- no case-specific branch is added;
- no relation state or Runtime action is added;
- immediate action, explanation, and revalidation need remain separately
  representable.

The factorization therefore passes the formal anti-additive gate. It increases
surface vocabulary slightly while reducing semantic collision and exception
pressure.

## Theory Adjudication

### M1 Factorized Transformation Semantics

Supported on the frozen formal grid.

### M0 Single Enum Sufficient

Rejected for the formal object. A strict subset legitimately carries both a
source-overlap fact and an information-reduction fact, while no-transform,
unverified-transform, and unknown applicability require distinct
representations.

### M2 Full Transformation Graph Required

Not supported by this finite grid. The two axes were sufficient for every
frozen case. Natural and domain-specific transformations remain untested.

### M3 Action Equivalence Makes Split Redundant

Rejected formally. States with the same immediate action can require different
evidence, explanations, drift handling, and next validation steps.

### M4 Factorization Complexity Exceeds Cbit

Not supported on the formal grid. One added axis resolved four anomaly families
without expanding the decision surface.

## Experimental Phenomenon

The main phenomenon is many-to-one action projection:

```text
different semantic states
  -> same immediate BLOCK action
  -> different explanation and revalidation trajectory
```

This reinforces the distinction between Runtime cognition and mechanical
action. A Runtime that stores only the final action loses information required
for future cognition, even when the immediate decision is safe.

## Deterministic Replay

Two complete runs were byte-identical:

| Artifact | SHA-256 |
| --- | --- |
| `result.json` | `46f6b6ec3ad683d73b49797bc70c3d7203ead485b610fd68049ef5d91d8d90cf` |
| `hash_inventory.json` | `55dd7f88d0d7f9d06dae46bf90ac32830b99577850417da1d3b2b7723a2fa071` |
| `closure.json` | `2c1ac0e1445e6759dd3e0d0649554d1fe5f0aeb575aeebbb78418e94bc0e609e` |

Validation:

- R4 experiment suite: 66 passed;
- AgentOS CoreSlim suite: 394 passed.

## Boundaries

This pass does not establish:

- Provider ability to infer the factorized axes;
- improvement over the legacy single enum;
- witness truth;
- natural-evidence safety;
- cross-Provider transfer;
- CoreSlim integration readiness.

## Next Research Object

`R4_V0_3J_FACTORIZATION_CAUSAL_BENEFIT`

The next theory should preregister a matched fresh-corpus comparison:

1. legacy `InformationRelation` arm;
2. factorized `TransformStatus + InformationEffect` arm;
3. identical public evidence and Provider;
4. Runtime action compiled independently in each arm;
5. false deduplication as a hard failure;
6. semantic ambiguity, exact inference, revalidation resolution, and token cost
   measured separately.

Provider calls remain paused until that comparative theory and corpus are
frozen.
