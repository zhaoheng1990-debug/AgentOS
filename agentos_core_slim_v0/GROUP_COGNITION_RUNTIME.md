# Modular Group Cognition Runtime

AgentOS CoreSlim 0.4.0-alpha.10 retains the pluggable P0-P5 group cognition layer. The design
keeps the Kernel as the cognitive and policy owner while allowing providers,
runners, Harnesses, evaluators, and state stores to be replaced independently.

## Object Mapping

| Upper ontology object | AgentOS object | Observable proxy | Primary metric or gate |
| --- | --- | --- | --- |
| SharedICM / plural cognition | isolated agent ensemble | role and context assignment receipt | distinct agent and context gate |
| EFG falsification | epistemic review protocol | objection and replication receipts | bounded support, pending, or falsified |
| effective Cbit | group evaluation harness | member and group run observations | group delta versus best member |
| learned trust allocation | epistemic credit ledger | adjudicated append-only events | bounded trust score and confidence |
| endogenous problem selection | agenda loop | provider-supported agenda candidates | priority gate and explicit stop |
| endogenous problem definition | four isolated problem roles | candidate, critique, researchability, and selection receipts | pending seed and no execution authority |
| problem-quality learning | quality lifecycle runtime | blinded forecasts, trial and feedback receipts | observed Cbit and prediction error |
| Temporal Difference hygiene | cascading invalidation graph | dependency and invalidation receipts | blocked reuse and cascade size |

These are engineering correspondences, not ontological identities. Passing the
current tests demonstrates implementation and audit behavior; it does not by
itself establish production group cognition.

The first independent cognitive-role runtime is documented in
`COGNITIVE_AGENT_RUNTIME.md`. P0-P5 remain epistemic organization modules;
`agentos_runtime` now supplies the role identities, information barriers,
private workspaces, formal-message protocol, and deliberation state machine
that execute those organizational contracts.
`COGNITIVE_COORDINATION_RUNTIME.md` documents the provider-backed coordination
function and the Kernel gates that apply its route proposals.
`ENDOGENOUS_PROBLEM_RUNTIME.md` documents plural problem framing, independent
problem challenge, researchability assessment, group selection, and seed intake.
`PROBLEM_QUALITY_LIFECYCLE.md` documents baseline comparison, Kernel-authorized
problem trials, outcome receipts, and agenda/credit/invalidation feedback.
`COGNITIVE_TEAM_FORMATION_RUNTIME.md` documents independent baselines, dynamic
formation proposals, and Kernel authorization. `COGNITIVE_TEAM_EXECUTION_RUNTIME.md`
documents actual three-arm execution, hidden-truth Harness scoring, and credit feedback.
`COGNITIVE_ORGANIZATION_LEARNING_RUNTIME.md` documents repeated protocol comparison,
matched-ablation attribution, bounded diagnosis, and separately authorized follow-up experiments.
`COGNITIVE_ORGANIZATION_ABLATION_RUNTIME.md` documents actual Kernel-authorized omission
execution, including the Generator-bound no-Synthesizer projection, blind assessment,
hidden-truth Harness measurement, repeated learning feedback, and non-pooled cross-project audit.
`SRO_RETENTION_RUNTIME.md` documents Provider-backed, query-conditioned reuse routing,
strong witness/task/receipt binding, candidate-only legacy migration, and persistent delayed retrieval.

## Modules

