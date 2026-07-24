# Organization Evolution Runtime

AgentOS CoreSlim 0.4.0-alpha.20 adds bounded, capability-conditioned cognitive-workflow optimization. It
extends the existing fixed policy Selector and organization-learning evidence loop without replacing
either component.

## Runtime Position

```text
admitted task + baseline organization + explicit budget
                         |
                         v
adaptive operator window from replayed operator credit
                         |
                         v
Provider-backed mutation proposals over registered operators
                         |
                         v
deterministic role / contract / communication-topology mutation
and exact Agent / model / Provider / Runner / Harness rebinding
                         |
                         v
external Runner/Harness evaluation with an execution-time cost ceiling
                         |
                         v
Kernel utility, evidence, budget, and cross-stage stability gates
                         |
                         v
retain best eligible genome -> update operator credit -> continue or stop
```

The Runtime remains the cognitive and lifecycle owner. The Provider supports semantic mutation
proposals. The Harness executes frozen candidates and owns observed outcomes. The Kernel computes
fitness, applies hard gates, chooses the retained candidate, updates bounded credit, and controls stop
state. None of these receipts grants production activation or accepted-baseline authority.

## First-Class Objects

| Object | Owns | Does not own |
| --- | --- | --- |
| `OrganizationEvolutionTask` | task, stage, scope, objective, evidence, anchor surface | workflow mutation |
| `OrganizationGenome` | roles, contracts, directed receipt edges, exact executor bindings, rounds, stop policy, lineage | execution outcome |
| `OrganizationCapabilityBindingReceipt` | Registry, capability, scope and exact-context evidence admission | Harness outcome or final retention |
| `OrganizationMutationProposal` | one Provider-supported bounded mutation | selection or execution authority |
| `OrganizationHarnessOutcome` | replay-valid score, Cbit, cost, correction and anchor observations | semantic promotion |
| `OrganizationEvolutionDecision` | Kernel utility and stability gate result | production activation |
| `OrganizationOperatorCredit` | observed trial, retention, utility and cost history | universal operator quality |
| `OrganizationGenerationReceipt` | exact proposal-candidate-outcome-decision bindings | hidden Harness truth |

## Registered Operators

The Runtime provides six explicit operators:

- exploration: `ADD_ROLE`, `ADD_EDGE`, `REBIND_ROLE_AGENT`;
- exploitation: `REMOVE_ROLE`, `REMOVE_EDGE`, `SPECIALIZE_ROLE`.

Every role and contract must exist in the Runtime role-contract catalog. Every edge endpoint must be
present in the candidate. Operator parameters are applied mechanically; a Provider cannot inject code,
an unknown role, an unknown operator, a self-loop, or a final candidate state.

When capability support is enabled, every role must bind to one registered, enabled Agent descriptor.
The binding freezes Agent, model, Provider, Runner, Harness, context-isolation key, capabilities, and
allowed evidence scopes. A changed executor is classified as `SUPPORTED`, `EXPLORATORY_TRIAL_ONLY`,
or `BLOCKED` from exact-project, exact-context, replay-valid evidence before candidate execution. This
receipt admits or blocks a trial; it never replaces the Kernel fitness and negative-transfer gates.

The strategy component preserves an exploration/exploitation surface where possible. Previously
untried operators receive priority, while observed mean utility affects later allocation. Credit is
context-local session evidence and remains advisory outside the current optimization task.

## Fitness and Stability

The default Kernel utility is explicit and configurable:

```text
primary score
+ 0.25 * observed Cbit
+ 0.10 * error-correction rate
- 0.20 * normalized cost
```

A candidate must also pass independent hard gates:

- exact task, stage, parent, proposal, genome, outcome, and evidence bindings;
- registered roles, contracts, operators, and communication endpoints;
- role, edge, Provider-call, generation, and normalized-cost budgets;
- replay-valid and candidate-specific Harness outcomes;
- minimum primary and utility gain;
- complete anchor-task surface;
- no anchor regression beyond the configured threshold.

The Runtime charges baseline and every evaluated candidate, including rejected candidates. The Harness
receives the remaining normalized-cost allowance before execution and must reject work it cannot run
within that ceiling.

## Persistence and Stop

Initialization, baseline admission, Provider blocks, generation receipts, Runtime blocks, and stop
state are stored in one public hash-chained event ledger. Restart reconstruction validates every object
hash, proposal/candidate/outcome/decision binding, event chain, current snapshot, incumbent pairing,
and Provider-call accounting.

The bounded optimizer stops on:

- generation budget exhaustion;
- Provider-call budget exhaustion;
- normalized-cost exhaustion;
- configured no-improvement patience;
- absence of an applicable registered operator;
- explicit fail-closed Provider, operator, Harness, replay, or binding failure.

## Current Boundary

Alpha.20 closes capability-conditioned workflow optimization over registered role and contract catalogs. It
does not yet implement unrestricted code synthesis, crossover between unrelated projects, global
population sharing, automatic curriculum-stage generation, endogenous problem evolution, or production
deployment. It also does not claim that a small-model collective has reached a strong-model ceiling;
that requires live fresh holdouts with matched tasks, Harnesses, budgets, and anchor surfaces. Cross-stage
stability is enforced through a frozen anchor surface supplied by the Harness; stage advancement remains
externally authorized.

## Verification

Run focused tests from `agentos_core_slim_v0`:

```powershell
python -m pytest -q `
  tests/test_organization_evolution_runtime.py `
  tests/test_organization_capability_evolution.py `
  tests/test_organization_evolution_modularity.py `
  tests/test_organization_evolution_smoke.py
```

Run the deterministic CLI smoke:

```powershell
python examples/organization_evolution_smoke.py `
  --output-dir artifacts/organization-evolution-smoke
```

The smoke writes `smoke_result.json`, a manifest, a rollback pointer from the retained genome to the
baseline, and a replayable event store.
