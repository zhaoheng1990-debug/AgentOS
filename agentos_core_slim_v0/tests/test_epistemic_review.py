import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    ClaimCandidate,
    EpistemicReviewProtocol,
    ObjectionReceipt,
    ReplicationReceipt,
)


def claim():
    return ClaimCandidate(
        claim_id="claim-1",
        author_agent_id="hypothesis-agent",
        statement="The bounded intervention improves the frozen metric.",
        research_object="bounded_intervention",
        observable_proxy="held_out_score",
        metric="quality_delta",
        scope="fixture-v1",
        rival_explanations=("random_seed_effect",),
        frozen_gate_ref="gate://fixture-v1",
        evidence_refs=("evidence://primary",),
    )


def replication(outcome="PASSED", replicator="replicator-agent"):
    return ReplicationReceipt(
        replication_id=f"replication-{outcome.lower()}",
        target_claim_id="claim-1",
        replicator_agent_id=replicator,
        independent_context_id="context-independent-1",
        outcome=outcome,
        evidence_refs=(f"evidence://replication/{outcome.lower()}",),
        provider_support_receipt_refs=("provider-receipt://replication",),
    )


def test_independent_pass_supports_only_bounded_epistemic_state():
    decision = EpistemicReviewProtocol().assess(claim(), replications=(replication(),))

    assert decision.decision == "SUPPORTED_BOUNDED"
    assert decision.independent_replication_count == 1
    assert decision.permission_granted is False
    assert decision.asset_promotion_authorized is False
    assert "provider-receipt://replication" in decision.evidence_refs


def test_failed_independent_replication_falsifies_claim():
    decision = EpistemicReviewProtocol().assess(
        claim(),
        replications=(replication("FAILED"),),
    )

    assert decision.decision == "FALSIFIED"
    assert "independent_replication_failed" in decision.reasons


def test_same_author_replication_is_not_independent():
    decision = EpistemicReviewProtocol().assess(
        claim(),
        replications=(replication(replicator="hypothesis-agent"),),
    )

    assert decision.decision == "PENDING"
    assert decision.independent_replication_count == 0
    assert "independent_replication_required" in decision.reasons


def test_sustained_adversarial_objection_falsifies_even_with_passing_replication():
    objection = ObjectionReceipt(
        objection_id="objection-1",
        target_claim_id="claim-1",
        reviewer_agent_id="red-team-agent",
        rival_explanation="measurement_leakage",
        strongest_falsifier_ref="falsifier://leakage-control",
        status="SUSTAINED",
        evidence_refs=("evidence://leakage-found",),
    )

    decision = EpistemicReviewProtocol().assess(
        claim(),
        objections=(objection,),
        replications=(replication(),),
    )

    assert decision.decision == "FALSIFIED"
    assert "strongest_falsifier_sustained" in decision.reasons


def test_missing_rival_set_remains_pending():
    incomplete = ClaimCandidate(
        claim_id="claim-1",
        author_agent_id="hypothesis-agent",
        statement="A claim without an explicit rival set.",
        research_object="bounded_intervention",
        observable_proxy="held_out_score",
        metric="quality_delta",
        scope="fixture-v1",
        rival_explanations=(),
        frozen_gate_ref="gate://fixture-v1",
        evidence_refs=("evidence://primary",),
    )

    decision = EpistemicReviewProtocol().assess(incomplete, replications=(replication(),))

    assert decision.decision == "PENDING"
    assert "rival_set_required" in decision.reasons
