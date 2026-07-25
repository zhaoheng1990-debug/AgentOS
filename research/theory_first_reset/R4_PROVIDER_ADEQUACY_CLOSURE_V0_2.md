# R4 Provider Adequacy Closure v0.2

## Status

`FAIL_COORDINATOR_MECHANICAL_VALIDITY`

Sub-result:

`ROLE_NUMERIC_PACKET_LAYER_SUPPORTED_IN_PAIRED_DIAGNOSTIC`

Evidence coordinate:

`LIVE_PROVIDER_PAIRED_PROTOCOL_DIAGNOSTIC_EARLY_STOP`

R4 v0.2 removed Provider-generated direction and derived direction locally.
Six role calls completed successfully. The run stopped when the first pair
coordinator call exhausted its two attempts.

The overall experiment failed. The role-layer sub-result is separately
reportable because all six preregistered role calls completed before the stop.
Full coordination, `K_info`, Shapley ordering, and action readbacks remain
unscorable.

## Frozen Coordinate

- theory: `R4_MINIMAL_SUFFICIENT_RECEIPT_THEORY_V0_2.md`;
- authorization:
  `R4_PROVIDER_PROTOCOL_DIAGNOSTIC_AUTHORIZATION_V0_2.json`;
- preregistration:
  `R4_PROVIDER_ADEQUACY_PREREGISTRATION_V0_2.md`;
- preregistration commit: `dfeaad6`;
- implementation commit: `a31693c`;
- Provider: DeepSeek `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- direction: derived by Runtime;
- fresh holdout consumption: 0;
- Runtime/CoreSlim, retention, and baseline writes: 0.

## Execution And Cost

| Quantity | Result |
| --- | ---: |
| planned logical calls | 11 |
| valid logical calls | 6 |
| physical attempts | 8 |
| prompt tokens | 9821 |
| completion tokens | 8913 |
| total tokens | 18734 |
| cache-hit tokens | 2560 |

All six role calls passed on their first attempt and consumed 11396 total
tokens, approximately 1899 tokens per complete role call.

The two failed pair-coordinator attempts consumed 7338 total tokens. The second
attempt reused 2560 cached prompt tokens but did not recover the contract or the
numeric composition.

## Gate Readback

Of the 15 frozen gates:

- 7 passed;
- 2 failed;
- 6 were not scorable.

Passed:

1. total token budget;
2. role mechanical validity;
3. mean role probability error;
4. maximum role probability error;
5. replicate direction agreement;
6. replicate probability MAE;
7. no forbidden project write.

Failed:

1. 11/11 logical calls within the attempt budget;
2. coordinator mechanical validity.

Not scorable:

1. full coordinator mean probability error;
2. full coordinator MAP direction agreement;
3. full coordinator strong wrong-direction count;
4. `K_info`;
5. Provider Shapley role ordering;
6. accepted coordinator leakage attestation.

The raw unaccepted arrays contained false raw/private-reference attestations,
but an invalid root cannot pass the accepted coordinator gate.

## Role-Layer Results

The six valid role calls produced 72 probability estimates.

| Metric | Result | Frozen gate |
| --- | ---: | ---: |
| mechanical coverage | 100% | 100% |
| mean absolute probability error | 0.0000383 | <= 0.02 |
| median absolute error | 0.000000171 | descriptive |
| maximum absolute error | 0.000971 | <= 0.08 |
| replicate probability MAE | 0.0000578 | <= 0.03 |
| replicate direction agreement | 100% | 100% |
| exact direction agreement | 100% | descriptive |

By role:

| Role | Mean error | Maximum error |
| --- | ---: | ---: |
| ROLE_A | 0.000000175 | 0.000000492 |
| ROLE_B | 0.0000653 | 0.000971 |
| ROLE_C | 0.0000494 | 0.000655 |

The largest order-sensitive deviation occurred in `R4-03 / ROLE_B`:

```text
exact       0.265121538
replicate A 0.265306
replicate B 0.264151
```

The two outputs differed by 0.001155 but preserved the correct direction and
remained far inside the frozen error bounds.

### Role-layer phenomenon

Removing the duplicate direction field moved the system from zero valid role
calls in v0.1 to six of six valid role calls in v0.2.

This supports the bounded mechanism:

```text
redundant deterministic output
  -> avoidable receipt rejection

minimal Provider estimate + Runtime projection
  -> stable canonical packet
