# R4 Receipt Envelope Canonicalization Closure v0.3C

## Status

`PASS_BOUNDED_REPRESENTATION_CONSTRUCTION`

Evidence coordinate:

`INTERNAL_PROJECT_EVIDENCE_PLUS_SYNTHETIC_FORMAL_AUDIT`

Claim ceiling:

`BOUNDED_RECEIPT_ENVELOPE_CONSTRUCTION_ONLY`

The result supports a key-agnostic, shape-bound receipt-envelope object on the
frozen adversarial surface and mechanically recovers both preserved v0.3B
responses. It does not repair v0.3B or establish Provider semantic adequacy.

## Frozen Coordinate

- theory:
  `R4_RECEIPT_ENVELOPE_CANONICALIZATION_THEORY_V0_3C.md`;
- authorization:
  `R4_RECEIPT_ENVELOPE_CANONICALIZATION_AUTHORIZATION_V0_3C.json`;
- preregistration:
  `R4_RECEIPT_ENVELOPE_CANONICALIZATION_PREREGISTRATION_V0_3C.md`;
- freeze commit: `cb7c8aa`;
- Provider calls: zero;
- fresh holdout consumption: zero;
- CoreSlim, retention, and baseline writes: zero.

No frozen expectation changed after execution.

## Engineering Object

The validated candidate is:

```text
ReceiptEnvelopeCanonicalizer
  input:
    JSON content
    caller-supplied required item keys
  output:
    copied receipt items
    root type
    source collection key
    scalar root metadata field names
```

The module is:

- 75 source lines;
- deterministic;
- Provider-independent;
- semantic-truth-independent;
- key-allowlist-free;
- outside CoreSlim;
- free of retention and baseline imports.

The existing semantic item validator remains the owner of:

- relation enumeration;
- evidence scope;
- authority-field rejection;
- case identity;
- exact expected coverage;
- extra-field exclusion.

The 217-line experiment evaluator is not a Runtime component. It contains
frozen controls, replay diagnostics, gates, and result assembly.

## Frozen Gate Results

| Gate family | Result |
| --- | ---: |
| accepted shapes | 5/5 |
| rejected shapes | 9/9 |
| total frozen gates | 15/15 |
| preserved responses replayed | 2/2 |
| recovered receipts | 24/24 |
| relation accuracy per replay | 12/12 |
| Runtime action accuracy per replay | 12/12 |
| false combine | 0 |
| false deduplicate | 0 |
| false block | 0 |
| source files changed | 0 |
| Provider calls | 0 |

Accepted:

- root array;
- direct item;
- `receipts` collection;
- `cases` collection;
- unseen `payload` collection with scalar metadata.

Blocked:

- scalar root;
- empty root array;
- empty wrapped array;
- root with no receipt collection;
- non-object items;
- heterogeneous items;
- two list fields;
- candidate list plus list metadata;
- candidate list plus nested object metadata.

End-to-end item gates also blocked:

- a forbidden action field;
- missing expected-case coverage;
- unknown case identity.

An extra non-authority item field was recorded and excluded from canonical
state.

## Preserved Response Replay

The original source files were read directly:

```text
batch_A_attempt_1.json.txt
  7f7e5c2beb2270577dfdcbfa6fc0ee04b5a0fa0ac9520dfcd6cff94d7f25cb94

batch_A_attempt_2.json.txt
  706fef18308dc37bfba3312824983566e748e271ae6ab23a42f8c333f4223236
```

Before and after hashes were identical.

Both responses produced:

- root type: `object_collection`;
- source key: `cases`;
- receipt count: 12;
- relation accuracy: 1.0;
- Runtime action accuracy: 1.0;
- zero harmful Runtime action.

These are v0.3C mechanical replay observations. They remain post-hoc,
non-promotional evidence about the failed v0.3B calls.

## Determinism

Two complete runs produced byte-identical artifacts:

```text
result.json
  37b6aaae22d50826d019e621c00f9bcfb13c7782041ac8116afd2b33ad156f7d

hash_inventory.json
  041b33fe5154574e661b3a10d5886f9c1fe13e12e3d005a4837bfbdd100f5497

closure.json
  f2788b098327072db1337af22606b603207c512fcf893c6545f04107d56f33d0
```

Local ignored artifact:

```text
outputs/r4_receipt_envelope_v0_3c/
```

## Facts

