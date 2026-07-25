# R4 Fresh Hard Relation Generalization Closure v0.3E

## Formal Status

`PASS_FRESH_HARD_RELATION_GENERALIZATION`

Theory interpretation:

`PASS_WITH_TRANSFORMATION_EQUIVALENCE_BOUNDARY_DISCOVERED`

Evidence coordinate:

`INTERNAL_PROJECT_PROVIDER_EVIDENCE_ON_FRESH_SYNTHETIC_CORPUS`

Claim ceiling:

`SAME_PROVIDER_FRESH_HARD_SYNTHETIC_RELATION_GENERALIZATION_ONLY`

All 13 frozen gates passed. The Provider transferred the six-state relation
object to a second unseen, lexically de-cued corpus with one conservative
boundary error.

## Frozen Coordinate

- theory:
  `R4_FRESH_HARD_RELATION_GENERALIZATION_THEORY_V0_3E.md`;
- authorization:
  `R4_FRESH_HARD_RELATION_GENERALIZATION_AUTHORIZATION_V0_3E.json`;
- preregistration:
  `R4_FRESH_HARD_RELATION_GENERALIZATION_PREREGISTRATION_V0_3E.md`;
- corpus manifest:
  `R4_FRESH_HARD_RELATION_CORPUS_MANIFEST_V0_3E.json`;
- theory freeze commit: `7108208`;
- corpus and implementation freeze commit: `289f279`;
- Provider: DeepSeek `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- private labels exposed: false;
- Runtime actions exposed: false;
- CoreSlim, retention, and baseline writes: zero.

The executed prompt hash matched the frozen manifest:

```text
7bb3f195080ad1841135f82e2c7f5b58b3d655749bd363fc52400b6551c5f1f7
```

## Corpus

| Quantity | Result |
| --- | ---: |
| cases | 18 |
| domains | 18 |
| relation states | 6 |
| cases per state | 3 |
| corpus preflight gates | 9/9 |
| old v0.3B cases reused | 0 |
| banned relation cue terms in public surface | 0 |
| private labels or actions in public surface | 0 |

Every non-unresolved case carried a private adjudication basis and one explicitly
ruled-out neighboring state. Every unresolved case preserved at least two
compatible states under the missing facts.

## Execution

| Quantity | Result |
| --- | ---: |
| logical calls | 1/1 |
| physical attempts | 1 |
| invalid attempts | 0 |
| prompt tokens | 3175 |
| completion tokens | 1330 |
| total tokens | 4505 |
| token ceiling | 20000 |
| receipts | 18/18 |
| tokens per receipt | 250.278 |
| frozen gates | 13/13 |

The single logical call completed on its first attempt.

## Accuracy

| Metric | Result |
| --- | ---: |
| relation accuracy | 17/18 = 0.9444 |
| macro state recall | 0.9444 |
| Runtime action accuracy | 17/18 = 0.9444 |
| false combine | 0 |
| false deduplicate | 0 |
| false block | 1 |
| true-unresolved assumption coverage | 3/3 |

Per-state recall:

| Relation state | Recall |
| --- | ---: |
| `INDEPENDENT_DISTINCT` | 3/3 |
| `EXACT_DUPLICATE` | 2/3 |
| `DEPENDENT_DISTINCT` | 3/3 |
| `PARTIAL_OVERLAP` | 3/3 |
| `SCOPE_INCOMPATIBLE` | 3/3 |
| `UNRESOLVED` | 3/3 |

## Only Disagreement

Case:

`R43E-06`

Target:

`What temperature was reported by probe P at frame 781.`

Packet A:

- raw sensor code from telemetry frame 781.

Packet B:

- the same frame's code converted to Celsius using calibration table C4;
- no other telemetry frame.

Frozen private reference:

`EXACT_DUPLICATE -> DEDUPE_AND_COMBINE`

Provider judgment:

`DEPENDENT_DISTINCT -> BLOCK`

The error is a false block, not a harmful false combine or false deduplicate.

## Why The Disagreement Matters

The private reference used evidence-source identity:

```text
one telemetry observation
  -> two representations
  -> no second target observation
