# R3 Minimal Synthetic Validation Preregistration v0.1

## Status

`FROZEN_BEFORE_IMPLEMENTATION_AND_RESULTS`

Freeze authority:

`R2_HUMAN_GATE_FREEZE_RECEIPT.json`

This window inherits Cognitive Research Architecture v3.7,
MethodologyKernel v1.1, and the frozen R2 v0.2 theory packet.

## Objective

Test whether a finite exact synthetic system recovers:

1. conditional packet information `J`;
2. role-specific Shapley information `J_i^uniq`;
3. the packet-only coordinator information ceiling;
4. the composition equation
   `g = k * J - (1 - k) * H`;
5. the phase boundary `k_star = H / (J + H)`;
6. the distinction between correction and suppression;
7. additive round accounting and the marginal stopping boundary.

R3 validates the theory and measurement instrument. It does not validate a
Provider, benchmark, Runtime, or production capability.

## Object-Before-Proxy

```text
OntologyObject:
  CognitiveOrganization
ProjectObject:
  conditionally informative packets plus bounded composition
ObservableProxy:
  exact finite binary signal system
Metric:
  base-2 log loss, conditional information, composition gain,
  hard-decision retention, harm, and exact phase sign
```

## Fixed Synthetic Object

The private reference is binary:

```text
Y in {0, 1}
P(Y = 0) = P(Y = 1) = 0.5
```

Every signal has error rate:

```text
e = 0.30
```

The matched control signal is:

```text
X = Y xor E0
E0 ~ Bernoulli(e)
```

The first role is deliberately redundant:

```text
Z1 = X
```

This provides a known zero-contribution role and tests whether
`J_1^uniq = 0`.

## Role Packet Conditions

### Null condition

```text
Z2 = X
Z3 = X
```

All packets are conditionally redundant with the matched control:

```text
J_set = 0
```

### Informative conditions

`Z2` and `Z3` are noisy observations of `Y`, independent of `X` conditional on
`Y`.

Their dependence is controlled by `d`:

```text
d in {0.0, 0.5, 1.0}
```

With probability `d`, both roles use one shared error draw:

```text
Z2 = Y xor Es
Z3 = Y xor Es
```

With probability `1 - d`, they use independent error draws:

```text
Z2 = Y xor E2
Z3 = Y xor E3
```

All error draws use `Bernoulli(e)` and are independent of `E0`.

Predicted ordering:

```text
J_set(d=0.0) >= J_set(d=0.5) >= J_set(d=1.0) > 0
```

No claim is made that this construction is a fair real-model organization
benchmark. It is a known-truth mechanism test.

## Exact Decoders

All supported finite states are enumerated exactly.

For any available variable subset `S`, the decoder is:

```text
q_S(Y) = P(Y | S)
```

Its expected loss is:

```text
L_S = E[-log2 q_S(Y)]
```

The matched reference control is `X`.

Joint packet information is:

```text
J_set = L_X - L_(X,Z1,Z2,Z3)
```

Role-specific information is the exact Shapley allocation over all subsets of
`{Z1, Z2, Z3}`, conditional on `X`.

Required identity:

```text
sum_i J_i^uniq = J_set
```

## Coordinator Construction

### Faithful output

The faithful packet-only coordinator emits:

```text
q_star = P(Y | X,Z1,Z2,Z3)
```

### Corrupt output

The corrupt coordinator emits the inverted matched-control posterior:

```text
q_corrupt(Y = X) = 0.30
q_corrupt(Y != X) = 0.70
```

Define:

```text
H = L_corrupt - L_X
```

`H` must be positive.

### Mixed coordinator

With probability `k`, the coordinator emits `q_star`. With probability
`1-k`, it emits `q_corrupt`.

Because expected log loss is linear over this explicit mixture event:

```text
G_observed = L_X - [k * L_star + (1-k) * L_corrupt]
G_analytic = k * J_set - (1-k) * H
```

Required identity:

```text
abs(G_observed - G_analytic) <= 1e-9
```

## Phase Grid

For each informative dependence condition, compute:

```text
k_star = H / (J_set + H)
```

Evaluate:

```text
k_below = max(0, k_star - 0.10)
k_at    = k_star
k_above = min(1, k_star + 0.10)
```

Expected signs:

```text
G(k_below) < 0
abs(G(k_at)) <= 1e-9
G(k_above) > 0
```

For the null condition, evaluate:

```text
k in {0.0, 0.5, 1.0}
```

No null cell may produce positive gain above `1e-9`.

## Hard-Decision And Suppression Control

A prediction is strong when:

```text
max(q) >= 0.60
```

Otherwise it is `ABSTAIN`.

The suppression-only coordinator always emits:

```text
q_suppress = (0.5, 0.5)
```

Predictions:

- harmful strong decisions fall to zero;
- correct strong retention falls to zero;
- task-bit gain relative to `X` is negative;
- suppression cannot count as correction.

## Error Dependence

Role error dependence is measured on `Z2` and `Z3` by exact paired error phi.

This is a diagnostic. The theory object remains `J_set`.

Required qualitative relationship:

```text
higher injected dependence
  -> nondecreasing paired error phi
  -> nonincreasing J_set
```

## Round Dynamics

Round accounting uses the frozen deterministic schedule:

```text
J_t = J_1 * 0.5^(t-1)
H_t = H
T in {1, 2, 4, 8}
```

For each round:

```text
g_t = k * J_t - (1-k) * H_t
```

Required identity:

```text
G_T = sum_(t=1..T) g_t
```

The first nonpositive `g_t` is the retrospective stopping boundary. R3 does
not implement a deployable stopping predictor.

## Frozen Gates

R3 passes only if:

1. all frozen source and result identities use tolerance `1e-9`;
2. the null condition produces no positive organization gain;
3. every informative condition changes sign at `k_star`;
4. gain is nondecreasing in `J` under fixed `k` and `H`;
5. gain is nondecreasing in `k` under fixed `J` and `H`;
6. exact Shapley contributions sum to `J_set`;
7. the redundant first role has zero contribution;
8. dependence ordering and `J_set` ordering match the prediction;
9. suppression fails task gain and correct-retention gates;
10. round totals equal the sum of round gains;
11. a second run produces identical result hashes;
12. no Provider, fresh holdout, Runtime, CoreSlim, retention, or baseline write
    occurs.

No threshold or metric may change after the first result is generated.

## Failure Classification

| Failure | Meaning |
| --- | --- |
| `CONSTRUCTION_FAILURE` | enumerated distribution does not match the frozen generator |
| `IMPLEMENTATION_FAILURE` | computed values disagree with analytic identities |
| `THEORY_FAILURE` | valid construction violates a frozen phase prediction |
| `IDENTIFIABILITY_FAILURE` | control or coordinator receives an unrecorded channel |
| `PROXY_FAILURE` | metric cannot recover its known generating quantity |
| `ANTI_ADDITIVE_FAILURE` | passing requires a new variable or exception |

## Output Boundary

Source code:

`experiments/theory_first_r3/`

Ignored local outputs:

`outputs/r3_minimal_synthetic_v0_1/`

Tracked writeback:

`research/theory_first_reset/R3_MINIMAL_SYNTHETIC_CLOSURE_V0_1.md`

## Stop And Rollback

Stop without patching the theory if any frozen gate fails.

Rollback target:

`R2_V0_2_FROZEN_R3_NOT_VALIDATED`
