# R4 Receipt Envelope Canonicalization Theory v0.3C

## Status

`FROZEN_FOR_ZERO_PROVIDER_ENGINEERING_VALIDATION`

This window inherits MethodologyKernel v1.1.
If any experimental conclusion conflicts with this kernel, the conflict must be
explicitly stated and converted into a theory revision, downgrade, or caveat.

Evidence coordinate:

`INTERNAL_PROJECT_EVIDENCE_PLUS_SYNTHETIC_FORMAL_AUDIT`

This packet is a theory writeback from the immutable v0.3B construction
failure. It does not repair or rescore v0.3B and does not authorize Provider
calls.

## Inheritance

- `R4_SEMANTIC_RELATION_COMPOSITION_THEORY_V0_3.md`;
- `R4_PROVIDER_SEMANTIC_RELATION_PREREGISTRATION_V0_3B.md`;
- `R4_PROVIDER_SEMANTIC_RELATION_CLOSURE_V0_3B.md`;
- `THEORY_FIRST_ENGINEERING_VALIDATION_PRINCIPLE.md`;
- MethodologyKernel v1.1.

## Ontology Object

`RECEIPT_ENVELOPE_IDENTITY`

A receipt envelope is the representation-level boundary that locates one
candidate receipt or one homogeneous collection of candidate receipts before
item-level semantic and authority validation.

The envelope is not:

- a semantic judgment;
- a decision receipt;
- a schema repair mechanism;
- a Provider instruction;
- a candidate-state transition.

Object chain:

```text
ReceiptEnvelopeIdentity
  -> UniqueHomogeneousReceiptCollection
  -> DeterministicEnvelopeCanonicalization
  -> canonical items plus envelope provenance
  -> acceptance, ambiguity-block, and byte-preservation metrics
```

The experiment may update only the representation-level envelope rule.
It cannot update semantic relation adequacy, composition policy, Provider
authority, or CoreSlim behavior.

## Problem Statement

v0.3B accepted:

- a root array;
- a direct receipt object;
- an object containing a `receipts` array.

The Provider twice returned an object containing one `cases` array. Every item
contained the required receipt fields and both arrays were semantically exact
under post-hoc diagnostics, but the outer key caused mechanical rejection.

The unresolved question is:

> When an object contains exactly one non-empty, homogeneous receipt-shaped
> collection, does the collection key carry information needed for safe
> Runtime acceptance?

## Leading Model

`M1_UNIQUE_SHAPE_SUFFICIENCY`

If a root object contains exactly one non-empty list and every list item
contains the frozen required receipt keys, the list is uniquely identifiable
as the candidate receipt collection. The collection key adds no semantic Cbit.

Predictions:

- `receipts`, `cases`, and an unseen neutral key canonicalize identically;
- item values remain byte-equivalent after canonical JSON projection;
- source key and root metadata remain observable as provenance;
- multiple collections, empty collections, and heterogeneous collections
  block before item validation;
- existing item-level authority and exact-coverage gates remain unchanged.

## Rival Models

### M0_KEY_IDENTITY_REQUIRED

The key name is a necessary contract component. Accepting an arbitrary key will
cause unsafe objects to be interpreted as receipts.

Discriminating failure:

- a shape-only rule accepts an ambiguous, heterogeneous, or authority-bearing
  object that the frozen parser previously blocked.

### M2_SHAPE_RULE_TOO_STRICT

Unique homogeneous shape is safe but rejects common non-semantic metadata
layouts, so it merely moves the mechanical bottleneck.

Discriminating failure:

- scalar root metadata prevents otherwise unique collection recovery;
- replay requires a key-specific exception.

### M3_ITEM_SCHEMA_IS_THE_REAL_FAILURE

The envelope is recoverable, but item values fail required fields, authority,
evidence scope, or exact expected coverage.

Discriminating failure:

- canonicalization succeeds while unchanged item validation rejects the two
  preserved v0.3B responses.

### M4_NULL_NO_INFORMATION_GAIN

