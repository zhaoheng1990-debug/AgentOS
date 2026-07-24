from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_two_axis_contracts import TWO_AXIS_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_warrant_calibration import build_warrant_calibration, validate_warrant_calibration  # noqa: E402
from local_collective_cognition.clarification_warrant_contracts import WARRANT_TASK_KIND, derive_warrant_decision  # noqa: E402
from local_collective_cognition.clarification_warrant_holdout import build_warrant_holdout_artifact, validate_warrant_holdout_artifact  # noqa: E402
from local_collective_cognition.clarification_warrant_runtime import BASELINE_LANE, LANES, ClarificationWarrantRuntime, validate_warrant_run  # noqa: E402
from local_collective_cognition.post_experiment_analysis import build_warrant_analysis  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class FixtureAdapter:
    def __init__(self, lane, oracle):
        self.lane = lane
        self.oracle = oracle
        task_kind = TWO_AXIS_TASK_KIND if lane == BASELINE_LANE else WARRANT_TASK_KIND
        self.profile = ProviderCapabilityProfile(provider_id="fixture-" + lane.lower(), model_id="fixture", task_kinds=(task_kind,), max_timeout_seconds=180)

    def invoke(self, task):
        items = []
        for case in task.inputs["public_cases"]:
            truth = self.oracle[case["blind_case_id"]]
            if self.lane == BASELINE_LANE:
                selection = truth["explicit_selection"] if truth["explicit_selection"] != "NONE" else truth["pragmatic_preference"]
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "request_object_quote": case["public_prompt"],
                    "object_selection": selection,
                    "assessment_status": "RESOLVED",
                    "decisive_quote": case["public_prompt"],
                    "selection_basis": "Fixture baseline uses the strongest preference.",
                    "status_basis": "Fixture resolved.",
                })
            else:
                explicit = truth["explicit_selection"]
                hard = truth["construction"] == "EXPLICIT"
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "request_object_quote": case["public_prompt"],
                    "explicit_selection": explicit,
                    "pragmatic_preference": truth["pragmatic_preference"],
                    "assessment_status": "RESOLVED",
                    "warrant_type": "EXACT_OBJECT_MENTION" if hard else "DEFAULT_COMPATIBILITY",
                    "warrant_quote": case["public_prompt"] if hard else "NONE",
                    "preference_basis": "Fixture preference.",
                    "status_basis": "Fixture resolved.",
                })
        return {
            "result": {"batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0], "assessments": items, "evidence_refs": list(task.allowed_evidence)},
            "usage": {"input_tokens": 55, "output_tokens": 40},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_warrant_fixture_preserves_preference_without_hard_authority():
    corpus = build_warrant_holdout_artifact()
    validate_warrant_holdout_artifact(corpus)
    oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationWarrantRuntime(corpus_artifact=corpus).evaluate(experiment_id="fixture-v010", adapters={lane: FixtureAdapter(lane, oracle) for lane in LANES})
    validate_warrant_run(run, corpus_artifact=corpus)
    calibration = build_warrant_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_warrant_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    assert calibration["candidate_state"] == "EXPLICIT_SELECTION_WARRANT_CANDIDATE"
    assert calibration["arm_metrics"]["BASELINE_TWO_AXIS"]["accuracy"] == 0.5
    assert calibration["arm_metrics"]["EXPLICIT_WARRANT"]["accuracy"] == 1.0
    assert calibration["arm_metrics"]["EXPLICIT_WARRANT"]["pragmatic_preference_alignment"] == 1.0
    assert calibration["action_credit_authority"] is False
    analysis = build_warrant_analysis(calibration, candidate_run=run)
    assert analysis["source_calibration_hash"] == calibration["artifact_hash"]
    assert analysis["receipt_diagnostics"]["baseline_failed_batches"] == 0


def test_soft_warrant_is_mechanically_downgraded():
    assert derive_warrant_decision("CANDIDATE_A", "RESOLVED", "DEFAULT_COMPATIBILITY") == ("OPEN_RIVALS", "NONE", True)
    assert derive_warrant_decision("CANDIDATE_B", "RESOLVED", "EXACT_OBJECT_MENTION") == ("PROMPT_FIXED", "CANDIDATE_B", False)


def test_warrant_run_rejects_prediction_tamper():
    corpus = build_warrant_holdout_artifact()
    oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationWarrantRuntime(corpus_artifact=corpus).evaluate(experiment_id="fixture-v010-tamper", adapters={lane: FixtureAdapter(lane, oracle) for lane in LANES})
    tampered = deepcopy(run)
    tampered["predictions"][0]["warrant_derived_category"] = "UNCERTAIN"
    tampered["candidate_run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "candidate_run_hash"})
    with pytest.raises(ValueError, match="predictions_invalid"):
        validate_warrant_run(tampered, corpus_artifact=corpus)
