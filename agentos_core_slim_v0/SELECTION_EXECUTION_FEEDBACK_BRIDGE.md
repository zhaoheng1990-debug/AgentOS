# Selection-to-Execution Feedback Bridge

AgentOS CoreSlim 0.4.0-alpha.12 closes the bounded loop from contextual organization-policy
selection to real execution and back to matched evidence. The bridge does not add another cognitive
authority. It composes an existing Selector, an existing Team or Ablation Runtime, a Kernel admission
gate, and a persistent record source.

## Why This Bridge Exists

Before alpha.12, the Selector could issue a project-scoped or exploratory assignment, while team
execution and organization learning existed as separate verified components. A caller still had to
manually translate the decision into an execution and then manually feed the outcome back. That gap
made it possible to drift the selected agents, evidence surface, trial identity, or execution budget.

The bridge turns that handoff into a committed protocol:

```text
problem + exact-context evidence
              |
              v
Contextual Organization Policy Selector
              |
              v
frozen selection + assignment + explicit execution budget
              |
              v
Team/Ablation execution adapter -> existing cognitive execution Runtime
              |
              v
Harness-owned outcomes + per-protocol execution footprints + replay
              |
              v
Kernel feedback gate -> OrganizationTrialRecord -> matched evidence
              |
              +-------------------------> next Selector decision
```

## Modular Ownership

| Module | Owns | Does not own |
| --- | --- | --- |
| `selection_execution_models.py` | immutable execution budget and request commitments | execution, persistence, or scoring |
| `selection_execution_outcomes.py` | Harness outcome, per-protocol footprint, and bundle commitments | admission policy or files |
| `selection_feedback_gate.py` | mechanical Kernel admission into organization records | Provider calls or execution |
| `selection_execution_adapters.py` | translation to existing Team and Ablation Runtimes | policy selection or evidence promotion |
| `selection_feedback_repository.py` | hash-chained events, snapshots, restart reconstruction, and record-source port | semantic judgment |
| `selection_feedback_bridge.py` | thin composition and transaction boundary | team cognition, Harness scoring, or final policy authority |

The bridge and Selector facades have architecture line caps. Kernel contracts import neither Runtime
nor filesystem APIs. The Selector reads feedback through the read-only `OrganizationTrialRecordSource`
protocol, avoiding a circular dependency on the bridge implementation.

## Strong Bindings

`SelectionExecutionRequest` commits the selection receipt, project, context, evidence tier, trial
group, trial ID, evidence references, selected policy, ordered roles, exact agent identities, complete
agent backend binding hash, Kernel authorization, and a separate execution budget. Replacing a model,
Provider, Harness, Runner, isolation key, Coordinator, or selected member invalidates admission.

Every actual protocol run has an `ExecutedProtocolFootprint` with:

- protocol identity;
- Provider call count;
- normalized cost;
- execution result hash;
- Harness receipt hash.

This distinction matters because the Team adapter executes three matched arms even when only the
selected policy and its comparator enter feedback. Kernel budget checks cover every actual arm, not
only the two admitted outcomes. The bundle also requires each admitted outcome to agree exactly with
its corresponding footprint.

## Authority Boundary

The execution adapter may run only after an explicit Kernel execution authorization and budget. It
cannot alter the selected assignment or promote a result. The Harness owns observed effectiveness,
Cbit, error correction, negative-transfer interception, cost, and convergence metrics. The Kernel
admits only scope-bound, evidence-bound, replay-valid outcomes.

Admitted records remain project- and context-scoped. One trial is insufficient by default; repeated
independent matched pairs are required before a later Selector decision can become
`AUTHORIZED_PROJECT_SCOPED`. No bridge receipt grants global policy authority, accepted knowledge,
or production activation.

## Verification

From `agentos_core_slim_v0`:

```powershell
python -m pytest -q tests/test_selection_execution_feedback_bridge.py `
  tests/test_selection_execution_adapters.py `
  tests/test_selection_execution_feedback_bridge_smoke.py `
  tests/test_contextual_policy_modularity.py

python examples/selection_execution_feedback_bridge_smoke.py `
  --output-dir artifacts/selection-execution-feedback-smoke

python examples/audit_release_artifacts.py `
  --artifact-dir artifacts/selection-execution-feedback-smoke `
  --output artifacts/selection-execution-feedback-audit.json
```

The deterministic smoke performs two independent real three-arm LIFE-Cog3R executions. The first
trial remains insufficient; the second closes matched evidence. After restart replay, a downstream
Selector reads the bridge through the record-source port and authorizes the supported project-scoped
policy without manually supplied records.