| Phase | Module | Owns | Does not own |
| --- | --- | --- | --- |
| P0 | `GroupCognitionEvalHarness` | deterministic group metrics | semantic quality judgment or scheduling |
| P1 | `EpistemicReviewProtocol` | falsification-first epistemic state | permissions or asset promotion |
| P2 | `CreditLedger` | adjudicated track record and advisory profile | route selection or evidence admission |
| P3 | `AgentRegistry` | role discovery and isolated team assembly | agent execution |
| P4 | `EndogenousAgendaLoop` | problem state, ranking, select-or-stop, feedback | external action execution |
| P5 | `CascadingInvalidationGraph` | dependency propagation and reuse blocking | semantic choice of invalidation roots |
| Quality lifecycle | `ProblemQualityLifecycleRuntime` | frozen forecasts, trial state, outcome and feedback | self-authorization or publication |
| Team formation | `CognitiveTeamFormationRuntime` | independent baselines, bounded team proposals, authorization receipts | team execution or truth ownership |
| Team execution | `CognitiveTeamExecutionRuntime` | isolated three-arm execution, replay admission, Harness evaluation and feedback | hidden truth, publication, or automatic promotion |
| Organization learning | `CognitiveOrganizationLearningRuntime` | context-isolated protocol evidence, bounded diagnosis, policy candidates, and experiment proposals | unsupported causality, route selection, or self-authorization |
| Organization ablation | `CognitiveOrganizationAblationRuntime` | authorized full-team and one-component-omission execution, replay, blind assessment, and Harness-owned metrics | self-authorization, hidden truth, causal promotion, or policy acceptance |
| SRO retention | `SRORetentionRuntime` | Provider-backed witness/task matching, Kernel route ownership, legacy migration candidates, persistent delayed retrieval and replay | global memory, unbound reuse, production activation, synthetic-weight deployment, or theory promotion |

`CognitiveModuleRegistry` is the thin composition root. It only installs,
discovers, and removes modules. Cognitive behavior remains inside the installed
modules, so the composition root cannot grow into a second monolithic Kernel.

## Runtime Flow

```text
runner + Harness + provider adapters
              |
              v
provider-backed semantic support receipts
              |
              v
P3 isolated agents -> P1 review/replication -> P2 credit history
       |                    |                       |
       |                    +-> P5 invalidation ----+
       v
P0 group evaluation -> organization learning -> P4 agenda selection
              |                    |
              +-> bounded ablation proposal -> separate Kernel authorization
              |
              v
Kernel scope, safety, candidate-state, replay, rollback, and final decision
```

Provider-backed semantic operations fail closed in
`ProviderBackedRuntimeCognitionLayer`. Group hypothesis generation,
adversarial review, replication interpretation, synthesis, non-mechanical
quality assessment, problem generation, and invalidation-root assessment all
require complete support receipts.

Provider receipt presence is not sufficient for operations with frozen
semantic consistency assertions. The Runtime compares structured receipt fields
with source-grounded assertions, blocks evidence/judgment conflicts, preserves
the conflicting receipt, and requires a consistent revalidation receipt before
the result can enter an epistemic state transition.

Local deterministic boundaries reject provider override: agent/context
isolation, metric calculation, matched-ablation arithmetic, credit projection,
dependency propagation, schema validation, capability enforcement, hashing,
replay, and rollback. Provider-backed organization diagnosis is admitted only
when its evidence references and causal status agree with those frozen results.

## Pluggable Composition

```python
from agentos_kernel import (
    AgentRegistry,
    CascadingInvalidationGraph,
    CognitiveModuleRegistry,
    CreditLedger,
    EndogenousAgendaLoop,
    EpistemicReviewProtocol,
    GroupCognitionEvalHarness,
)

runtime_modules = CognitiveModuleRegistry()
for module in (
    GroupCognitionEvalHarness(),
    EpistemicReviewProtocol(),
    CreditLedger(),
    AgentRegistry(),
    EndogenousAgendaLoop(),
    CascadingInvalidationGraph(),
):
    runtime_modules.register(module)

review = runtime_modules.require_one("epistemic_review")
runtime_modules.unregister(CreditLedger.module_id)
```

P2 can persist across Runtime restarts by injecting
`JsonlCreditEventStore(path)` into `CreditLedger`. The remaining modules expose
plain immutable records and can receive project-specific persistence adapters
without changing their cognitive contracts.

## Verification

Each phase has a dedicated test module, followed by a cross-module smoke test.
Run the complete suite from `agentos_core_slim_v0`:

```powershell
pytest -q tests
python -m compileall -q agentos_kernel agentos_runtime tests examples
```
