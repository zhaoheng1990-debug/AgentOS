# AgentOS SRO-conditioned Retention Runtime v0.1

Status: `PROJECT_SCOPED_KERNEL_PATCH__NO_PRODUCTION_ACTIVATION`

## Purpose

This patch turns the bounded retention/SFI research results into AgentOS
infrastructure contracts. It does not make AgentOS the research object and it
does not deploy the synthetic v1.8 matcher weights.

The runtime separates three decisions:

```text
candidate formation / durable retention eligibility
  -> ConstraintAlignedRetentionGate

stored witness + current task
  -> GradedSROCompatibilityGate
  -> DIRECT_REUSE / LOCAL_RECONSTRUCTION / OBSERVE /
     REJECT / REVISE / ABSTAIN

predicted route + later outcome
  -> DelayedRetrievalLedger
  -> role fidelity - negative-transfer penalty
```

## Theory-to-engineering correspondence

```text
UpperOntologyObject
  TemporalSRO + RankedCompatibilityFiber + MemoryUnit address/guidance

ProjectObject
  SerialSelectionWitness + GradedSROCompatibilityGate
  + DelayedRetrievalLedger

ObservableProxy
  frozen provider/matcher receipt with route probabilities,
  compatibility, uncertainty, drift, validity and evidence scope

Metric
  route, confidence, uncertainty, drift risk, delayed retrieval score,
  negative-transfer penalty and hash-chain integrity
```

Correspondence is not ontological identity. A passing matcher receipt is a
project-scoped runtime input, not proof of a universal memory mechanism.

## Public kernel objects

### `SerialSelectionWitness`

Reference-only representation of:

```text
W_i = <C_i^sel, Delta_i, B_i^valid, A_i^SRO,
       R_i^recon, Authority_i, Privacy_i>
```

The schema stores immutable artifact addresses, hashes and evidence refs. It
does not store raw chat. Its lifecycle is append-only by replacement:

```text
PRECOMMITTED
  -> IMMEDIATE_DELTA_OBSERVED
  -> DELAYED_VALUE_OBSERVED
```

A precommit cannot contain future outcome refs.

### `GradedSROCompatibilityGate`

The Provider/model supplies bounded semantic estimates. AgentOSKernel validates:

- exact five-class probability schema and probability sum;
- frozen calibration and evidence scope;
- replayable evidence and provider-support receipt refs;
- structural, role, boundary and interface compatibility;
- trace sufficiency, uncertainty, drift, validity and negative-transfer risk.

The Kernel owns the final route. Safety invariants include:

- missing/invalid matcher contracts -> `ABSTAIN`;
- insufficient task trace or unknown validity -> `OBSERVE`;
- structural-role/boundary mismatch or high negative-transfer risk -> `REJECT`;
- stale/drifted validity -> `REVISE`;
- insufficiently calibrated commitment -> `ABSTAIN`;
- compatible family with interface/drift adaptation -> `LOCAL_RECONSTRUCTION`;
- direct reuse only under project/internal or external evidence with low drift;
- synthetic/formal evidence cannot authorize `DIRECT_REUSE` and is downgraded to `LOCAL_RECONSTRUCTION`.

`OBSERVE` is environment-facing evidence acquisition. `ABSTAIN` is
matcher-facing refusal to commit.

### `DelayedRetrievalLedger`

The ledger seals a route prediction before later-task reveal, then records one
immutable outcome and computes:

```text
DR_score = role_reconstruction_fidelity - negative_transfer_penalty
```

Predictions and outcomes form a deterministic hash chain. Duplicate outcomes,
outcomes without a prediction, and reveals at or before the prediction seal are
rejected.

## Provider contract

`provider_backed_runtime_cognition_layer_v0_7` adds:

```text
graded_sro_retention_candidate_routing
```

Provider cognition estimates semantic compatibility and calibrated route
probabilities. It has no final route, durable-write, production-activation or
theory-promotion authority.

## Compatibility

- The existing `ConstraintAlignedRetentionGate` API is unchanged.
- Existing project-scoped durable stores are unchanged.
- No migration of existing retention candidates is automatic.
- Existing candidates need an explicit `SerialSelectionWitness` reconstruction
  and a new matcher receipt before query-time routing.
- No release version bump is included; the active AgentOS release owner decides
  when this candidate patch enters a release.

## Evidence boundary

May claim:

- AgentOS can represent a privacy-minimal serial witness;
- AgentOS can fail closed on uncalibrated or incomplete SRO receipts;
- AgentOS can distinguish direct reuse, local reconstruction, observation,
  rejection, revision and abstention;
- AgentOS can audit pre-outcome delayed retrieval predictions.

Must not claim:

- the v1.8 synthetic matcher is production-valid;
- universal/natural SRO accuracy;
- mature memory value or minimality;
- online family-language invention, split or retirement;
- autonomous global-memory or theory-baseline write authority.
