# Independent Cognitive Role Runtime

AgentOS CoreSlim 0.4.0-alpha.4 turns the first four epistemic roles from labels
into independently bound runtime agents. This is the first-stage cognitive
organization substrate, not a claim of production group cognition.

## Ownership Boundary

```text
AgentOS Kernel
  owns goals, scope, authorization, gates, state transitions, and candidate state

agentos_runtime
  owns role execution order, information barriers, private workspaces,
  formal-message exchange, provider binding, receipts, and replay

Runner / Harness / Provider adapters
  execute bounded work orders and return evidence or semantic support
```

No cognitive agent can grant permission, publish an asset, mark a claim
accepted, or move the Kernel-owned final candidate state.

## First-Stage Roles

| Role | Provider operation | Formal output | Allowed prior role messages |
| --- | --- | --- | --- |
| Hypothesis Generator | `group_hypothesis_generation` | `HYPOTHESIS_PROPOSAL` | none |
| Adversarial Reviewer | `adversarial_epistemic_review` | `ADVERSARIAL_REVIEW` | proposal only |
| Independent Replicator | `independent_replication_interpretation` | `REPLICATION_REPORT` | proposal only |
| Synthesizer | `group_synthesis_and_conflict_resolution` | `BOUNDED_SYNTHESIS` | proposal, review, replication |

The Replicator cannot read the Reviewer message. The Reviewer and Replicator
therefore cannot coordinate their judgments through hidden shared session
state. The Synthesizer receives all three formal messages only after they have
passed their role contracts and provider support gates.

## Agent Identity

Each `CognitiveAgent` binds:

- stable `agent_id` and epistemic role;
- immutable role contract;
- Runner and Harness identity;
- Provider and model identity;
- unique context-isolation key;
- unique private-memory namespace;
- declared Harness capabilities;
- independent credit subject identity;
- allowed project evidence scopes.

Context keys, private-memory namespaces, credit identities, and agent IDs must
be unique inside the four-role organization. Provider diversity is measurable
but optional: separate models do not replace context and memory isolation.

## Private And Public State

Each agent receives an owner-scoped `PrivateAgentWorkspace`. Its events are
hash chained, and another agent cannot read the workspace through the runtime
interface. Only the workspace descriptor, not its contents, enters a Provider
task.

Agents communicate through `CognitiveMessage` objects. A formal message commits
to its public payload, evidence refs, parent messages, sender identity, and
timestamp. Payload keys associated with chain of thought, hidden reasoning,
scratchpads, or private memory are rejected.

The organization also writes a public deliberation ledger:

```text
SESSION_INITIALIZED
ROLE_COMPLETED or ROLE_BLOCKED
ROLE_COMPLETED or ROLE_BLOCKED
...
```

Events form a previous-hash chain, while `snapshot.json` carries a content
hash. Replay verification detects removed, reordered, or modified events.

## Deliberation State Machine

```text
GENERATION
  -> REVIEW
  -> REPLICATION
  -> SYNTHESIS
  -> CANDIDATE
```

Any stage can transition to `BLOCKED`. A bounded retry preserves the failed
execution receipt and event before accepting a later successful receipt. A
completed synthesis produces only:

```text
PENDING_EPISTEMIC_REVIEW
```

It does not produce `ACCEPTED`, `PUBLISHED`, or execution permission.

When `CognitiveCoordinationRuntime` is configured, `COORDINATION` checkpoints
surround the role stages. The coordinator proposes routes; the Kernel applies
only routes that satisfy prerequisites, budgets, evidence scope, and anti-loop
rules. The fixed four-stage path remains available when coordination is absent.

## Provider Boundary

`ProviderCognitiveAgentAdapter` translates one formal role work order into a
`ProviderCognitiveTask`. The existing `ProviderTaskRouter` remains the only
provider execution plane. The adapter enforces:

- output schema and enum checks;
- provider support receipt presence;
- source-evidence admission;
- optional source-grounded semantic consistency assertions;
- exact Provider/model binding for the agent identity;
- invocation receipt preservation;
- fail-closed behavior without local semantic substitution.

A fallback that changes the bound Provider or model cannot silently become the
same cognitive agent.

## Verified Behavior

The local suite covers:

- distinct role contracts and objectives;
- context, memory, evidence, and credit identity isolation;
- formal-message private-reasoning rejection;
- Reviewer/Replicator information barriers;
- Provider/model binding and provider envelope preservation;
- missing output, evidence-scope, and final-state authority blocks;
- blocked-stage retry with failed receipt retention;
- public ledger replay and tamper detection;
- end-to-end four-role execution through independent ProviderTaskRouter paths.

The LIFE-COG3R live smokes additionally demonstrated four role identities, four
contexts, four private workspaces, two Provider organizations, three models,
recovered Provider outages, dynamic role ordering, overclaim falsification,
bounded local-result preservation, and a Kernel-owned pending candidate.

## Remaining Boundary

The current Replicator independently interprets frozen source evidence in an
isolated context. Independent Harness re-execution of experiments is not yet a
generic runtime primitive. Dynamic team formation and comparative problem-quality
evaluation now live in separate runtimes; durable cross-session role learning and
multi-agent parallel scheduling remain later stages. See
`COGNITIVE_COORDINATION_RUNTIME.md`, `ENDOGENOUS_PROBLEM_RUNTIME.md`,
`PROBLEM_QUALITY_LIFECYCLE.md`, and `COGNITIVE_TEAM_FORMATION_RUNTIME.md`.
