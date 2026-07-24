"""Harness-owned report for the frozen hard-null coordinator validation."""

from __future__ import annotations

from .ambiguity_hard_null_holdout import (
    CASES,
    HOLDOUT_SPEC,
    NULL,
    POSITIVE,
    validate_hard_null_holdout_spec,
)
from .ambiguity_hard_null_runtime import validate_hard_null_coordinator_run
from .ambiguity_hard_null_surface import (
    build_hard_null_surface,
    validate_hard_null_surface,
)
from .provider_telemetry import hash_payload


REPORT_VERSION = "ambiguity_hard_null_report_v0_1"


def build_hard_null_report(*, role_artifact, model_runs, surface, coordinator_run):
    validate_hard_null_holdout_spec()
    validate_hard_null_surface(
        surface, role_artifact=role_artifact, model_runs=model_runs,
    )
    validate_hard_null_coordinator_run(coordinator_run, surface=surface)
    runs = {run["model_id"]: run for run in model_runs}
    roles = role_artifact["role_candidates"]
    proposer = _run_states(runs[roles["ambiguity_proposer"]["model_id"]])
    skeptic = _run_states(runs[roles["null_skeptic"]["model_id"]])
    expected = {case.item_id: case.expected_state for case in CASES}
    fixed_predictions = {
        "PROPOSER_ONLY": proposer,
        "SKEPTIC_ONLY": skeptic,
        "OR_POSITIVE": {
            item: POSITIVE if POSITIVE in {proposer[item], skeptic[item]} else NULL
            for item in expected
        },
        "AND_POSITIVE": {
            item: POSITIVE if proposer[item] == skeptic[item] == POSITIVE else NULL
            for item in expected
        },
    }
    fixed_profiles = {
        name: _score(expected, predictions)
        for name, predictions in fixed_predictions.items()
    }
    coordinator_decisions = _coordinator_decisions(surface, coordinator_run)
    coordinator_states = {
        item: decision["final_state"] for item, decision in coordinator_decisions.items()
    }
    coordinator_profile = _score(expected, coordinator_states)
    frozen_name = HOLDOUT_SPEC["frozen_comparator"]
    frozen_profile = fixed_profiles[frozen_name]
    balanced_gain = (
        coordinator_profile["balanced_accuracy"] - frozen_profile["balanced_accuracy"]
    )
    fixed_calls = sum(run["profile"]["total_provider_calls"] for run in model_runs)
    fixed_tokens = sum(run["profile"]["total_tokens"] for run in model_runs)
    coordinator_calls = coordinator_run["profile"]["total_provider_calls"]
    coordinator_tokens = coordinator_run["profile"]["total_tokens"]
    call_ratio = (fixed_calls + coordinator_calls) / fixed_calls if fixed_calls else None
    token_ratio = (fixed_tokens + coordinator_tokens) / fixed_tokens if fixed_tokens else None
    uncertain_rate = sum(
        coordinator_states.get(item) not in {POSITIVE, NULL} for item in expected
    ) / len(expected)
    decision_count = len(coordinator_decisions)
    low_quality_positives = sum(
        decision["final_state"] == POSITIVE
        and not any(
            assessment["quality_state"] == "USABLE_MATERIAL_SUPPORT"
            for assessment in decision["receipt_assessments"]
        )
        for decision in coordinator_decisions.values()
    )
    control_consistency = decision_count / len(expected)
    low_quality_positive_rate = low_quality_positives / decision_count if decision_count else 1.0
    hard_null_material_support = sum(
        expected[item] == NULL
        and any(
            assessment["quality_state"] == "USABLE_MATERIAL_SUPPORT"
            for assessment in decision["receipt_assessments"]
        )
        for item, decision in coordinator_decisions.items()
    )
    gates = HOLDOUT_SPEC["frozen_gates"]
    gate_results = {
        "balanced_accuracy": (
            coordinator_profile["balanced_accuracy"] >= gates["minimum_balanced_accuracy"]
        ),
        "positive_recall": (
            coordinator_profile["positive_recall"] >= gates["minimum_positive_recall"]
        ),
        "hard_null_specificity": (
            coordinator_profile["null_specificity"]
            >= gates["minimum_hard_null_specificity"]
        ),
        "balanced_gain": (
            balanced_gain >= gates["minimum_balanced_gain_vs_frozen_comparator"]
        ),
        "receipt_control_consistency": (
            control_consistency >= gates["minimum_receipt_control_consistency"]
        ),
        "low_quality_positive_rate": (
            low_quality_positive_rate <= gates["maximum_low_quality_positive_rate"]
        ),
        "uncertainty": (
            uncertain_rate <= gates["maximum_uncertain_or_unavailable_rate"]
        ),
        "provider_call_budget": (
            call_ratio is not None and call_ratio <= gates["maximum_provider_call_ratio"]
        ),
        "token_budget": (
            token_ratio is not None and token_ratio <= gates["maximum_token_ratio"]
        ),
        "complete_decision_surface": decision_count == len(expected),
    }
    passed = all(gate_results.values())
    commitment = {
        "report_version": REPORT_VERSION,
        "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"],
        "role_artifact_hash": role_artifact["artifact_hash"],
        "surface_hash": surface["surface_hash"],
        "coordinator_run_hash": coordinator_run["coordinator_run_hash"],
        "fixed_strategy_profiles": fixed_profiles,
        "frozen_comparator": frozen_name,
        "coordinator_profile": coordinator_profile,
        "balanced_gain_vs_frozen_comparator": balanced_gain,
        "corrected_vs_frozen_comparator": sum(
            coordinator_states.get(item) == expected[item]
            and fixed_predictions[frozen_name][item] != expected[item]
            for item in expected
        ),
        "harmed_vs_frozen_comparator": sum(
            coordinator_states.get(item) != expected[item]
            and fixed_predictions[frozen_name][item] == expected[item]
            for item in expected
        ),
        "uncertain_or_unavailable_rate": uncertain_rate,
        "receipt_control_profile": {
            "controlled_decision_count": decision_count,
            "receipt_control_consistency": control_consistency,
            "low_quality_positive_count": low_quality_positives,
            "low_quality_positive_rate": low_quality_positive_rate,
            "hard_null_items_with_material_support": hard_null_material_support,
        },
        "cost_profile": {
            "fixed_provider_calls": fixed_calls,
            "fixed_tokens": fixed_tokens,
            "coordinator_provider_calls": coordinator_calls,
            "coordinator_tokens": coordinator_tokens,
            "coordinated_route_provider_calls": fixed_calls + coordinator_calls,
            "coordinated_route_tokens": fixed_tokens + coordinator_tokens,
            "provider_call_ratio": call_ratio,
            "token_ratio": token_ratio,
        },
        "gate_results": gate_results,
        "candidate_state": (
            "HARD_NULL_COORDINATOR_VALIDATION_CANDIDATE"
            if passed else "HARD_NULL_COORDINATOR_GATE_FAILED"
        ),
        "evidence_coordinate": "INTERNAL_SYNTHETIC_FRESH_HARD_NULL_HOLDOUT",
        "predecessor_label_tuning": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "report_hash": hash_payload(commitment)}


