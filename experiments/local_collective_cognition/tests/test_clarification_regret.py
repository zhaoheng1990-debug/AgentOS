from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_regret_calibration import build_clarification_regret_calibration, validate_clarification_regret_calibration  # noqa: E402
from local_collective_cognition.clarification_regret_contracts import DIRECT_TASK_KIND, REGRET_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_regret_fusion import DIRECT, LANES, REGRET_1, REGRET_2, REGRET_3  # noqa: E402
from local_collective_cognition.clarification_regret_holdout import CASES, build_clarification_regret_artifact, validate_clarification_regret_artifact, validate_clarification_regret_spec  # noqa: E402
from local_collective_cognition.clarification_regret_runtime import ClarificationRegretRuntime, validate_clarification_regret_run  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class FixtureAdapter:
    def __init__(self, lane, *, oracle, noisy_ids=()):
        self.lane = lane
        self.oracle = oracle
        self.noisy_ids = set(noisy_ids)
        task_kind = DIRECT_TASK_KIND if lane == DIRECT else REGRET_TASK_KIND
        self.profile = ProviderCapabilityProfile(
            provider_id=f"fixture-{lane.lower()}", model_id="fixture",
            task_kinds=(task_kind,), max_timeout_seconds=180,
        )

    def invoke(self, task):
        assert task.inputs["private_intent_oracle"] == "WITHHELD_AND_INACCESSIBLE"
        assert "private_oracle" not in task.inputs
        assessments = []
        for case in task.inputs["public_cases"]:
            blind_id = case["blind_case_id"]
            binding = self.oracle[blind_id]
            if self.lane == DIRECT:
                assessments.append({"blind_case_id": blind_id, "action": "ASK", "evidence_basis": "Fixture direct.", "confidence": 0.8})
            else:
                answer = binding["valid_direct_actions"][0]
                probability = 0.5 if binding["category"] == "OPEN" or blind_id in self.noisy_ids else 0.05
                assessments.append({
                    "blind_case_id": blind_id,
                    "preferred_direct_answer": answer,
                    "probability_preferred_wrong": probability,
                    "evidence_basis": "Fixture regret.",
                    "counterfactual": "A changed request would alter the estimate.",
                    "confidence": 0.8,
                })
        return {
            "result": {"batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0], "assessments": assessments, "evidence_refs": list(task.allowed_evidence)},
            "usage": {"input_tokens": 30, "output_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def _run(corpus):
    oracle = corpus["private_oracle"]["bindings"]
    controls = [blind_id for blind_id, item in oracle.items() if item["category"] != "OPEN"]
    adapters = {
        DIRECT: FixtureAdapter(DIRECT, oracle=oracle),
        REGRET_1: FixtureAdapter(REGRET_1, oracle=oracle, noisy_ids=controls[:4]),
        REGRET_2: FixtureAdapter(REGRET_2, oracle=oracle),
        REGRET_3: FixtureAdapter(REGRET_3, oracle=oracle),
    }
    return ClarificationRegretRuntime(corpus_artifact=corpus).evaluate(experiment_id="fixture-clarification-regret", adapters=adapters)


def test_formal_holdout_is_balanced_hash_bound_and_private():
    validate_clarification_regret_spec()
    corpus = build_clarification_regret_artifact()
    validate_clarification_regret_artifact(corpus)
    assert len(CASES) == 20
    assert len(corpus["public_surface"]["batches"]) == 10
    assert corpus["public_surface"]["oracle_exposed"] is False
    assert corpus["private_oracle"]["revealed_to_provider"] is False


def test_runtime_derives_actions_without_oracle_exposure():
    corpus = build_clarification_regret_artifact()
    run = _run(corpus)
    validate_clarification_regret_run(run, corpus_artifact=corpus)
    records = run["fusion"]["records"]
    oracle = corpus["private_oracle"]["bindings"]
    assert all(item["single_regret_action"] == "ASK" for item in records if oracle[item["blind_case_id"]]["category"] == "OPEN")
    assert run["fusion"]["arm_accounting"]["SINGLE_REGRET"]["attributed_provider_calls"] == 10
    assert run["fusion"]["arm_accounting"]["THREE_PASS_REGRET"]["attributed_provider_calls"] == 30


def test_formal_calibration_accepts_only_three_pass_fixture():
    corpus = build_clarification_regret_artifact()
    run = _run(corpus)
    calibration = build_clarification_regret_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_clarification_regret_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    assert calibration["candidate_state"] == "THREE_PASS_REGRET_CANDIDATE"
    assert calibration["arm_metrics"]["THREE_PASS_REGRET"]["mean_utility"] == 0.9
    assert calibration["three_pass_regret_gate_results"]["utility_gain_vs_single"] is True
    tampered = deepcopy(calibration)
    tampered["arm_metrics"]["THREE_PASS_REGRET"]["mean_utility"] = 1.0
    tampered["artifact_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "artifact_hash"})
    with pytest.raises(ValueError, match="calibration_invalid"):
        validate_clarification_regret_calibration(tampered, corpus_artifact=corpus, candidate_run=run)


def test_runtime_rejects_fusion_tamper():
    corpus = build_clarification_regret_artifact()
    run = _run(corpus)
    tampered = deepcopy(run)
    tampered["fusion"]["records"][0]["three_pass_regret_action"] = "ANSWER_B"
    tampered["candidate_run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "candidate_run_hash"})
    with pytest.raises(ValueError, match="fusion_invalid"):
        validate_clarification_regret_run(tampered, corpus_artifact=corpus)
