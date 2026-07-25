# R4 Engineering Object Map v0.3

## Status

`CANDIDATE_ONLY_STANDALONE_EXPERIMENT`

This object map optimizes the earlier two-box proposal. It does not add a second
coordination Runtime and does not authorize CoreSlim synchronization.

## Existing Owner

### CognitiveCoordinationRuntime

Existing responsibility:

- organize cognitive role progression;
- request Provider-backed route advice;
- apply Kernel prerequisites, budgets, evidence scope, and anti-loop gates;
- produce only pending candidate progression.

Change in v0.3:

`NONE`

It may later consume a `CompositionReceipt` as bounded evidence. It does not
become the packet arithmetic engine.

## New Candidate Objects

### 1. SemanticRelationQuestion

Owner: Runtime

Purpose:

- bind two packet references;
- bind the admissible evidence descriptors;
- ask only for their semantic composition relation.

Forbidden:

- probability composition;
- route selection;
- final candidate state.

### 2. ProviderRelationAssessment

Owner: Provider-backed support layer

Status: candidate only

Required semantic output:

- relation state;
- cited descriptor references;
- bounded rationale;
- unresolved assumptions.

Forbidden output:

- composition action;
- selected packet;
- composed probability;
- accept, retain, promote, or publish state.

### 3. RelationAssessmentReceipt

Owner: Runtime

Purpose:

- validate Provider/model/question binding;
- validate relation enum and evidence scope;
- preserve raw assessment and invocation receipt;
- expose no automatic acceptance.

### 4. PacketRelationGraphCandidate

Owner: Runtime

Purpose:

- require one relation per packet pair;
- preserve relation conflicts and unresolved edges;
- identify exact-duplicate components;
- remain candidate only.

It is not a second task repository or durable state machine.

### 5. CompositionPlan

Owner: deterministic Runtime compiler

Allowed actions:

- `COMBINE`
- `DEDUPE_AND_COMBINE`
- `BLOCK`

Derivation:

- all independent distinct -> combine;
- exact duplicates plus otherwise independent components -> dedupe and combine;
- any dependence, partial overlap, scope mismatch, unresolved edge, missing
  edge, or internal contradiction -> block.

Provider cannot emit this object.

### 6. CompositionReceipt

Owner: deterministic Runtime

Purpose:

- bind graph hash, selected packet IDs, excluded duplicate IDs, prior, formula,
  result probability, errors, and no-Provider-call attestation;
- support replay and later Kernel review.

It grants no retention or baseline authority.

## Dependency Direction

```text
SemanticRelationQuestion
  -> ProviderRelationAssessment
  -> RelationAssessmentReceipt
  -> PacketRelationGraphCandidate
  -> CompositionPlan
  -> CompositionReceipt
  -> existing CognitiveCoordinationRuntime / Kernel review
```

No reverse dependency may mutate an upstream receipt.

## Modularity Constraints

- contracts contain no Provider client;
- Provider adapter contains no compiler policy;
- graph compiler contains no network code;
- composer contains no semantic classifier;
- receipt writer contains no promotion policy;
- no module may create a durable Runtime state owner;
- experiment code remains outside CoreSlim.

## Removal Tests

1. Remove `ProviderRelationAssessment`:
   oracle relation receipts still validate the compiler construction.
2. Remove `PacketRelationGraphCandidate`:
   incomplete pair coverage can no longer be detected.
3. Remove `CompositionPlan`:
   Provider relation state can leak directly into action.
4. Remove deduplication:
   exact duplicates become overconfident.
5. Remove block states:
   unsupported dependence can be composed.
6. Remove `CognitiveCoordinationRuntime` integration:
   standalone composition remains testable; no new coordinator is needed.

## Core Synchronization Gate

Core synchronization remains forbidden until:

- v0.3A zero-Provider construction passes;
- a fresh Provider relation experiment passes;
- an independent-model or independent-context replication exists;
- false composition and false deduplication are zero;
- object removal tests pass;
- HumanGate approves contract-only synchronization.
