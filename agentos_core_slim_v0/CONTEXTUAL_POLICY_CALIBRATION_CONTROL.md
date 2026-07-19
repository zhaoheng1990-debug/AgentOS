# Contextual Policy Calibration Control

AgentOS CoreSlim 0.4.0-alpha.15 closes the loop between Selector calibration and later organization-policy
decisions. The feature is an authority constraint, not a replacement prediction model: the current
Provider still assesses every registered policy, while the Kernel uses historical calibration to limit
how much authority that new assessment may receive.

## Object Mapping

| Upper object | AgentOS object | Observable proxy | Gate |
| --- | --- | --- | --- |
| prediction validity | `SelectorCalibrationReceipt` | latest replay-valid context-policy revision | latest-map and receipt hash binding |
| bounded control field | `ContextualPolicyCalibrationControl` | one control for each registered policy | exact seven-policy coverage and scope |
| authority adaptation | `ContextualPolicyCalibrationGate` | control mode plus existing matched evidence | authorize, explore, or block |
| versioned decision | `ContextualOrganizationPolicyDecision` | committed controls and evidence refs | decision hash, selection receipt, replay |

## State Semantics

| Source state | Control mode | Selector effect |
| --- | --- | --- |
| source not configured | `LEGACY_COMPATIBLE` | preserve the prior Selector contract |
| no exact-scope receipt | `EXPLORATION_ONLY` | no project-scoped authorization |
| `INSUFFICIENT_HISTORY` | `EXPLORATION_ONLY` | collect more independent selected-policy outcomes |
| `CALIBRATED` | `TRUSTED` | preserve eligibility for existing evidence, budget, risk, and registry gates |
| `WATCH` | `EXPLORATION_ONLY` | retain bounded trials but remove project-scoped authorization |
| `DRIFTED` | `BLOCKED` | reject the affected policy until a later valid calibration revision |

`CALIBRATED` does not directly authorize a policy. It only removes the calibration restriction; every
existing Kernel gate still applies. Likewise, `WATCH` exploration remains subject to the risk envelope's
role ceiling, and a drifted preferred policy may lead to another bounded policy or complete abstention.

## Strong Source Binding

A configured source must provide both a replay verification result and a latest-receipt hash map. The
resolver checks that the returned receipt is exactly the ledger head for the requested context, evidence
tier, and policy. It then verifies project scope, candidate state, profile and decision hashes, Provider
judgment binding, legal mechanical-to-final state transitions, and independent history.

The Runtime generates controls for all seven registered policies. Missing observations are explicit
controls rather than absent fields. Calibration receipt references are included in decision evidence,
and the complete control tuple enters the Kernel decision hash, selection receipt, event ledger,
snapshot, and restart reconstruction.

## Provider Boundary

`contextual_selector_calibration_control` is Provider-forbidden mechanical enforcement. A Provider may
support the original policy assessment and the earlier semantic drift diagnosis, but may not choose the
control mode, rewrite a historical state, relax freshness, or restore authorization. This keeps the
Runtime as the cognitive subject and the Kernel as final authority owner.

## Verification

```powershell
pytest -q tests/test_contextual_policy_calibration_control.py
pytest -q tests/test_contextual_policy_calibration_modularity.py
python examples/contextual_policy_calibration_control_smoke.py --output-dir D:\AgentOS_selector_control_smoke
```

The end-to-end smoke reuses real selection-to-execution feedback, builds independently thresholded
`CALIBRATED`, `WATCH`, and `DRIFTED` ledgers, feeds each into a new Selector, and verifies authorization,
exploration downgrade, hard blocking, persistence, replay, manifest hashes, and ZIP surface.
