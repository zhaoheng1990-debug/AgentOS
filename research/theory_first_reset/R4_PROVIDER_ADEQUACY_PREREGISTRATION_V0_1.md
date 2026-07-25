# R4 Provider Adequacy Preregistration v0.1

## Status

`FROZEN_BEFORE_PROVIDER_CALLS`

Authorization:

`R4_PROVIDER_AUTHORIZATION_RECEIPT.json`

Inherited theory:

- R2 v0.2 HumanGate freeze;
- R3 synthetic-formal closure;
- `Cbit_task_proxy` is not ontological Cbit;
- positive task compression is not sufficient for action admissibility.

## Objective

Test whether one real Provider, under stateless context-isolated calls, can
instantiate the minimum observable objects required by the frozen organization
theory:

1. schema-valid commensurate role packets;
2. calibrated subset probabilities;
3. stable outputs under order and wording variation;
4. positive realized conditional packet information;
5. packet-only coordination without raw-evidence or reference leakage;
6. bounded `K_info`, direction error, abstention, and token cost.

This experiment does not test:

- independent Providers;
- independent model priors;
- general natural-language research ability;
- small-model versus large-model equivalence;
- production AgentOS cognition.

Claim ceiling:

`SAME_PROVIDER_CONTEXT_ISOLATION_ADEQUACY_ONLY`

## Provider Contract

```text
provider: DeepSeek
model: deepseek-v4-flash
endpoint: https://api.deepseek.com/chat/completions
thinking: disabled
response_format: json_object
temperature: 0
```

The model name and request shape follow the current official DeepSeek API.

Logical call budget:

```text
role batches:
  3 roles * 2 counterbalanced replicates = 6
packet-only coordinator:
  3 pair subsets + 2 full-packet replicates = 5
total logical calls = 11
```

Each logical call permits at most two physical attempts for transport, empty
content, or invalid JSON recovery.

Hard ceilings:

```text
physical attempts <= 22
total tokens <= 200000
```

No same-version prompt or threshold repair is allowed after the first
semantically valid Provider response.

## Finite Evidence Objects

Each case has:

- binary state `Y0` or `Y1`;
- prior probability `p = P(Y1)`;
- three conditionally independent evidence items;
- one likelihood ratio per role:
  `LR_i = P(E_i | Y1) / P(E_i | Y0)`.

For any evidence subset `S`:

```text
posterior_odds(S) = prior_odds * product(LR_i for i in S)
P(Y1 | S) = posterior_odds / (1 + posterior_odds)
```

The Provider never receives the full private answer table.

## Frozen Case Table

| Case | Prior `P(Y1)` | Role A LR | Role B LR | Role C LR |
| --- | ---: | ---: | ---: | ---: |
| R4-01 | 0.50 | 4.00 | 2.50 | 0.40 |
| R4-02 | 0.50 | 0.25 | 0.40 | 2.50 |
| R4-03 | 0.35 | 4.00 | 0.67 | 1.50 |
| R4-04 | 0.65 | 0.25 | 1.50 | 0.67 |
| R4-05 | 0.20 | 4.00 | 4.00 | 0.67 |
| R4-06 | 0.80 | 0.25 | 0.25 | 1.50 |
| R4-07 | 0.50 | 1.50 | 0.67 | 1.00 |
| R4-08 | 0.35 | 2.50 | 0.40 | 1.00 |
| R4-09 | 0.65 | 0.40 | 2.50 | 1.00 |
| R4-10 | 0.50 | 4.00 | 0.25 | 1.00 |
| R4-11 | 0.20 | 2.50 | 2.50 | 0.40 |
| R4-12 | 0.80 | 0.40 | 0.40 | 2.50 |

The table is the complete task population for v0.1. It is not a benchmark
holdout.

## Role Isolation

Role A receives:

- case ID;
- common prior;
- Role A evidence ID and LR;
- the shared output schema.

Role B and Role C receive the corresponding isolated inputs.

No role receives:

- another role's LR or packet;
- full posterior;
- private MAP state;
- prior Provider output;
- calibration score.

Each role returns one JSON object per case:

```json
{
  "case_id": "R4-01",
  "role_id": "ROLE_A",
  "evidence_id": "R4-01-EA",
  "probability_y1": 0.8,
  "direction": "Y1",
  "calculation_basis": "PRIOR_ODDS_TIMES_ASSIGNED_LR",
  "assumptions": [
    "ONLY_ASSIGNED_EVIDENCE",
    "COMMON_PRIOR"
  ]
}
```

Allowed directions:

```text
Y1
Y0
UNRESOLVED
```

`UNRESOLVED` is required only when the reported probability equals 0.5 within
`1e-6`.

## Counterbalanced Stability

Every role is called twice:

### Replicate A

- cases in ascending ID order;
- direct probability wording.

### Replicate B

- cases in descending ID order;
- equivalent odds-update wording;
- no previous response included.

Stability metrics:

- exact case coverage;
- schema validity;
- direction agreement;
- mean and maximum absolute probability difference;
- semantic assumption compliance.

The two calls are separate contexts. This tests context isolation and
repeatability, not independent model cognition.

## Packet-Only Coordinator

