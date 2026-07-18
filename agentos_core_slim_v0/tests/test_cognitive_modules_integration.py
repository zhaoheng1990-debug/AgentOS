import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    AgendaCandidate,
    AgentDescriptor,
    AgentRegistry,
    AgentRoleRequirement,
    CascadingInvalidationGraph,
    ClaimCandidate,
    CognitionRunObservation,
    CognitiveModuleRegistry,
    CreditEvent,
    CreditLedger,
    DependencyEdge,
    EndogenousAgendaLoop,
    EpistemicReviewProtocol,
    GroupCognitionEvalHarness,
    KnowledgeNode,
    OpenProblem,
    ReplicationReceipt,
)


def modules():
    return (
        GroupCognitionEvalHarness(),
        EpistemicReviewProtocol(),
        CreditLedger(),
        AgentRegistry(),
        EndogenousAgendaLoop(),
        CascadingInvalidationGraph(),
    )


def test_p0_to_p5_are_independently_installable_and_removable():
    registry = CognitiveModuleRegistry()
    installed = modules()
    for module in installed:
        registry.register(module)

    assert registry.contract()["module_count"] == 6
    assert registry.contract()["centralized_cognition_owner"] is False
    assert registry.require_one("epistemic_review") is installed[1]

    removed = registry.unregister(installed[2].module_id)

    assert removed is installed[2]
    assert registry.contract()["module_count"] == 5
    assert registry.resolve("credit_profile_projection") == ()
    assert registry.require_one("group_cognition_evaluation") is installed[0]


def test_composition_root_rejects_duplicate_module_identity():
    registry = CognitiveModuleRegistry()
    registry.register(GroupCognitionEvalHarness())

    with pytest.raises(ValueError, match="duplicate_runtime_module_id"):
        registry.register(GroupCognitionEvalHarness())


def test_bounded_group_cognition_workflow_exchanges_receipts_without_module_coupling():
    evaluator, reviewer, credit, agents, agenda, invalidation = modules()

    for descriptor in (
        AgentDescriptor(
            "generator",
            "HYPOTHESIS_GENERATOR",
            ("semantic_judgment",),
            "codex",
            "harness-a",
            "deepseek",
            "ctx-a",
            ("project://fixture",),
        ),
        AgentDescriptor(
            "reviewer",
            "ADVERSARIAL_REVIEWER",
            ("semantic_judgment",),
            "claude-code",
            "harness-b",
            "anthropic",
            "ctx-b",
            ("project://fixture",),
        ),
        AgentDescriptor(
            "replicator",
            "REPLICATOR",
            ("semantic_judgment",),
            "workbuddy",
            "harness-c",
            "openai",
            "ctx-c",
            ("project://fixture",),
        ),
    ):
        agents.register(descriptor)
    team = agents.form_team(
        "team-fixture",
        (
            AgentRoleRequirement("HYPOTHESIS_GENERATOR"),
            AgentRoleRequirement("ADVERSARIAL_REVIEWER"),
            AgentRoleRequirement("REPLICATOR"),
        ),
    )

    claim = ClaimCandidate(
        "claim-fixture",
        team.by_role("HYPOTHESIS_GENERATOR").agent_id,
        "The ensemble improves the frozen quality metric.",
        "ensemble_trial",
        "held_out_quality",
        "group_delta_vs_best_member",
        "project://fixture",
        ("aggregation_only",),
        "gate://fixture",
        ("evidence://primary",),
    )
    review = reviewer.assess(
        claim,
        replications=(
            ReplicationReceipt(
                "replication-fixture",
                claim.claim_id,
                team.by_role("REPLICATOR").agent_id,
                "ctx-c",
                "PASSED",
                ("evidence://replication",),
                ("provider-receipt://replication",),
            ),
        ),
    )
    credit.append(
        CreditEvent(
            "credit-fixture",
            claim.author_agent_id,
            "agent",
            "CLAIM_SURVIVED_REPLICATION",
            f"epistemic-decision://{claim.claim_id}/{review.decision}",
            review.evidence_refs,
        )
    )
    evaluation = evaluator.evaluate(
        "trial-fixture",
        (
            CognitionRunObservation("generator", 0.6, evidence_refs=("run://generator",)),
            CognitionRunObservation("replicator", 0.7, evidence_refs=("run://replicator",)),
        ),
        CognitionRunObservation("team-fixture", 0.85, evidence_refs=("run://team",)),
    )

    agenda.register_problem(
        OpenProblem(
            "problem-fixture",
            "Which rival should the next trial attack?",
            "ensemble_trial",
            "project://fixture",
            ("evidence://open-problem",),
            ("aggregation_only",),
        )
    )
    agenda.propose(
        AgendaCandidate(
            "agenda-fixture",
            "problem-fixture",
            "Test aggregation-only as the strongest rival.",
            "project://fixture",
            "provider-receipt://agenda",
            ("evidence://agenda",),
            0.9,
            0.9,
            0.8,
            0.7,
            0.6,
            0.1,
            0.2,
        )
    )

    invalidation.register_node(
        KnowledgeNode("claim-fixture", "claim", "project://fixture", review.evidence_refs)
    )
    invalidation.register_node(
        KnowledgeNode("report-fixture", "report", "project://fixture", ("report://fixture",))
    )
    invalidation.add_dependency(
        DependencyEdge("claim-fixture", "report-fixture", "DERIVED_IN")
    )

    assert review.decision == "SUPPORTED_BOUNDED"
    assert credit.profile("generator").trust_score == 1.0
    assert evaluation.verdict == "GROUP_OUTPERFORMS_BEST_MEMBER"
    assert agenda.select_next().decision == "SELECT"

    receipt = invalidation.invalidate(
        "claim-fixture",
        reason="later_independent_falsification",
        adjudication_ref="epistemic-decision://claim-fixture/FALSIFIED",
        evidence_refs=("evidence://later-falsifier",),
    )
    assert receipt.cascade_size == 1
    assert invalidation.node("report-fixture").status == "INVALIDATED"
