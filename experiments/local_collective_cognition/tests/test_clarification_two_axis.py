from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_action_credit_contracts import FINGERPRINT_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_two_axis_calibration import build_two_axis_calibration, validate_two_axis_calibration  # noqa: E402
from local_collective_cognition.clarification_two_axis_contracts import TWO_AXIS_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_two_axis_holdout import build_two_axis_holdout_artifact, validate_two_axis_holdout_artifact  # noqa: E402
from local_collective_cognition.clarification_two_axis_runtime import CATEGORY_LANE, LANES, ClarificationTwoAxisRuntime, validate_two_axis_run  # noqa: E402
from local_collective_cognition.post_experiment_analysis import build_two_axis_analysis  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class FixtureAdapter:
    def __init__(self, lane, oracle):
        self.lane = lane
        self.oracle = oracle
        task_kind = FINGERPRINT_TASK_KIND if lane == CATEGORY_LANE else TWO_AXIS_TASK_KIND
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + lane.lower(),
            model_id="fixture",
            task_kinds=(task_kind,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        items = []
        for case in task.inputs["public_cases"]:
            truth = self.oracle[case["blind_case_id"]]
            if self.lane == CATEGORY_LANE:
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "fingerprint": "OPEN_RIVALS",
                    "preferred_direct_answer": "ANSWER_A",
                    "evidence_basis": "Fixture category.",
                    "counterfactual": "Request wording may change the category.",
                })
            else:
                selection = {"ANSWER_A": "CANDIDATE_A", "ANSWER_B": "CANDIDATE_B", "NONE": "NONE"}[truth["object_selection"]]
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "request_object_quote": case["public_prompt"],
                    "object_selection": selection,
                    "assessment_status": "RESOLVED",
                    "decisive_quote": case["public_prompt"] if selection != "NONE" else "NONE",
                    "selection_basis": "Fixture object selection.",
                    "status_basis": "The public wording is sufficient.",
                })
        return {
            "result": {
                "batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0],
                "assessments": items,
                "evidence_refs": list(task.allowed_evidence),
            },
            "usage": {"input_tokens": 50, "output_tokens": 35},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_two_axis_fixture_passes_without_action_authority():
    corpus = build_two_axis_holdout_artifact()
    validate_two_axis_holdout_artifact(corpus)
    oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationTwoAxisRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-v09",
        adapters={lane: FixtureAdapter(lane, oracle) for lane in LANES},
    )
    validate_two_axis_run(run, corpus_artifact=corpus)
    calibration = build_two_axis_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_two_axis_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    assert calibration["candidate_state"] == "TWO_AXIS_REPRESENTATION_CANDIDATE"
    assert calibration["arm_metrics"]["CATEGORY_FINGERPRINT"]["accuracy"] == 0.5
    assert calibration["arm_metrics"]["SHUFFLED_TWO_AXIS"]["accuracy"] == 1.0
    assert calibration["paired_visibility_advantage"] == 0
    assert calibration["action_credit_authority"] is False
    analysis = build_two_axis_analysis(calibration, candidate_run=run)
    assert analysis["source_calibration_hash"] == calibration["artifact_hash"]
    assert analysis["receipt_diagnostics"]["shuffled_error_count"] == 0


def test_shuffled_layout_hides_true_counterparts_with_equal_coverage():
    corpus = build_two_axis_holdout_artifact()
    oracle = corpus["private_oracle"]["bindings"]
    for layout in ("PAIRED", "SHUFFLED"):
        ids = [case["blind_case_id"] for batch in corpus["public_surfaces"][layout]["batches"] for case in batch["public_cases"]]
        assert len(ids) == 24
        assert set(ids) == set(oracle)
    for batch in corpus["public_surfaces"]["SHUFFLED"]["batches"]:
        pair_tokens = {case["pair_token"] for case in batch["public_cases"]}
        assert len(pair_tokens) == 2


def test_two_axis_run_rejects_prediction_tamper():
    corpus = build_two_axis_holdout_artifact()
    oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationTwoAxisRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-v09-tamper",
        adapters={lane: FixtureAdapter(lane, oracle) for lane in LANES},
    )
    tampered = deepcopy(run)
    tampered["predictions"][0]["shuffled_derived_category"] = "UNCERTAIN"
    tampered["candidate_run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "candidate_run_hash"})
    with pytest.raises(ValueError, match="predictions_invalid"):
        validate_two_axis_run(tampered, corpus_artifact=corpus)
