# R2 Symbol And Proxy Audit

## Status

`COMPLETE`

Evidence coordinate: `THEORY_CORRESPONDENCE_AUDIT`

This audit aligns the AgentOS collective-cognition project with:

1. Cognitive Research Architecture v3.7;
2. MethodologyKernel v1.1;
3. the R1 archived organizational identifiability result.

It changes no Runtime, Provider, CoreSlim, retention, or baseline behavior.

## Upper-Level Inheritance

Cognitive Research Architecture v3.7 defines:

```text
Cognition = constraint-guided effective compression of possibility space
Cbit = Delta H_c
Cbit_eff = Delta H_c * Meaning or constraint alignment
```

`H_c` is entropy over candidate cognitive structures under a constraint field.
It is not automatically the entropy of a benchmark label.

The architecture also already uses `U` inside Meaning to denote whether the
subject can call or use an object constraint.

## Audit Finding 1: Symbol Collision

R1 and R2 v0.1 used `U_i` for unique conditional role information.

This collides with the upper-level `U` usability term:

```text
Meaning = V * R * U
```

Decision:

```text
historical U_role -> J_i^uniq
```

`J_i^uniq` denotes role `i`'s unique conditional predictive information. It is
a project-level organization variable, not the upper-level Meaning usability
term.

## Audit Finding 2: Benchmark Bits Are A Proxy

For a private task reference `Y*` and calibrated prediction `q`, log loss is:

```text
L_log(q, Y*) = -log2 q(Y*)
```

A reduction in expected log loss has units of bits per item:

```text
G_task_bits = E[L_log(control, Y*) - L_log(candidate, Y*)]
```

This is a valid controlled task-compression proxy when:

- the candidate set is explicit and exhaustive for the task;
- the object and reference relation are fixed;
- the prediction is a normalized probability distribution;
- calibration and evidence alignment are separately checked.

It is not ontologically identical to `Delta H_c`.

Decision:

```text
G_task_bits -> Cbit_task_proxy
Cbit_task_proxy != ontological Cbit
```

## Audit Finding 3: Effective Cbit Cannot Be Recovered By One Arbitrary Score

R1 shows why accuracy, harm, retention, and token cost cannot be collapsed
after the fact:

- v0.82 improves correctness without recovering every semantic class;
- v0.88 improves some cases and harms different cases at the same accuracy;
- v0.89 lowers one harm by broadly suppressing correct actions.

Decision:

Report a vector:

```text
task compression
constraint alignment
correct retention
harm
operational cost
```

Do not invent a posthoc scalar exchange rate between task bits and tokens.
Cost is a Pareto coordinate and a preregistered budget boundary.

## Audit Finding 4: Two Claims Had Been Conflated

The small-model organization hypothesis contains two different claims.

### Cognitive equivalence

A small-model organization reaches the task performance of a larger model by
using more rounds or tokens.

```text
L(group_small) <= L(large_model) + noninferiority_margin
```

This can be useful even without cognitive multiplication.

### Organizational surplus

The organization exceeds both the best small member and a matched-budget
serial small-model control.

```text
L(group_small) < min(
    L(best_small_member),
    L(matched_budget_serial_small)
)
```

This is the stronger collective-cognition claim.

Decision:

R3 studies the mechanism and phase boundary. R5 must evaluate equivalence and
organizational surplus as separate claims.

## Audit Finding 5: Coordinator Information Has A Ceiling

Let `Z` be the set of role packets and `X_c` the information available to the
matched control. A pure coordinator receives `X_c` and `Z`, but no private
reference and no new evidence channel.

Under that boundary:

```text
I(Y; coordinator_output | X_c)
<= I(Y; Z | X_c)
```

This is a data-processing ceiling. A coordinator may synthesize information
distributed across packets and outperform every individual member, but it
cannot exceed the joint packet information without an additional channel.

If the coordinator sees raw evidence or makes a new Provider query that the
control does not receive, unique coordination gain is confounded with new
information acquisition.

Decision:

R3 requires a packet-only coordinator arm. Later full Runtime experiments may
add evidence access, but must label it as a different causal object.

## Correspondence Map

| Layer | Object | Allowed claim |
| --- | --- | --- |
| upper ontology | `Delta H_c` under constraint alignment | effective possibility-space compression |
| project theory | cognitive organization | conditional role information plus faithful composition |
| observable proxy | held-out proper-score gain | task-level compression in bits per item |
| diagnostics | correction, retention, harm, oracle gap, cost | bounded behavior and failure mechanism |

The arrows are correspondence mappings:

```text
UpperOntologyObject
  -> ProjectObject
  -> ObservableProxy
  -> Metric
```

They are not identities.

## Anti-Additive Result

No new Runtime variable is needed.

The audit removes two ambiguities:

1. `U` symbol collision;
2. ontological Cbit versus benchmark-bit proxy collapse.

The revised minimum theory uses:

- `J^uniq`: conditional role information;
- `K`: coordinator composition profile;
- `E_dep`: role error dependence;
- `F`: friction and cost;
- `T`: cognitive rounds.

Representation adequacy remains a prerequisite and readback, not an additional
organization mechanism.

## Writeback

```text
Object:
  AgentOS collective-cognition measurement language
Status:
  REVISED
Evidence:
  upper-level theory correspondence plus R1 internal evidence
Boundary:
  no empirical organization claim
BaselineInsertion:
  R2 theory packet v0.2
```
