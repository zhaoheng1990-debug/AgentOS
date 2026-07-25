# R4 Provider Transformation Attribute Inference Closure v0.3G

## Formal Status

`FAIL_SEMANTIC_WITH_ZERO_RUNTIME_ACTION_HARM`

Evidence coordinate:

`INTERNAL_PROJECT_PROVIDER_EVIDENCE_ON_FRESH_SYNTHETIC_CORPUS`

Claim ceiling:

`SAME_PROVIDER_FRESH_SYNTHETIC_TRANSFORMATION_ATTRIBUTE_INFERENCE_ONLY`

The frozen v0.3G PASS criteria were not met. Twelve of fifteen gates passed.
The failure is preserved without a repeated call, prompt repair, relabel,
threshold change, or same-version rerun.

## Frozen Coordinate

- theory freeze commit: `9bb0857`;
- corpus and implementation freeze commit: `aa43e49`;
- Provider: DeepSeek;
- requested and returned model: `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- logical calls: 1/1;
- physical attempts: 1/2;
- total tokens: 6011/20000;
- private reference exposed: false;
- Provider relation or action authority: false;
- CoreSlim, retention, and baseline writes: zero.

The first physical attempt produced a mechanically valid twelve-receipt
envelope. No retry was used.

## Aggregate Results

| Metric | Result |
| --- | ---: |
| frozen gates | 12/15 |
| exact five-attribute tuples | 8/12 |
| exact attribute evidence-reference sets | 12/12 |
| counterfactual pairs | 5/6 |
| Runtime relations | 11/12 |
| Runtime actions | 12/12 |
| false combine | 0 |
| false deduplicate | 0 |
| false block | 0 |

Per-attribute exact accuracy:

| Attribute | Result |
| --- | ---: |
| `SourceIdentity` | 12/12 |
| `LineageCoupling` | 12/12 |
| `InformationRelation` | 8/12 |
| `AddedUncertainty` | 12/12 |
| `TargetClaimRelation` | 12/12 |

Failed gates:

1. each attribute at least 10/12;
2. exact five-attribute tuple at least 9/12;
3. all true missing-attribute cases preserve the frozen unknown form.

The evidence-reference gate passed exactly. Every proposed attribute cited the
frozen case-local reference set, and no cross-case or forbidden authority field
entered canonical state.

## Four Semantic Disagreements

### R43G-02: Registered Calibration

Private reference:

`VERIFIED_CLAIM_EQUIVALENCE`

Provider:

`UNVERIFIED_TRANSFORM`

The public case said that packet B applied a registered calibration but did not
explicitly state that the calibration's claim-preserving behavior had been
verified. The Provider used a stricter verification reading. Runtime changed
`DEPENDENT_DISTINCT` to `UNRESOLVED`, but both map to `BLOCK`.

This is partly a corpus-reference ambiguity rather than clean evidence of
Provider error. The frozen reference remains unchanged.

### R43G-09: Strict Subset

Private reference:

`NOT_APPLICABLE`

Provider:

`INFORMATION_REDUCING`

The private model treated subset relation as owned by `SourceIdentity`, so
`InformationRelation` was not applicable. The Provider also represented the
subset operation's information effect. Both descriptions can be true:

```text
SourceIdentity = PARTIAL_SOURCE
InformationEffect = INFORMATION_REDUCING
```

The current single enum forces these compatible facts into an artificial
choice. Runtime still compiled `PARTIAL_OVERLAP -> BLOCK`.

### R43G-10: No Transformation Record

Private reference:

`UNVERIFIED_TRANSFORM`

Provider:

`NOT_APPLICABLE`

The case stated that no transformation record was available. This can mean
either:

- a transformation may exist but is unverified;
- no transformation relation has been established and applicability is
  unknown.

The current enum lacks a clean distinction between `NO_TRANSFORM`,
`UNKNOWN_TRANSFORM_APPLICABILITY`, and `ASSERTED_UNVERIFIED_TRANSFORM`.
Runtime remained `UNRESOLVED -> BLOCK`.

### R43G-11: Exact Speed Conversion

Private reference:

`VERIFIED_GLOBAL_EQUIVALENCE`

Provider:

`VERIFIED_CLAIM_EQUIVALENCE`

The conversion formula was exact, while the task was explicitly framed around
one threshold claim. The Provider selected the narrower valid scope instead of
asserting global equivalence. Both compiled to
`EXACT_DUPLICATE -> DEDUPE_AND_COMBINE`.

This disagreement exposes a missing rule for when exact invertibility warrants
global rather than claim-scoped equivalence.

## Experimental Phenomena

### 1. Semantic Error Was Fully Localized

All four disagreements occurred in `InformationRelation`. The other four
attributes and all evidence bindings were exact. This rejects a broad account
in which natural descriptions are generally too underdetermined for structured
Provider support.

### 2. Runtime Absorbed Provider Error

Attribute tuple accuracy was only 8/12, but Runtime action accuracy was 12/12.
The compiler's ordered constraints absorbed the disagreements:

- material uncertainty blocked even when transform verification differed;
- partial source identity dominated information-effect disagreement;
- unknown source and lineage forced unresolved;
- both global and claim equivalence admitted the same bounded deduplication.

This is positive evidence for the intended division of cognition:

```text
Provider semantic support
  + Runtime object hierarchy and decision boundary
  -> safer result than Provider label accuracy alone
