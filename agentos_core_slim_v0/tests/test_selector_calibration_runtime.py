import json
import sys
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    SelectorCalibrationEvaluator,
    SelectorCalibrationThresholds,
    SelectionExecutionRequest,
)
from agentos_runtime import (  # noqa: E402
    ContextualPolicyRepository,
    SelectionFeedbackRepository,
    SelectionExecutionFeedbackReceipt,
    SelectorCalibrationRuntime,
)
from examples.selection_execution_feedback_bridge_smoke import run_smoke  # noqa: E402


PROJECT_SCOPE = "project://LIFE_COG3R"


class CalibrationProvider:
    def __init__(self, *, semantic_drift=False, inconsistent_history=False, omit_profile=False):
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-selector-calibration-provider",
            model_id="scripted-selector-calibration-model",
            task_kinds=("selector_calibration_drift_assessment",),
            max_timeout_seconds=120,
        )
        self.semantic_drift = semantic_drift
        self.inconsistent_history = inconsistent_history
        self.omit_profile = omit_profile
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        profile = task.inputs["calibration_profile"]
        insufficient = profile["mechanical_state"] == "INSUFFICIENT_HISTORY"
        state = "INSUFFICIENT_HISTORY" if insufficient else "NO_SEMANTIC_DRIFT"
        drivers = []
        action = "COLLECT_MORE" if insufficient else "KEEP_CURRENT_CALIBRATION"
        if self.semantic_drift and not insufficient:
            state = "MATERIAL_SEMANTIC_DRIFT"
            drivers = ["MODEL_CHANGE"]
            action = "REASSESS_CONTEXT_POLICY"
        if self.inconsistent_history:
            state = "NO_SEMANTIC_DRIFT" if insufficient else "INSUFFICIENT_HISTORY"
            action = "KEEP_CURRENT_CALIBRATION" if insufficient else "COLLECT_MORE"
        refs = [task.allowed_evidence[1] if self.omit_profile else task.allowed_evidence[0]]
        result = {
            "diagnostic_state": state,
            "drift_drivers": drivers,
            "recommended_action": action,
            "uncertainty": 0.2,
            "rationale": "bounded diagnosis over the exact frozen calibration profile",
            "evidence_refs": refs,
        }
        return {
            "result": result,
            "usage": {"total_tokens": 12},
            "provenance_refs": list(task.allowed_evidence),
        }


@pytest.fixture(scope="module")
def source_receipts(tmp_path_factory):
    root = tmp_path_factory.mktemp("selector-calibration-source")
    result = run_smoke(root)
    assert result["status"] == "PASS"
    return (
        ContextualPolicyRepository._receipt_from_dict(result["initial_selection"]),
        SelectionFeedbackRepository._receipt_from_dict(result["first_feedback"]),
        SelectionFeedbackRepository._receipt_from_dict(result["second_feedback"]),
        ContextualPolicyRepository._receipt_from_dict(result["downstream_selection"]),
    )


def runtime(tmp_path, provider=None, thresholds=None):
    provider = provider or CalibrationProvider()
    return SelectorCalibrationRuntime(
        runtime_id="selector-calibration-test",
        project_scope=PROJECT_SCOPE,
        provider_router=ProviderTaskRouter([provider]),
        workspace_root=tmp_path,
        thresholds=thresholds,
    ), provider


def lenient_thresholds():
    return SelectorCalibrationThresholds(
        threshold_ref="threshold://selector-calibration/lenient-fixture",
        cbit_mae_watch=0.20,
        cbit_mae_drift=0.30,
        cost_mae_watch=0.20,
        cost_mae_drift=0.30,
        absolute_bias_watch=0.20,
        absolute_bias_drift=0.30,
    )


def observe(engine, selection, feedback, index):
    return engine.observe(
        calibration_id=f"calibration-{index}",
        selection=selection,
        feedback=feedback,
        kernel_authorization_ref=f"kernel://selector-calibration/{index}",
    )


