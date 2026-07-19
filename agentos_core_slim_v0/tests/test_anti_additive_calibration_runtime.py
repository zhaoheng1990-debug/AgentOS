import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
)
from agentos_runtime import AntiAdditiveCalibrationRuntime, AntiAdditiveMethodologyRuntime


EVIDENCE = ("evidence://anti-additive-prediction", "evidence://anti-additive-outcome")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class PredictionProvider:
    profile = ProviderCapabilityProfile(
        provider_id="anti-additive-predictor",
        model_id="fixture-predictor",
        task_kinds=("anti_additive_methodology_assessment",),
        max_timeout_seconds=120,
    )

    def invoke(self, task):
        return {
            "result": {
                "current_object_adequacy": "UNDERPOWERED",
                "trigger_assessments": [
                    {
                        "trigger_id": trigger_id,
                        "triggered": trigger_id == "PATCH_PRESERVES_OBJECT_WITHOUT_CBIT_GAIN",
                        "rationale": f"fixture {trigger_id}",
                        "evidence_refs": list(EVIDENCE),
                    }
                    for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS
                ],
                "expected_effective_cbit_gain": 0.80,
                "complexity_cost": 0.20,
                "object_upgrade_gain": 0.70,
                "abstraction_cost": 0.20,
                "uncertainty": 0.15,
                "recommended_action": "UPGRADE_OBJECT",
                "rationale": "bounded object lift",
                "evidence_refs": list(EVIDENCE),
            },
            "usage": {},
            "provenance_refs": list(EVIDENCE),
        }


def candidate(index):
    return AntiAdditiveChangeCandidate.create(
        audit_id=f"audit-calibration-{index}",
        candidate_id=f"candidate-calibration-{index}",
        project_scope="project://anti-additive-calibration",
        change_kind="MODULE",
        target_type="ProblemStructure",
        current_object_ref="object://proxy",
        proposed_object_ref="object://ontology",
        current_object_level="PROXY",
        proposed_object_level="ONTOLOGY_OBJECT",
        prior_failure_count=2,
        prior_patch_count=2,
        candidate_payload_hash=digest(f"candidate-payload-{index}"),
        evidence_refs=EVIDENCE,
    )


def methodology_runtime(tmp_path, *, calibration_source=None, suffix="methodology"):
    return AntiAdditiveMethodologyRuntime(
        runtime_id=suffix,
        project_scope="project://anti-additive-calibration",
        provider_router=ProviderTaskRouter([PredictionProvider()]),
        workspace_root=tmp_path,
        calibration_source=calibration_source,
    )


def calibration_runtime(tmp_path):
    return AntiAdditiveCalibrationRuntime(
        runtime_id="calibration",
        project_scope="project://anti-additive-calibration",
        workspace_root=tmp_path,
    )


def predicted_receipt(tmp_path, index):
    return methodology_runtime(tmp_path, suffix=f"methodology-{index}").review_change(
        candidate=candidate(index),
        kernel_authorization_ref="kernel://methodology",
    )


def record(engine, receipt, index, *, observed=(0.78, 0.22, 0.68, 0.22)):
    return engine.record_outcome(
        calibration_id=f"calibration-{index}",
        observation_id=f"observation-{index}",
        methodology_receipt=receipt,
        outcome_source_hash=digest(f"outcome-source-{index}"),
        harness_receipt_hash=digest(f"harness-{index}"),
        observed_effective_cbit_gain=observed[0],
        observed_complexity_cost=observed[1],
        observed_object_upgrade_gain=observed[2],
        observed_abstraction_cost=observed[3],
        evidence_refs=EVIDENCE,
        kernel_authorization_ref="kernel://calibration",
    )


def test_two_independent_low_error_outcomes_calibrate_future_methodology_decision(tmp_path):
    engine = calibration_runtime(tmp_path)
    first = record(engine, predicted_receipt(tmp_path, 1), 1)
    second = record(engine, predicted_receipt(tmp_path, 2), 2)

    future = methodology_runtime(
        tmp_path, calibration_source=engine, suffix="methodology-controlled"
    ).review_change(
        candidate=candidate(3), kernel_authorization_ref="kernel://methodology"
    )

    assert first.decision.state == "INSUFFICIENT_HISTORY"
    assert second.decision.state == "CALIBRATED"
    assert future.decision.state == "ALLOW_BOUNDED_CHANGE"
    assert future.decision.calibration_control.control_mode == "TRUSTED"
    assert future.decision.calibration_control.calibration_receipt_hash == second.receipt_hash
    assert engine.verify_replay()["valid"] is True


def test_configured_source_without_history_allows_candidate_only_not_durable_change(tmp_path):
    engine = calibration_runtime(tmp_path)

    receipt = methodology_runtime(
        tmp_path, calibration_source=engine, suffix="methodology-no-history"
    ).review_change(candidate=candidate(1), kernel_authorization_ref="kernel://methodology")

    assert receipt.decision.state == "REQUIRE_CALIBRATED_VALIDATION"
    assert receipt.decision.allowed is False
    assert receipt.decision.candidate_only_allowed is True
    assert receipt.decision.calibration_control.calibration_state == "NO_OBSERVATION"


def test_drifted_outcomes_block_future_methodology_prediction_authority(tmp_path):
    engine = calibration_runtime(tmp_path)
    bad = (0.10, 0.80, 0.10, 0.80)
    record(engine, predicted_receipt(tmp_path, 1), 1, observed=bad)
    drifted = record(engine, predicted_receipt(tmp_path, 2), 2, observed=bad)

    future = methodology_runtime(
        tmp_path, calibration_source=engine, suffix="methodology-drifted"
    ).review_change(candidate=candidate(3), kernel_authorization_ref="kernel://methodology")

    assert drifted.decision.state == "DRIFTED"
    assert future.decision.state == "BLOCK_CALIBRATION_DRIFT"
    assert future.decision.candidate_only_allowed is False


def test_duplicate_methodology_receipt_cannot_increase_calibration_history(tmp_path):
    engine = calibration_runtime(tmp_path)
    receipt = predicted_receipt(tmp_path, 1)
    record(engine, receipt, 1)

    with pytest.raises(ValueError, match="duplicate_methodology_receipt"):
        record(engine, receipt, 2)


def test_calibration_event_tamper_breaks_replay_and_control_resolution(tmp_path):
    engine = calibration_runtime(tmp_path)
    record(engine, predicted_receipt(tmp_path, 1), 1)
    event_path = engine.public_store_path / "events.jsonl"
    event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[0])
    event["payload"]["receipt"]["profile"]["mean_absolute_cbit_error"] = 0.99
    event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    assert engine.verify_replay()["valid"] is False
    with pytest.raises(ValueError, match="calibration_source_replay_invalid"):
        methodology_runtime(
            tmp_path, calibration_source=engine, suffix="methodology-tampered"
        ).review_change(candidate=candidate(3), kernel_authorization_ref="kernel://methodology")