```

The Provider appears to have used representational or computational identity:

```text
raw code
  -> calibrated physical value
  -> distinct derived quantity sharing one source
```

Both accounts are compatible with part of the current taxonomy:

- `EXACT_DUPLICATE` says packets restate the same underlying observation or
  source item;
- `DEPENDENT_DISTINCT` says packets are different outputs sharing a derivation
  or measurement process.

Calibration table C4 introduces a transformation input. The public case does
not specify whether:

- the transform is invertible;
- calibration uncertainty is material;
- the converted value adds target-relevant information;
- the raw and converted forms are functionally interchangeable for downstream
  claims.

Therefore the disagreement is not safely attributable to Provider failure
alone.

No post-hoc relabel is applied. The frozen reference and Provider output remain
unchanged.

## Unresolved Cases

All three true `UNRESOLVED` cases were correct and contained material missing
facts:

`R43E-16`:

- missing catalog numbers, scan identifiers, page ranges, and transcription
  lineage.

`R43E-17`:

- missing device IDs, sampling times, and aggregation windows.

`R43E-18`:

- missing study identifiers, authors, sample sizes, and dates.

This shows that the Provider did not merely map all difficult cases to a generic
block state. It distinguished specified blocking relations from genuine
lineage uncertainty.

## Envelope And Cost

The response again used:

```text
root_type: object_collection
source_key: cases
```

No extra Provider fields entered canonical state.

Cost comparison:

| Batch | Cases | Tokens per receipt |
| --- | ---: | ---: |
| v0.3D reversed explicit corpus | 12 | 257.917 |
| v0.3E fresh hard corpus | 18 | 250.278 |

The fresh hard batch cost about 0.970 times the tokens per receipt of v0.3D
Batch B. Increasing semantic difficulty and batch size did not increase
per-object token cost in this run.

This is one observation, not a general scaling law.

## Facts

1. Seventeen of eighteen unseen cases matched the frozen private references.
2. Five relation states achieved 3/3 recall.
3. Exact duplicate achieved 2/3 because one transformed-observation case was
   classified as dependent distinct.
4. All dangerous action gates remained clean.
5. All three material-uncertainty cases were recognized and explained.
6. Prompt and receipt mechanics passed on the first attempt.
7. Per-receipt batch cost remained approximately flat relative to v0.3D.

## Phenomena

### Structural transfer survived lexical de-cueing

The public descriptors omitted direct relation words, yet the Provider
correctly recovered:

- separate source lineages;
- immutable source identity;
- complete shared upstream populations;
- partial set intersections;
- target-scope mismatches;
- materially missing identity metadata.

This is stronger evidence than v0.3B/v0.3D that the receipts depend on
structural relations rather than surface label cues.

### The remaining error was conservative and ontological

The only error moved an actionable exact-duplicate case into a blocking
dependent state. It reduced retained utility but did not create false
confidence.

This matches a limited conservative-block tendency, but not a broad
conservative classifier: all three independent cases and two other exact
duplicates remained actionable.

### Transformation equivalence is a missing dimension

Source identity alone is insufficient to determine whether two packets should
be deduplicated. Runtime may also need:

- transform identity;
- invertibility;
- information preservation;
- added calibration or model uncertainty;
- target-claim equivalence.

The six-state relation enum compresses these dimensions into one categorical
choice.

## Mechanism Interpretation

The result supports:

`M1_STRUCTURAL_RELATION_TRANSFER`

within the claim ceiling.

The Provider successfully supplied relation semantics for new structural
descriptions, while Runtime:

- enforced exact evidence binding;
- derived actions;
- blocked unsafe outputs;
- preserved the one disagreement without promotion.

## Rival Explanations

### M0_LEXICAL_CUE_DEPENDENCE

Strongly weakened:

- 17/18 transfer after banned cue removal;
- no broad state collapse.

### M2_BOUNDARY_COLLAPSE

Weakened:

- dependence, partial overlap, scope mismatch, and unresolved all achieved 3/3.

One local duplicate/dependent boundary remains.

### M3_CONSERVATIVE_BLOCK_BIAS

Weakly supported at one transformation boundary:

- one false block;
- no broad suppression of independent or exact-duplicate states.

### M4_OVERCONFIDENT_RESOLUTION

Rejected on this corpus:

- all true unresolved cases were retained as unresolved;
- all contained material missing-fact assumptions;
- no unresolved case became actionable.

### M5_TAXONOMY_INSUFFICIENCY

Partially activated:

- `R43E-06` exposes ambiguity between source identity and transformed-output
  identity.

The current evidence supports an ontology audit before another larger corpus.

### M6_NULL_MECHANICAL_FAILURE

Rejected:

- one valid first-attempt receipt collection covered all 18 cases.

## Negative Results And Boundaries

- Relation accuracy was not perfect.
- `EXACT_DUPLICATE` did not fully transfer.
- The experiment cannot decide whether the R43E-06 error belongs to Provider,
  corpus reference, or relation ontology.
- No repeat call established response stability.
- No Single arm diagnosed the transformed-observation case.
- No second Provider was tested.
- No natural evidence passages were used.
- Passing thresholds do not authorize CoreSlim integration.

## Theory Update

Accept, bounded:

`same-Provider structural relation transfer to a fresh hard synthetic corpus`

Accept:

`batch cost efficiency remained stable at 18 cases`

Revise:

```text
EXACT_DUPLICATE vs DEPENDENT_DISTINCT
  cannot always be decided from source identity alone
