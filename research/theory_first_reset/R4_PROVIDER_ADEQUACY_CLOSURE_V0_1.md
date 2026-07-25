# R4 Provider Adequacy Closure v0.1

## Status

`FAIL_MECHANICAL_RECEIPT_VALIDITY`

Evidence coordinate:

`LIVE_PROVIDER_CALIBRATION_EARLY_STOP`

The preregistered experiment stopped after the first logical role call exhausted
its two allowed physical attempts. No same-version prompt, schema, threshold, or
receipt repair was applied.

This result does not estimate Provider probability calibration, packet
composition fidelity, organizational information capture, or role
complementarity. Those outcomes are unscorable because no logical call passed
the frozen mechanical receipt contract.

## Frozen Coordinate

- authorization: `R4_PROVIDER_AUTHORIZATION_RECEIPT.json`;
- preregistration: `R4_PROVIDER_ADEQUACY_PREREGISTRATION_V0_1.md`;
- preregistration commit: `294d96e`;
- Provider: DeepSeek `deepseek-v4-flash`;
- thinking mode: disabled;
- response format: JSON object;
- temperature: 0;
- first logical call: `role_ROLE_A_A`;
- allowed attempts per logical call: 2;
- fresh holdout consumption: 0;
- Runtime/CoreSlim imports or writes: 0;
- retention or baseline writes: 0.

## Observed Facts

| Observation | Value |
| --- | ---: |
| planned logical calls | 11 |
| valid logical calls | 0 |
| physical attempts | 2 |
| prompt tokens | 1622 |
| completion tokens | 2434 |
| total tokens | 4056 |
| cache-hit tokens | 768 |
| failing case | `R4-05` |
| validator error | `direction mismatch for R4-05` |

Both attempts used the same frozen prompt:

```text
af72e0f3373fee429d7d04a87774b860d66136d8000e8fec545d04c5af5096d5
```

The attempt ledger is preserved locally:

```text
outputs/r4_provider_adequacy_v0_1/attempt_ledger_checkpoint.json
sha256:
ed85ddb96e1b0197f8b97ccc1bc49c704dbf6a9fa0d830a784c639dfd536a502
```

The second call reused 768 cached prompt tokens but reproduced the same
validation coordinate. This is repeatable deterministic contract failure under
the frozen setting, not a transient transport error.

## Case-Level Phenomenon

For `ROLE_A` in `R4-05`, the visible inputs were:

```text
prior P(Y1) = 0.20
assigned likelihood ratio = 4.00
```

The exact update is:

```text
prior odds = 0.20 / 0.80 = 0.25
posterior odds = 0.25 * 4.00 = 1
posterior P(Y1) = 0.50
```

The frozen protocol therefore required:

```text
probability_y1 = 0.5
direction = UNRESOLVED
```

The parser successfully reached the direction-consistency check, which means
the response was valid JSON, contained the expected case and identity fields,
and supplied a numeric probability strictly between zero and one. It rejected
the packet because the emitted direction was not the deterministic projection
required by the emitted probability.

The invalid raw response body was not persisted. The exact emitted probability
and direction pair cannot be reconstructed and must remain
`INSUFFICIENT_TRACE`. The report therefore does not claim which of the two
fields was wrong.

## Mechanism Interpretation

### Leading interpretation: redundant receipt surface

`direction` contains no information not already present in `probability_y1`.
Requiring the Provider to emit both creates two lexical surfaces for one
cognitive quantity. The Provider can produce a numerically usable probability
while failing the duplicated categorical projection.

This is an anti-additive protocol violation:

```text
Provider semantic output
  + redundant Provider mechanical output
  -> new inconsistency channel without new Cbit
```

The minimal sufficient division of labor is:

```text
Provider: probability judgment
Runtime: deterministic direction projection
```

### Rival 1: Provider arithmetic failure

The Provider may have emitted a probability away from 0.5 and a direction that
did not match even that emitted value. This remains possible because the raw
invalid body was not retained.

Discriminator: retain invalid response bodies in the next version and score the
probability independently of the redundant field.

### Rival 2: boundary convention failure

The Provider may have computed exactly 0.5 but mapped equality to `Y1` or `Y0`
despite the explicit `UNRESOLVED` instruction. This would indicate that
categorical boundary conventions are less stable than numeric calculation.

Discriminator: remove the generated direction field and derive it locally.

### Rival 3: prompt comprehension failure

The model may have ignored the explicit neutral rule. The two identical failures
at temperature zero are compatible with a stable instruction-following error.

Discriminator: use a new diagnostic protocol that changes only receipt
minimality while preserving cases, model, arithmetic task, and thresholds.

## Negative Result

R4 v0.1 fails its first and third preregistered gates:

1. 11 logical calls did not complete within the attempt budget;
2. role receipt mechanical validity was not 100%.

All semantic adequacy gates are `NOT_SCORABLE`, not failed measurements:

- role probability error;
- replicate stability;
- coordinator probability error;
- direction agreement;
- strong wrong-direction count;
- `K_info`;
- Shapley role ordering.

No evidence supports or rejects same-Provider context-isolation adequacy.

## Theory Writeback

Add a minimal-sufficient-receipt constraint:

```text
For a semantic variable z and deterministic projection f(z),
the Provider-backed receipt SHOULD request z only.
The Runtime MUST derive f(z) locally unless f adds an independently
meaningful judgment.
```

Consequences:

1. Provider support is not reduced to mechanical work.
2. Runtime remains the cognitive subject and owns canonical state.
3. Provider supplies irreducible semantic estimates.
4. Deterministic projections remain replayable and exact.
5. Redundant fields cannot veto useful cognition without adding information.

This revision narrows the Provider contract. It does not revise the R2
organization theory or the R3 phase model.

## Instrument Limitation

The attempt ledger preserved hashes, errors, and token usage, including tokens
consumed by invalid schema responses. It did not preserve the invalid raw
response body. That omission prevents a stronger case-level diagnosis.

The next version must persist invalid response content locally before
validation, with no promotion authority.

## Next Research Object

`R4_v0_2_MINIMAL_SUFFICIENT_RECEIPT_DIAGNOSTIC`

It may:

- reuse the 12 synthetic calibration cases only as a paired protocol diagnostic;
- remove Provider-generated `direction`;
- derive direction locally from probability;
- preserve invalid raw contents;
- retain all probability, stability, composition, leakage, and budget gates.

It may not:

- call the reused cases a fresh confirmation;
- change probability thresholds after observing outputs;
- consume a fresh holdout;
- write Runtime, CoreSlim, retention, or baseline state;
- promote Provider output to decision authority.