```

It does not show semantic evidence judgment. The Provider received explicit
priors and likelihood ratios and performed finite arithmetic.

## Coordinator Failure

Both pair-coordinator attempts returned a top-level JSON array instead of:

```json
{"receipts": []}
```

Therefore both failed the frozen root contract.

The preserved raw arrays permit a non-authoritative diagnostic:

| Metric | Attempt 1 | Attempt 2 |
| --- | ---: | ---: |
| mean probability error | 0.111776 | 0.111776 |
| maximum probability error | 0.300000 | 0.300000 |
| direction agreement | 41.7% | 25.0% |
| outputs exactly at 0.5 | 6/12 | 10/12 |
| outputs copying the prior | 6/12 | 2/12 |

Between attempts:

```text
probability MAE = 0.05
exactly equal cases = 8/12
```

The equal mean error across attempts is produced by the symmetric case design.
It must not be interpreted as stability: the case-level distributions and
direction agreement differ substantially.

### Case phenomena

For `R4-05`, exact ROLE_A + ROLE_B composition is 0.8. Both attempts returned
0.5.

For `R4-06`, exact composition is 0.2. Both attempts returned 0.5.

Attempt 1 often copied the prior rather than composing packets:

- `R4-03`: prior 0.35, exact 0.59068, output 0.35;
- `R4-04`: prior 0.65, exact 0.41053, output 0.65;
- `R4-08`: prior and exact are both 0.35;
- `R4-09`: prior and exact are both 0.65.

Attempt 2 showed stronger uncertainty collapse, returning 0.5 in ten cases.

This is not a wrapper-only failure. Normalizing the array into a root object
would leave mean error far above the frozen 0.03 coordinator threshold and
direction agreement far below 100%.

## Post-Hoc Deterministic Composition

The six accepted role packets were composed locally with the exact frozen
log-odds formula. This used zero additional Provider calls and has no promotion
authority.

| Packet subset | Mean error | Maximum error |
| --- | ---: | ---: |
| ROLE_A + ROLE_B | 0.0000458 | 0.000317 |
| ROLE_A + ROLE_C | 0.0000243 | 0.000183 |
| ROLE_B + ROLE_C | 0.0000651 | 0.000447 |
| ROLE_A + ROLE_B + ROLE_C | 0.0000721 | 0.000424 |

The small residual errors are inherited from rounded Provider role
probabilities.

Bounded conclusion:

`ROLE_PACKETS_CONTAINED_SUFFICIENT_NUMERIC_INFORMATION`

The large Provider coordinator loss did not arise because role information was
missing. It arose during the Provider's attempted deterministic recomposition.

## Mechanism Analysis

### Leading interpretation: responsibility-layer mismatch

The coordinator prompt supplied a complete deterministic formula. Requiring a
Provider to recompute that formula violates the minimal-sufficient-receipt
principle for the same reason that generated direction did:

```text
known deterministic operation
  -> Provider generation
  -> added format, arithmetic, and collapse channels
  -> no new semantic information
```

The correct split is:

```text
Provider:
  judge non-mechanical relations such as dependence, conflict,
  applicability, evidence scope, and missing assumptions

Runtime:
  compose accepted numeric packets under the selected relation model
```

### Rival 1: long-batch instruction degradation

The coordinator prompt was substantially longer than a role prompt and
contained two packets per case. The failure may be caused by batch complexity
rather than coordinator role identity.

Discriminator: hold the semantic relation task fixed while varying batch size,
without asking the Provider to perform deterministic composition.

### Rival 2: shared-prior correction was not understood

The model may have treated opposite packet movements as cancellation, copied the
prior, or abstained at 0.5 instead of removing the duplicated prior in log-odds
space.

Discriminator: inspect relation receipts rather than final probabilities, then
let a deterministic compiler perform shared-prior removal.

### Rival 3: general coordination weakness

The Provider may be adequate for isolated local updates but weak at integrating
multiple packet objects.

Discriminator: test a non-arithmetic relation-classification coordinator on new
synthetic structures. A failure there would support a broader coordination
limit.

## Theory Writeback

The minimal sufficient receipt theory is extended with a two-stage coordinator:

```text
SemanticRelationCoordinator
  -> relation receipt R

DeterministicPacketComposer
  -> compose packets under R
```

The Provider-backed layer is needed for `R` when dependence, contradiction,
scope, or relevance cannot be mechanically known. The Runtime retains final
authority and computes all deterministic consequences of `R`.

This preserves the user's architecture requirement:

- Runtime is the cognitive subject;
- Provider strengthens Runtime cognition;
- Provider is not reduced to report generation;
- Provider is not granted state or decision authority;
- local code does not pretend to make semantic judgments;
- local code does own exact consequences once semantic premises are accepted.

## Negative Results Preserved

1. R4 v0.2 did not establish coordinator adequacy.
2. It did not produce a full organizational result.
3. It did not score `K_info` or role Shapley ordering.
4. It did not test natural-language evidence semantics.
5. It did not test independent Providers or models.
6. It did not consume a fresh holdout.
7. The post-hoc local composition cannot convert the preregistered failure into
   a pass.

## Artifact Inventory

Local ignored artifacts:

```text
outputs/r4_provider_adequacy_v0_2/
```

Key hashes:

```text
attempt_ledger_checkpoint.json
  653fb087842271b988695865f9759f6be29d34b70e4b14080045a31d5a82c4ba
partial_analysis.json
  0769a9119356536168496f9782fbbac1b3c4661dd469052d2f9bbfc43a8a9bc4
hash_inventory.json
  38ac23ed29aa7d3e97d5c3307c96427af1dbda8411641fc231028f3e22e7512d
```

## Next Research Object

Before another Provider call, theory should define:

`SEMANTIC_RELATION_RECEIPT_AND_DETERMINISTIC_COMPOSITION_BOUNDARY`

It must specify:

- which relation judgments are genuinely semantic;
- how relation uncertainty is represented;
- how conflicts and dependence change composition;
- which fields the Runtime can derive mechanically;
- how a wrong relation receipt is falsified;
- a fresh synthetic relation set not reused from R4 v0.1-v0.2;
- an oracle-relation control and a wrong-relation control;
- matched token and information boundaries.

Provider calls remain paused until that theory packet and a new preregistration
are reviewed.
