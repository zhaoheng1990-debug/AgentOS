# R2 Cognitive Organization Theory Packet v0.2

## Status

`READY_FOR_HUMAN_FREEZE_REVIEW`

This is not a frozen engineering authorization. R3 remains blocked until the
HumanGate explicitly approves this packet and its quantitative gates.

## Inheritance

Upper ontology: `Cognitive Research Architecture v3.7`

Project baseline: `COLLECTIVE_COGNITION_THEORY_BASELINE_V0_1`

Methodology: `MethodologyKernel v1.1`

Empirical boundary: `R1_ORGANIZATIONAL_IDENTIFIABILITY_AUDIT.md`

Proxy audit: `R2_SYMBOL_AND_PROXY_AUDIT.md`

## Target Object

```text
CognitiveOrganization
= conditionally informative role trajectories
+ a provenance-preserving composition process
+ a bounded iteration and stopping policy
```

The strong organization claim requires positive task compression beyond:

1. the best matched individual member;
2. a matched-budget serial single-agent control.

The weaker cognitive-equivalence claim is evaluated separately against a
larger model and does not establish organizational surplus.

## Excluded Claims

This packet does not claim that:

- role names or prompts create independent cognitive actors;
- workflow depth is collective cognition;
- a benchmark label bit is identical to ontological Cbit;
- hindsight oracle selection is a deployable coordinator;
- abstention or veto is semantic correction;
- more tokens are harmful when they buy stable positive task compression;
- a synthetic phase diagram establishes Provider or benchmark transfer;
- endogenous problem definition has been solved.

R3 holds the cognitive object and task reference fixed.

## Symbol Table

| Symbol | Meaning |
| --- | --- |
| `O` | fixed cognitive object |
| `Y*` | private task reference |
| `X_c` | information available to the matched control |
| `Z_i,t` | bounded packet from role `i` at round `t` |
| `q_m` | calibrated predictive distribution emitted by system `m` |
| `L_m` | expected base-2 log loss of system `m` |
| `J_set` | joint conditional packet information beyond the matched control |
| `J_i^uniq` | role-specific conditional information allocation |
| `E_dep` | dependence among role error residuals |
| `K` | coordinator composition profile |
| `F` | coordination friction and resource cost |
| `T` | number of cognitive rounds |

`J` replaces the historical project symbol `U_role`. Upper-level `U` remains
reserved for Meaning usability.

## Task-Cbit Proxy

For normalized prediction `q_m`:

```text
L_m = E[-log2 q_m(Y*)]
```

Define the strongest matched control:

```text
L_ref = min(
    L_best_member,
    L_matched_budget_serial
)
```

The organizational task-compression proxy is:

```text
G_org_bits = L_ref - L_coordinated
```

Interpretation:

- `G_org_bits > 0`: positive organizational task compression;
- `G_org_bits = 0`: no identifiable surplus;
- `G_org_bits < 0`: anti-additive organization.

This is `Cbit_task_proxy`, not ontological `Delta H_c`.

Hard-decision correction surplus is secondary:

```text
S_correction = corrected_count - introduced_error_count
```

The organization claim requires both proper-score gain and bounded
hard-decision harm. Accuracy alone is insufficient.

## Unique Conditional Role Information

Let `Z_all` be all blind role packets. The packet-set information available
beyond the strongest matched control is:

```text
J_set = I(Y*; Z_all | X_c)
```

Under a calibrated Bayes-consistent decoder, the operational proxy is:

```text
J_set_proxy =
    L(decoder using X_c)
  - L(decoder using X_c and Z_all)
```

Both decoders must be evaluated out of sample or by cross-fitting.

### Role attribution

Simple leave-one-out attribution is order-dependent when roles overlap.
Role-specific information therefore uses a Shapley allocation:

```text
J_i^uniq =
  average over subsets S not containing i of
  [L(decoder using S) - L(decoder using S plus i)]
```

For the minimal three-role design, every subset can be evaluated exactly.

A role is cognitively nonredundant for the tested object only when:

- `J_i^uniq` is out-of-sample positive;
- the role is blind before its first packet;
- it uses the shared decision contract;
- evidence and token access are recorded;
- its contribution persists across held-out seeds or tasks;
- its gain is not explained only by broader access or abstention.

## Coordinator Composition Profile

A pure coordinator receives `X_c` and role packets. It receives no private
reference and opens no new evidence or Provider channel.

### Information capture

Let `L_packet_star` be the held-out loss of the best admissible decoder of the
joint packet set:

```text
J_set_proxy = L_ref - L_packet_star
```