1. The arbitrary `payload` key passed without an alias rule.
2. The observed `cases` key passed under the same shape rule.
3. Item values were preserved in every accepted fixture.
4. Ambiguous and heterogeneous roots remained fail-closed.
5. Existing semantic and authority gates remained active.
6. Both preserved Provider responses passed unchanged item validation.

## Phenomena

### Collection identity was structural, not lexical

The collection key varied across `receipts`, `cases`, and `payload`, while
canonical item identity remained unchanged. The information needed to locate
the receipt collection came from uniqueness, non-emptiness, homogeneity, and
required-key presence.

### Safety did not require lexical rigidity

Removing the key-name restriction did not require relaxing:

- authority fields;
- evidence binding;
- case identity;
- exact coverage;
- ambiguous-container blocking.

The previous key gate therefore mixed representation convention with semantic
admissibility.

### Conservative ambiguity handling remained visible

A root with one candidate list and a separate warnings list still blocks, even
when the warnings list is empty. A root with nested metadata also blocks.

This is deliberate under v0.3C. The experiment establishes one safe bounded
surface, not universal JSON-envelope acceptance.

## Mechanism Interpretation

The observations support:

`M1_UNIQUE_SHAPE_SUFFICIENCY`

on the frozen surface.

The causal account is:

1. required item keys define a receipt-shaped observable;
2. one non-empty homogeneous collection makes the collection location unique;
3. scalar metadata does not compete with collection identity;
4. provenance preserves the original key without granting it semantic
   authority;
5. unchanged item validation preserves downstream safety gates.

This removes a zero-Cbit rejection path while retaining the information-bearing
boundaries.

## Rival Explanations

### M0_KEY_IDENTITY_REQUIRED

Not supported on the frozen surface:

- no ambiguous fixture was accepted;
- no authority field entered canonical state;
- an unseen key recovered safely.

M0 is not universally falsified because the adversarial space is finite.

### M2_SHAPE_RULE_TOO_STRICT

Not supported for scalar metadata:

- the unseen collection plus two scalar metadata fields passed.

Still plausible for realistic envelopes containing warnings arrays or nested
metadata, which v0.3C intentionally blocks.

### M3_ITEM_SCHEMA_IS_THE_REAL_FAILURE

Rejected for the two preserved v0.3B responses:

- both passed the unchanged item validator after envelope recovery.

It remains possible on future Provider outputs with genuinely invalid item
content.

### M4_NULL_NO_INFORMATION_GAIN

Rejected on this anomaly:

- both previously rejected roots were mechanically recovered without a key
  exception.

## Negative Results And Boundaries

- v0.3B remains formally failed and early-stopped.
- Batch B was not executed.
- single-case robustness was not tested.
- no second fresh semantic corpus was tested.
- no new Provider response was generated.
- list-valued metadata and nested root metadata remain unsupported.
- the candidate has not entered CoreSlim.

The result must not be described as Provider semantic generalization.

## Theory Update

Accept, bounded:

`ReceiptEnvelopeIdentity = unique homogeneous receipt collection`

Reject for this anomaly:

`receipt collection identity requires the literal key receipts`

Preserve:

- item validation as a separate mechanical owner;
- Provider as semantic support only;
- Runtime as final cognitive and state authority;
- fail-closed ambiguity handling.

## Anti-Additive Audit

Added:

- one 75-line generic representation module;
- two provenance fields;
- adversarial and replay tests.

Not added:

- `cases` alias;
- Provider-specific branch;
- second schema;
- second coordinator;
- new Runtime state;
- semantic repair.

The object upgrade replaces a growing alias surface with one falsifiable
structural invariant.

## Residual Uncertainty

1. Will the Provider remain relation-accurate under reversed batch order?
2. Does single-case presentation improve or degrade relation judgments?
3. Are list-valued or nested metadata common enough to justify a later theory
   revision?
4. Does relation accuracy transfer to a second unseen corpus?
5. Does a different Provider family instantiate the same relation object?

## Next Research Object

Highest immediate information gain:

`R4_v0_3D_HYBRID_PRESENTATION_ROBUSTNESS`

Candidate design:

- preserve the two v0.3B Batch A responses as historical evidence;
- make no repeated Batch A call;
- preregister one reversed-order Batch B call and twelve isolated Single calls;
- use the v0.3C canonicalizer;
- report a hybrid-time limitation explicitly;
- keep false combine and false deduplicate as hard gates.

This would resolve the unfinished presentation question at lower token cost.

Fresh semantic generalization remains a separate later object requiring a
second unseen corpus. Provider calls remain paused until v0.3D is separately
preregistered.

