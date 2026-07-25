# R4 Hybrid Presentation Robustness Theory v0.3D

## Status

`FROZEN_FOR_BOUNDED_PROVIDER_VALIDATION`

This window inherits MethodologyKernel v1.1.
If any experimental conclusion conflicts with this kernel, the conflict must be
explicitly stated and converted into a theory revision, downgrade, or caveat.

Evidence coordinate:

`INTERNAL_PROJECT_PROVIDER_EVIDENCE_WITH_HYBRID_TIME_LIMIT`

## Inheritance

- `R4_PROVIDER_SEMANTIC_RELATION_PREREGISTRATION_V0_3B.md`;
- `R4_PROVIDER_SEMANTIC_RELATION_CLOSURE_V0_3B.md`;
- `R4_RECEIPT_ENVELOPE_CANONICALIZATION_CLOSURE_V0_3C.md`;
- MethodologyKernel v1.1.

## Research Object

`PRESENTATION_ROBUSTNESS_OF_SEMANTIC_RELATION_ASSESSMENT`

The object is whether a fixed semantic relation taxonomy and fixed public case
surface produce materially consistent Provider judgments under:

- one reversed-order batch presentation;
- twelve isolated single-case presentations;
- one preserved ascending-order historical batch anchor.

Object chain:

```text
PresentationRobustness
  -> fixed case semantics under changed context packing and order
  -> relation-state and Runtime-action agreement
  -> cross-arm accuracy, agreement, harmful-action, and cost metrics
```

The historical Batch A anchor and new Batch B/Single calls are not
contemporaneous. Therefore:

```text
observed disagreement
  = presentation effect + possible Provider time drift + residual stochasticity
```

The experiment can reject robustness, but cannot uniquely attribute a failure
to presentation.

## Historical Anchor

The two preserved v0.3B Batch A responses are immutable inputs:

```text
attempt 1
7f7e5c2beb2270577dfdcbfa6fc0ee04b5a0fa0ac9520dfcd6cff94d7f25cb94

attempt 2
706fef18308dc37bfba3312824983566e748e271ae6ab23a42f8c333f4223236
```

Frozen anchor rule:

1. parse both with the v0.3C canonicalizer;
2. require 12/12 relation-state agreement;
3. use attempt 1 as the primary Batch A prediction;
4. retain attempt 2 only as a historical stability witness;
5. if the two attempts disagree, stop before new Provider calls.

No Batch A call may be repeated.

## Leading Model

`M1_PRESENTATION_ROBUST_RELATION_OBJECT`

The case descriptions contain enough explicit structural evidence that relation
states remain stable under reversed batch order and isolated presentation.

Predictions:

- Batch B relation accuracy at least 11/12;
- Single relation accuracy at least 11/12;
- Batch A versus Batch B agreement at least 11/12;
- historical Batch A versus Single agreement at least 10/12;
- macro state recall at least 0.80 in both new arms;
- zero false combine and false deduplicate actions.

## Rival Models

### M0_BATCH_CONTEXT_DEPENDENCE

Relation judgments depend on neighboring cases or batch-level contrast.

Signature:

- Single accuracy or agreement differs materially from both batch arms;
- errors cluster in relation pairs needing contrast, especially
  `DEPENDENT_DISTINCT` versus `PARTIAL_OVERLAP`.

### M2_ORDER_OR_DEFINITION_POSITION_BIAS

Relation judgments depend on case order or definition order.

Signature:

- reversed Batch B disagrees with historical Batch A while isolated Single
  remains accurate;
- errors follow labels moved across definition positions.

### M3_TIME_DRIFT_OR_PROVIDER_NONSTATIONARITY

Current responses differ because the Provider changed between the historical
and current calls.

Signature:

- Batch B and Single agree with each other but both disagree with Batch A;
- disagreement cannot be explained by context packing alone.

This model is not directly identifiable without a contemporaneous repeated
Batch A, which is forbidden to avoid redundant cost and historical repair.

### M4_TAXONOMY_AMBIGUITY

One or more case surfaces do not uniquely identify the private relation label.