def test_two_independent_outcomes_close_calibration_and_replay(tmp_path, source_receipts):
    selection, first_feedback, second_feedback, _ = source_receipts
    engine, provider = runtime(tmp_path, thresholds=lenient_thresholds())

    first = observe(engine, selection, first_feedback, 1)
    second = observe(engine, selection, second_feedback, 2)

    assert first.kernel_decision.final_state == "INSUFFICIENT_HISTORY"
    assert first.kernel_decision.prediction_trusted is False
    assert second.kernel_decision.final_state == "CALIBRATED"
    assert second.kernel_decision.prediction_trusted is True
    assert second.profile.observation_count == 2
    assert second.profile.independent_source_count == 2
    assert second.supersedes_receipt_hash == first.receipt_hash
    assert len(provider.tasks) == 2
    assert provider.tasks[1].inputs["calibration_profile"]["profile_hash"] == second.profile.profile_hash
    assert engine.verify_replay()["valid"] is True

    restarted, _ = runtime(tmp_path, thresholds=lenient_thresholds())
    assert restarted.verify_replay()["valid"] is True
    assert restarted.receipt("calibration-2").receipt_hash == second.receipt_hash


def test_strict_prefrozen_thresholds_detect_mechanical_drift(tmp_path, source_receipts):
    selection, first_feedback, second_feedback, _ = source_receipts
    thresholds = SelectorCalibrationThresholds(
        threshold_ref="threshold://selector-calibration/strict-test",
        cbit_mae_watch=0.01,
        cbit_mae_drift=0.03,
        cost_mae_watch=0.01,
        cost_mae_drift=0.03,
        absolute_bias_watch=0.01,
        absolute_bias_drift=0.03,
    )
    engine, _ = runtime(tmp_path, thresholds=thresholds)
    observe(engine, selection, first_feedback, 1)
    second = observe(engine, selection, second_feedback, 2)

    assert second.profile.mechanical_state == "DRIFTED"
    assert second.kernel_decision.final_state == "DRIFTED"
    assert second.kernel_decision.prediction_trusted is False
    assert second.kernel_decision.action == "SUSPEND_PREDICTION_TRUST"


def test_provider_semantic_drift_can_raise_watch_but_not_fabricate_mechanical_drift(
    tmp_path, source_receipts
):
    selection, first_feedback, second_feedback, _ = source_receipts
    engine, _ = runtime(
        tmp_path,
        provider=CalibrationProvider(semantic_drift=True),
        thresholds=lenient_thresholds(),
    )
    observe(engine, selection, first_feedback, 1)
    second = observe(engine, selection, second_feedback, 2)

    assert second.profile.mechanical_state == "CALIBRATED"
    assert second.provider_judgment.diagnostic_state == "MATERIAL_SEMANTIC_DRIFT"
    assert second.kernel_decision.final_state == "WATCH"
    assert second.kernel_decision.prediction_trusted is False


def test_duplicate_feedback_and_trial_group_are_not_double_counted(tmp_path, source_receipts):
    selection, first_feedback, _, _ = source_receipts
    engine, _ = runtime(tmp_path)
    observe(engine, selection, first_feedback, 1)

    with pytest.raises(ValueError, match="duplicate_selector_calibration_feedback"):
        observe(engine, selection, first_feedback, 2)
    assert len(engine.snapshot().receipts) == 1


def test_selection_feedback_mismatch_is_blocked(tmp_path, source_receipts):
    _, first_feedback, _, downstream_selection = source_receipts
    engine, _ = runtime(tmp_path)

    with pytest.raises(ValueError, match="selection_receipt_hash_mismatch"):
        observe(engine, downstream_selection, first_feedback, 1)
    assert len(engine.snapshot().receipts) == 0


