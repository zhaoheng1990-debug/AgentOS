import hashlib
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (  # noqa: E402
    CONTEXTUAL_POLICY_IDS,
    ContextualMatchedEvidenceEvaluator,
    ContextualOrganizationPolicySelector,
    ContextualProblemStructure,
    ContextualProviderPolicyAssessment,
    MatchedPolicyEvidence,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    OrganizationTrialRecord,
    default_contextual_role_policies,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def trial_record(
    policy_id: str,
    group_id: str,
    source_id: str,
    *,
    context_key: str = "ctx-validation",
    effectiveness: float = 0.7,
    cbit: float = 0.6,
    cost: float = 0.5,
) -> OrganizationTrialRecord:
    refs = (f"evidence://{source_id}",)
    return OrganizationTrialRecord.create(
        record_id=f"record-{group_id}-{policy_id.lower()}",
        trial_group_id=group_id,
        context_key=context_key,
        evidence_tier="LIVE_PROJECT",
        protocol_id=policy_id,
        effectiveness_score=effectiveness,
        observed_cbit_gain=cbit,
        normalized_cost=cost,
        convergence_steps=4,
        errors_exposed=2,
        errors_corrected=1,
        negative_transfer_opportunities=2,
        negative_transfer_intercepts=1,
        evidence_refs=refs,
        harness_receipt_ref=f"harness://{source_id}/{policy_id}",
        execution_result_hash=digest(f"execution-{group_id}-{policy_id}"),
        source_result_hash=digest(source_id),
        replay_valid=True,
    )


def matched_no_synth_records(*, adverse: bool = False) -> tuple[OrganizationTrialRecord, ...]:
    records = []
    for index in (1, 2):
        source = f"source-{index}"
        group = f"group-{index}"
        records.extend(
            (
                trial_record("DYNAMIC_TEAM", group, source, effectiveness=0.70, cbit=0.60, cost=0.70),
                trial_record(
                    "DYNAMIC_NO_SYNTHESIZER",
                    group,
                    source,
                    effectiveness=0.60 if adverse else 0.82,
                    cbit=0.50 if adverse else 0.76,
                    cost=0.55,
                ),
            )
        )
    return tuple(records)


def problem(**overrides):
    values = {
        "problem_id": "problem-validation-1",
        "context_key": "ctx-validation",
        "project_scope": "project://selector-test",
        "objective": "Challenge premises and independently replicate a bounded finding.",
        "premise_uncertainty": 0.8,
        "evidence_conflict": 0.2,
        "replication_need": 0.8,
        "synthesis_need": 0.2,
        "coordination_complexity": 0.8,
        "novelty_need": 0.5,
        "evidence_refs": ("evidence://problem",),
        "structure_receipt_ref": "provider-receipt://problem-structure",
        "structure_receipt_hash": digest("problem-structure"),
    }
    values.update(overrides)
    return ContextualProblemStructure(**values)


def budget(**overrides):
    values = {
        "budget_ref": "budget://selector-test",
        "max_roles": 4,
        "max_provider_calls": 5,
        "max_coordination_steps": 4,
        "max_normalized_cost": 0.8,
    }
    values.update(overrides)
    return OrganizationBudgetEnvelope(**values)


def risk(**overrides):
    values = {
        "risk_ref": "risk://selector-test",
        "max_residual_risk": 0.5,
        "max_provider_uncertainty": 0.4,
        "max_anti_additive_signal": 0.5,
        "matched_evidence_required_above_risk": 0.4,
        "allow_unmatched_exploration": True,
        "exploration_max_roles": 2,
    }
    values.update(overrides)
    return OrganizationRiskEnvelope(**values)


def assessments(*, residual_risk: float = 0.2):
    return tuple(
        ContextualProviderPolicyAssessment(
            policy_id=policy_id,
            structure_fit=0.95 if policy_id == "DYNAMIC_NO_SYNTHESIZER" else 0.55,
            expected_cbit_gain=0.8 if policy_id == "DYNAMIC_NO_SYNTHESIZER" else 0.5,
            estimated_normalized_cost=0.55 if policy_id == "DYNAMIC_NO_SYNTHESIZER" else 0.7,
            residual_risk=residual_risk,
            anti_additive_signal=0.2,
            uncertainty=0.2,
            rationale=f"bounded assessment for {policy_id}",
            evidence_refs=("evidence://problem",),
        )
        for policy_id in CONTEXTUAL_POLICY_IDS
    )


def select(records, *, problem_value=None, budget_value=None, risk_value=None, assessments_value=None):
    problem_value = problem_value or problem()
    evidence = ContextualMatchedEvidenceEvaluator().evaluate(
        tuple(records),
        context_key=problem_value.context_key,
        evidence_tier="LIVE_PROJECT",
    )
    return ContextualOrganizationPolicySelector().select(
        decision_id="decision-selector-1",
        problem=problem_value,
        budget=budget_value or budget(),
        risk=risk_value or risk(),
        policies=default_contextual_role_policies(),
        matched_evidence=evidence,
        provider_assessments=assessments_value or assessments(),
        provider_advice_hash=digest("provider-advice"),
        feasible_policy_ids=CONTEXTUAL_POLICY_IDS,
        kernel_authorization_ref="kernel://selector-test",
    )


def test_matched_evidence_and_structure_select_bounded_role_combination():
    decision = select(matched_no_synth_records())

    assert decision.selected_policy_id == "DYNAMIC_NO_SYNTHESIZER"
    assert decision.selected_roles == (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "COORDINATOR",
    )
    assert decision.activation_mode == "AUTHORIZED_PROJECT_SCOPED"
    assert decision.execution_authorized is True
    dynamic = next(item for item in decision.candidate_evaluations if item.policy_id == "DYNAMIC_TEAM")
    assert "role_budget_exceeded" in dynamic.hard_gate_failures


def test_matched_evidence_ignores_other_contexts_and_requires_unique_sources():
    records = (*matched_no_synth_records(), *(
        trial_record("DYNAMIC_TEAM", "other-1", "other-source", context_key="ctx-other"),
        trial_record("DYNAMIC_NO_SYNTHESIZER", "other-1", "other-source", context_key="ctx-other"),
    ))
    evidence = ContextualMatchedEvidenceEvaluator().evaluate(
        tuple(records), context_key="ctx-validation", evidence_tier="LIVE_PROJECT"
    )
    no_synth = next(item for item in evidence if item.policy_id == "DYNAMIC_NO_SYNTHESIZER")
    assert no_synth.matched_pair_count == 2
    assert no_synth.unique_source_count == 2
    assert no_synth.sufficient_matched_evidence is True


def test_matched_surface_mismatch_fails_closed():
    records = (
        trial_record("DYNAMIC_TEAM", "group-x", "source-a"),
        trial_record("DYNAMIC_NO_SYNTHESIZER", "group-x", "source-b"),
    )
    with pytest.raises(ValueError, match="contextual_policy_matched_surface_mismatch"):
        ContextualMatchedEvidenceEvaluator().evaluate(
            records, context_key="ctx-validation", evidence_tier="LIVE_PROJECT"
        )


def test_low_risk_unmatched_solo_is_trial_only_not_execution_authorized():
    simple_problem = problem(
        premise_uncertainty=0.1,
        replication_need=0.1,
        coordination_complexity=0.1,
        novelty_need=0.8,
    )
    decision = select(
        (),
        problem_value=simple_problem,
        budget_value=budget(max_roles=1, max_provider_calls=2, max_coordination_steps=1),
    )
    assert decision.selected_policy_id == "SOLO"
    assert decision.activation_mode == "EXPLORATORY_TRIAL_ONLY"
    assert decision.execution_authorized is False
    assert decision.trial_authorized is True


def test_high_risk_without_matched_evidence_abstains():
    decision = select((), assessments_value=assessments(residual_risk=0.45))
    assert decision.selected_policy_id == ""
    assert decision.activation_mode == "ABSTAIN"
    assert decision.trial_authorized is False
    assert all(
        "matched_evidence_required_for_risk_level" in item.hard_gate_failures
        or item.hard_gate_failures
        for item in decision.candidate_evaluations
    )


def test_adverse_matched_evidence_blocks_formally_supported_policy():
    decision = select(matched_no_synth_records(adverse=True))
    no_synth = next(
        item for item in decision.candidate_evaluations
        if item.policy_id == "DYNAMIC_NO_SYNTHESIZER"
    )
    assert "adverse_matched_evidence" in no_synth.hard_gate_failures
    assert decision.activation_mode == "ABSTAIN"


def test_matched_evidence_object_rejects_metric_tampering():
    evidence = ContextualMatchedEvidenceEvaluator().evaluate(
        matched_no_synth_records(), context_key="ctx-validation", evidence_tier="LIVE_PROJECT"
    )
    payload = next(
        item.as_dict() for item in evidence if item.policy_id == "DYNAMIC_NO_SYNTHESIZER"
    )
    payload["mean_effectiveness"] = 1.0
    for name in ("matched_trial_group_ids", "evidence_refs", "record_hashes"):
        payload[name] = tuple(payload[name])

    with pytest.raises(ValueError, match="contextual_matched_evidence_hash_mismatch"):
        MatchedPolicyEvidence(**payload)