```

Add pending ontology:

```text
EvidenceTransformationEquivalence
  = SourceIdentity
  + TransformIdentity
  + InformationPreservation
  + AddedUncertainty
  + TargetClaimEquivalence
```

Do not add a seventh relation state yet. First determine whether these are
attributes that compile into the existing action space.

## Anti-Additive Audit

Do not patch `R43E-06`.

Do not:

- change its private label;
- add a telemetry exception;
- weaken the exact-duplicate gate;
- add a new relation enum immediately;
- run an unregistered Single call.

The next step is an object upgrade that explains a family of transformations,
not a case-specific correction.

## Artifacts

Local ignored directory:

```text
outputs/r4_fresh_hard_relation_v0_3e/
```

Hashes:

```text
result.json
  60ce91be3d9cb6e3269f8f6c267839199d662567ccf60c0e77998afdae637247

raw_attempts/fresh_hard_batch_attempt_1.json.txt
  fce62d7d728651043c6b94b0c01253e1b76c9dcf21013efef9a88eb04c11ea51

hash_inventory.json
  ae16c0cf2334bfeb925ddd58f56962a49bd9ae26660cfc1ecbd7a086383e471d

closure.json
  bb850f45d4f8c374a735c6f6fcc4c6e019e8f5025a756f98c3d530566c0d5fdb
```

## Residual Uncertainty

1. Which transformations preserve evidence information for a target claim?
2. When does calibration add enough uncertainty to prohibit deduplication?
3. Should transformation equivalence be a relation attribute or a new state?
4. Can Runtime mechanically verify common transformations?
5. Does another Provider resolve the same boundary differently?
6. Does the 17/18 transfer persist on natural evidence?

## Next Research Object

Highest effective Cbit:

`R4_v0_3F_EVIDENCE_TRANSFORMATION_EQUIVALENCE`

Required sequence:

1. theory-only decomposition of source identity, transformation, information
   preservation, added uncertainty, and target-claim equivalence;
2. formal action table for `DEDUPE_AND_COMBINE` versus `BLOCK`;
3. zero-Provider synthetic grid containing renaming, lossless compression, unit
   conversion, calibrated conversion, aggregation, lossy summary, and
   model-derived transformations;
4. removal tests to determine whether attributes compile into the existing six
   states;
5. only then consider another Provider diagnostic.

Provider calls are paused.

