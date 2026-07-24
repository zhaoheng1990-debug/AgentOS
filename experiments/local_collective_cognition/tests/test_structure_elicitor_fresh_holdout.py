from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_elicitor_calibration_eval import (  # noqa: E402
    CRITERIA, build_calibration_report, build_profile,
)
from local_collective_cognition.structure_elicitor_calibration_holdout import CASES as CALIBRATION_CASES  # noqa: E402
from local_collective_cognition.structure_elicitor_calibration_runtime import StructureElicitorCalibrationRuntime  # noqa: E402
from local_collective_cognition.structure_elicitor_fresh_eval import (  # noqa: E402
    build_fresh_report, calibration_route, validate_calibration_artifact, validate_fresh_report,
)
from local_collective_cognition.structure_elicitor_fresh_holdout import (  # noqa: E402
    CASES, TRUTH_COMMITMENT, public_inputs,
)


def _packet(case):
    return (
        f"RIVAL_A: The output denotes {case.rival_a_terms[0]}, with a defined counting object. | "
        f"RIVAL_B: The output instead denotes {case.rival_b_terms[0]}, with another object boundary. | "
        f"CONTRAST: The decisive distinction is {case.rival_a_terms[0]} versus "
        f"{case.rival_b_terms[0]}. | QUESTION: Should the output represent "
        f"{case.question_terms[0]} or {case.question_terms[1]}?"
    )


class FixtureAdapter:
    def __init__(self, model_id):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id, model_id=model_id,
            task_kinds=("pilot_object_structure_expansion",), max_timeout_seconds=900,
        )

    def invoke(self, task):
        item_id = task.inputs["benchmark_item_ids"][0]
        case = next(item for item in CASES if item.item_id == item_id)
        return {
            "result": {"item_1_packet": _packet(case)},
            "usage": {"provider_calls": 1, "input_tokens": 100, "output_tokens": 50},
            "provenance_refs": list(task.allowed_evidence),
        }


def _profile(model_id, score, *, scope="CALIBRATION_ONLY", successful=4, calls=4):
    criteria = {key: index < round(score * len(CRITERIA)) for index, key in enumerate(CRITERIA)}
    outcomes = []
    for index in range(4):
        committed = {
            "model_id": model_id,
            "provider_status": "COMPLETED" if index < successful else "PROVIDER_UNAVAILABLE",
            "criteria": criteria if index < successful else {key: False for key in CRITERIA},
            "quality_score": sum(criteria.values()) / len(CRITERIA) if index < successful else 0.0,
            "provider_calls": calls // 4 if calls == 4 else 2,
            "input_tokens": 10,
            "output_tokens": 10,
            "evaluation_scope": scope,
        }
        outcomes.append({**committed, "outcome_hash": hash_payload(committed)})
    return build_profile(model_id=model_id, provider_id="p-" + model_id, outcomes=tuple(outcomes))


def _calibration_artifact():
    profiles = (
        _profile("deepseek-r1:32b", 0.6),
        _profile("llama-3.2-1b-instruct", 0.0, successful=0, calls=8),
        _profile("qwen2.5-1.5b-instruct", 0.4),
        _profile("gemma-2-2b-it", 0.6),
    )
    report = build_calibration_report(
        experiment_id="calibration-fixture", profiles=profiles,
        strong_model_id="deepseek-r1:32b", truth_commitment="a" * 64,
    )
    commitment = {"experiment_id": "calibration-fixture", "report": report, "model_runs": []}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _fresh_profiles(selected_score=0.8, comparator_score=0.6):
    return (
        _profile("gemma-2-2b-it", selected_score, scope="FRESH_HOLDOUT"),
        _profile("qwen2.5-1.5b-instruct", comparator_score, scope="FRESH_HOLDOUT"),
        _profile("deepseek-r1:32b", 1.0, scope="FRESH_HOLDOUT"),
    )


def test_fresh_truth_is_hidden_and_objects_are_unseen():
    public = public_inputs()
    assert len(public) == 4 and len(TRUTH_COMMITMENT) == 64
    assert {item.item_id for item in CASES}.isdisjoint(item.item_id for item in CALIBRATION_CASES)
    assert {item.prompt for item in CASES}.isdisjoint(item.prompt for item in CALIBRATION_CASES)
    assert "rival_a_terms" not in str(public) and "truth" not in str(public).lower()


def test_fresh_runtime_reuses_frozen_harness_with_explicit_scope():
    runtime = StructureElicitorCalibrationRuntime(
        cases=CASES, evaluation_scope="FRESH_HOLDOUT",
    )
    run = runtime.evaluate_model(experiment_id="fresh-fixture", adapter=FixtureAdapter("gemma"))
    assert run["profile"]["scope"] == "FRESH_HOLDOUT"
    assert run["profile"]["mean_quality_score"] == 1.0
    assert all(item["outcome"]["evaluation_scope"] == "FRESH_HOLDOUT" for item in run["trials"])


def test_fresh_report_binds_calibration_route_and_exclusion():
    calibration = _calibration_artifact()
    assert calibration_route(calibration)[:3] == (
        "gemma-2-2b-it", "qwen2.5-1.5b-instruct", "deepseek-r1:32b",
    )
    report = build_fresh_report(
        experiment_id="fresh-fixture", calibration_artifact=calibration,
        profiles=_fresh_profiles(), truth_commitment=TRUTH_COMMITMENT,
    )
    validate_fresh_report(report, calibration_artifact=calibration)
    assert report["selection_replicated"] is True
    assert report["candidate_state"] == "PROJECT_CAPABILITY_EVIDENCE_CANDIDATE"
    assert report["small_model_routing_regret"] == 0
    assert report["selection_authority"] is False and report["retention_authority"] is False
    assert report["excluded_models"] == [{
        "model_id": "llama-3.2-1b-instruct",
        "reason": "CALIBRATION_TRANSPORT_FAILURE_BUDGET_BLOCK",
        "calibration_profile_hash": calibration["report"]["profiles"][1]["profile_hash"],
        "calibration_provider_calls": 8,
        "calibration_tokens": 80,
    }]


def test_fresh_report_rejects_nonreplicated_calibration_route():
    report = build_fresh_report(
        experiment_id="fresh-fixture", calibration_artifact=_calibration_artifact(),
        profiles=_fresh_profiles(selected_score=0.4, comparator_score=0.8),
        truth_commitment=TRUTH_COMMITMENT,
    )
    assert report["selection_replicated"] is False
    assert report["candidate_state"] == "CALIBRATION_ROUTE_NOT_REPLICATED"
    assert report["small_model_routing_regret"] > 0


def test_calibration_artifact_tamper_fails_closed():
    artifact = _calibration_artifact()
    artifact["report"]["selected_small_model_id"] = "tampered"
    with pytest.raises(ValueError, match="artifact_hash_invalid"):
        validate_calibration_artifact(artifact)


def test_rehashed_fresh_report_semantic_tamper_fails_closed():
    calibration = _calibration_artifact()
    report = build_fresh_report(
        experiment_id="fresh-fixture", calibration_artifact=calibration,
        profiles=_fresh_profiles(), truth_commitment=TRUTH_COMMITMENT,
    )
    report["selection_replicated"] = False
    committed = {key: value for key, value in report.items() if key != "report_hash"}
    report["report_hash"] = hash_payload(committed)
    with pytest.raises(ValueError, match="semantics_invalid"):
        validate_fresh_report(report, calibration_artifact=calibration)
