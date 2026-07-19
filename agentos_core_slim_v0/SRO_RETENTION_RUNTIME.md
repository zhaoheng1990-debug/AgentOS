# AgentOS SRO-conditioned Retention Runtime v0.2

Status: `INTEGRATED_PROJECT_SCOPED_RUNTIME__NO_PRODUCTION_ACTIVATION`

## Purpose

This runtime turns bounded retention/SFI research through the latest closed
v1.8 result into an end-to-end AgentOS capability. It does not make AgentOS the
research object, deploy the synthetic v1.8 matcher weights, or promote the
planned and unexecuted v1.9 minimality hypothesis.

The runtime separates three decisions:

```text
candidate formation / durable retention eligibility
  -> ConstraintAlignedRetentionGate

stored witness + current task
  -> SRORetentionRuntime
  -> ProviderTaskRouter + ProviderBackedRuntimeCognitionLayer
  -> strongly bound matcher receipt
  -> GradedSROCompatibilityGate (Kernel-owned route)
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

Every v0.2 witness also carries a concrete `project_scope_ref`. A generic
`project_scoped` label cannot move a witness between projects.

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

## Runtime orchestration and strong binding

`agentos_runtime.SRORetentionRuntime` accepts only registered witnesses and
frozen `SRORetentionTask` / `SROCalibrationContract` objects. It builds the
Provider task itself, admits exactly the declared semantic output fields, runs
the Provider cognition audit, and then binds:

- witness ID, record hash and concrete project URI;
- target task ID and commitment hash;
- frozen matcher/calibration identity and evidence scope;
- actual Provider invocation receipt hash and output hash;
- cognition audit hash and cited evidence refs.

The Provider cannot return identity, scope, authority or route-state fields.
Unknown fields, unknown evidence, missing provenance, failed schema, receipt
hash mismatch, or project mismatch block before a route receipt is formed.

## Persistent delayed retrieval and replay

The delayed ledger is an append-only JSONL hash chain. Each write verifies the
on-disk head, appends and `fsync`s the event. Restart reconstructs predictions
and scores only after sequence, previous-hash, event-hash and payload-hash
checks pass. A stale second writer is blocked instead of silently forking the
chain. Runtime events and snapshots form a separate public replay chain.

## Legacy migration lifecycle

Migration never turns an old record directly into reusable memory:

```text
legacy constraint-aligned record
  -> PENDING_WITNESS_RECONSTRUCTION

legacy ACCEPT-label record without current metrics
  -> PENDING_PROVIDER_REVALIDATION
  -> PENDING_WITNESS_RECONSTRUCTION or QUARANTINED_LEGACY_RECORD

explicit Kernel-authorized reconstruction
  -> WITNESS_REGISTERED_PROJECT_SCOPED
```

Candidate identity, legacy source hash and original evidence must survive
revalidation. Reconstruction requires explicit SRO, validity, reconstruction,
authority and privacy references. No migration state grants route authority.

## Compatibility

- The existing `ConstraintAlignedRetentionGate` API is unchanged.
- Existing project-scoped durable stores remain readable and unchanged.
- Migration is explicit and candidate-only; no existing record is automatically promoted.
- Existing candidates need an explicit `SerialSelectionWitness` reconstruction
  and a new matcher receipt before query-time routing.
- The integrated runtime enters CoreSlim `0.4.0-alpha.10`.

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

## Verification

From `agentos_core_slim_v0`:

```powershell
python -m pytest -q tests/test_sro_retention_runtime.py tests/test_sro_retention_orchestrator.py tests/test_sro_retention_runtime_smoke.py
python examples/sro_retention_runtime_smoke.py --output-dir ../outputs/sro_retention_runtime_alpha10_smoke
python -m compileall -q agentos_kernel agentos_runtime tests examples
```
