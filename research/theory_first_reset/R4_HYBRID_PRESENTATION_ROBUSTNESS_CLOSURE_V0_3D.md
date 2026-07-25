# R4 Hybrid Presentation Robustness Closure v0.3D

## Status

`PASS_PRESENTATION_ROBUST_WITH_HYBRID_TIME_LIMIT`

Evidence coordinate:

`INTERNAL_PROJECT_PROVIDER_EVIDENCE_WITH_HYBRID_TIME_LIMIT`

Claim ceiling:

`SAME_PROVIDER_PRESENTATION_ROBUSTNESS_ON_EXPOSED_SYNTHETIC_CORPUS`

All 15 frozen gates passed. The result supports relation-label and
Runtime-action robustness across the tested presentations. It does not
establish fresh semantic generalization or full explanatory invariance.

## Frozen Coordinate

- theory:
  `R4_HYBRID_PRESENTATION_ROBUSTNESS_THEORY_V0_3D.md`;
- authorization:
  `R4_HYBRID_PRESENTATION_ROBUSTNESS_AUTHORIZATION_V0_3D.json`;
- preregistration:
  `R4_HYBRID_PRESENTATION_ROBUSTNESS_PREREGISTRATION_V0_3D.md`;
- implementation manifest:
  `R4_HYBRID_PRESENTATION_IMPLEMENTATION_MANIFEST_V0_3D.json`;
- theory freeze commit: `9b794fb`;
- implementation freeze commit: `97fb899`;
- Provider: DeepSeek `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- repeated Batch A calls: zero;
- CoreSlim, retention, and baseline writes: zero.

All 13 executed prompt hashes matched the frozen manifest.

## Execution

| Quantity | Result |
| --- | ---: |
| new logical calls | 13/13 |
| new physical attempts | 13 |
| invalid attempts | 0 |
| incremental prompt tokens | 8853 |
| incremental completion tokens | 1816 |
| incremental total tokens | 10669 |
| token ceiling | 80000 |
| new receipts | 24/24 |
| frozen gates | 15/15 |

Every logical call completed on its first physical attempt.

## Arm Results

| Arm | Relation accuracy | Macro recall | Runtime action accuracy |
| --- | ---: | ---: | ---: |
| historical Batch A | 12/12 | 1.0 | 12/12 |
| current reversed Batch B | 12/12 | 1.0 | 12/12 |
| current isolated Single | 12/12 | 1.0 | 12/12 |

Each of the six relation states had recall 1.0 in every arm:

- `INDEPENDENT_DISTINCT`;
- `EXACT_DUPLICATE`;
- `DEPENDENT_DISTINCT`;
- `PARTIAL_OVERLAP`;
- `SCOPE_INCOMPATIBLE`;
- `UNRESOLVED`.

## Cross-Arm Results

| Comparison | Exact agreement |
| --- | ---: |
| historical Batch A vs current Batch B | 12/12 |
| historical Batch A vs current Single | 12/12 |
| current Batch B vs current Single | 12/12 |

Case-level disagreement matrix:

`EMPTY`

Harmful Runtime actions:

| Error | Count |
| --- | ---: |
| false combine | 0 |
| false deduplicate | 0 |
| false block | 0 |

## Cost Structure

### Reversed Batch B

| Quantity | Result |
| --- | ---: |
| receipts | 12 |
| prompt tokens | 2206 |
| completion tokens | 889 |
| total tokens | 3095 |
| tokens per receipt | 257.917 |

### Isolated Single

| Quantity | Result |
| --- | ---: |
| receipts | 12 |
| prompt tokens | 6647 |
| completion tokens | 927 |
| total tokens | 7574 |
| tokens per receipt | 631.167 |

Single-to-batch token ratio per receipt:

`2.447`

The additional Single cost produced no relation-label or action improvement on
this explicit synthetic surface.

This does not imply that isolation is generally wasteful. Harder cases may
benefit from context isolation, and independent agents may contribute
information unavailable in a shared batch. Neither condition was present here.

## Envelope Behavior

The reversed Batch B response again used:

```text
root_type: object_collection
source_key: cases
```

All twelve Single responses used:

```text
root_type: direct_item
source_key: null
```

No response contained extra Provider fields. Evidence references were complete
and exact.

This repeats the v0.3B observation that batch output tends to preserve the input
collection label. The v0.3C structural canonicalizer handled it without an
alias rule.

## Facts

1. Reversing case order and relation-definition order changed no relation
   label.
2. Isolating every case changed no relation label.
3. Runtime-derived actions were exact in all three arms.
4. All new calls passed mechanically on the first attempt.
5. Single presentation cost 2.447 times more tokens per receipt.
6. Batch and Single used different envelope shapes.
7. Unresolved-assumption wording and granularity varied despite label
   stability.

## Phenomena

### Relation identity was presentation-stable

The relation taxonomy was not acting as a menu-position classifier on this
surface. Reversing definition order and removing neighboring cases caused no
observable label shift.

### Isolation increased communication cost without increasing label Cbit

Single calls repeated:

- the system instruction;
- all six relation definitions;
- the receipt contract;
- request framing.

This overhead was paid twelve times. Batch processing amortized the shared
context and instruction cost.

For these cases:

```text
Delta relation-label Cbit from isolation = 0
Delta token cost from isolation > 0
```

This is a bounded example of coordination or communication friction, not a
general argument against multi-agent isolation.

### Classification stability did not imply explanation invariance

For `R43B-11`, both presentations emitted one unresolved assumption with
different wording.

For `R43B-12`:

- Batch B emitted one aggregated unresolved assumption;
- Single emitted three decomposed unresolved assumptions covering source
  identity, extraction-window overlap, and row identity.

The categorical state remained `UNRESOLVED`, but the explanatory decomposition
changed.

This suggests at least two separable robustness objects:

```text
RelationLabelRobustness
ExplanationDecompositionRobustness
```

Only the first was frozen and passed.

## Mechanism Interpretation

The evidence supports:

`M1_PRESENTATION_ROBUST_RELATION_OBJECT`

on this corpus.

The explicit structural cues appear sufficient to determine relation labels
without relying on:

- neighboring case contrasts;
- definition order;
- batch-level calibration.

Runtime action derivation then preserves that stability because it is a fixed
deterministic mapping from relation state.

## Rival Explanations

### M0_BATCH_CONTEXT_DEPENDENCE

Weakened for relation labels:

- Single matched both batch arms 12/12.

Still possible for richer explanation, confidence, or hypothesis generation
objects not tested here.

### M2_ORDER_OR_DEFINITION_POSITION_BIAS

Weakened:

- reversed Batch B matched historical Batch A 12/12;
- rotated Single definition orders also remained exact.

### M3_TIME_DRIFT_OR_PROVIDER_NONSTATIONARITY

No label-level drift was observed.

It is not falsified because the design intentionally omitted a contemporaneous
Batch A repetition. Drift could exist below the categorical readout or in
explanatory wording.

### M4_TAXONOMY_AMBIGUITY

Weakened for the twelve frozen labels:

- all current arms matched the private references.

The variation in unresolved-assumption decomposition shows that semantic
underspecification still exists below the coarse label surface.

### M5_NULL_MECHANICAL_FAILURE

Rejected for this run:

- all 13 calls passed on their first attempt.

## Negative Results

- Single isolation produced zero label or action gain.
- No case exposed a presentation-dependent semantic correction.
- The experiment generated no evidence that more calls increase Cbit on easy,
  explicit relation cases.
- The experiment did not test independent Providers or agents.
- The experiment did not test fresh cases.
- The experiment did not test natural evidence passages.
- Explanation decomposition was not preregistered as a scored outcome.

The absence of disagreement is informative but also limits mechanism
identifiability: the rival models did not receive a hard case on which to
separate.

## Theory Update

Accept, bounded:

`RelationLabelRobustness across batch order and isolated presentation`

Accept as a cost observation:

`Single-call isolation can impose substantial repeated-instruction overhead`

Add as a new pending distinction:

```text
stable categorical judgment
does not imply
stable explanatory decomposition
```

Do not accept:

- fresh semantic generalization;
- cross-Provider robustness;
- general multi-agent efficiency;
- explanation-level invariance.

## Anti-Additive Audit

The experiment reused:

- the v0.3B corpus;
- frozen prompts;
- the Provider adapter;
- v0.3C canonicalization;
- existing semantic scoring.

It did not add:

- another Batch A call;
- new labels;
- a new Runtime component;
- an envelope exception;
- a benchmark-specific correction.

No code from this experiment is promoted to CoreSlim.

## Artifacts

Local ignored directory:

```text
outputs/r4_hybrid_presentation_v0_3d/
```

Hashes:

```text
result.json
  c84422f9a166f3fef1f0cdbccb102d31266b07d4d07fd40512a4429fddd2ab17

