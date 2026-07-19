# Anti-Additive Methodology Runtime

AgentOS CoreSlim 0.4.0-alpha.17 extends the executable MethodologyKernel Anti-Additive Constraint with
prediction-outcome calibration and one replayable receipt source. A Provider estimate is therefore
treated as bounded cognitive support whose authority depends on observed outcomes, not as a timeless
truth or a replacement for Kernel judgment.

## What Was Missing

Earlier releases contained `anti_additive_signal` in the Contextual Organization Policy Selector. That
signal asks whether roles or coordination inside one organization policy may cancel each other's value.
It is an organization-interaction risk signal.

The methodology constraint asks a different question: after failure, is the system adding variables,
modules, metrics, windows, exceptions, or memory objects to preserve an inadequate research object?
Before alpha.16, this question was present only as prose-level intent. It did not have a dedicated object,
Provider contract, Kernel decision, persistent receipt, replay boundary, or mandatory write consumer.

## Frozen Method

Every proposed complexity-expanding object must satisfy:

```text
expected effective Cbit gain > complexity cost
```

An object lift must additionally satisfy:

```text
object-upgrade gain > abstraction cost
```

The Provider must assess all seven MethodologyKernel triggers:

1. terms increase without reducing excluded error paths;
2. explanations grow without clarifying the main constraint;
3. candidate trajectories multiply without stabilizing a main path;
4. patches preserve an old object without increasing Cbit;
5. the experiment becomes table filling instead of possibility-space compression;
6. new controls protect edge cases while the central failure remains;
7. baseline writeback grows without becoming more decisive.

These are semantic judgments, so AgentOS does not replace them with keywords. The Provider supports the
assessment over a frozen candidate and admitted evidence. The Runtime remains the cognitive subject: it
defines the object levels and trigger set, validates evidence and invocation bindings, compares gains and
costs, owns the final state, persists the receipt, and controls downstream authority.

## Layer Placement

| Layer | Component | Responsibility |
| --- | --- | --- |
| Kernel base contract | `anti_additive_base.py` | candidate, object levels, seven-trigger surface, payload commitments |
| Kernel semantic contract | `anti_additive_judgment.py` | Provider judgment and frozen methodology policy |
| Kernel decision contract | `anti_additive_decision.py` | final state, authority boundary, decision hash, receipt |
| Kernel compatibility facade | `anti_additive_models.py` | stable imports without combining implementation ownership |
| Kernel meta-rule | `anti_additive_gate.py` | Cbit/complexity comparison, object-level comparison, abstraction-fog gate, final state |
| Kernel calibration control | `anti_additive_control.py` | exact-scope trust state and candidate/durable authority mode |
| Kernel calibration contracts | `anti_additive_calibration_observation.py`, `anti_additive_calibration_models.py` | immutable prediction/outcome binding, profile, decision, and receipt |
| Kernel calibration evaluator | `anti_additive_calibration_eval.py` | mechanical error and margin-survival aggregation against frozen thresholds |
| Provider support | `anti_additive_provider.py` | bounded first-principles object and trigger assessment with provenance |
| Runtime persistence | `anti_additive_repository.py` | append-only event chain, snapshot, receipt integrity, restart replay |
| Runtime codec | `anti_additive_codec.py` | pure receipt reconstruction outside persistence ownership |
| Runtime orchestration | `anti_additive_runtime.py` | thin composition of Provider, Kernel, and repository |
| Calibration Runtime | `anti_additive_calibration_runtime.py` | admit executed outcomes and compose observation, evaluator, and ledger |
| Calibration source | `anti_additive_calibration_source.py` | resolve latest replay-valid exact-scope control as trusted, exploration-only, or blocked |
| Methodology source | `anti_additive_source.py` | resolve the latest exact candidate receipt and enforce the requested authority class |
| Candidate consumers | `problem_structure_admission.py`, `anti_additive_baseline_evolution.py` | accept candidate-only authority while preserving admission/proposal status |
| Durable consumers | `autonomous_icm_evolution.py`, `sro_retention_migration.py` | require exact durable authority before project-scoped write or retention promotion |

The Runtime facade does not contain Provider parsing, gate logic, or filesystem replay logic. Kernel
modules do not import `agentos_runtime`.

