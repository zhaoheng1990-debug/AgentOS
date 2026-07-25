# R4 Fresh Hard Relation Generalization Theory v0.3E

## Status

`FROZEN_FOR_FRESH_CORPUS_CONSTRUCTION_AND_PROVIDER_VALIDATION`

This window inherits MethodologyKernel v1.1.
If any experimental conclusion conflicts with this kernel, the conflict must be
explicitly stated and converted into a theory revision, downgrade, or caveat.

Evidence coordinate:

`INTERNAL_PROJECT_PROVIDER_EVIDENCE_ON_FRESH_SYNTHETIC_CORPUS`

## Inheritance

- `R4_SEMANTIC_RELATION_COMPOSITION_THEORY_V0_3.md`;
- `R4_RECEIPT_ENVELOPE_CANONICALIZATION_CLOSURE_V0_3C.md`;
- `R4_HYBRID_PRESENTATION_ROBUSTNESS_CLOSURE_V0_3D.md`;
- MethodologyKernel v1.1.

## Research Object

`FRESH_STRUCTURAL_RELATION_GENERALIZATION`

The object is whether the frozen six-state semantic relation taxonomy transfers
from the explicit v0.3B corpus to a second unseen corpus whose labels must be
inferred from source lineage, unit identity, partial set intersection, and
target scope rather than label-like wording.

Object chain:

```text
FreshStructuralRelationGeneralization
  -> unseen hard-but-adjudicable packet pairs
  -> Provider relation receipts
  -> exact relation, per-state recall, Runtime action, and harm metrics
```

The experiment can update confidence in same-Provider synthetic transfer.
It cannot update the six-state taxonomy, Runtime action mapping, production
readiness, or cross-Provider claims.

## Frozen Relation States

- `INDEPENDENT_DISTINCT`;
- `EXACT_DUPLICATE`;
- `DEPENDENT_DISTINCT`;
- `PARTIAL_OVERLAP`;
- `SCOPE_INCOMPATIBLE`;
- `UNRESOLVED`.

No state may be added or renamed after corpus construction begins.

## Corpus Construction Theory

Eighteen cases are generated after this theory freeze:

- three per relation state;
- at least twelve distinct application domains;
- exactly two packet descriptors and two evidence references per case;
- no case reused from v0.3B;
- no public private label, Runtime action, or adjudication rationale.

### Hard-but-adjudicable rule

For every non-`UNRESOLVED` case:

- the public surface contains all facts needed for one frozen state;
- no unstated fact is required;
- at least one plausible neighboring state is ruled out by an explicit
  structural fact;
- difficulty comes from indirect representation, not missing information.

For every `UNRESOLVED` case:

- a specific lineage, identity, intersection, or scope fact is absent;
- at least two relation states remain compatible with the public surface;
- inventing the missing fact would be required to choose a narrower state.

### State construction rules

`INDEPENDENT_DISTINCT`:

- separate observation units and upstream source lineage;
- no shared sampling, transformation, model, or measurement artifact;
- distinct content rather than duplicated rendering.

`EXACT_DUPLICATE`:

- both packets derive from one immutable underlying source item or event;
- different formatting, naming, or summary does not add a second observation.

`DEPENDENT_DISTINCT`:

- packets report different quantities or outputs;
- both inherit one complete upstream data, model, sampling, or measurement
  process;
- they are not exact copies and do not merely share a subset.

`PARTIAL_OVERLAP`:

- some observation units or source items occur in both packets;
- each packet also contains at least one unique unit or item.

`SCOPE_INCOMPATIBLE`:

- at least one packet concerns a population, time, intervention, configuration,
  or target different from the frozen target scope;
- the incompatibility is explicit but not stated using the relation label.

`UNRESOLVED`:

- available metadata cannot determine whether lineage or units are identical,
  shared, partially shared, or separate;
- the uncertainty is material to composition.

## Lexical De-Cueing Rule

Public descriptors may not use:

- exact relation-state names;
- `independent`;
- `duplicate`;
- `dependent`;
- `overlap`;
- `incompatible`;
- `unresolved`.

Structural facts may use identifiers, counts, set ranges, checksums, source
paths, timestamps, transformations, populations, and configurations.

This removes direct lexical shortcuts without removing adjudicative evidence.

## Leading Model

`M1_STRUCTURAL_RELATION_TRANSFER`

The Provider can infer the frozen relation object from structural facts rather
than memorized wording from v0.3B.

Predictions:

- relation accuracy at least 15/18;
- every state recall at least 2/3;
- macro state recall at least 0.80;
- Runtime action accuracy at least 17/18;
- zero false combine;
- zero false deduplicate;
- at most one false block;
- all true `UNRESOLVED` cases contain explicit missing-fact assumptions.

