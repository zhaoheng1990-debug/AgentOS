# R3 Minimal Synthetic Validation Closure v0.1

## Status

`PASS_SYNTHETIC_FORMAL_ONLY`

Evidence coordinate:

`SYNTHETIC_FORMAL_AUDIT`

This result validates the frozen finite construction and its analytic
measurement identities. It does not validate a Provider, a real agent group,
a benchmark capability, or AgentOS production behavior.

## Frozen Coordinate

- HumanGate freeze: `R2_HUMAN_GATE_FREEZE_RECEIPT.json`;
- preregistration:
  `R3_MINIMAL_SYNTHETIC_PREREGISTRATION_V0_1.md`;
- preregistration commit: `aaa394e`;
- Provider calls: 0;
- fresh holdout consumption: 0;
- Runtime/CoreSlim imports: 0;
- retention or baseline writes: 0.

## Verification

### Preregistered gates

Result: `12/12 PASS`

Passed:

1. finite distributions normalize to one;
2. observed and analytic composition gains agree;
3. `J=0` produces no positive gain;
4. informative cells change sign at `k_star`;
5. gain is monotone in `J`;
6. gain is monotone in `k`;
7. Shapley allocations sum to `J_set`;
8. the redundant role has zero contribution;
9. dependence and information ordering match;
10. suppression is not counted as correction;
11. round totals equal marginal-gain sums;
12. no forbidden information or write channel is present.

### Source tests

Result:

```text
15 passed in 0.14s
```

### Deterministic replay

Two complete CLI runs produced byte-identical:

- `result.json`;
- `hash_inventory.json`;
- `closure.json`.

Local artifact hashes:

```text
result.json
  eae7d20a08560695c9bd00f00b69f01635b705f70e9508b142cb1835ed609648
hash_inventory.json
  412615d68bf25b97fe898cc441dfcefcc8638bd04636dc722ca2a6f901c1d323
closure.json
  5877d4ff76f0217ccaccfbf096b758beb9b97dfeceab2ebd3025a130810919d3
```

The derived artifacts remain under the ignored local output directory:

`outputs/r3_minimal_synthetic_v0_1/`

## Main Results

| Condition | Error phi | `J_set` bits/item | `J1` | `J2` | `J3` | `k_star` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| null | 1.000 | 0.000000 | 0 | 0 | 0 | 1.000 |
| dependence 0.0 | 0.000 | 0.186617 | 0 | 0.093308 | 0.093308 | 0.724 |
| dependence 0.5 | 0.500 | 0.129545 | 0 | 0.064773 | 0.064773 | 0.791 |
| dependence 1.0 | 1.000 | 0.100163 | 0 | 0.050081 | 0.050081 | 0.830 |

### Finding 1: agreement is not information

The null roles agree perfectly with each other and the control:

```text
error phi = 1
J_set = 0
```

The packet-only coordinator cannot create positive gain from those redundant
packets. At `k=1`, its gain is exactly zero.

Bounded conclusion:

`ROLE_AGREEMENT_AND_ROLE_COUNT_DO_NOT_CREATE_CONDITIONAL_INFORMATION`

### Finding 2: dependence consumes organization potential

As role-error dependence rises from 0 to 1:

```text
J_set:   0.186617 -> 0.100163 bits/item
k_star:  0.724    -> 0.830
```

The correlated roles still add information because their shared signal remains
independent of the matched control. They add less information, and the
coordinator must be more faithful before the organization becomes
task-compression positive.

Bounded conclusion:

`ERROR_DIVERSITY_IS_VALUABLE_ONLY_WHEN_IT_CARRIES_REFERENCE_RELEVANT_INFORMATION`

### Finding 3: unique role information is recoverable

The deliberately redundant first role receives exactly zero Shapley credit in
every condition.

The two informative symmetric roles split `J_set` equally.

This validates the exact finite estimator and its efficiency identity:

```text
sum_i J_i^uniq = J_set
```

It does not establish that natural-language roles will have stable positive
`J_i^uniq`.

### Finding 4: the analytic composition boundary is recovered

For every informative condition:

```text
gain below k_star < 0
gain at k_star    = 0
gain above k_star > 0
```

The observed gain equals:

```text
g = kJ - (1-k)H
```

within the frozen `1e-9` tolerance.

Bounded conclusion:

`R2_MINIMAL_COMPOSITION_PHASE_MODEL_IS_CONSTRUCTION_VALID`