The new rule reproduces the old accepted shapes but cannot safely recover the
observed `cases` responses.

## Causal Mechanism

Let:

```text
R = required item-key set
L(root) = root-level list-valued fields
C(root) = lists whose items are non-empty objects containing R
```

For a direct receipt object:

```text
R subset_of keys(root) -> one direct item
```

For a root array:

```text
non_empty(root) and every item contains R -> root items
```

For an envelope object:

```text
|L(root)| = 1 and |C(root)| = 1 -> unique collection
```

All other root shapes block.

Non-list root metadata may be recorded but cannot alter items. Nested root
containers block because they create an unmodeled interpretation surface.

After envelope canonicalization, the existing item validator still owns:

- required value types;
- relation-state enumeration;
- evidence binding;
- forbidden authority fields;
- expected-case identity and exact coverage;
- extra-item-field recording.

## Discriminating Predictions

| Observation | M1 | M0 | M2 | M3 |
| --- | --- | --- | --- | --- |
| arbitrary unique collection key accepted | expected | unsafe | expected | expected |
| two candidate arrays blocked | expected | uncertain | expected | expected |
| scalar metadata accepted and recorded | expected | uncertain | rejected | expected |
| nested or list metadata blocked | expected | expected | expected | expected |
| preserved v0.3B responses pass unchanged item validation | expected | not tested | may fail mechanically | rejected |
| forbidden authority item remains blocked | expected | may leak | expected | expected |

## Engineering Derivation Contract

| Engineering object | Frozen variable | Minimality | Removal test | Authority |
| --- | --- | --- | --- | --- |
| `ReceiptEnvelopeCanonicalizer` | unique homogeneous collection | one pure representation module | old parser fails preserved `cases` roots | none |
| `EnvelopeProvenance` | root type, source key, root metadata fields | replay explanation only | remove it and source shape becomes unauditable | observation only |
| existing semantic item validator | item semantic and authority gates | unchanged owner | removal admits invalid receipts | mechanical gate |
| replay evaluator | v0.3B recovery and value preservation | zero-call evidence | removal leaves anomaly unresolved | diagnostic only |

No second parser schema, Provider coordinator, Runtime, or state machine is
authorized.

## Falsification Conditions

Reject M1 for this instrument if:

- any ambiguous or heterogeneous root is accepted;
- an item value changes during canonicalization;
- arbitrary-key recovery needs a key allowlist;
- either preserved v0.3B response still fails unchanged item validation;
- forbidden authority or incomplete coverage enters canonical state;
- deterministic replay differs across two runs.

Revise M1 if unique collection recovery works but scalar metadata cannot be
handled without semantic interpretation.

## Proxy Validity Limits

Passing v0.3C establishes only:

- deterministic identification of a unique homogeneous receipt collection;
- continued item-level fail-closed behavior;
- mechanical recovery of two preserved invalid v0.3B responses.

It does not establish:

- formal passage of v0.3B;
- Provider semantic adequacy;
- Batch B or single-case robustness;
- generalization to a second fresh corpus;
- production Runtime integration readiness.

## Anti-Additive Audit

Object upgrade:

```text
key alias compatibility
  -> unique homogeneous receipt collection identity
```

Removed:

- key-specific `receipts` ownership;
- pressure to add a `cases` alias branch.

Added:

- one generic representation module;
- one provenance record;
- adversarial shape tests.

Free semantic parameters added:

`0`

Patch accumulation triggers:

- any key allowlist;
- Provider-specific behavior;
- more than one candidate collection;
- semantic truth inspection;
- silent item repair.

## Stop And Rollback

Stop immediately if:

- a frozen adversarial expectation needs revision after execution;
- replay requires editing preserved raw responses;
- Provider calls occur;
- a CoreSlim, retention, or baseline write is attempted;
- the implementation absorbs item validation into the envelope module.

Rollback is deletion of the standalone canonicalizer and v0.3C ignored output.
The immutable v0.3B closure remains unchanged.

