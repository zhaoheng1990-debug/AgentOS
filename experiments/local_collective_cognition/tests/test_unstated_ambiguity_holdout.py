from pathlib import Path
import json
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.ambiguity_discovery_contracts import (  # noqa: E402
    TASK_KIND, discovery_schema, state_order, validate_discovery_payload,
)
from local_collective_cognition.ambiguity_discovery_adapters import ambiguity_discovery_messages  # noqa: E402
from local_collective_cognition.ambiguity_discovery_eval import (  # noqa: E402
    build_discovery_report, validate_discovery_report,
)
from local_collective_cognition.ambiguity_discovery_runtime import AmbiguityDiscoveryRuntime  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.unstated_ambiguity_holdout import (  # noqa: E402
    CASES, EVIDENCE_REFS, HOLDOUT_SPEC, LEAKAGE_TERMS, NULL, POSITIVE, validate_holdout_spec,
)


class FixtureDiscoveryAdapter:
    def __init__(self, model_id="small-a"):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture", model_id=model_id, task_kinds=(TASK_KIND,),
            max_timeout_seconds=120,
        )
        self.seen_inputs = []

    def invoke(self, task):
        self.seen_inputs.append(task.inputs)
        item_id = task.inputs["public_task"]["item_id"]
        positive = int(item_id[1:]) % 2 == 1
        payload = {
            "item_id": item_id,
            "discovery_state": POSITIVE if positive else NULL,
            "rival_a": "signed or object A" if positive else "",
            "rival_b": "magnitude or object B" if positive else "",
            "decisive_contrast": "requested output object" if positive else "",
            "discriminating_question": "Which output object is intended?" if positive else "",
            "confidence": 0.9, "evidence_refs": list(EVIDENCE_REFS),
        }
        return {"result": payload, "usage": {"input_tokens": 10, "output_tokens": 10},
                "provenance_refs": list(task.allowed_evidence)}


class IncompletePacketAdapter(FixtureDiscoveryAdapter):
    def invoke(self, task):
        result = super().invoke(task)
        result["result"]["discovery_state"] = POSITIVE
        result["result"]["discriminating_question"] = "incomplete without question mark"
        return result


def _calibration_artifact():
    def profile(model_id, score):
        commitment = {
            "model_id": model_id, "successful_provider_trials": 4, "independent_trials": 4,
            "mean_quality_score": score, "total_tokens": 100, "total_provider_calls": 4,
        }
        return {**commitment, "profile_hash": hash_payload(commitment)}
    profiles = [profile("small-a", 0.6), profile("small-b", 0.5), profile("strong", 0.7)]
    report_commitment = {
        "profiles": profiles, "selected_small_model_id": "small-a", "strong_model_id": "strong",
        "selection_authority": False, "fresh_holdout_required": True,
    }
    report = {**report_commitment, "report_hash": hash_payload(report_commitment)}
    commitment = {"report": report}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _clone_profile(profile, model_id):
    commitment = {key: value for key, value in profile.items() if key not in {"profile_hash", "model_id"}}
    commitment["model_id"] = model_id
    return {**commitment, "profile_hash": hash_payload(commitment)}


def test_holdout_is_balanced_paired_and_contains_no_ambiguity_leak():
    validate_holdout_spec()
    assert HOLDOUT_SPEC["positive_count"] == HOLDOUT_SPEC["null_count"] == 4
    assert len({case.pair_id for case in CASES}) == 4
    assert all(case.expected_state not in str(case.public_input()) for case in CASES)
    assert not any(term in case.prompt.lower() for case in CASES for term in LEAKAGE_TERMS)


def test_discovery_contract_blocks_spurious_structure_on_null_state():
    payload = {
        "item_id": "U02", "discovery_state": NULL,
        "rival_a": "", "rival_b": "", "decisive_contrast": "",
        "discriminating_question": "", "confidence": 0.8,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    validate_discovery_payload(payload, item_id="U02")
    payload["rival_a"] = "spurious rival"
    with pytest.raises(ValueError, match="null_packet_not_empty"):
        validate_discovery_payload(payload, item_id="U02")


def test_state_menu_is_counterbalanced_without_concrete_confidence_template():
    first_states = [discovery_schema(case.item_id)["properties"]["discovery_state"]["enum"][0]
                    for case in CASES]
    assert set(first_states) == {POSITIVE, NULL, "UNCERTAIN"}
    assert max(first_states.count(state) for state in set(first_states)) == 3
    task = AmbiguityDiscoveryRuntime._task("fixture", "model", CASES[0], 120)
    rendered = str(ambiguity_discovery_messages(task))
    assert "confidence': 0.0" not in rendered and '"confidence": 0.0' not in rendered
    assert json.dumps(state_order("U01")) in rendered


def test_runtime_keeps_truth_hidden_and_scores_provider_with_harness():
    adapter = FixtureDiscoveryAdapter()
    run = AmbiguityDiscoveryRuntime().evaluate_model(experiment_id="fixture", adapter=adapter)
    assert run["profile"]["balanced_accuracy"] == 1.0
    assert run["profile"]["null_false_positive_rate"] == 0.0
    assert all("expected_state" not in inputs and "pair_id" not in inputs for inputs in adapter.seen_inputs)
    assert all(trial["outcome"]["harness_owned"] for trial in run["trials"])


def test_discovery_state_survives_incomplete_packet_as_separate_proxy():
    run = AmbiguityDiscoveryRuntime().evaluate_model(
        experiment_id="fixture", adapter=IncompletePacketAdapter(),
    )
    assert run["profile"]["positive_recall"] == 1.0
    assert run["profile"]["null_specificity"] == 0.0
    assert run["profile"]["packet_contract_successes"] == 0
    assert all(trial["outcome"]["observed_state"] == POSITIVE for trial in run["trials"])
    assert all(trial["provider_payload"] is not None and trial["payload"] is None for trial in run["trials"])


def test_report_applies_frozen_gates_without_granting_authority():
    run = AmbiguityDiscoveryRuntime().evaluate_model(
        experiment_id="fixture", adapter=FixtureDiscoveryAdapter(),
    )
    profiles = (
        run["profile"], _clone_profile(run["profile"], "small-b"),
        _clone_profile(run["profile"], "strong"),
    )
    calibration = _calibration_artifact()
    judge = {"artifact_hash": "j" * 64}
    report = build_discovery_report(
        experiment_id="fixture", calibration_artifact=calibration,
        judge_calibration_artifact=judge, profiles=profiles,
    )
    validate_discovery_report(
        report, calibration_artifact=calibration, judge_calibration_artifact=judge,
    )
    assert report["candidate_state"] == "ENDOGENOUS_OBJECT_DISCOVERY_EVIDENCE_CANDIDATE"
    assert report["semantic_packet_quality_pending"] is True
    assert not report["selection_authority"] and not report["production_authority"]
