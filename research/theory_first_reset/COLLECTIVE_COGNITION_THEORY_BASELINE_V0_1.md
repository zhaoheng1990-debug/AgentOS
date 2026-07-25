# Collective Cognition Theory Baseline v0.1

## Status

`CANDIDATE_THEORY - NOT YET EXPERIMENTALLY ACCEPTED`

This document defines the object to be studied before another implementation
round. It revises the earlier engineering-centered object and does not claim
that AgentOS already realizes collective cognition.

## 1. Target Object

The research object is not a collection of agents, roles, prompts, or
receipts. It is:

> A cognitive organization whose structured interaction produces positive
> marginal effective Cbit beyond its best available member on the same object,
> under explicit evidence, harm, and coordination-cost boundaries.

The theory-to-measurement chain is:

```text
CognitiveOrganization
  -> conditional role contribution and composition dynamics
  -> matched-access, matched-budget task behavior
  -> correction, retained-correct, calibration, harm, and cost metrics
```

Benchmark accuracy is therefore a proxy. Receipt validity is an operational
precondition. Neither is the ontology object.

## 2. Runtime and Provider

AgentOS Runtime remains the cognitive subject. It owns:

- goals and problem boundaries;
- the current cognitive object and its allowed transformations;
- role constitution and evidence-access policy;
- evidence organization and conflict state;
- composition, stopping, replay, rollback, and final candidate state.

Providers support those capabilities by supplying bounded semantic judgments.
They do not become the subject merely because local code cannot perform the
same semantic operation.

## 3. Minimal Formal Objects

Let:

- `O` be the target cognitive object;
- `E0` be the evidence available before collaboration;
- `B0` be the initial Runtime belief or candidate state;
- `Zi,t` be the receipt produced by role `i` at round `t`;
- `pi` be the organizational policy for access, routing, communication,
  composition, and stopping;
- `BT` be the final Runtime belief or candidate state;
- `L(B, O*)` be a preregistered proper loss or decision loss against a private
  reference `O*`.

The observable gross gain is:

```text
G = L(B0, O*) - L(BT, O*)
```

For one role, its conditional contribution is measured by a preregistered
ablation:

```text
Delta_i = E[L(B_without_i, O*) - L(B_with_i, O*)] - IncrementalCost_i
```

A role is cognitively real for the tested object only if `Delta_i` is
out-of-sample positive and its contribution is not explained solely by more
tokens, broader evidence access, or increased abstention.

The current candidate effective-Cbit functional is:

```text
Cbit_eff_proxy =
    gross decision gain
  - harmful certainty
  - lost correct decisions
  - redundant correlated work
  - coordination friction
  - architecture complexity cost
  - negative-transfer risk
```

This is a calibrated proxy, not a claim that the benchmark directly measures
physical information bits.

## 4. Necessary Conditions

### 4.1 Object adequacy

The organization must represent the object at the level needed to explain the
task. Repeated local errors with a shared cause require object upgrading, not
another field.

### 4.2 Conditional complementarity

Different roles must supply conditionally non-redundant evidence or
transformations. Different names or prompts do not establish complementarity.

### 4.3 Error diversity

The organization needs partially independent failure modes. Multiple roles
sharing the same framing, context, evidence, and Provider may create correlated
confidence rather than collective intelligence.

### 4.4 Relation-aware composition

The meaning of a receipt depends on the target relation. Contradiction is
failure for a support claim but evidence for a refutation claim. Kernel
meta-rules must compose typed relations rather than count positive fields.

### 4.5 Coordinator conservation

A coordinator is useful only if it preserves identity, provenance,
disagreement, and uncertainty while composing contributions. Majority voting,
premature consensus, or universal veto are not sufficient.

### 4.6 Marginal stopping

Another round is justified when predicted marginal effective Cbit is positive.
Token cost may be high when cognitive gain is stably higher; cost becomes
anti-additive when extra work adds redundancy, harm, or unidentifiable
complexity.

## 5. Problem Emergence

Correct problem definition is treated as an upstream cognitive operation.

Before problem-space search, the organization may need to expand an
object-structure space:

```text
ObjectStructureSpace
  -> candidate objects, relations, boundaries, coordinate systems
  -> challenged and contrasted problem definitions
  -> admitted research problem
  -> hypothesis and experiment space
```

The structure expansion should include at least:

- direct decomposition;
- reverse challenge;
- object substitution;
- coordinate-system change;
- side-view or structurally analogous objects;
- boundary and counterexample search;
- unknown-variable and missing-relation proposals.

An imaginative proposal is not rejected merely for distance from the current
baseline. It competes under the same expected effective-Cbit criterion, with a
bounded exploration budget and no automatic baseline authority.

## 6. Theory Propositions

### P1: Decomposition is not multiplication

Splitting one judgment into more receipts increases collective performance
only when the receipts add unique conditional information or error correction.

### P2: Object-first advantage

When failures share a latent structural cause, object-space expansion before
local classification should outperform additional classifier refinement.

### P3: Independent evidence beats cosmetic role diversity

Roles with asymmetric evidence, priors, methods, or isolated trajectories
should provide more marginal gain than one Provider wearing multiple labels
under shared context.

### P4: Coordination has a phase boundary

Below a complementarity threshold, added communication creates friction and
correlated error. Above it, a provenance-preserving coordinator can convert
distributed partial information into net gain.

### P5: Safety and cognition are orthogonal

Fail-closed behavior can reduce harmful actions without increasing semantic
correctness. Both axes must be measured.

### P6: Problem quality bounds downstream Cbit

If the organization selects the wrong object or problem, additional solution
iterations mainly refine the wrong target. High-value problem definition is
therefore a prerequisite, though not a guarantee, for positive effective Cbit.

### P7: Complexity needs theoretical rent

Every added role, state, receipt, or gate must be justified by a predicted
change in a named theory variable and must survive ablation. Otherwise it is a
patch.

## 7. Rival Hypotheses

| Rival | Discriminating implication |
| --- | --- |
| Compute-only | A matched-token single agent performs as well as the organization. |
| Abstention-only | Harm falls, but valid correction and retained-correct performance do not rise. |
| Benchmark-coordinate artifact | Gains disappear under a second metric or independently defined object. |
| Same-Provider correlation | Role gains disappear when contexts are isolated or evidence access is made asymmetric. |
| Coordinator bottleneck | Independent roles contain useful evidence that is lost only after composition. |
| Object-mismatch | Local classifiers fail together, while object-first expansion changes the error class. |

## 8. Current Theory State

### Accepted as bounded evidence

- decomposition alone is insufficient;
- fail-closed safety is not semantic correction;
- object binding, warrant, context utility, and final utility are
  non-equivalent;
- Provider-backed stages can amplify correlated framing;
- more tokens can be rational, but only with positive marginal gain.

### Pending

- whether true role independence produces stable positive marginal Cbit;
- whether a coordinator can conserve disagreement and compose complementary
  evidence;
- whether object-structure expansion improves problem definition;
- whether small-model organizations can match larger models by trading more
  iterations for lower per-agent capacity;
- whether the gain survives matched-compute and fresh-transfer controls.

### Rejected over-strong claims

- more roles imply more cognition;
- schema-valid receipts imply safe Runtime cognition;
- benchmark accuracy alone establishes cognitive multiplication;
- a veto-only organization is better because it produces fewer harmful
  actions;
- one successful surface authorizes a general AgentOS capability.