The coordinator receives:

- case ID;
- common prior;
- one or more role packets;
- the packet-composition rule.

It does not receive:

- raw likelihood ratios;
- evidence text beyond receipt IDs;
- exact subset or full posterior;
- private MAP state;
- role calibration scores.

For `m` role packets based on the same prior:

```text
combined_log_odds
  = sum(logit(packet_probability_i))
    - (m - 1) * logit(prior)
```

The coordinator returns:

```json
{
  "case_id": "R4-01",
  "included_roles": ["ROLE_A", "ROLE_B"],
  "probability_y1": 0.909091,
  "direction": "Y1",
  "composition_basis": "PACKET_LOG_ODDS_WITH_SHARED_PRIOR_REMOVAL",
  "raw_evidence_used": false,
  "private_reference_used": false
}
```

Coordinator calls:

- pair AB;
- pair AC;
- pair BC;
- full ABC replicate A;
- full ABC replicate B with reversed packet and case order.

## Private Mechanical Reference

Local code computes exact subset and full posteriors from the frozen table.

The private reference contains:

- exact probability for every subset;
- exact full MAP direction;
- exact expected cross-entropy under the full posterior;
- exact Shapley allocation over the three roles.

The reference is never included in a Provider request.

## Metrics

### Receipt quality

- valid JSON;
- exact case count;
- no duplicate or missing IDs;
- required fields and enums;
- probability in `[0,1]`;
- evidence and role identity preserved;
- no forbidden input attestation.

### Role calibration

For each role packet:

```text
absolute probability error
= abs(provider_probability - exact_subset_probability)
```

Report mean, median, maximum, and direction agreement.

### Stability

Compare role replicate A versus B:

- probability MAE;
- maximum drift;
- direction agreement.

### Provider packet information

Let the full exact posterior be the evaluation target.

For a prediction `q`:

```text
CE(q) =
  -p_full * log2(q)
  -(1-p_full) * log2(1-q)
```

The realized Provider packet gain is:

```text
J_provider = CE(prior) - CE(provider_full_coordinator)
```

The exact available gain is:

```text
J_exact = CE(prior) - CE(exact_full_posterior)
```

Across the 12 cases, report their means.

### Coordinator capture

```text
K_info = mean(J_provider) / mean(J_exact)
```

`K_info > 1.05` triggers a leakage, scoring, or hidden-channel audit. It is not
called super-synergy.

### Role-specific realized contribution

Use Provider predictions for:

- empty subset: prior;
- singleton subsets: role packets;
- pair subsets: pair coordinator calls;
- full subset: full coordinator call.

Compute exact three-role Shapley allocation over Provider-arm expected losses.

Compare its role ordering and absolute deviation with the private exact
Shapley allocation.

### Action readbacks

Using the exact full posterior as reference:

- MAP direction agreement;
- strong wrong-direction count at confidence `>=0.70`;
- abstention count for probability within `[0.45,0.55]`;
- correct strong decisions retained from the best singleton packet.

Positive task compression does not override these action gates.

### Cost

- logical and physical calls;
- prompt, completion, cache, and total tokens where returned;
- invalid or empty attempts;
- tokens per valid packet;
- tokens per positive realized task bit, descriptive only.

## Frozen PASS Gates

R4 passes Provider adequacy only if all conditions hold:

1. 11/11 logical calls complete within 22 physical attempts;
2. total tokens do not exceed 200000;
3. role receipt mechanical validity is 100%;
4. coordinator receipt mechanical validity is 100%;
5. mean role probability error is at most 0.02;
6. maximum role probability error is at most 0.08;
7. replicate direction agreement is 100%;
8. replicate probability MAE is at most 0.03;
9. full coordinator mean probability error is at most 0.03;
10. full coordinator MAP direction agreement is 100%;
11. no full coordinator strong wrong direction occurs;
12. `0 < K_info <= 1.05`;
13. Provider Shapley role ordering matches the exact ordering;
14. full packet prompts and receipts attest no raw evidence or private
    reference use;
15. no forbidden project write occurs.

## PARTIAL And FAIL

`PARTIAL`:

- all mechanical and leakage gates pass;
- at least one semantic calibration, stability, or `K_info` gate fails.

`FAIL`:

- missing or invalid packet coverage;
- private-reference or raw-evidence leakage;
- budget exceeded;
- negative realized packet information;
- result cannot be scored without changing a frozen prompt, metric, or
  threshold.

## Stop And Rollback

Stop immediately if:

- the API key is unavailable;
- the selected model is unavailable after two attempts;
- Provider output exposes or requests the private reference;
- any logical call exceeds its attempt limit;
- the global call or token budget is reached;
- scoring requires a same-version semantic repair.

Rollback target:

`R3_COMPLETE_R4_PROVIDER_ADEQUACY_NOT_ESTABLISHED`

## Output Boundary

Source:

`experiments/theory_first_r4/`

Ignored local artifacts:

`outputs/r4_provider_adequacy_v0_1/`

Tracked closure:

`research/theory_first_reset/R4_PROVIDER_ADEQUACY_CLOSURE_V0_1.md`

No result can authorize Runtime, CoreSlim, retention, or baseline changes.