def test_request_agent_id_must_match_frozen_selection_assignment(tmp_path, source_receipts):
    selection, first_feedback, _, _ = source_receipts
    request = first_feedback.request
    forged = SelectionExecutionRequest.create(
        bridge_run_id=request.bridge_run_id,
        selection_receipt_hash=request.selection_receipt_hash,
        project_scope=request.project_scope,
        context_key=request.context_key,
        evidence_tier=request.evidence_tier,
        trial_group_id=request.trial_group_id,
        trial_id=request.trial_id,
        selected_policy_id=request.selected_policy_id,
        selected_agent_ids=("substituted-agent", *request.selected_agent_ids[1:]),
        selected_roles=request.selected_roles,
        selected_agent_binding_hash=request.selected_agent_binding_hash,
        trial_evidence_refs=request.trial_evidence_refs,
        execution_budget=request.execution_budget,
        kernel_execution_authorization_ref=request.kernel_execution_authorization_ref,
    )
    forged_feedback = SelectionExecutionFeedbackReceipt.create(
        request=forged,
        execution_bundle=first_feedback.execution_bundle,
        admitted_records=first_feedback.admitted_records,
        matched_evidence=first_feedback.matched_evidence,
    )
    engine, _ = runtime(tmp_path)

    with pytest.raises(ValueError, match="assignment_identity_mismatch"):
        observe(engine, selection, forged_feedback, 1)


def test_provider_cannot_omit_profile_receipt_or_misstate_history(tmp_path, source_receipts):
    selection, first_feedback, _, _ = source_receipts
    missing, _ = runtime(tmp_path / "missing", provider=CalibrationProvider(omit_profile=True))
    with pytest.raises(ValueError, match="provider_evidence_invalid"):
        observe(missing, selection, first_feedback, 1)

    inconsistent, _ = runtime(
        tmp_path / "inconsistent", provider=CalibrationProvider(inconsistent_history=True)
    )
    with pytest.raises(ValueError, match="provider_history_state_inconsistent"):
        observe(inconsistent, selection, first_feedback, 1)


def test_evaluator_forbids_cross_context_pooling(tmp_path, source_receipts):
    selection, first_feedback, second_feedback, _ = source_receipts
    engine, _ = runtime(tmp_path)
    first = engine._adapter.build(observation_id="observation-one", selection=selection, feedback=first_feedback)
    second = engine._adapter.build(observation_id="observation-two", selection=selection, feedback=second_feedback)
    payload = second.as_dict()
    payload.pop("observation_hash")
    payload["context_key"] = "ctx-other"
    payload["evidence_refs"] = tuple(payload["evidence_refs"])
    changed = type(second).create(**payload)

    with pytest.raises(ValueError, match="cross_scope_pooling_forbidden"):
        SelectorCalibrationEvaluator().evaluate(
            profile_id="profile-cross-context",
            observations=(first, changed),
            thresholds=engine.thresholds,
        )


def test_revision_history_uses_event_order_and_freezes_thresholds(tmp_path, source_receipts):
    selection, first_feedback, second_feedback, _ = source_receipts
    engine, _ = runtime(tmp_path / "ordered", thresholds=lenient_thresholds())
    first = engine.observe(
        calibration_id="calibration-z",
        selection=selection,
        feedback=first_feedback,
        kernel_authorization_ref="kernel://selector-calibration/z",
    )
    second = engine.observe(
        calibration_id="calibration-a",
        selection=selection,
        feedback=second_feedback,
        kernel_authorization_ref="kernel://selector-calibration/a",
    )
    assert second.profile.observation_hashes == (
        first.observation.observation_hash,
        second.observation.observation_hash,
    )
    restarted, _ = runtime(tmp_path / "ordered", thresholds=lenient_thresholds())
    assert restarted.verify_replay()["valid"] is True

    initial, _ = runtime(tmp_path / "threshold-change")
    observe(initial, selection, first_feedback, 1)
    changed, provider = runtime(tmp_path / "threshold-change", thresholds=lenient_thresholds())
    with pytest.raises(ValueError, match="lineage_threshold_change_forbidden"):
        observe(changed, selection, second_feedback, 2)
    assert len(provider.tasks) == 0


def test_event_tamper_blocks_restart(tmp_path, source_receipts):
    selection, first_feedback, _, _ = source_receipts
    engine, _ = runtime(tmp_path)
    observe(engine, selection, first_feedback, 1)
    ledger = engine.public_store_path / "events.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[-1])
    event["payload"]["receipt"]["observation"]["observed_cbit_gain"] = 0.0
    lines[-1] = json.dumps(event, sort_keys=True)
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="selector_calibration_replay_invalid"):
        runtime(tmp_path)