```

It is not evidence that attribute accuracy can be ignored. A different case
could place the same disagreement on a harmful action boundary.

### 3. The Failed Attribute Is Not Orthogonal

`InformationRelation` currently combines at least four questions:

1. does a transformation exist;
2. is that transformation verified;
3. what information effect does it have;
4. is equivalence global or limited to the current claim.

The four errors are different manifestations of this conflation. Another
prompt patch would not resolve the object-level overlap.

### 4. Evidence Binding Was Not Decorative

All 60 attribute-level reference sets matched the private reference. The
Provider did not obtain plausible labels while citing arbitrary evidence.
`M3_WITNESS_DECORATION` is not supported on this corpus.

## Theory Adjudication

### M1 Structured Attribute Inference Adequacy

Rejected as stated because the frozen per-attribute and exact-tuple thresholds
failed.

Bounded retained subclaim:

Four attributes and evidence binding were adequate on this surface, and the
Provider-supported Runtime chain produced zero action harm.

### M0 Natural Description Underdetermination

Not supported as a global explanation. Underdetermination was concentrated in
one overloaded attribute.

### M2 Attribute Label Coupling

Not strongly supported. Five of six frozen counterfactual pairs passed. In the
sixth pair, the Provider still distinguished verified and unverified
transforms, but the verified endpoint was scoped as claim-equivalent instead of
global-equivalent.

### M3 Witness Decoration

Not supported: 12/12 cases and all attribute reference sets were exact.

### M4 Boundary Attribute Bottleneck

Supported. Every semantic failure occurred in `InformationRelation`.

### M5 Compiler Harm Amplification

Not observed on this corpus. Runtime action accuracy was 12/12 with zero false
deduplication. This remains a future risk, not a rejected possibility.

## Negative Result Classification

Primary:

`ONTOLOGY_ATTRIBUTE_OVERLOAD`

Secondary:

`PRIVATE_REFERENCE_BOUNDARY_AMBIGUITY`

Not classified as:

- Provider construction failure;
- general semantic inadequacy;
- action-safety failure;
- prompt-format failure.

## Theory Update

The next object should factor the overloaded attribute before another Provider
experiment:

```text
InformationRelation
  -> TransformStatus
  + InformationEffect
```

Candidate axes:

`TransformStatus`:

- `NO_TRANSFORM`;
- `VERIFIED_TRANSFORM`;
- `ASSERTED_UNVERIFIED_TRANSFORM`;
- `UNKNOWN_TRANSFORM_APPLICABILITY`.

`InformationEffect`:

- `GLOBAL_EQUIVALENT`;
- `CLAIM_EQUIVALENT`;
- `INFORMATION_REDUCING`;
- `INFORMATION_AUGMENTING`;
- `UNKNOWN_EFFECT`;
- `NOT_APPLICABLE`.

The factorization is accepted only if a zero-Provider grid shows that it
resolves all four disagreements, preserves existing Runtime actions, and
reduces rather than relocates ambiguity.

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| raw Provider response | `39a58595d63ee8b44cdea6455bc5e9a0e7e15200231a9d9908ef6fa12f4b02db` |
| attempt ledger | `4950d95903851e03b3b79c307350a05f2d0491176313cfd96c402dc8d5332794` |
| result | `7c1bcbe3774cdd86b67fcd1a7887fa3df1735febc7f310c7cad5d3e78f7a154e` |
| hash inventory | `73d6cb08263afe3dd9dd3d9391c0b50e3eeb8414833d5260fdc03e2e03d81ce2` |
| closure receipt | `6daecb887a29a231d1c7293b218de6ce4d8cbf56162af128172efed0ae54169a` |

Deterministic replay from the preserved raw response and attempt ledger
reproduced the result artifact byte-for-byte under the recorded Windows newline
coordinate.

## Next Research Object

`R4_V0_3H_TRANSFORMATION_SEMANTICS_FACTORIZATION`

Provider calls are paused. The next step is a theory packet and zero-Provider
formal grid, not a prompt repair or v0.3G rerun.
