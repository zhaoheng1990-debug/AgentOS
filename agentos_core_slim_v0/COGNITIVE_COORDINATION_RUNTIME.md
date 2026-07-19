# Cognitive Coordination Runtime

AgentOS CoreSlim 0.4.0-alpha.4 includes a provider-backed coordination function
without making the coordinator a super-agent. The coordinator interprets the
public deliberation state and proposes what should happen next. The Kernel
decides whether that proposal is legal and applies the route.

## Ownership Split

| Component | Owns | Does not own |
| --- | --- | --- |
| Cognitive Coordinator | task-level route proposal, unresolved-question map, evidence-gap judgment, expected Cbit estimate | execution, permissions, private role memory, candidate state |
| Synthesizer | bounded content synthesis from admitted formal messages | scheduling or final acceptance |
| Kernel | route prerequisites, evidence scope, budgets, state transitions, replay, candidate state | provider semantic judgment |

The coordinator has an independent Agent identity, context key, private-memory
namespace, Provider/model binding, Runner/Harness binding, and credit identity.
It receives public `CognitiveMessage` records and public coordination outcomes,
not another role's private workspace or hidden reasoning.

## Proposal Contract

Every provider-backed coordination call returns a structured
`COORDINATION_PROPOSAL` containing:

- route action and target role;
- rationale and unresolved questions;
- concrete evidence gaps;
- public conflict-message references;
- admitted evidence references;
- expected Cbit gain and stop condition.

Supported route actions are `RUN_ROLE`, `PROCEED_TO_SYNTHESIS`,
`FINALIZE_CANDIDATE`, `REQUEST_EVIDENCE`, and `STOP_BLOCKED`. These values are
proposals only. They cannot set accepted, published, permission, or final-state
fields.

## Dynamic Deliberation

```text
COORDINATION(INTAKE)
  -> GENERATION
  -> COORDINATION
  -> REVIEW or REPLICATION
  -> COORDINATION
  -> remaining independent role
  -> COORDINATION
  -> SYNTHESIS
  -> COORDINATION
  -> CANDIDATE
```

Review and replication order may change. A negative replication or failed gate
does not prevent synthesis; it is material for a bounded negative synthesis.
Re-executing an already completed role requires a reference to a public conflict
message. This prevents unsupported coordination loops while preserving a route
for evidence-backed reopening.

## Kernel Gates

The local Runtime mechanically enforces:

- exact coordinator Provider/model binding;
- admitted evidence and public conflict references;
- role prerequisites and synthesis completeness;
- positive expected Cbit for additional role execution;
- per-role execution and total coordination-cycle budgets;
- checkpoint-scoped retry with failed receipts retained;
- coordinator identity and private-memory isolation;
- Kernel-only final candidate formation.

Provider unavailability, invalid schemas, authority claims, illegal routes, and
budget exhaustion block closed. The Runtime does not replace a failed semantic
coordination judgment with a local guess.

## Verified Boundary

The coordinated LIFE-COG3R live smoke completed five applied route decisions,
four formal role messages, and a Kernel-owned `PENDING_EPISTEMIC_REVIEW`
candidate. It recovered one rejected zero-Cbit coordination proposal and two
temporary Synthesizer Provider failures. Public replay and the artifact manifest
remained valid.

This establishes dynamic routing over a registered team. Endogenous problem
definition can supply a pending seed through `ENDOGENOUS_PROBLEM_RUNTIME.md`,
and `COGNITIVE_TEAM_FORMATION_RUNTIME.md` can now propose and authorize a
problem-fit registered team. Production reliability and repeated group
performance above the best member remain unestablished.