def build_hard_null_artifact(*, experiment_id, role_artifact, model_runs, surface,
                             coordinator_run):
    _validate_hash(role_artifact, "role")
    for run in model_runs:
        _validate_model_run(run)
    report = build_hard_null_report(
        role_artifact=role_artifact,
        model_runs=model_runs,
        surface=surface,
        coordinator_run=coordinator_run,
    )
    commitment = {
        "experiment_id": experiment_id,
        "holdout_spec": HOLDOUT_SPEC,
        "role_artifact_hash": role_artifact["artifact_hash"],
        "model_runs": list(model_runs),
        "blind_surface": surface,
        "coordinator_run": coordinator_run,
        "report": report,
        "claim_boundary": (
            "fresh internal synthetic hard-null validation with frozen materiality and "
            "receipt-quality controls; predecessor labels were neither exposed nor used for "
            "adaptation; no baseline, selection, retention, or production authority"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_hard_null_artifact(artifact, *, role_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("hard_null_artifact_hash_invalid")
    expected = build_hard_null_artifact(
        experiment_id=artifact["experiment_id"],
        role_artifact=role_artifact,
        model_runs=tuple(artifact["model_runs"]),
        surface=artifact["blind_surface"],
        coordinator_run=artifact["coordinator_run"],
    )
    if artifact != expected:
        raise ValueError("hard_null_artifact_semantics_invalid")


def _score(expected, predicted):
    positives = [item for item, state in expected.items() if state == POSITIVE]
    nulls = [item for item, state in expected.items() if state == NULL]
    recall = sum(predicted.get(item) == POSITIVE for item in positives) / len(positives)
    specificity = sum(predicted.get(item) == NULL for item in nulls) / len(nulls)
    return {
        "positive_recall": recall,
        "null_specificity": specificity,
        "hard_null_specificity": specificity,
        "balanced_accuracy": (recall + specificity) / 2,
        "accuracy": (
            sum(predicted.get(item) == state for item, state in expected.items())
            / len(expected)
        ),
    }


def _run_states(run):
    return {
        trial["item_id"]: trial["outcome"]["observed_state"]
        for trial in run["trials"]
    }


def _coordinator_decisions(surface, run):
    binding = surface["private_position_bindings"]
    decisions = {}
    for judgment in run["judgments"]:
        rendered = str(judgment["provider_input"])
        forbidden = {run["model_id"], run["provider_id"], "PROPOSER", "SKEPTIC"}
        if any(value and value in rendered for value in forbidden):
            raise ValueError("hard_null_identity_blinding_failed")
        if "expected_state" in rendered or "construction_basis" in rendered:
            raise ValueError("hard_null_truth_leak_detected")
        for decision in judgment["payload"]["decisions"]:
            item_id = binding[decision["coordination_item_id"]]["source_item_id"]
            decisions[item_id] = decision
    return decisions


def _validate_model_run(run):
    commitment = {key: value for key, value in run.items() if key != "model_run_hash"}
    if run.get("model_run_hash") != hash_payload(commitment):
        raise ValueError("hard_null_model_run_hash_invalid")
    profile = run["profile"]
    profile_commitment = {key: value for key, value in profile.items() if key != "profile_hash"}
    if profile.get("profile_hash") != hash_payload(profile_commitment):
        raise ValueError("hard_null_model_profile_hash_invalid")


def _validate_hash(artifact, name):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError(f"hard_null_{name}_artifact_hash_invalid")