## Kernel States

| State | Meaning | Durable ICM write |
| --- | --- | --- |
| `ALLOW_BOUNDED_CHANGE` | both gain/cost gates pass and the object is adequately resolved | eligible, still subject to existing evidence, scope, rollback, and write gates |
| `REQUIRE_FIRST_PRINCIPLES_REFRAMING` | object adequacy or Provider uncertainty is unresolved | blocked |
| `REQUIRE_OBJECT_UPGRADE` | active triggers expose an underpowered or wrong object, but the proposal remains at the same or lower object level | blocked |
| `BLOCK_PATCH_ACCUMULATION` | effective Cbit gain does not strictly exceed complexity cost | blocked |
| `BLOCK_ABSTRACTION_FOG` | a proposed object lift does not pay for its abstraction cost | blocked |
| `REQUIRE_CALIBRATED_VALIDATION` | the semantic prediction is structurally admissible but the exact scope has no, insufficient, or watch-state outcome history | candidate-only |
| `BLOCK_CALIBRATION_DRIFT` | observed outcomes show the exact prediction scope has drifted beyond frozen limits | blocked |

No state grants global memory, accepted-baseline, or production authority. An allowed methodology receipt
only removes this one meta-governance block. Safety quarantine remains available without the receipt
because it reduces reuse authority instead of expanding cognitive complexity.

## Strong Binding

The receipt commits the exact project scope, candidate identity, target type, object refs and levels,
failure and patch history, candidate payload hash, evidence refs, all seven trigger assessments, Provider
invocation receipt, cognition audit, policy hash, Kernel authorization, and final decision hash.

`AutonomousICMEvolutionPolicy` recomputes the candidate payload commitment. Missing, wrong-scope,
wrong-target, stale, modified, or non-allowing receipts keep the object as a candidate. A nonempty string
cannot substitute for a valid receipt.

The shared source repeats this validation for every consumer and additionally checks source replay and
the latest receipt map. Authority is explicit:

| Authority requirement | Consumers | Accepted methodology state |
| --- | --- | --- |
| `CANDIDATE_ONLY` | problem-structure admission, baseline evolution proposal | trusted or exploration-only receipt |
| `DURABLE_PROJECT_WRITE` | retention promotion, Autonomous ICM evolution | fully allowing receipt only |

One receipt cannot be reused for another candidate, payload, target type, project, or stale audit head.
Batch retention migration takes an audit-id map keyed by candidate id so independent objects cannot
accidentally share one authorization.

## Prediction-Outcome Calibration

Calibration binds each actually executed, allowing methodology receipt to an admitted outcome source
and Harness receipt. It records predicted and observed effective Cbit gain, complexity cost,
object-upgrade gain, abstraction cost, and whether both positive margins survived. Profiles are isolated
by exact `project_scope + change_kind + target_type`; duplicate methodology receipts cannot inflate the
history.

The Kernel mechanically computes absolute errors and margin-survival rates. Fewer than two observations
or two independent outcome sources remains `INSUFFICIENT_HISTORY`; bounded errors become `CALIBRATED`;
degraded but not failed profiles become `WATCH`; threshold-breaking profiles become `DRIFTED`. No
Provider may rewrite these arithmetic results or promote the resulting authority mode.

## Boundary

Alpha.17 does not claim universal calibration. Trust is local to the observed project, change kind, and
target type; a calibrated retention profile does not authorize a baseline or problem-structure change.
Problem admission and baseline evolution remain candidate/proposal operations. Official baseline writes,
global memory, and production activation still require their existing higher authorization boundaries.

## Verification

The release passes Python compilation and all 348 tests in a minimal clean copy. Verification includes
focused prediction-outcome calibration tests, cross-consumer candidate/durable authority tests,
module-size gates, the existing Anti-Additive durable-write smoke, an upgraded problem-admission smoke
with an exploration receipt, and a calibration smoke covering trusted retention plus candidate-only
baseline evolution. Independent artifact audits passed all manifests, hashes, ZIP CRCs, and exact entry
surfaces: 8/9 files for durable ICM, 13/14 for problem admission, and 7/8 for calibration.
