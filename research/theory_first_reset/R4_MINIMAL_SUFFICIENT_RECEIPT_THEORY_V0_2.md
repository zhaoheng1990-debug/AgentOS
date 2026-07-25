# R4 Minimal Sufficient Receipt Theory v0.2

## Status

`FROZEN_FOR_BOUNDED_PROTOCOL_DIAGNOSTIC`

This packet is a theory writeback from the immutable R4 v0.1 negative result.
It changes the Provider-to-Runtime receipt boundary. It does not change the R2
organization theory, R3 phase model, task probabilities, scoring functions, or
semantic performance thresholds.

## Ontology Object

`MINIMAL_SUFFICIENT_COGNITIVE_RECEIPT`

A Provider-backed cognitive receipt is minimal and sufficient when it contains:

1. the irreducible semantic estimate requested from the Provider;
2. identity and evidence-binding fields needed to locate that estimate;
3. non-derivable boundary attestations needed for governance;
4. no generated field that is a deterministic function of another accepted
   field.

For R4:

```text
irreducible estimate: probability_y1
deterministic projection: direction(probability_y1)
binding: case_id, role_id, evidence_id
boundary attestation: calculation_basis, assumptions
```

## Runtime-Provider Division

The Runtime remains the cognitive subject. It defines the object, prior,
evidence boundary, update rule, receipt contract, conflict policy, and candidate
state. The Provider supports the Runtime by estimating a semantic or
probabilistic quantity that the Runtime cannot obtain through schema validation
alone.

The division is:

```text
Provider:
  estimate z

Runtime:
  validate the admissible domain of z
  derive deterministic projections f(z)
  bind z to evidence and scope
  record provenance and conflicts
  decide candidate state
```

The Runtime must not outsource `f(z)` when `f` is deterministic and locally
replayable.

## Leading Causal Model

Let:

```text
z = irreducible Provider estimate
f(z) = deterministic Runtime projection
r = Provider-generated duplicate of f(z)
```

The additive receipt requires both `z` and `r`. It accepts only when:

```text
r = f(z)
```

The duplicate adds no task information:

```text
I(Y; z, r) = I(Y; z)
```

when `r` is intended to equal `f(z)`.

It does add a rejection path:

```text
P(reject | useful z) >= P(r != f(z))
```

The minimal receipt accepts `z`, derives `f(z)` locally, and removes that
failure channel without relaxing the domain, identity, evidence, or leakage
boundaries.

## Rival Models

### R0: arithmetic inadequacy

The Provider cannot reliably compute the posterior probability. Removing
`direction` will not make probability error or coordinator composition pass.

### R1: general instruction failure

The Provider does not follow even the reduced JSON and binding contract.
Mechanical validity will still fail before semantic scoring.

### R2: boundary-only representation failure

The Provider computes useful probabilities but inconsistently labels exact
neutral cases. Removing the duplicate categorical output restores mechanical
coverage and leaves probability calibration intact.

### R3: broader redundant-surface problem

Other copied fields such as basis or assumptions become the next failure
surface. Direction removal alone will move, rather than close, the bottleneck.

## Discriminating Predictions

Holding cases, model, thinking mode, temperature, arithmetic instructions, call
budget, scoring, and thresholds fixed:

1. R2 predicts 100% minimal receipt coverage and low probability error.
2. R0 predicts valid packets may increase, but numeric calibration still fails.
3. R1 predicts early mechanical failure on required minimal fields.
4. R3 predicts failure migrates to another non-probability field.

The diagnostic is paired and intervention-specific. It is not a fresh
generalization test.

## Canonicalization Rule

The v0.2 Runtime derives:

```text
UNRESOLVED if abs(probability_y1 - 0.5) <= 1e-6
Y1         if probability_y1 > 0.5
Y0         otherwise
```

If the Provider supplies extra fields:

- required fields are validated normally;
- extra fields are recorded;
- extra fields are excluded from canonical state;
- an extra `direction` cannot veto an otherwise valid probability;
- no extra field receives decision or promotion authority.

This is canonicalization, not silent trust.

## Falsification Conditions

The minimal-receipt hypothesis is falsified for this instrument if:

- the same first role call still cannot produce complete valid probabilities;
- mean or maximum role probability error fails the frozen bounds;
- coordinator numeric composition remains invalid;
- the failure migrates to required identity or boundary binding fields;
- the experiment cannot be scored without another semantic repair.

## Proxy Limits

Passing v0.2 would establish only that one Provider can instantiate this finite
numeric packet protocol under context isolation.

It would not establish:

- independent models or independent learned priors;
- natural-language evidence judgment;
- real multi-agent complementarity;
- fresh benchmark generalization;
- organizational surplus over a matched single model;
- Runtime, retention, or baseline promotion readiness.

## Anti-Additive Audit

Removed:

- Provider-generated deterministic direction.

Preserved:

- one probability per case;
- evidence identity;
- scope and basis attestations;
- packet-only coordinator;
- exact private scoring;
- all cost, stability, leakage, and action readbacks.

No new Runtime module is authorized. The implementation remains a standalone
experiment instrument.

## Stop And Rollback

Stop v0.2 immediately when:

- one logical call exhausts two attempts;
- the token ceiling is crossed;
- raw evidence or private reference leakage is observed;
- a frozen semantic threshold would need revision;
- any project write outside ignored experiment outputs is attempted.

Do not repair v0.2 after a Provider response. Close and version again.
