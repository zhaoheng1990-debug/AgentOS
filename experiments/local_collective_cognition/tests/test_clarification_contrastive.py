from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_action_credit_contracts import FINGERPRINT_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_contrastive_calibration import build_contrastive_calibration, validate_contrastive_calibration  # noqa: E402
from local_collective_cognition.clarification_contrastive_contracts import SELECTION_TASK_KIND, validate_selection  # noqa: E402
from local_collective_cognition.clarification_contrastive_holdout import build_contrastive_holdout_artifact, validate_contrastive_holdout_artifact  # noqa: E402
from local_collective_cognition.clarification_contrastive_runtime import CATEGORY_LANE, SELECTION_LANE, ClarificationContrastiveRuntime, validate_contrastive_run  # noqa: E402
from local_collective_cognition.post_experiment_analysis import build_contrastive_analysis  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class FixtureAdapter:
    def __init__(self, lane, oracle):
        self.lane = lane
        self.oracle = oracle
        task_kind = FINGERPRINT_TASK_KIND if lane == CATEGORY_LANE else SELECTION_TASK_KIND
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + lane.lower(),
            model_id="fixture",
            task_kinds=(task_kind,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        items = []
        for case in task.inputs["public_cases"]:
            binding = self.oracle[case["blind_case_id"]]
            if self.lane == CATEGORY_LANE:
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "fingerprint": "OPEN_RIVALS",
                    "preferred_direct_answer": "ANSWER_A",
                    "evidence_basis": "Fixture category.",
                    "counterfactual": "A request edit may change the relation.",
                })
            else:
                selected = binding["selected_candidate"]
                explicit = {"ANSWER_A": "CANDIDATE_A", "ANSWER_B": "CANDIDATE_B", "NEITHER": "NEITHER"}[selected]
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "request_object_quote": case["public_prompt"],
                    "explicit_selection": explicit,
                    "decisive_quote": case["public_prompt"] if explicit != "NEITHER" else "NONE",
                    "contrastive_explanation": "The matched request changes explicit selection.",
                })
        return {
            "result": {
                "batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0],
                "assessments": items,
                "evidence_refs": list(task.allowed_evidence),
            },
            "usage": {"input_tokens": 40, "output_tokens": 30},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_contrastive_representation_passes_fixture_gate_without_action_authority():
    corpus = build_contrastive_holdout_artifact()
    validate_contrastive_holdout_artifact(corpus)
    oracle = corpus["private_oracle"]["bindings"]
    adapters = {lane: FixtureAdapter(lane, oracle) for lane in (CATEGORY_LANE, SELECTION_LANE)}
    run = ClarificationContrastiveRuntime(corpus_artifact=corpus).evaluate(experiment_id="fixture-v08", adapters=adapters)
    validate_contrastive_run(run, corpus_artifact=corpus)
    calibration = build_contrastive_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_contrastive_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    assert calibration["candidate_state"] == "CONTRASTIVE_REPRESENTATION_CANDIDATE"
    assert calibration["arm_metrics"]["CATEGORY_FINGERPRINT"]["accuracy"] == 0.5
    assert calibration["arm_metrics"]["REQUEST_SELECTION"]["accuracy"] == 1.0
    assert calibration["action_credit_authority"] is False
    analysis = build_contrastive_analysis(calibration, candidate_run=run, corpus_artifact=corpus)
    assert analysis["source_calibration_hash"] == calibration["artifact_hash"]
    assert analysis["changes_frozen_gate_or_candidate_state"] is False
    assert analysis["receipt_diagnostics"]["fixed_direction_accuracy"] == 1.0


def test_selection_contract_rejects_unbound_quote():
    corpus = build_contrastive_holdout_artifact()
    batch = corpus["public_surface"]["batches"][0]
    payload = {
        "batch_id": batch["batch_id"],
        "assessments": [{
            "blind_case_id": case["blind_case_id"],
            "request_object_quote": "text absent from prompt",
            "explicit_selection": "NEITHER",
            "decisive_quote": "NONE",
            "contrastive_explanation": "Fixture.",
        } for case in batch["public_cases"]],
        "evidence_refs": [*corpus["evidence_refs"], f"artifact://{corpus['artifact_hash']}"],
    }
    with pytest.raises(ValueError, match="request_quote_unbound"):
        validate_selection(payload, batch_id=batch["batch_id"], public_cases=batch["public_cases"], evidence_refs=payload["evidence_refs"])


def test_contrastive_run_rejects_prediction_tamper():
    corpus = build_contrastive_holdout_artifact()
    oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationContrastiveRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-v08-tamper",
        adapters={lane: FixtureAdapter(lane, oracle) for lane in (CATEGORY_LANE, SELECTION_LANE)},
    )
    tampered = deepcopy(run)
    tampered["predictions"][0]["selection_derived_category"] = "UNCERTAIN"
    tampered["candidate_run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "candidate_run_hash"})
    with pytest.raises(ValueError, match="predictions_invalid"):
        validate_contrastive_run(tampered, corpus_artifact=corpus)
