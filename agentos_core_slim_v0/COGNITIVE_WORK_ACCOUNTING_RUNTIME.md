# Cognitive Work Accounting Runtime

AgentOS CoreSlim 0.4.0-alpha.18 introduces a Provider-backed, Kernel-controlled
runtime for measuring how much online work a cognitive trajectory consumes and
whether another round is justified.

## Object mapping

```text
Collective cognitive compression
-> project-scoped cognitive-work trajectory
-> admitted per-round work and semantic diagnostics
-> Harness Cbit, tokens, calls, latency, cost, drift, redundancy, and control action
```

Equal benchmark scores are treated as comparable task-side outcomes, not proof
that two systems used the same internal cognitive process. `observed_cbit_gain`
is an external Harness observation. Tokens and calls are work counters, not Cbit.

## Module boundary

| Module | Owner | Responsibility |
| --- | --- | --- |
| `cognitive_work_models.py` | Kernel | Immutable budgets, observations, semantic assessments, and control receipts |
| `cognitive_work_eval.py` | Kernel | Exact aggregation, marginal efficiency, budget enforcement, and final action |
| `cognitive_work_integrations.py` | Kernel | Small adapters into existing gates without a central mega-runtime |
| `cognitive_work_provider.py` | Runtime | One bounded semantic assessment per admitted round |
| `cognitive_work_repository.py` | Runtime | Append-only events, snapshots, restart reconstruction, and replay checks |
| `cognitive_work_runtime.py` | Runtime | Thin composition facade |

The Provider assesses evidence novelty, constraint coverage, hypothesis
diversity, redundancy, error correlation, problem drift, and uncertainty. It may
recommend an action, but the recommendation is advisory. The Kernel owns exact
work arithmetic and chooses one of:

```text
CONTINUE
STOP_SUFFICIENT
STOP_LOW_MARGINAL
REORGANIZE
ESCALATE
BLOCK_BUDGET
```

## Mechanical work surface

Every round binds:

```text
input_tokens + output_tokens + cached_tokens
provider_calls + tool_calls
latency_ms + api_cost + tool_cost
observed_cbit_gain
errors_exposed + errors_corrected
agent_ids + model_ids + topology_id
evidence_refs + Harness receipt
```

Cached tokens remain separately visible and are not double-counted in total
tokens. The Runtime never infers missing counters from prose.

## Control integrations

One hash-bound `CognitiveWorkControlDecision` can constrain six existing paths:

1. SRO direct reuse is downgraded when the trajectory does not support reuse.
2. Task Lifecycle persists continue, stop, reorganize, escalate, or budget-block directives.
3. Contextual policy selection blocks team expansion after marginal work is exhausted.
4. Anti-Additive blocks same-level expansion that lacks marginal Cbit support.
5. Retention requires a sufficient, evidence-bound work trajectory when a control is supplied.
6. OperatorMemory writes require repeated sufficient work and the existing methodology receipt.

All integrations validate project scope. Contextual policy selection also binds
the exact context key. Anti-Additive, Retention, and OperatorMemory require the
control evidence reference to be present in the candidate evidence surface.

## Authority boundary

A cognitive-work receipt is project-scoped evidence. It grants no accepted
baseline, global memory, production activation, execution, or publication
authority. Existing Kernel authorization and Anti-Additive methodology gates
remain mandatory.

## Current boundary

This runtime establishes accountable online cognitive work and deterministic
control semantics. It does not yet establish a universal conversion between
parameters, tokens, benchmark score, and Cbit. Cross-model scaling claims still
require compute-matched trials, external Harness outcomes, and repeated
cross-task validation.
