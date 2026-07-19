import hashlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    SelectorCalibrationDecision,
    SelectorCalibrationObservation,
    SelectorCalibrationProfile,
    SelectorCalibrationProviderJudgment,
    SelectorCalibrationReceipt,
)
from agentos_kernel.contextual_policy_models import hash_payload  # noqa: E402
from agentos_kernel.provider_cognition_layer import (  # noqa: E402
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
)
from agentos_runtime import (  # noqa: E402
    ContextualOrganizationPolicyRuntime,
    selector_calibration_scope_key,
)
from examples.contextual_organization_policy_selector_smoke import (  # noqa: E402
    StaticOrganizationProvider,
    _problem,
    _records,
    _registry,
)


PROJECT_SCOPE = "project://contextual-policy-selector-smoke"
CONTEXT_KEY = "ctx-selector-smoke"
EVIDENCE_TIER = "LIVE_PROJECT"
SELECTED_POLICY = "DYNAMIC_NO_SYNTHESIZER"


def digest(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def calibration_receipt(state, *, project_scope=PROJECT_SCOPE, policy_id=SELECTED_POLICY):
    count = 1 if state == "INSUFFICIENT_HISTORY" else 2
    observation = SelectorCalibrationObservation.create(
        observation_id=f"observation-{state.lower()}",
        project_scope=project_scope,
        context_key=CONTEXT_KEY,
        evidence_tier=EVIDENCE_TIER,
        policy_id=policy_id,
        selection_id=f"selection-{state.lower()}",
        selection_receipt_hash=digest(f"selection-{state}"),
        provider_advice_hash=digest(f"advice-{state}"),
        provider_assessment_hash=digest(f"assessment-{state}"),
        feedback_receipt_hash=digest(f"feedback-{state}"),
        request_hash=digest(f"request-{state}"),
        execution_bundle_hash=digest(f"bundle-{state}"),
        outcome_hash=digest(f"outcome-{state}"),
        selected_agent_binding_hash=digest(f"agents-{state}"),
        trial_group_id=f"group-{state.lower()}",
        trial_id=f"trial-{state.lower()}",
        trial_surface_hash=digest(f"surface-{state}"),
        source_result_hash=digest(f"source-{state}"),
        harness_receipt_ref=f"harness://calibration/{state.lower()}",
        harness_receipt_hash=digest(f"harness-{state}"),
        execution_result_hash=digest(f"execution-{state}"),
        predicted_cbit_gain=0.8,
        observed_cbit_gain=0.8,
        cbit_error=0.0,
        estimated_normalized_cost=0.55,
        observed_normalized_cost=0.55,
        cost_error=0.0,
        provider_uncertainty=0.2,
        cbit_within_uncertainty=True,
        predicted_residual_risk=0.2,
        observed_negative_transfer_rate=0.2,
        evidence_refs=("evidence://selector-smoke/problem",),
    )
    observation_hashes = (
        *((digest(f"prior-observation-{state}"),) if count == 2 else ()),
        observation.observation_hash,
    )
    source_hashes = (
        *((digest(f"prior-source-{state}"),) if count == 2 else ()),
        observation.source_result_hash,
    )
    threshold_hash = digest("frozen-calibration-threshold")
    profile = SelectorCalibrationProfile.create(
        profile_id=f"profile-{state.lower()}",
        project_scope=project_scope,
        context_key=CONTEXT_KEY,
        evidence_tier=EVIDENCE_TIER,
        policy_id=policy_id,
        observation_count=count,
        independent_source_count=count,
        mean_absolute_cbit_error=0.0,
        mean_cbit_bias=0.0,
        mean_absolute_cost_error=0.0,
        mean_cost_bias=0.0,
        cbit_uncertainty_coverage=1.0,
        mean_residual_risk_error=0.0,
        mechanical_state=state,
        observation_hashes=observation_hashes,
        source_result_hashes=source_hashes,
        threshold_hash=threshold_hash,
    )
    diagnostic, action, drivers = {
        "INSUFFICIENT_HISTORY": ("INSUFFICIENT_HISTORY", "COLLECT_MORE", ()),
        "CALIBRATED": ("NO_SEMANTIC_DRIFT", "KEEP_CURRENT_CALIBRATION", ()),
        "WATCH": ("POSSIBLE_SEMANTIC_DRIFT", "REASSESS_CONTEXT_POLICY", ("MODEL_CHANGE",)),
        "DRIFTED": ("MATERIAL_SEMANTIC_DRIFT", "SUSPEND_PREDICTION_TRUST", ("MODEL_CHANGE",)),
    }[state]
    semantic = {
        "diagnostic_state": diagnostic,
        "drift_drivers": list(drivers),
        "recommended_action": action,
        "uncertainty": 0.2,
        "rationale": f"synthetic bounded {state.lower()} diagnosis",
        "evidence_refs": [profile.evidence_ref],
    }
    judgment = SelectorCalibrationProviderJudgment.create(
        profile_hash=profile.profile_hash,
        diagnostic_state=diagnostic,
        drift_drivers=drivers,
        recommended_action=action,
        uncertainty=0.2,
        rationale=semantic["rationale"],
        evidence_refs=(profile.evidence_ref,),
        provider_invocation_receipt={
            "input_hash": digest(f"input-{state}"),
            "output_hash": hash_payload(semantic),
        },
        provider_audit={"status": PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT},
    )
    decision = SelectorCalibrationDecision.create(
        decision_id=f"decision-{state.lower()}",
        final_state=state,
        prediction_trusted=state == "CALIBRATED",
        recalibration_required=state in {"WATCH", "DRIFTED"},
        action={
            "INSUFFICIENT_HISTORY": "COLLECT_MORE",
            "CALIBRATED": "KEEP_CURRENT_CALIBRATION",
            "WATCH": "REASSESS_CONTEXT_POLICY",
            "DRIFTED": "SUSPEND_PREDICTION_TRUST",
        }[state],
        reason=f"synthetic_{state.lower()}",
        kernel_authorization_ref=f"kernel://calibration/{state.lower()}",
        profile_hash=profile.profile_hash,
        provider_judgment_hash=judgment.judgment_hash,
        threshold_hash=threshold_hash,
    )
    return SelectorCalibrationReceipt.create(
        calibration_id=f"calibration-{state.lower()}",
        runtime_id="synthetic-calibration-source",
        observation=observation,
        profile=profile,
        provider_judgment=judgment,
        kernel_decision=decision,
        supersedes_receipt_hash=digest(f"prior-receipt-{state}") if count == 2 else "",
        created_at="2026-07-19T00:00:00+08:00",
    )


class CalibrationSource:
    def __init__(self, receipt=None, *, replay_valid=True, latest_hash_override=None):
        self.receipt = receipt
        self.replay_valid = replay_valid
        self.latest_hash_override = latest_hash_override

    def latest(self, *, context_key, evidence_tier, policy_id):
        if self.receipt is None or policy_id != self.receipt.observation.policy_id:
            return None
        return self.receipt

    def verify_replay(self):
        latest = {}
        if self.receipt is not None:
            key = selector_calibration_scope_key(
                context_key=CONTEXT_KEY,
                evidence_tier=EVIDENCE_TIER,
                policy_id=self.receipt.observation.policy_id,
            )
            latest[key] = self.latest_hash_override or self.receipt.receipt_hash
        return {"valid": self.replay_valid, "latest_receipt_hashes": latest}


def budget():
    return OrganizationBudgetEnvelope(
        budget_ref="budget://calibration-control",
        max_roles=5,
        max_provider_calls=6,
        max_coordination_steps=5,
        max_normalized_cost=0.8,
    )


def risk():
    return OrganizationRiskEnvelope(
        risk_ref="risk://calibration-control",
        max_residual_risk=0.5,
        max_provider_uncertainty=0.4,
        max_anti_additive_signal=0.5,
        matched_evidence_required_above_risk=0.4,
        allow_unmatched_exploration=True,
        exploration_max_roles=5,
        require_distinct_provider=True,
    )


def select(tmp_path, source, *, selection_id="calibration-controlled-selection"):
    provider = StaticOrganizationProvider()
    runtime = ContextualOrganizationPolicyRuntime(
        runtime_id="calibration-controlled-selector",
        project_scope=PROJECT_SCOPE,
        registry=_registry(),
        provider_router=ProviderTaskRouter([provider]),
        workspace_root=tmp_path,
        calibration_source=source,
    )
    receipt = runtime.select_policy(
        selection_id=selection_id,
        problem=_problem(),
        records=_records(),
        evidence_tier=EVIDENCE_TIER,
        budget=budget(),
        risk=risk(),
        kernel_authorization_ref=f"kernel://calibration-control/{selection_id}",
    )
    return runtime, receipt, provider


@pytest.mark.parametrize(
    ("state", "activation", "trusted"),
    (
        ("INSUFFICIENT_HISTORY", "EXPLORATORY_TRIAL_ONLY", False),
        ("CALIBRATED", "AUTHORIZED_PROJECT_SCOPED", True),
        ("WATCH", "EXPLORATORY_TRIAL_ONLY", False),
    ),
)
def test_calibration_state_controls_selector_authority(tmp_path, state, activation, trusted):
    source_receipt = calibration_receipt(state)
    _, selected, _ = select(tmp_path, CalibrationSource(source_receipt))
    control = next(
        item for item in selected.kernel_decision.calibration_controls if item.policy_id == SELECTED_POLICY
    )

    assert selected.kernel_decision.selected_policy_id == SELECTED_POLICY
    assert selected.kernel_decision.activation_mode == activation
    assert selected.kernel_decision.execution_authorized is (activation == "AUTHORIZED_PROJECT_SCOPED")
    assert control.prediction_trusted is trusted
    assert control.calibration_receipt_hash == source_receipt.receipt_hash
    assert control.calibration_receipt_ref in selected.kernel_decision.evidence_refs


def test_configured_source_without_observation_forces_exploration(tmp_path):
    _, selected, _ = select(tmp_path, CalibrationSource())
    assert selected.kernel_decision.selected_policy_id == SELECTED_POLICY
    assert selected.kernel_decision.activation_mode == "EXPLORATORY_TRIAL_ONLY"
    assert all(
        item.calibration_state == "NO_OBSERVATION"
        for item in selected.kernel_decision.calibration_controls
    )


def test_drifted_policy_is_hard_blocked(tmp_path):
    _, selected, _ = select(tmp_path, CalibrationSource(calibration_receipt("DRIFTED")))
    evaluation = next(
        item for item in selected.kernel_decision.candidate_evaluations if item.policy_id == SELECTED_POLICY
    )
    assert evaluation.eligibility == "BLOCKED"
    assert "selector_calibration_drifted" in evaluation.hard_gate_failures
    assert selected.kernel_decision.selected_policy_id != SELECTED_POLICY
    assert selected.kernel_decision.execution_authorized is False


def test_absent_source_preserves_legacy_authorization(tmp_path):
    _, selected, _ = select(tmp_path, None)
    assert selected.kernel_decision.selected_policy_id == SELECTED_POLICY
    assert selected.kernel_decision.activation_mode == "AUTHORIZED_PROJECT_SCOPED"
    assert all(
        item.calibration_state == "UNMONITORED"
        for item in selected.kernel_decision.calibration_controls
    )


def test_control_surface_replays_without_live_source(tmp_path):
    source_receipt = calibration_receipt("CALIBRATED")
    runtime, selected, _ = select(tmp_path, CalibrationSource(source_receipt))
    assert runtime.verify_replay()["valid"] is True

    restarted = ContextualOrganizationPolicyRuntime(
        runtime_id="calibration-controlled-selector",
        project_scope=PROJECT_SCOPE,
        registry=_registry(),
        provider_router=ProviderTaskRouter([StaticOrganizationProvider()]),
        workspace_root=tmp_path,
    )
    recovered = restarted.selection(selected.selection_id)
    assert restarted.verify_replay()["valid"] is True
    assert recovered.receipt_hash == selected.receipt_hash
    assert recovered.kernel_decision.calibration_controls == selected.kernel_decision.calibration_controls


def test_invalid_stale_or_wrong_scope_source_fails_before_provider(tmp_path):
    invalid = CalibrationSource(calibration_receipt("CALIBRATED"), replay_valid=False)
    with pytest.raises(ValueError, match="source_replay_invalid"):
        select(tmp_path / "invalid", invalid)

    stale = CalibrationSource(
        calibration_receipt("CALIBRATED"),
        latest_hash_override=digest("stale-receipt"),
    )
    with pytest.raises(ValueError, match="latest_receipt_mismatch"):
        select(tmp_path / "stale", stale)

    wrong_scope = CalibrationSource(
        calibration_receipt("CALIBRATED", project_scope="project://wrong-scope")
    )
    with pytest.raises(ValueError, match="receipt_scope_mismatch"):
        select(tmp_path / "wrong-scope", wrong_scope)


def test_control_contract_rejects_bare_state_mutation():
    from agentos_kernel import ContextualPolicyCalibrationControl

    control = ContextualPolicyCalibrationControl.from_receipt(calibration_receipt("CALIBRATED"))
    with pytest.raises(ValueError, match="state_mode_mismatch"):
        replace(control, calibration_state="DRIFTED", control_hash=digest("mutated-control"))


def test_hash_consistent_receipt_cannot_downgrade_mechanical_drift(tmp_path):
    drifted = calibration_receipt("DRIFTED")
    forged_decision = SelectorCalibrationDecision.create(
        decision_id="forged-calibrated-decision",
        final_state="CALIBRATED",
        prediction_trusted=True,
        recalibration_required=False,
        action="KEEP_CURRENT_CALIBRATION",
        reason="forged_downgrade",
        kernel_authorization_ref="kernel://calibration/forged",
        profile_hash=drifted.profile.profile_hash,
        provider_judgment_hash=drifted.provider_judgment.judgment_hash,
        threshold_hash=drifted.profile.threshold_hash,
    )
    forged = SelectorCalibrationReceipt.create(
        calibration_id="calibration-forged-downgrade",
        runtime_id=drifted.runtime_id,
        observation=drifted.observation,
        profile=drifted.profile,
        provider_judgment=drifted.provider_judgment,
        kernel_decision=forged_decision,
        supersedes_receipt_hash=drifted.supersedes_receipt_hash,
        created_at=drifted.created_at,
    )
    with pytest.raises(ValueError, match="state_transition_invalid"):
        select(tmp_path, CalibrationSource(forged))
