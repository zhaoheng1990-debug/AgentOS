import hashlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(TEST_ROOT))

from agentos_kernel import (  # noqa: E402
    CONTEXTUAL_POLICY_IDS,
    AutonomousICMEvolutionPolicy,
    CognitiveWorkControlDecision,
    ConstraintAlignedRetentionGate,
    ContextualMatchedEvidenceEvaluator,
    ContextualOrganizationPolicySelector,
    GradedSROCompatibilityGate,
    default_contextual_role_policies,
)
from test_anti_additive_methodology_runtime import (  # noqa: E402
    EVIDENCE as ANTI_EVIDENCE,
    change_candidate,
    provider_result,
    runtime as anti_additive_runtime,
)
from test_autonomous_icm_evolution import methodology_receipt, ups_candidate  # noqa: E402
from test_constraint_aligned_retention import valid_candidate  # noqa: E402
from test_contextual_policy_selector import (  # noqa: E402
    assessments,
    budget,
    digest,
    matched_no_synth_records,
    problem,
    risk,
)
from test_sro_retention_runtime import HASH_A, HASH_B, matcher_receipt, precommitted_witness  # noqa: E402


def work_control(
    *,
    project_scope,
    context_key,
    action="STOP_LOW_MARGINAL",
    sufficient=False,
    trajectory_id="trajectory-integration",
):
    count = 2 if sufficient else 1
    return CognitiveWorkControlDecision.create(
        decision_id=f"decision-{hashlib.sha256((project_scope + context_key + action).encode()).hexdigest()[:12]}",
        trajectory_id=trajectory_id,
        project_scope=project_scope,
        context_key=context_key,
        action=action,
        allow_additional_round=action in {"CONTINUE", "REORGANIZE", "ESCALATE"},
        allow_organization_expansion=action in {"CONTINUE", "REORGANIZE"},
        allow_direct_sro_reuse=sufficient,
        retention_eligible=sufficient,
        operator_memory_eligible=sufficient,
        marginal_cbit_gain=0.01 if not sufficient else 0.4,
        cognitive_efficiency=0.00001 if not sufficient else 0.0004,
        cumulative_cbit_gain=0.1 if not sufficient else 0.85,
        total_tokens=1000 * count,
        total_provider_calls=count,
        total_tool_calls=0,
        total_latency_ms=1000 * count,
        total_api_cost=0.02 * count,
        total_tool_cost=0.0,
        round_count=count,
        reason="integration fixture",
        observation_hashes=tuple(hashlib.sha256(f"observation-{i}".encode()).hexdigest() for i in range(count)),
        provider_receipt_hashes=tuple(hashlib.sha256(f"provider-{i}".encode()).hexdigest() for i in range(count)),
        budget_hash=hashlib.sha256(b"integration-budget").hexdigest(),
        kernel_authorization_ref="kernel://cognitive-work/integration",
    )


def test_low_marginal_work_downgrades_direct_sro_reuse_to_observe():
    witness = precommitted_witness()
    control = work_control(
        project_scope=witness.project_scope_ref,
        context_key="ctx-sro",
    )
    receipt = matcher_receipt(witness_hash=witness.as_dict()["record_hash"])

    decision = GradedSROCompatibilityGate().evaluate(
        receipt,
        witness=witness,
        task_commitment_hash=HASH_B,
        provider_invocation_receipt_hash=HASH_A,
        cognitive_work_control=control,
    )

    assert decision.route == "OBSERVE"
    assert decision.reuse_allowed is False
    assert control.decision_hash in decision.decision_factors[0]


def test_control_contract_rejects_action_authority_inconsistency():
    control = work_control(project_scope="project://control-test", context_key="ctx")

    with pytest.raises(ValueError, match="round_authority_inconsistent"):
        replace(control, allow_additional_round=True)


def test_low_marginal_work_blocks_team_expansion_in_policy_selection():
    problem_value = problem()
    control = work_control(
        project_scope=problem_value.project_scope,
        context_key=problem_value.context_key,
    )
    evidence = ContextualMatchedEvidenceEvaluator().evaluate(
        matched_no_synth_records(),
        context_key=problem_value.context_key,
        evidence_tier="LIVE_PROJECT",
    )

    decision = ContextualOrganizationPolicySelector().select(
        decision_id="decision-cognitive-work-selector",
        problem=problem_value,
        budget=budget(),
        risk=risk(),
        policies=default_contextual_role_policies(),
        matched_evidence=evidence,
        provider_assessments=assessments(),
        provider_advice_hash=digest("provider-advice-cognitive-work"),
        feasible_policy_ids=CONTEXTUAL_POLICY_IDS,
        kernel_authorization_ref="kernel://selector/cognitive-work",
        cognitive_work_control=control,
    )

    assert decision.activation_mode == "ABSTAIN"
    assert control.evidence_ref in decision.evidence_refs
    assert all(
        "cognitive_work_expansion_not_authorized" in item.hard_gate_failures
        for item in decision.candidate_evaluations
        if item.policy_id != "SOLO"
    )


def test_low_marginal_work_blocks_same_level_anti_additive_expansion(tmp_path):
    control = work_control(
        project_scope="project://anti-additive-test",
        context_key="ctx-anti-additive",
    )
    evidence = (*ANTI_EVIDENCE, control.evidence_ref)
    receipt = anti_additive_runtime(tmp_path, provider_result()).review_change(
        candidate=change_candidate(
            proposed_object_level="PROXY",
            evidence_refs=evidence,
        ),
        kernel_authorization_ref="kernel://anti-additive/cognitive-work",
        cognitive_work_control=control,
    )

    assert receipt.decision.state == "BLOCK_PATCH_ACCUMULATION"
    assert receipt.decision.reason == "cognitive_work_marginal_gain_does_not_authorize_same_level_expansion"


def test_retention_requires_sufficient_bound_cognitive_work_evidence():
    control = work_control(
        project_scope="project://retention-work",
        context_key="ctx-retention",
    )
    candidate = valid_candidate()
    candidate["project_scope_ref"] = control.project_scope
    candidate["evidence_refs"].append(control.evidence_ref)

    decision = ConstraintAlignedRetentionGate().evaluate(
        candidate,
        cognitive_work_control=control,
    )

    assert decision.eligible_for_retention is False
    assert decision.reason == "cognitive_work_trajectory_not_retention_eligible"


def test_operator_memory_write_requires_sufficient_work_trajectory():
    candidate = ups_candidate()
    low = work_control(
        project_scope=candidate["project_scope_ref"],
        context_key="ctx-operator-memory",
    )
    candidate["evidence_refs"].append(low.evidence_ref)
    methodology = methodology_receipt(candidate)

    blocked = AutonomousICMEvolutionPolicy().review(
        candidate,
        methodology,
        cognitive_work_control=low,
    )
    assert blocked.decision == "NO_WRITE_KEEP_CANDIDATE"
    assert blocked.reason == "cognitive_work_trajectory_not_operator_memory_eligible"

    sufficient = work_control(
        project_scope=candidate["project_scope_ref"],
        context_key="ctx-operator-memory",
        action="STOP_SUFFICIENT",
        sufficient=True,
    )
    candidate["evidence_refs"][-1] = sufficient.evidence_ref
    admitted = AutonomousICMEvolutionPolicy().review(
        candidate,
        methodology_receipt(candidate),
        cognitive_work_control=sufficient,
    )
    assert admitted.decision == "AUTONOMOUS_PROJECT_OPERATORMEMORY_WRITE"
