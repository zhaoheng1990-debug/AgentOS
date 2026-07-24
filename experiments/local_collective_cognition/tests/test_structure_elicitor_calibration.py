from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(Path(__file__).resolve().parents[1])]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_elicitor_calibration_eval import (  # noqa: E402
    CRITERIA, build_calibration_report, build_profile, evaluate_packet, parse_packet,
    validate_report,
)
from local_collective_cognition.structure_elicitor_calibration_holdout import (  # noqa: E402
    CASES, TRUTH_COMMITMENT, public_inputs,
)
from local_collective_cognition.structure_elicitor_calibration_runtime import (  # noqa: E402
    StructureElicitorCalibrationRuntime,
)
from local_collective_cognition.local_structure_packet_provider import (  # noqa: E402
    LocalQualityGatedStructureAdapter, recover_single_packet_payload,
)


def _packet(case, *, reverse=False):
    left = case.rival_b_terms[0] if reverse else case.rival_a_terms[0]
    right = case.rival_a_terms[0] if reverse else case.rival_b_terms[0]
    return (
        f"RIVAL_A: The output denotes {left}, with an explicit object and boundary. | "
        f"RIVAL_B: The output instead denotes {right}, using a different target object. | "
        f"CONTRAST: The decisive distinction is {case.rival_a_terms[0]} versus "
        f"{case.rival_b_terms[0]}. | QUESTION: Which requested output is intended: "
        f"{case.question_terms[0]} or {case.question_terms[1]}?"
    )


def _invocation(model_id="fixture"):
    return {
        "token_usage": {"provider_calls": 1, "input_tokens": 100, "output_tokens": 50},
        "receipt_hash": hash_payload({"model_id": model_id}),
    }


class FixtureAdapter:
    def __init__(self, model_id, builder):
        self.builder = builder
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id, model_id=model_id,
            task_kinds=("pilot_object_structure_expansion",),
            max_timeout_seconds=900,
        )

    def invoke(self, task):
        item_id = task.inputs["benchmark_item_ids"][0]
        case = next(item for item in CASES if item.item_id == item_id)
        return {
            "result": {"item_1_packet": self.builder(case)},
            "usage": {"provider_calls": 1, "input_tokens": 100, "output_tokens": 50},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_hidden_truth_is_committed_but_absent_from_public_inputs():
    public = public_inputs()
    assert len(public) == 4 and len(TRUTH_COMMITMENT) == 64
    assert "rival_a_terms" not in str(public) and "truth" not in str(public).lower()


def test_semantic_prompt_omits_internal_item_identifier_copy_shortcut():
    runtime = StructureElicitorCalibrationRuntime()
    task = runtime._task(
        "prompt-fixture", "small", CASES[0], timeout_seconds=600,
    )
    prompt = LocalQualityGatedStructureAdapter._structure_messages(task)[1]["content"]
    assert CASES[0].item_id not in prompt
    assert CASES[0].prompt in prompt
    assert "item_1_packet" in prompt


def test_raw_packet_recovery_adds_only_the_missing_single_key_transport():
    text = _packet(CASES[0])
    recovered = recover_single_packet_payload("Packet:\n" + text, "item_1_packet")
    assert recovered == {"item_1_packet": text}
    assert recover_single_packet_payload("RIVAL_A: incomplete", "item_1_packet") is None
    assert recover_single_packet_payload(text + "\n" + text, "item_1_packet") is None


def test_packet_harness_accepts_complete_semantics_in_either_rival_order():
    for reverse in (False, True):
        case = CASES[0]
        packet = {"item_id": case.item_id, "contrastive_packet": _packet(case, reverse=reverse)}
        outcome = evaluate_packet(
            case=case, packet=packet, model_id="fixture", provider_id="fixture",
            task_hash="a" * 64, invocation_receipt=_invocation(), provider_status="COMPLETED",
        )
        assert parse_packet(packet["contrastive_packet"])
        assert outcome["quality_score"] == 1.0
        assert all(outcome["criteria"].values())


def test_identifier_or_prompt_restatement_cannot_score_as_capability():
    case = CASES[0]
    for text in (case.item_id, case.prompt):
        outcome = evaluate_packet(
            case=case, packet={"item_id": case.item_id, "contrastive_packet": text},
            model_id="fixture", provider_id="fixture", task_hash="a" * 64,
            invocation_receipt=_invocation(), provider_status="COMPLETED",
        )
        assert outcome["quality_score"] == 0.0
        assert set(outcome["criteria"]) == set(CRITERIA)


def test_runtime_builds_four_independent_direct_quality_trials():
    run = StructureElicitorCalibrationRuntime().evaluate_model(
        experiment_id="calibration-fixture",
        adapter=FixtureAdapter("small-perfect", _packet),
    )
    assert run["profile"]["independent_trials"] == 4
    assert run["profile"]["mean_quality_score"] == 1.0
    assert run["profile"]["perfect_packets"] == 4
    assert run["profile"]["total_provider_calls"] == 4
    assert all(item["packet"] for item in run["trials"])


def test_report_ranks_direct_packet_quality_and_keeps_ceiling_non_authoritative():
    def outcome(model_id, score):
        criteria = {key: index < round(score * len(CRITERIA)) for index, key in enumerate(CRITERIA)}
        committed = {
            "model_id": model_id, "provider_status": "COMPLETED", "criteria": criteria,
            "quality_score": sum(criteria.values()) / len(CRITERIA), "provider_calls": 1,
            "input_tokens": 10, "output_tokens": 10,
        }
        return {**committed, "outcome_hash": hash_payload(committed)}

    profiles = []
    for model_id, score in (("deepseek-r1:32b", 1.0), ("small-a", 0.8), ("small-b", 0.4)):
        trials = tuple(outcome(model_id, score) for _ in range(4))
        profiles.append(build_profile(model_id=model_id, provider_id="p-" + model_id, outcomes=trials))
    report = build_calibration_report(
        experiment_id="report-fixture", profiles=tuple(profiles),
        strong_model_id="deepseek-r1:32b", truth_commitment="b" * 64,
    )
    validate_report(report)
    assert report["selected_small_model_id"] == "small-a"
    assert report["strong_model_quality_ceiling"] == 1.0
    assert report["routing_support_mode"] == "CALIBRATION_TRANSFER_CANDIDATE_EXPLORATORY"
    assert report["selection_authority"] is False and report["fresh_holdout_required"] is True


def test_failed_provider_attempts_remain_visible_cognitive_work():
    case = CASES[0]
    outcome = evaluate_packet(
        case=case, packet=None, model_id="failed", provider_id="failed",
        task_hash="a" * 64, invocation_receipt=_invocation("failed"),
        provider_status="PROVIDER_UNAVAILABLE", provider_failures=("transport",),
        work_usage={"provider_calls": 2, "input_tokens": 80, "output_tokens": 40},
        telemetry_hashes=("b" * 64, "c" * 64),
    )
    assert outcome["quality_score"] == 0.0
    assert outcome["provider_calls"] == 2
    assert outcome["input_tokens"] + outcome["output_tokens"] == 120
    assert outcome["telemetry_hashes"] == ["b" * 64, "c" * 64]