## Rival Models

### M0_LEXICAL_CUE_DEPENDENCE

The v0.3B success depended on explicit relation-like wording.

Signature:

- broad accuracy decline across states after lexical de-cueing;
- correct evidence references but wrong relation labels.

### M2_BOUNDARY_COLLAPSE

The Provider recognizes obvious independent and duplicate cases but collapses
the boundaries among dependence, partial overlap, scope mismatch, and
unresolved.

Signature:

- high recall on the first two states;
- confusion concentrated in the four blocking states.

### M3_CONSERVATIVE_BLOCK_BIAS

The Provider avoids harmful composition by mapping difficult actionable cases
to a blocking state.

Signature:

- zero false combine and false deduplicate;
- reduced recall for `INDEPENDENT_DISTINCT` or `EXACT_DUPLICATE`;
- false block count above one.

### M4_OVERCONFIDENT_RESOLUTION

The Provider invents missing lineage facts in true `UNRESOLVED` cases.

Signature:

- low `UNRESOLVED` recall;
- empty or non-material unresolved-assumption receipts;
- possible false combine or false deduplicate.

### M5_TAXONOMY_INSUFFICIENCY

The six states cannot uniquely represent one or more well-formed fresh cases.

Signature:

- pre-call adjudication audit finds two states equally supported despite all
  relevant facts being present;
- close as corpus or ontology construction failure before Provider calls.

### M6_NULL_MECHANICAL_FAILURE

The one batch call cannot produce a valid 18-receipt envelope.

## Causal Mechanism

The Provider supplies semantic relation assessment from public structural
facts. Runtime supplies:

- frozen state enumeration;
- evidence and case binding;
- exact coverage validation;
- deterministic action mapping;
- harm gates;
- final experiment status.

Provider remains semantic support, not decision authority.

## Discriminating Predictions

| Observation | M1 | M0 | M2 | M3 | M4 |
| --- | --- | --- | --- | --- | --- |
| all states transfer | supported | weakened | weakened | weakened | weakened |
| broad label decline | weakened | supported | possible | possible | possible |
| blocking-state confusion | weakened | possible | supported | possible | possible |
| actionable states become blocked | weakened | possible | possible | supported | weakened |
| unresolved becomes actionable | rejected | possible | possible | weakened | supported |

## Engineering Derivation Contract

| Engineering object | Frozen variable | Minimality | Removal test | Authority |
| --- | --- | --- | --- | --- |
| `HardRelationCase` | public structural facts plus private adjudication | one data contract | removal loses fresh transfer surface | fixture only |
| `HardCorpusAudit` | balance, lexical de-cueing, adjudicability metadata | deterministic preflight | removal permits contaminated corpus | mechanical gate |
| `FreshHardBatchRunner` | one frozen batch call | cheapest validated presentation | removal leaves transfer untested | orchestration only |
| `FreshHardScorer` | frozen accuracy, recall, action, and harm gates | reuses relation mapping | removal makes rivals undiscriminated | diagnostic only |

No CoreSlim module or new Runtime owner is authorized.

## Falsification Conditions

Reject M1 on this corpus if any frozen semantic or harm gate fails.

Close before calls if:

- state balance is not exactly 3 each;
- lexical de-cueing fails;
- a non-unresolved case requires an unstated fact;
- an unresolved case has only one compatible state;
- private labels or actions enter the prompt.

## Proxy Validity Limits

Passing establishes only one Provider's batch relation accuracy on one fresh
hard synthetic corpus.

It does not establish:

- natural-world evidence judgment;
- external benchmark validity;
- cross-Provider transfer;
- multi-agent surplus;
- explanation completeness;
- production integration readiness.

## Anti-Additive Audit

Reused:

- six relation states;
- Runtime action mapping;
- v0.3C canonicalizer;
- DeepSeek adapter;
- batch presentation;
- evidence and authority gates.

Added:

- one fresh corpus module;
- one deterministic corpus audit;
- one batch runner and scorer.

Not added:

- new state labels;
- Single calls;
- key aliases;
- Provider-specific semantic repairs;
- CoreSlim code.

## Stop And Rollback

Stop immediately if:

- pre-call corpus audit fails;
- the batch logical call exhausts two attempts;
- total tokens exceed 20000;
- a frozen prompt or source hash differs;
- any same-version corpus, label, threshold, or prompt repair is proposed;
- a CoreSlim, retention, or baseline write is attempted.

Rollback removes only v0.3E candidate code and ignored outputs. Prior closures
remain unchanged.