hash_inventory.json
  e1a2d7f211c5035a8af86446e7b1400bc69010e0c73536b1f5d38647f6b5cae0

closure.json
  2431ec30f96af66fc0f399c5816e880f466f8880db2495a991bc76e9a7993ae0
```

## Residual Uncertainty

1. Does relation accuracy transfer to a second unseen, less explicit corpus?
2. Does explanation decomposition remain faithful and complete?
3. When does isolation produce enough semantic gain to repay its token cost?
4. Does the relation object transfer to another Provider family?
5. Does natural evidence introduce entity, scope, and provenance ambiguity not
   represented by these synthetic descriptors?

## Next Research Object

Highest effective Cbit:

`R4_v0_3E_FRESH_HARD_RELATION_GENERALIZATION`

Recommended theory-first design:

- create a second unseen corpus after preregistration;
- preserve the six-state taxonomy without adding labels;
- reduce explicit lexical cues;
- include hard boundaries between dependence, partial overlap, scope mismatch,
  and unresolved;
- use one batch arm first to exploit the validated cost efficiency;
- retain false combine and false deduplicate as hard failure gates;
- use isolated follow-up only in a separately preregistered diagnostic if the
  fresh batch reveals specific ambiguous cases.

This tests semantic transfer rather than spending more calls on a surface that
already saturated at 12/12.

Provider calls are paused until v0.3E theory and corpus-generation rules are
frozen.

