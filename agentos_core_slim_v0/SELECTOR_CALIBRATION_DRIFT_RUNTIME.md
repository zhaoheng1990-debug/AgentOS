# Selector Calibration and Drift Runtime

AgentOS CoreSlim 0.4.0-alpha.14 adds a project-scoped calibration loop for the Contextual Organization
Policy Selector. The runtime asks a narrow question: when the Selector predicted Cbit, cost, residual
risk, and uncertainty for the policy it actually selected, how well did those predictions match the
admitted Harness outcome in the same evidence scope?

## Object Mapping

| Upper object | AgentOS object | Observable proxy | Metric or gate |
| --- | --- | --- | --- |
| prediction mismatch | `SelectorCalibrationObservation` | frozen Provider assessment versus selected Harness outcome | signed Cbit and cost error |
| context-local drift | `SelectorCalibrationProfile` | repeated observations in one project/context/evidence-tier/policy cell | MAE, bias, uncertainty coverage, independent-source count |
| semantic drift support | `SelectorCalibrationProviderJudgment` | scope, evidence, model, Harness, and residual-risk diagnosis | exact profile/evidence binding and uncertainty ceiling |
| bounded trust state | `SelectorCalibrationDecision` | mechanical profile plus Provider diagnosis | `INSUFFICIENT_HISTORY`, `CALIBRATED`, `WATCH`, or `DRIFTED` |
| versioned writeback | `SelectorCalibrationReceipt` | append-only revisions and latest-predecessor binding | event hash chain, snapshot, restart replay |

The mapping is deliberately bounded. Observed negative-transfer residue is a proxy for residual risk,
not an ontological identity. There is no mechanical ground truth for `anti_additive_signal`, so alpha.14
does not invent one.

## Strong Binding

An observation is admitted only when the selection and feedback receipts agree on project, context,
evidence tier, selected policy, assignment, and selection hash. It additionally freezes Provider advice
and assessment hashes, request and bundle hashes, trial group and surface, selected outcome, Harness
receipt, execution result, and independent source result. The organization record must reproduce the
selected outcome fields exactly.

Only the actually selected policy becomes a calibration observation. Comparator execution remains
matched organization evidence; it is not relabeled as a Selector-authorized prediction sample.

## Runtime and Provider Responsibilities

Local Runtime code performs exact arithmetic and enforcement: schema and hash validation, duplicate
rejection, signed errors, MAE, bias, uncertainty coverage, source independence, scope isolation,
threshold application, revision ancestry, persistence, and replay.

The Provider interprets possible semantic causes of drift, including scope, evidence, model, Harness,
systematic Cbit or cost bias, and residual-risk mismatch. Its receipt must cite the frozen profile and
may not alter observations, metrics, thresholds, candidate state, or authority.

The Kernel combines both layers. Mechanical `DRIFTED` cannot be downgraded by Provider prose. A
Provider-supported material semantic concern may raise a mechanically calibrated profile to `WATCH`,
but does not fabricate mechanical drift. One observation remains `INSUFFICIENT_HISTORY`; independent
source count must meet the pre-frozen minimum.

## State Boundary

- `INSUFFICIENT_HISTORY`: collect more independent selected-policy outcomes; prediction trust is withheld.
- `CALIBRATED`: current metrics pass the frozen thresholds and semantic diagnosis; trust is project scoped.
- `WATCH`: recalibration is required because metrics or semantic diagnosis show concern.
- `DRIFTED`: prediction trust is suspended until a later, separately admitted revision repairs the profile.

These states do not authorize execution, select a global policy, promote knowledge, or activate a
production route. Alpha.14 emits a trustworthy calibration decision surface. Alpha.15 consumes that
surface through a separate, explicit control contract documented in
`CONTEXTUAL_POLICY_CALIBRATION_CONTROL.md`; the calibration Runtime itself still owns no selection or
execution authority.

## Verification

```powershell
pytest -q tests/test_selector_calibration_runtime.py tests/test_selector_calibration_modularity.py
python examples/selector_calibration_drift_smoke.py --output-dir D:\AgentOS_selector_calibration_smoke
```

The tests cover exact binding, independent history, thresholded drift, semantic watch escalation,
duplicate rejection, cross-context pooling, Provider history/evidence inconsistency, restart replay,
event tampering, and module-size caps.
