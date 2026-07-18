# Modular Group Cognition Runtime

AgentOS CoreSlim 0.3.1 provides a pluggable P0-P5 group cognition layer. The design
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
| Temporal Difference hygiene | cascading invalidation graph | dependency and invalidation receipts | blocked reuse and cascade size |

These are engineering correspondences, not ontological identities. Passing the
current tests demonstrates implementation and audit behavior; it does not by
itself establish production group cognition.

## Modules

| Phase | Module | Owns | Does not own |
| --- | --- | --- | --- |
| P0 | `GroupCognitionEvalHarness` | deterministic group metrics | semantic quality judgment or scheduling |
| P1 | `EpistemicReviewProtocol` | falsification-first epistemic state | permissions or asset promotion |
| P2 | `CreditLedger` | adjudicated track record and advisory profile | route selection or evidence admission |
| P3 | `AgentRegistry` | role discovery and isolated team assembly | agent execution |
| P4 | `EndogenousAgendaLoop` | problem state, ranking, select-or-stop, feedback | external action execution |
| P5 | `CascadingInvalidationGraph` | dependency propagation and reuse blocking | semantic choice of invalidation roots |

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
P0 group evaluation -> P4 agenda selection -> next bounded iteration
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
isolation, metric calculation, credit projection, dependency propagation,
schema validation, capability enforcement, hashing, replay, and rollback.

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
python -m compileall -q agentos_kernel tests
```
