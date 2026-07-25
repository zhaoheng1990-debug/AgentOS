# R4 Relation Boundary Synthetic Closure v0.3A

## Status

`PASS_SYNTHETIC_RELATION_CONSTRUCTION_ONLY`

Evidence coordinate:

`SYNTHETIC_FORMAL_AUDIT`

This result validates the finite engineering object chain from an accepted
oracle relation graph to a deterministic composition receipt. It does not
validate Provider semantic relation recognition, natural evidence dependence,
or AgentOS production behavior.

## Frozen Coordinate

- theory: `R4_SEMANTIC_RELATION_COMPOSITION_THEORY_V0_3.md`;
- object map: `R4_ENGINEERING_OBJECT_MAP_V0_3.md`;
- authorization: `R4_RELATION_BOUNDARY_AUTHORIZATION_V0_3A.json`;
- preregistration:
  `R4_RELATION_BOUNDARY_SYNTHETIC_PREREGISTRATION_V0_3A.md`;
- preregistration commit: `536a87e`;
- Provider calls: 0;
- fresh holdout consumption: 0;
- CoreSlim, Runtime, retention, and baseline writes: 0.

## Verification

### Frozen gates

Result:

`14/14 PASS`

Passed:

1. all 12 fixtures loaded;
2. actions matched 12/12;
3. actionable mean probability error was zero;
4. actionable maximum probability error was zero;
5. blocked cases emitted no probability;
6. exact duplicates were selected once;
7. duplicate-plus-independent composition was order invariant;
8. an incomplete graph blocked;
9. duplicate probability conflict blocked;
10. contradictory cross-component relation blocked;
11. common-prior mismatch blocked;
12. naive duplicate composition exposed overconfidence;
13. removal and wrong-relation controls exposed the frozen failure;
14. forbidden calls and writes remained zero.

### Source tests

Initial run:

```text
12 passed, 1 setup error
```

The setup error was a Windows permission failure in the system pytest temporary
directory before the replay test executed. No source or frozen case was changed.

Repository-local temporary directory rerun:

```text
13 passed in 0.06s
```

### Deterministic replay

The replay test produced byte-identical:

- `result.json`;
- `hash_inventory.json`;
- `closure.json`.

Local artifact hashes:

```text
result.json
  1e3faf9e619ddcd7fd360e6ae44a02ddccd7944934b1c17cd4bb468875714a4f
hash_inventory.json
  ce6449ef9d1fc44054465c43d0241c78ec57c07f34c3291f2995a3c152c93755
```

## Outcome Distribution

| Outcome | Count |
| --- | ---: |
| `COMBINE` | 2 |
| `DEDUPE_AND_COMBINE` | 2 |
| `BLOCK` | 8 |

The four actionable cases produced exact probabilities:

| Case | Action | Selected | Excluded | Probability |
| --- | --- | --- | --- | ---: |
| R43A-01 | COMBINE | P1, P2 | none | 0.888889 |
| R43A-02 | COMBINE | P1, P2, P3 | none | 0.666667 |
| R43A-03 | DEDUPE_AND_COMBINE | P1 | P2 | 0.800000 |
| R43A-04 | DEDUPE_AND_COMBINE | P1, P3 | P2 | 0.666667 |

The eight blocked cases represented:

- dependent distinct evidence;
- partial evidence overlap;
- scope incompatibility;
- unresolved relation;
- incomplete relation graph;
- duplicate packets with inconsistent probabilities;
- contradictory relation states around a duplicate component;
- common-prior mismatch.

## Main Phenomena

### 1. Relation premise and arithmetic consequence are separable

Once a complete admissible relation graph is accepted, packet selection,
deduplication, shared-prior removal, and probability composition are exact and
require no Provider call.

Bounded conclusion:

`SEMANTIC_PREMISE_AND_DETERMINISTIC_CONSEQUENCE_HAVE_DISTINCT_OWNERS`

### 2. Duplicate evidence creates substantial false confidence

Two exact duplicate packets each implied probability 0.8.

Correct deduplication:

```text
0.800000
```

Naive independent composition:

```text
0.941176
```

Overconfidence error:

```text
+0.141176
```

For an exact duplicate pair plus one independent packet:

```text
correct: 0.666667
naive:   0.888889
error:  +0.222222
```

This is a concrete anti-additive failure: one redundant packet adds no
information but materially changes the decision surface if counted twice.

### 3. Relation completeness is an admissibility condition

Removing one required edge from a valid two-packet graph changed the plan from
`COMBINE` to `BLOCK`.

This does not mean missing information is negative evidence. It means the
composition operation is not identified.

### 4. Wrong relation state is more dangerous than missing relation state

Changing an exact duplicate relation to `INDEPENDENT_DISTINCT` produced:

```text
action: COMBINE
probability: 0.941176
```

An unresolved relation blocks and loses coverage. A confidently wrong
independent relation produces unsupported confidence. Future Provider
experiments must therefore place a zero-harm gate on false `COMBINE`, not only
maximize overall classification accuracy.

### 5. Block rate is not cognitive quality

Eight of twelve cases blocked because the frozen corpus deliberately contains
eight non-actionable graph conditions. The result cannot be interpreted as
evidence that conservative blocking creates Cbit.

The future semantic experiment must separately report:

- correct block;
- false block;
- false combine;
- false deduplicate;
- actionable coverage.

## Rival Readback

### R0: relation state is insufficient

Not supported inside this finite construction. The six-state relation object was
sufficient to derive all frozen plans.

Boundary:

This does not show sufficiency for real dependence magnitudes or partial
composition.

### R1: packet identity alone is sufficient

Not tested. v0.3A receives oracle relation states. A fresh semantic experiment
must hide private canonical relation labels from Runtime and Provider prompts.

### R2: fail-closed compilation is too conservative

Still open. v0.3A contains no beneficial dependent or partial-overlap case with
a supplied numeric dependence model. Blocking is correct under the frozen
information boundary but may reduce future coverage.

### R3: graph works but Provider cannot instantiate it

Now becomes the leading unresolved rival.

## Engineering Object Decision

Accepted for the next standalone experiment:

- `SemanticRelationQuestion`;
- candidate-only `ProviderRelationAssessment`;
- Runtime-owned `RelationAssessmentReceipt`;
- `PacketRelationGraphCandidate`;
- Runtime-owned `CompositionPlan`;
- Runtime-owned `CompositionReceipt`.

Rejected:

- a new `ProviderSemanticRelationCoordinator`;
- a second coordination Runtime;
- Provider-computed composition probabilities;
- Provider-emitted composition actions.

No Core synchronization is authorized.

## Negative Results And Limits

1. The experiment did not call or validate a Provider.
2. Relation labels were oracle inputs.
3. Exact finite arithmetic is not natural-language cognition.
4. Blocking does not establish positive Cbit.
5. Dependence and partial overlap remain non-composable without an accepted
   quantitative model.
6. The state taxonomy may require revision after fresh semantic evidence.
7. No baseline object update is justified.

## Next Research Object

`FRESH_PROVIDER_SEMANTIC_RELATION_INSTANTIATION`

The next experiment should:

- use newly generated semantic micro-worlds not present in R4 v0.1-v0.3A;
- expose packet descriptors but hide private relation labels;
- ask Provider only for the six-state relation;
- compare batch and single-case presentation;
- derive composition action locally;
- include oracle and wrong-relation controls;
- require zero false `COMBINE` and zero false `DEDUPE_AND_COMBINE`;
- preserve false blocks separately from harmful actions;
- prohibit Core, retention, and baseline writes.