When `J_set_proxy > 0`:

```text
K_info =
  (L_ref - L_coordinated)
  / (L_ref - L_packet_star)
```

Interpretation:

- `K_info = 1`: the coordinator captures the measured packet potential;
- `0 < K_info < 1`: partial capture;
- `K_info = 0`: no capture;
- `K_info < 0`: composition is actively harmful;
- `K_info > 1`: estimator error, leakage, or an unrecorded information channel
  must be audited before calling it synergy.

### Conservation

```text
K_preserve =
  upstream-correct decisions retained
  / upstream-correct decisions available
```

### Grounding and invention

Report:

- unsupported final additions;
- provenance loss;
- disagreement erased without warrant;
- calibrated uncertainty lost;
- harmful strong decisions.

`K` is a latent composition object with multiple readbacks. It is not reduced
to majority vote or one scalar field in Runtime.

## Information Ceiling

For a packet-only coordinator:

```text
I(Y*; coordinator_output | X_c)
<= I(Y*; Z_all | X_c)
```

Consequences:

1. If `J_set = 0`, stable positive organization gain is impossible under a
   proper loss without leakage or estimator error.
2. More roles cannot create information when all packets are conditionally
   redundant.
3. A coordinator can outperform every member by combining distributed
   information while remaining below the joint-packet ceiling.
4. Raw-evidence access or extra Provider calls define a different experiment
   because they add an information channel.

## Minimal Composition Phase Model

At round `t`, define:

- `J_t >= 0`: packet information potentially capturable at that round;
- `k_t in [0, 1]`: probability or fraction of faithful composition;
- `H_t >= 0`: expected task-bit loss under a corrupt composition event.

The minimal expected round gain is:

```text
g_t = k_t * J_t - (1 - k_t) * H_t
```

The positive-composition boundary is:

```text
k_t > H_t / (J_t + H_t)
```

This yields the required phase behavior:

- low `J_t`: even a good coordinator has little to capture;
- high `J_t`, low `k_t`: v0.88-like complementarity without realization;
- low `k_t`, high `H_t`: v0.89-like anti-additive suppression or corruption;
- high `J_t`, high `k_t`: positive organizational task compression.

Across rounds:

```text
G_T = sum from t=1 to T of g_t
```

The retrospective optimal stopping boundary is:

```text
continue while expected g_(t+1) > 0
```

R3 may identify this boundary offline. It does not authorize a Runtime stopping
predictor.

## Error Dependence

`E_dep` controls how much new information later roles can contribute.

The primary readback is conditional residual dependence among blind judgments
on the same object. Pairwise error phi is permitted as a diagnostic, but is not
treated as the ontology object.

Predictions:

- perfect redundancy drives `J_set` toward zero;
- lower dependence can increase `J_set`, but only when differences are
  reference-relevant;
- random disagreement without predictive information does not increase
  `J_set`;
- diversity is potential, not organization, until `K` captures it.

## Friction And Cost

`F` includes:

- tokens;
- latency;
- packet count and size;
- invalid packet rate;
- communication loss;
- premature convergence;
- repeated correlated work.

Cost is reported as a Pareto coordinate:

```text
(G_org_bits, harm, correct retention, tokens, latency)
```

R2 does not define an arbitrary conversion from tokens to task bits.

A test may be cognitively positive but operationally outside budget. Those are
different statuses:

```text
COGNITIVELY_POSITIVE_OUTSIDE_BUDGET
OPERATIONALLY_ADMISSIBLE
```

## Small-Model Collective Hypotheses

### H-equivalence

A small-model organization can approach a larger model by accumulating task
compression across more rounds:

```text
L_small_group <= L_large + delta_noninferiority
```

Expected signature:

- similar final task compression;
- more rounds and tokens;
- positive early marginal gains followed by saturation.

### H-surplus

The organization exceeds a matched-budget serial small-model trajectory:

```text
G_org_bits > 0
```

Expected signature:

- `J_set > 0` beyond the serial control;
- positive `K_info`;
- positive correction surplus;
- correct retention does not collapse.

H-equivalence may hold while H-surplus fails.

## Rival Models

| Rival | Frozen signature |
| --- | --- |
| compute-depth equivalence | matched-budget serial control removes group gain |
| representation-only | best role explains the result and all `J_i^uniq` except one are zero |
| random diversity | disagreement rises but `J_set` remains zero |
| suppression-only | harm falls while correct retention and task bits collapse |
| diversity without composition | `J_set` or packet ceiling is positive but `K_info` is low |
| leakage | apparent `K_info > 1` or gain vanishes when extra information channels are closed |
| cognitive organization | positive `J_set`, positive capture, positive out-of-sample `G_org_bits` |

