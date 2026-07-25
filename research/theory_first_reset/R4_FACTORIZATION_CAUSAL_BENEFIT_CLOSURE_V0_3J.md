# R4 Factorization Causal Benefit Closure v0.3J

## Formal Status

`FAIL_CAUSAL_BENEFIT_WITH_REVALIDATION_GAIN_AND_PRESENTATION_COST`

Evidence coordinate:

`INTERNAL_PROJECT_PROVIDER_EVIDENCE_ON_FRESH_SYNTHETIC_CORPUS`

Claim ceiling:

`SAME_PROVIDER_MATCHED_FRESH_SYNTHETIC_FACTORIZATION_COMPARISON_ONLY`

Thirteen of eighteen frozen gates passed. The leading causal-benefit model is
rejected as stated. No call, prompt, corpus, reference, threshold, or compiler
was repaired or repeated.

## Frozen Coordinate

- theory freeze commit: `e4a0299`;
- corpus and implementation freeze commit: `1b2ba12`;
- Provider and returned model: DeepSeek `deepseek-v4-flash`;
- logical calls: 4/4;
- physical attempts: 4/8;
- call order: `L-F-F-L`;
- total tokens: 25681/60000;
- private surface exposed: false;
- Provider relation or action authority: false;
- CoreSlim, retention, and baseline writes: zero.

All four calls were mechanically valid on their first attempt.

## Aggregate Result

| Gate group | Result |
| --- | --- |
| frozen gates | 13/18 |
| legacy action agreement | 12/12 |
| factorized action agreement | 9/12 |
| false deduplicate | 0 across all calls |
| deterministic replay | byte-identical |

Failed gates:

1. evidence-reference exactness;
2. factorized latent-pair gain in both rounds;
3. Runtime relation accuracy in every call;
4. Runtime action accuracy in every call;
5. within-factorized-arm action agreement.

## Per-Call Results

| Call | References | Latent | Revalidation | Relation | Action | Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy forward | 8/12 | 10/12 | 10/12 | 11/12 | 12/12 | 6249 |
| factorized forward | 12/12 | 11/12 | 12/12 | 11/12 | 11/12 | 6593 |
| factorized reverse | 8/12 | 12/12 | 12/12 | 7/12 | 10/12 | 6547 |
| legacy reverse | 12/12 | 10/12 | 10/12 | 12/12 | 12/12 | 6292 |

Matched gains:

| Round | Factorized latent gain | Factorized revalidation gain |
| --- | ---: | ---: |
| forward | +1/12 | +2/12 |
| reverse | +2/12 | +2/12 |

The frozen leading model required at least +2 latent and +2 revalidation in
both rounds. It therefore failed on forward latent resolution.

## Attribute Results

Legacy:

- forward `InformationRelation`: 11/12;
- reverse `InformationRelation`: 12/12.

Factorized:

- forward `TransformStatus`: 12/12;
- reverse `TransformStatus`: 12/12;
- forward `InformationEffect`: 11/12;
- reverse `InformationEffect`: 12/12.

The Provider could populate the new axes. The factorization's representational
gain was not merely theoretical.

However, shared attributes degraded in the wider factorized receipt:

- factorized `SourceIdentity`: 10/12 in both rounds;
- factorized `LineageCoupling`: 11/12 in both rounds;
- legacy shared attributes ranged from 11/12 to 12/12.

This indicates interference outside the newly added axes.

## Main Failure Modes

### Harmful False Combine

Factorized forward case `R43J-12`:

- expected: same dossier source, no established transform relation;
- expected action: `BLOCK`;
- observed source and lineage: distinct source plus separate pipelines;
- observed action: `COMBINE`.

This was one false combine, not a false deduplicate. It shows that correct
transform-status inference cannot compensate for a provenance-axis error.

### Reverse-Order Witness Omission

Factorized reverse omitted the explicit tolerance reference for:

- `R43J-01`;
- `R43J-02`;
- `R43J-03`;
- `R43J-11`.

All four attribute labels were otherwise correct. Runtime correctly produced:

`CLAIM_TOLERANCE_WITNESS_MISSING -> UNRESOLVED -> BLOCK`

This created two false blocks and two relation-only conservative deviations.
The behavior is safe but demonstrates that semantic label accuracy and witness
binding robustness are different capabilities.

### Unknown-Applicability Boundary

Factorized forward `R43J-10` correctly identified
`UNKNOWN_TRANSFORM_APPLICABILITY` but selected an inconsistent information
effect. Runtime detected:

`STATUS_EFFECT_INCONSISTENT`

and blocked. The revalidation trajectory remained correct.

## Cost

Mean tokens per call:

- legacy: 6270.5;
- factorized: 6570.0.

Factorized overhead was approximately 4.8 percent. Token cost was not the
failure driver and remained comfortably within budget.

## Experimental Phenomena

### 1. Revalidation Benefit Is Real

The factorized arm achieved 12/12 revalidation in both rounds versus 10/12 for
legacy. It correctly distinguished:

- verify an asserted transform;
- discover whether a transform relation exists.

This is an observed Runtime cognitive benefit even when immediate actions are
the same.

### 2. Wider Semantic Receipts Create Cross-Attribute Interference

Adding orthogonal transformation axes did not reduce their own inferability.
Instead, errors migrated into source identity, lineage, and witness selection.
The bottleneck is therefore no longer ontology expressiveness alone.

### 3. Order Sensitivity Acts Through Evidence Binding

Factorized labels were slightly better in reverse order, but reference binding
was worse. The same semantic answer can therefore produce different Runtime
actions because witness completeness changes with presentation.

### 4. Runtime Fail-Closed Logic Worked

Missing tolerance and inconsistent status-effect pairs were blocked locally.
This prevented false deduplication. Runtime did not repair or trust incomplete
Provider cognition.

## Theory Adjudication

### M1 Factorization Causal Benefit

Rejected as stated. Revalidation improved, but latent gain was not at least
2/12 in both rounds and action robustness degraded.

### M0 No Causal Benefit

Rejected. Revalidation improved by 2/12 in both rounds.

### M2 Complexity Harms Inference

Supported in bounded form. The new axes remained accurate, but the wider
receipt degraded unrelated provenance attributes and action stability.

### M3 Representational Gain Only

Rejected in its strong form. Provider-backed revalidation resolution actually
improved to 12/12.

### M4 Action Equivalence Is Sufficient

Rejected. Distinct revalidation trajectories were recovered, and provenance
errors showed that immediate action alone is not an adequate cognitive state.

### M5 Presentation Or Time Drift

Supported. Factorized action agreement was 9/12 and reference coverage changed
from 12/12 to 8/12 across order. Legacy actions remained 12/12 despite its own
reference variation.

## Negative Result Classification

Primary:

`COGNITIVE_LOAD_INTERFERENCE_IN_WIDE_RECEIPT`

Secondary:

`PRESENTATION_SENSITIVE_WITNESS_BINDING`

The result is not classified as:

- factorized ontology failure;
- Provider construction failure;
- token-budget failure;
- Runtime safety-kernel failure.

## Theory Update

The next object should be:

`ROLE_DECOMPOSED_SEMANTIC_INFERENCE`

Candidate decomposition:

```text
Provenance role
  -> SourceIdentity + LineageCoupling + TransformStatus

Effect-and-scope role
  -> InformationEffect + AddedUncertainty + TargetClaimRelation

Runtime
  -> validates witnesses
  -> composes the two receipts
  -> compiles relation, action, and revalidation
```

This is not yet an authorized architecture change. The next theory must compare
one wide factorized receipt with decomposed independent role receipts on a
fresh corpus and matched information.

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| legacy forward raw | `0a7c9c83c37987718344226a906588b3fb3b0b49968f5daf1d754985e520c89f` |
| factorized forward raw | `b00355da1e8707a7d0c678c0c8f4348911d99502a9e9f9ea835507c3aab0cc65` |
| factorized reverse raw | `6c8f0dfc7e475b5839038227d17108a38bf8a8e0ef66b85d88fe87966ba51461` |
| legacy reverse raw | `7091b50d248637fa169883b962d57a54bfae7547a55f3d7b85655498ff902066` |
| attempt ledger | `751938a56256624959c9d255afeb2c732a3bd799b96ecf60c97e2d1a8cbf800a` |
| result | `90fbe0ac3935c542b8776798ceb0d1273174591f6c8f0a3e640f070a6c2ce05f` |
| inventory | `51edba15e87282df0965c5e50af8c349dbe1b2e65a18a5ff4bda1794b1433499` |
| closure receipt | `257e763282a88b5a45b780cd48432d181c08f1a42ed8fc5fa4e28060d3b418bb` |

## Validation

- comparative experiment suite: 71 passed;
- AgentOS CoreSlim suite: 394 passed;
- raw-response replay: byte-identical;
- Provider calls after closure: paused.
