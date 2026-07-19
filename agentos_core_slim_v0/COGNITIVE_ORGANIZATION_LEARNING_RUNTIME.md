# Cognitive Organization Learning Runtime

AgentOS CoreSlim 0.4.0-alpha.7 introduced a bounded learning layer above completed cognitive-team trials. Alpha.8 keeps that contract and adds actual Kernel-authorized matched-ablation execution and feedback.

## Runtime Position

```text
alpha.6 equal-surface execution trials
        |
        v
mechanical admission gates
        |
        v
repeated protocol evaluation + matched-ablation attribution
        |
        v
Provider-backed bounded diagnosis
        |
        v
pending policy candidate -> bounded experiment proposal
        |
        v
separate Kernel authorization -> Runner/Harness execution
```

The Runtime remains the cognitive subject. It owns the learning context, evidence tier, admitted observations, comparison rules, conflict boundaries, candidate state, replay, and next-experiment envelope. The Provider supports semantic diagnosis inside those boundaries. It cannot select a winning protocol, manufacture an ablation, authorize execution, or promote a candidate.

## Objects

| Object | Owns | Does not own |
| --- | --- | --- |
| `OrganizationTrialRecord` | one replay-valid protocol observation and its Harness metrics | semantic diagnosis or policy authority |
| `OrganizationLearningEvaluator` | complete-group protocol comparison and matched-ablation arithmetic | Provider judgment or execution |
| `OrganizationDiagnosisReceipt` | evidence-bounded failure hypotheses and experiment suggestions | unsupported causal attribution |
| `OrganizationPolicyCandidate` | observed recommendation, incumbent, statistics, and advisory exploration priority | route or execution authority |
| `OrganizationExperimentPlan` | bounded variants, budget, stop conditions, and required Harnesses | self-authorization |
| `CognitiveOrganizationLearningRuntime` | lifecycle, gates, persistence, replay, and candidate state | hidden truth or external action execution |

## Evidence Rules

Learning is isolated by both `context_key` and `evidence_tier`. Scripted fixtures, project-source observations, and live Provider-backed trials cannot silently pool into one conclusion.

A protocol recommendation requires repeated complete groups containing exactly the comparable `SOLO`, `FIXED_TEAM`, and `DYNAMIC_TEAM` arms. Complete groups must have one evidence surface and one source-result hash, and the source-result hash must be unique across repeated groups. Renaming a copied result cannot create repeated evidence. A single live trial may establish an incumbent from observed performance, but it remains `REQUIRE_EXPLORATION`.

A role contribution requires repeated matched pairs in the same context, evidence tier, and trial group:

- `DYNAMIC_TEAM` versus `DYNAMIC_NO_COORDINATOR`;
- `DYNAMIC_TEAM` versus `DYNAMIC_NO_REVIEWER`;
- `DYNAMIC_TEAM` versus `DYNAMIC_NO_REPLICATOR`;
- `DYNAMIC_TEAM` versus `DYNAMIC_NO_SYNTHESIZER`.

Without those pairs, the contribution is `NOT_IDENTIFIABLE`. A Provider receipt that claims otherwise is rejected. When a matched effect is identifiable, the Provider also cannot label a positive frozen effectiveness contribution as harmful, or a negative one as beneficial.

## Credit and Authority

Historical credit is advisory. It can increase the priority of revalidating a protocol when historical trust disagrees with current observations or confidence is weak. It cannot change the protocol winner computed from admitted metrics.

The policy object is always a candidate. It has neither route-selection nor execution authority. A proposed ablation plan also has no execution authority until the Kernel issues a separate authorization with an explicit budget. The actual ablation still belongs to a Runner/Harness execution adapter.

## Current Evidence

The first LIFE-Cog3R live alpha.6 observation remains a negative but useful three-arm result: `SOLO` was the incumbent and the Runtime returned `REQUIRE_EXPLORATION`. Alpha.8 then ran two independent live matched-ablation bundles over the LIFE evidence surface. Coordinator, Adversarial Reviewer, and Replicator now each have two matched pairs and bounded context-specific attribution; Synthesizer remains unidentifiable because no no-synthesizer arm was authorized.

The feedback policy still returns `REQUIRE_EXPLORATION`. These trials validate executable attribution and Provider/Kernel conflict gates, not universal role superiority or production group cognition. Single MATH_CBIT1 and OCS1R2 project-source observations likewise remain exploratory. Execution details are in `COGNITIVE_ORGANIZATION_ABLATION_RUNTIME.md`.

## Verification

Run the focused learning tests from `agentos_core_slim_v0`:

```powershell
python -m pytest -q tests/test_cognitive_organization_learning_runtime.py tests/test_organization_learning_project_source_smoke.py
```

Run `examples/organization_learning_project_source_smoke.py` over one or more completed alpha.6 `smoke_result.json` files to produce a snapshot, manifest, rollback pointer, and return pack.