## Discriminating Predictions

1. `J_set = 0` implies no stable positive packet-only coordination gain.
2. Under fixed `J` and `H`, gain changes sign at
   `k_star = H / (J + H)`.
3. Under fixed `k` and `H`, gain is monotone nondecreasing in `J`.
4. Under fixed `J` and `H`, gain is monotone nondecreasing in `k`.
5. Higher raw disagreement without higher `J_set` cannot improve the packet
   ceiling.
6. Suppression can lower harmful actions while leaving `G_org_bits` negative.
7. Additional rounds become anti-additive after marginal `g_t` turns
   nonpositive.

## R3 Minimal Synthetic Validation

R3 validates the measurement and phase model, not real-world collective
cognition.

### Fixed objects

- one explicit finite candidate space;
- three blind role channels;
- one packet-only coordinator;
- one exact private reference;
- no domain semantics;
- no Provider calls;
- no Runtime or retention writes.

### Generative controls

- shared versus private signal noise controls `E_dep`;
- packet likelihood ratios determine measurable `J_set`;
- a faithful-versus-corrupt composition mixture controls `k`;
- the corruption channel fixes `H`;
- rounds expose diminishing `J_t`.

### Required arms

1. best single packet;
2. matched-budget serial packet control;
3. uncoordinated packet set;
4. packet-only coordinator;
5. suppression-only coordinator;
6. held-out joint-packet decoder ceiling;
7. descriptive hindsight oracle, never used for action.

### Required exact gates

Because R3 is a finite synthetic system, use exact enumeration where possible.

1. computed log-loss quantities match analytic values within `1e-9`;
2. `J_set = 0` produces no positive coordinated gain;
3. gain is negative below and positive above the analytic `k_star`;
4. monotonic predictions in `J` and `k` hold in every fixed-control slice;
5. round gains sum to the reported `G_T` within `1e-9`;
6. suppression-only cannot pass both task-bit and correct-retention gates;
7. no extra variable or domain exception is added after observing results.

### Failure interpretation

- metric mismatch: `CONSTRUCTION_OR_IMPLEMENTATION_FAILURE`;
- phase sign mismatch with valid construction: `THEORY_FAILURE`;
- leaked channel: `IDENTIFIABILITY_FAILURE`;
- unstable exact decoder: `PROXY_FAILURE`;
- added exceptions: `ANTI_ADDITIVE_FAILURE`.

R3 must not reinterpret a failed exact gate as benchmark noise.

## R4 And R5 Boundaries

R4 asks whether actual Providers can instantiate:

- blind commensurate packets;
- stable positive `J_i^uniq`;
- bounded disagreement;
- calibrated probabilities;
- packet-only coordination without leakage.

R5 separately tests:

1. small-group cognitive equivalence to a larger model;
2. organizational surplus over matched-budget serial small-model iteration;
3. transfer to fresh tasks and changed Providers.

No R3 result authorizes either R5 claim.

## Anti-Additive Audit

The revised model removes, rather than adds, ambiguity:

- historical `U_role` is renamed `J^uniq`;
- proper-score bits are explicitly a task proxy;
- coordinator synergy is bounded by packet information;
- equivalence and surplus are separated;
- cost is not hidden inside an unfrozen scalar.

The causal model uses:

```text
J, E_dep, K, F, T
```

Representation adequacy, harm, retention, and calibration are prerequisites or
readbacks. They are not new causal modules.

## Falsification And Rollback

Return to theory if:

- exact R3 quantities cannot recover their generating values;
- positive gain appears at `J_set = 0`;
- the predicted `k_star` boundary is absent;
- matched controls cannot be defined without unequal information access;
- a safety gain depends on broad correct-action suppression;
- a new exception is needed for each failed cell.

Rollback target:

`R2_THEORY_ONLY_NO_ENGINEERING_AUTHORITY`

## HumanGate Freeze Checklist

HumanGate must explicitly approve:

- `J` replacing the historical role-information symbol `U`;
- task log-loss reduction as `Cbit_task_proxy`, not ontological Cbit;
- the strongest matched-control definition;
- the packet-only coordinator boundary;
- the `K_info` and `K_preserve` readbacks;
- the analytic phase model and `k_star`;
- exact R3 gates and failure classifications;
- separate H-equivalence and H-surplus claims;
- no Provider, Runtime, or retention authority in R3.

Until explicit approval:

`R2_READY_FOR_REVIEW_NOT_FROZEN`
