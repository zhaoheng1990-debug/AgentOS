# Cognitive Organization Ablation Runtime

AgentOS CoreSlim 0.4.0-alpha.9 completes the first four-component matched organization experiment. Alpha.8 executed Coordinator, Reviewer, and Replicator omissions; alpha.9 adds a true Synthesizer omission, cross-project live repetitions, and a context-preserving transfer audit.

## Runtime Position

```text
alpha.7 pending experiment proposal
        |
        v
separate Kernel authorization + frozen budget
        |
        v
DYNAMIC_TEAM baseline + one-component omissions
        |
        v
blind Provider assessment + hidden-truth Harness metrics
        |
        v
replay-valid ablation bundle
        |
        v
repeated matched attribution + bounded Provider diagnosis
```

The Runtime is the cognitive subject. It owns the objective, admitted evidence surface, protocol identity, role omission contract, information barriers, comparison rule, causal sign convention, replay, and candidate state. Providers support role cognition, coordination, normalization, semantic assessment, and diagnosis. They do not own hidden truth, observed Cbit, matched-pair arithmetic, identifiability, authorization, or promotion.

## Matched Protocols

Every bundle runs one full baseline and the Kernel-authorized omissions:

| Protocol | Cognitive organization |
| --- | --- |
| `DYNAMIC_TEAM` | Coordinator plus Generator, Reviewer, Replicator, and Synthesizer |
| `DYNAMIC_NO_COORDINATOR` | All four cognitive roles in a frozen static order |
| `DYNAMIC_NO_REVIEWER` | Coordinator plus Generator, Replicator, and Synthesizer |
| `DYNAMIC_NO_REPLICATOR` | Coordinator plus Generator, Reviewer, and Synthesizer |
| `DYNAMIC_NO_SYNTHESIZER` | Coordinator plus Generator, Reviewer, and Replicator; a Generator-bound projection reads only the formal hypothesis proposal |

The full baseline and every omission share the same trial, evidence and finding catalogs, Provider-call envelope, blind semantic assessment contract, and hidden-truth Harness. Only one organization component changes at a time. A role omission requires a `kernel://` authorization reference; the ordinary four-role deliberation path remains unchanged. The no-Synthesizer projection is bound to the Generator Provider/model and cannot inspect Reviewer or Replicator message bodies, so normalization cannot recreate a hidden synthesis stage.

## Measurement Boundary

Provider-backed agents produce evidence-citing candidate outputs. The semantic assessor receives an opaque candidate identity and cannot see protocol identity or hidden truth. The Harness alone calculates finding accuracy, rejection accuracy, uncertainty preservation, observed Cbit, errors exposed and corrected, negative-transfer interception, normalized cost, and convergence steps.

One passing bundle creates matched records but does not establish a component effect. `OrganizationLearningEvaluator` requires at least two independent source-result hashes in the same `context_key` and evidence tier. It defines contribution as:

```text
component contribution = DYNAMIC_TEAM - matched ablation
```

A positive effectiveness contribution means the component was beneficial in the admitted trials; a negative value means harmful; zero remains uncertain. The Provider receives this frozen sign contract and may explain the result, but a contradictory direction or unsupported causal status is rejected.

Blind semantic quality is expressed on an inclusive `[0, 1]` scale. The range is part of the Provider task contract and is independently enforced by the Runtime. Harness-owned metrics cannot be overwritten by the Provider.

## Live Cross-Project Evidence

LIFE-Cog3R, MATH_CBIT1, and OCS1R2 each now provide at least two live matched pairs for Coordinator, Adversarial Reviewer, Replicator, and Synthesizer. Every admitted bundle passed authorization, equal-evidence, replay, hidden-truth, blind-assessment, Harness-ownership, and budget gates.

The direction matrix is deliberately non-universal: all four components are beneficial in the bounded LIFE context and harmful in the bounded MATH_CBIT1 and OCS1R2 contexts. The cross-project audit therefore marks every component `CONTEXT_DEPENDENT`. It emits no pooled effect, universal role ranking, or proof of cognitive multiplication. Transfer conclusions remain `CANDIDATE_ONLY` and have no route-selection or execution authority.

## Verification

From `agentos_core_slim_v0`:

```powershell
python -m pytest -q tests/test_cognitive_organization_learning_runtime.py tests/test_cognitive_organization_ablation_project_source_smoke.py
python examples/cognitive_organization_ablation_project_source_smoke.py --help
python examples/organization_ablation_learning_feedback_smoke.py --help
python examples/organization_cross_project_attribution_smoke.py --help
```

The project-source smoke writes the runtime snapshot, Provider task audit, manifest, and return pack. Failed live attempts are preserved separately and never imported as learning evidence.
