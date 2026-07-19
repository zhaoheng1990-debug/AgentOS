# Contextual Organization Policy Selector

AgentOS CoreSlim 0.4.0-alpha.11 adds a bounded organization-policy selector. It does not assume
that more agents are always better. For each problem, the Runtime combines a structured problem
receipt, exact-context matched evidence, an explicit budget, a risk envelope, registered agent
feasibility, and Provider semantic support. The Kernel then chooses one executable role policy,
authorizes only an exploratory trial, or abstains.

## Object Mapping

| Upper object | AgentOS object | Observable | Gate or metric |
| --- | --- | --- | --- |
| constraint-conditioned operator fiber | contextual organization policy | fixed role-policy catalog | registered policy and role binding |
| problem constraint field | `ContextualProblemStructure` | uncertainty, conflict, replication, synthesis, coordination, novelty | structure receipt hash and evidence refs |
| context-local organizational knowledge | `MatchedPolicyEvidence` | repeated matched trial pairs | exact context, tier, source, evidence surface, and self-hash |
| bounded semantic support | Provider policy assessment | fit, expected Cbit, cost, risk, anti-additivity, uncertainty | exact schema, provenance, and invocation binding |
| executable organization | `EnsembleAssignment` | registered role and isolated context bindings | registry feasibility and optional Provider diversity |
| final runtime policy | Kernel decision | selected policy and activation mode | budget, risk, evidence, role coverage, and authorization |

These mappings are engineering contracts. A passing selector run demonstrates bounded selection and
auditability, not a universal law about the best cognitive organization.

## Modular Architecture

| Module | Owns | Does not own |
| --- | --- | --- |
| `contextual_policy_models.py` | immutable policy, problem, budget, risk, evidence, assessment, and decision contracts | Provider calls, files, or routing |
| `contextual_policy_evidence.py` | exact-context matched-pair aggregation | semantic interpretation or cross-context pooling |
| `contextual_policy_selector.py` | Kernel hard gates, transparent ranking, and final activation mode | Provider execution or persistence |
| `contextual_policy_provider.py` | one bounded semantic assessment call and receipt audit | role mutation or final selection |
| `contextual_policy_repository.py` | hash-chained events, snapshots, restart reconstruction, and replay | semantic judgment |
| `contextual_policy_runtime.py` | thin orchestration facade | monolithic policy logic |

Kernel modules do not import `agentos_runtime`, `pathlib`, or operating-system APIs. Filesystem access
is confined to the Runtime repository through the existing deliberation event-store adapter.

## Registered Policy Catalog

The selector evaluates a finite set of policies that existing Runtime components can actually form:

| Policy | Roles |
| --- | --- |
| `SOLO` | Generator |
| `FIXED_TEAM` | Generator, Reviewer, Replicator, Synthesizer |
| `DYNAMIC_TEAM` | Generator, Reviewer, Replicator, Synthesizer, Coordinator |
| `DYNAMIC_NO_COORDINATOR` | Dynamic team without Coordinator |
| `DYNAMIC_NO_REVIEWER` | Dynamic team without Reviewer |
| `DYNAMIC_NO_REPLICATOR` | Dynamic team without Replicator |
| `DYNAMIC_NO_SYNTHESIZER` | Dynamic team without Synthesizer |

The Runtime does not search an arbitrary power set of roles. Adding a new policy requires a named,
registered, executable protocol with its own tests and evidence surface.

## Selection Flow

```text
problem structure receipt + project scope
                 |
                 v
exact context/tier matched trial evaluation
                 |
                 v
AgentRegistry feasibility for every registered policy
                 |
                 v
Provider assessment of fit, Cbit, cost, risk, uncertainty
                 |
                 v
Kernel role coverage + budget + risk + evidence gates
                 |
        +--------+---------+
        |                  |
        v                  v
project-scoped       exploratory trial
authorization        or abstention
        |
        v
assignment receipt + hash-chained event + snapshot/replay
```

Problem fields mechanically determine required roles at the configured threshold. Premise
uncertainty requires a Reviewer, replication need requires a Replicator, evidence conflict or
synthesis need requires a Synthesizer, and coordination complexity requires a Coordinator. The
Provider may estimate semantic fit, but it cannot remove a required role.

## Matched Evidence Boundary

Organization evidence is admitted only when candidate and comparator records share:

- the exact `context_key` and evidence tier;
- the same trial group and independent source result hash;
- the same evidence references and source surface;
- replay-valid `OrganizationTrialRecord` receipts;
- at least two independent matched pairs by default.

The selector does not pool effect sizes across projects or contexts. A cross-context record is ignored,
a mismatched surface fails closed, and repeated use of one source cannot simulate independent evidence.
The evidence object validates its own metric commitment hash after reconstruction.

## Provider and Kernel Authority

The Provider receives the frozen problem, registered policies, matched evidence, budget, risk, and
public agent profiles. It must assess every policy using an exact schema and evidence-bounded
provenance. Its `recommended_policy_id` is advisory.

The Kernel independently rejects policies that:

- cannot be formed from registered, context-isolated agents;
- omit a role required by the problem structure;
- exceed role, Provider-call, coordination-step, or normalized-cost budgets;
- exceed residual-risk, uncertainty, or anti-additive ceilings;
- lack matched evidence when risk requires it;
- have adverse matched outcomes or violate exploratory-trial limits.

The possible final modes are:

- `AUTHORIZED_PROJECT_SCOPED`: sufficient matched evidence and every hard gate passes;
- `EXPLORATORY_TRIAL_ONLY`: no sufficient matched evidence, but a low-risk bounded trial is allowed;
- `ABSTAIN`: no policy passes all gates.

No receipt grants global policy authority, accepted knowledge status, or production activation.

## Persistence and Replay

Every successful selection stores Provider advice, matched evidence, the Kernel decision, and the
exact `EnsembleAssignment` in a hash-chained public event log. Provider contract failures are also
stored as blocked events. Restart reconstruction revalidates object hashes, assignment roles,
Provider-advice binding, context/tier binding, the event chain, and the current snapshot.

## Verification

Run the focused tests and deterministic smoke from `agentos_core_slim_v0`:

```powershell
python -m pytest -q tests/test_contextual_policy_selector.py `
  tests/test_contextual_policy_runtime.py `
  tests/test_contextual_policy_modularity.py `
  tests/test_contextual_policy_selector_smoke.py

python examples/contextual_organization_policy_selector_smoke.py `
  --output-dir artifacts/contextual-policy-selector-smoke

python examples/audit_release_artifacts.py `
  --artifact-dir artifacts/contextual-policy-selector-smoke `
  --output artifacts/contextual-policy-selector-audit.json
```

The smoke intentionally makes the Provider recommend the full dynamic team while the role budget
forbids it. The Kernel selects the matched, feasible `DYNAMIC_NO_SYNTHESIZER` policy, persists the
receipt, restarts, verifies replay, and packages an independently auditable return pack.