This is not external mechanism validation.

### Finding 5: positive task compression is not action admissibility

The cells immediately above `k_star` have positive probabilistic task gain,
but correct retention remains between approximately 0.65 and 0.75.

Even with a perfectly faithful packet decoder (`k=1`):

| Dependence | Task-bit gain | Correct retention | Strict correction surplus | Abstention |
| --- | ---: | ---: | ---: | ---: |
| 0.0 | 0.186617 | 0.910 | +0.0840 | 0.000 |
| 0.5 | 0.129545 | 0.805 | -0.1365 | 0.315 |
| 1.0 | 0.100163 | 0.700 | -0.2100 | 0.420 |

The later two conditions improve calibrated log loss and reduce strong harm,
but they abstain on many decisions that the control got right.

Theory revision:

```text
compression-positive phase
  != action-admissible phase
```

An organization candidate requires the intersection:

```text
G_org_bits > 0
AND correct-retention gate
AND coverage gate
AND harmful-strong gate
```

No new causal variable is required. The action metrics are independent gates
over the existing `K` readbacks.

### Finding 6: suppression improves one axis by deleting action

The suppression-only arm:

```text
harmful strong decisions = 0
correct retention        = 0
task gain                = -0.118709 bits/item
```

This exactly reproduces the safety-versus-cognition distinction identified in
R1.

### Finding 7: more rounds can erase a valid first-round gain

The round schedule uses the frozen diminishing information rule:

```text
J_t = J_1 * 0.5^(t-1)
```

Observed:

| Round | Marginal gain | Cumulative gain |
| --- | ---: | ---: |
| 1 | +0.067557 | +0.067557 |
| 2 | -0.009307 | +0.058251 |
| 3 | -0.047739 | +0.010512 |
| 4 | -0.066955 | -0.056443 |
| 8 | -0.084970 | -0.383112 |

The first nonpositive marginal round is round 2. Continuing through round 4
turns an initially positive organization into a negative one.

Bounded conclusion:

`ROUND_COUNT_IS_NOT_A_COGNITIVE_GOOD; MARGINAL_INFORMATION_MUST OUTRUN COMPOSITION_HARM`

R3 identifies this boundary retrospectively. It does not validate a Runtime
stopping predictor.

## Negative Results And Boundaries

Preserved negative results:

- perfect agreement can contain zero new information;
- positive task-bit gain can coexist with unacceptable correct-action loss;
- a faithful Bayes packet decoder can become conservative under correlated
  evidence and a strong-decision threshold;
- more rounds can destroy cumulative gain;
- suppression can remove harm while removing all useful action.

These are theory constraints, not defects to patch away.

## Audit Corrections During Verification

Two shell-level verification attempts used paths relative to the experiment
directory while referring to repository-level outputs.

Those attempts did not validate their intended claims and are not counted.
Both checks were rerun with correct absolute or package-local paths:

- deterministic artifact replay: passed;
- absence of AgentOS Runtime imports: passed.

## Theory Writeback

### Accepted as bounded synthetic-formal results

- exact `J_set` and Shapley recovery;
- packet-only information ceiling;
- `k_star` phase sign;
- dependence-to-information ordering in the frozen generator;
- marginal-round accounting;
- suppression/correction separation.

### Revised

Old candidate:

> Positive `G_org_bits` is sufficient to identify an admissible cognitive
> organization.

Revised:

> Positive `G_org_bits` identifies a task-compression-positive phase only.
> Action admissibility requires separate retention, coverage, and harm gates.

### Still pending

- whether Providers can emit calibrated commensurate packets;
- whether natural role contexts produce stable positive `J_i^uniq`;
- whether a real coordinator can achieve sufficient `K_info` and
  `K_preserve`;
- whether matched-budget small-model groups show organizational surplus;
- whether small-model groups achieve large-model cognitive equivalence;
- whether gains transfer across tasks and Providers.

## Baseline And Authority

Baseline insertion:

`THEORY_FIRST_RESET_RESEARCH_LAYER_ONLY`

No AgentOS Runtime, CoreSlim, retention, or production baseline update is
authorized.

R3 status:

`COMPLETE`

Next research object:

`R4_PROVIDER_ADEQUACY_PREREGISTRATION`

R4 Provider calls remain unauthorized until a new theory packet and HumanGate
freeze are completed.