Signature:

- stable disagreement across Batch B and Single on the same cases;
- unresolved-assumption receipts identify missing structural facts;
- errors cluster by case rather than presentation.

### M5_NULL_MECHANICAL_FAILURE

The Provider cannot complete the canonical receipt protocol even after v0.3C.

Signature:

- a logical call exhausts two attempts before semantic scoring.

## Causal Mechanism

Batch presentation supplies:

- shared relation definitions;
- neighboring cases as implicit contrasts;
- one larger context with possible attention interference.

Single presentation removes neighboring cases but rotates definition order.

If relation assessment is object-grounded, explicit descriptors should dominate
these presentation differences. If it is menu- or context-calibrated,
predictions will shift when neighbors or ordering change.

Runtime continues to derive actions mechanically:

| Relation | Runtime action |
| --- | --- |
| `INDEPENDENT_DISTINCT` | `COMBINE` |
| `EXACT_DUPLICATE` | `DEDUPE_AND_COMBINE` |
| all other states | `BLOCK` |

Provider cannot emit or control the action.

## Discriminating Predictions

| Observation | M1 | M0 | M2 | M3 | M4 |
| --- | --- | --- | --- | --- | --- |
| all three arms agree | supported | weakened | weakened | weakened | weakened |
| Single differs, batches agree | weakened | supported | weakened | possible | possible |
| Batch B differs, Single matches A | weakened | weakened | supported | possible | possible |
| B and Single agree against A | weakened | possible | possible | supported | possible |
| same cases fail in B and Single | weakened | possible | possible | possible | supported |

Because M0, M2, M3, and M4 are not fully identifiable in every outcome, closure
must report rival compatibility rather than force one cause.

## Engineering Derivation Contract

| Engineering object | Frozen variable | Minimality | Removal test | Authority |
| --- | --- | --- | --- | --- |
| `HistoricalBatchAnchor` | immutable Batch A states and hashes | reuses existing evidence | removal loses unfinished cross-arm comparison | evidence only |
| `HybridPresentationRunner` | Batch B plus Single call schedule | only 13 new calls | removal leaves presentation question unresolved | orchestration only |
| `HybridPresentationScorer` | frozen agreement and harm metrics | no new semantic label | removal makes models undiscriminated | diagnostic only |
| v0.3C canonicalizer | representation recovery | already validated | old parser rejects historical anchor | mechanical gate |

No CoreSlim module, coordinator, retention object, or baseline candidate is
authorized.

## Falsification Conditions

Reject M1 on this surface if:

- either new arm scores below 11/12 relation accuracy;
- either new arm macro recall falls below 0.80;
- Batch A versus Batch B agreement falls below 11/12;
- Batch A versus Single agreement falls below 10/12;
- any false combine or false deduplicate action occurs;
- mechanical receipt coverage is incomplete.

Close as construction failure if a logical call exhausts two attempts.

## Proxy Validity Limits

Passing establishes only bounded same-Provider presentation robustness on the
already exposed v0.3B synthetic corpus.

It does not establish:

- fresh semantic generalization;
- a causal separation of presentation from time drift;
- cross-Provider transfer;
- natural-world evidence judgment;
- production integration readiness.

## Anti-Additive Audit

Reused:

- existing cases;
- existing prompts;
- existing Provider adapter;
- v0.3C canonicalizer;
- existing per-arm relation scorer.

Added:

- one historical-anchor loader;
- one hybrid runner;
- one hybrid scorer and CLI.

Removed:

- redundant Batch A Provider call.

No threshold, label, prompt wording, private reference, or Runtime action rule
may change.

## Stop And Rollback

Stop immediately if:

- historical hashes or 12/12 historical agreement fail;
- one logical call exhausts two attempts;
- total incremental tokens exceed 80000;
- private labels appear in a Provider prompt;
- a same-version semantic or threshold repair is proposed;
- a CoreSlim, retention, or baseline write is attempted.

Rollback removes only v0.3D ignored outputs and candidate code. Historical
v0.3B and v0.3C artifacts remain unchanged.

