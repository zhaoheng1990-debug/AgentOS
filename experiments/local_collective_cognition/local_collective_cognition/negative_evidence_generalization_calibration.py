"""Frozen post-reference gates for four-arm role-structure generalization."""

from __future__ import annotations

from .negative_evidence_generalization_fusion import ARMS
from .negative_evidence_generalization_holdout import (
    validate_generalization_corpus_artifact,
)
from .negative_evidence_generalization_runtime import (
    validate_generalization_candidate_run,
)
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


CALIBRATION_VERSION = "negative_evidence_generalization_calibration_v0_2"
ARM_STATE_KEYS = {
    "SINGLE_MONOLITHIC": "single_monolithic_state",
    "BUDGET_MATCHED_MONOLITHIC": "budget_matched_monolithic_state",
    "SAME_MODEL_SPLIT": "same_model_split_state",
    "HETEROGENEOUS_SPLIT": "heterogeneous_split_state",
}
FROZEN_GATES = {
    "maximum_same_split_false_usable_rate": 0.20,
    "minimum_false_usable_reduction_vs_budget_when_unsafe": 0.20,
    "minimum_same_split_usable_recall": 0.85,
    "maximum_usable_recall_harm_vs_budget": 0.10,
    "maximum_same_split_unresolved_rate": 0.10,
    "maximum_worst_category_false_usable_rate": 0.25,
    "minimum_packet_accuracy_gain_vs_budget": 0.10,
    "maximum_same_split_call_multiplier": 3.20,
    "complete_prediction_surface_required": True,
}


def build_generalization_calibration(*, corpus_artifact, candidate_run,
                                     reference_artifact):
    validate_generalization_corpus_artifact(corpus_artifact)
    validate_generalization_candidate_run(
        candidate_run, corpus_artifact=corpus_artifact,
    )
    reference = _reference_states(reference_artifact, corpus_artifact)
    bindings = corpus_artifact["blind_surface"]["bindings"]
    fusion_records = {
        item["blind_candidate_id"]: item
        for item in candidate_run["fusion"]["records"]
    }
    blind_ids = sorted(bindings)
    complete = set(reference) == set(fusion_records) == set(blind_ids)
    comparisons = []
    for blind_id in blind_ids:
        source = fusion_records[blind_id]
        comparisons.append({
            "blind_candidate_id": blind_id,
            "construction_category": bindings[blind_id]["construction_category"],
            "surface_style": bindings[blind_id]["surface_style"],
            "reference_packet_state": reference[blind_id],
            **{
                arm: source[state_key]
                for arm, state_key in ARM_STATE_KEYS.items()
            },
        })
    metrics = {
        arm: _arm_metrics(
            arm, comparisons, candidate_run["fusion"]["arm_accounting"][arm],
        )
        for arm in ARMS
    }
    budget = metrics["BUDGET_MATCHED_MONOLITHIC"]
    same = metrics["SAME_MODEL_SPLIT"]
    hetero = metrics["HETEROGENEOUS_SPLIT"]
    false_usable_reduction = (
        budget["false_usable_rate"] - same["false_usable_rate"]
    )
    accuracy_gain = same["packet_accuracy"] - budget["packet_accuracy"]
    recall_harm = max(0.0, budget["usable_recall"] - same["usable_recall"])
    gain_required = budget["false_usable_rate"] > FROZEN_GATES[
        "maximum_same_split_false_usable_rate"
    ]
    same_gates = {
        "same_split_false_usable_rate": (
            same["false_usable_rate"]
            <= FROZEN_GATES["maximum_same_split_false_usable_rate"]
        ),
        "false_usable_reduction_vs_budget_when_required": (
            false_usable_reduction
            >= FROZEN_GATES["minimum_false_usable_reduction_vs_budget_when_unsafe"]
            if gain_required else True
        ),
        "same_split_usable_recall": (
            same["usable_recall"]
            >= FROZEN_GATES["minimum_same_split_usable_recall"]
        ),
        "usable_recall_harm_vs_budget": (
            recall_harm <= FROZEN_GATES["maximum_usable_recall_harm_vs_budget"]
        ),
        "same_split_unresolved_rate": (
            same["unresolved_rate"]
            <= FROZEN_GATES["maximum_same_split_unresolved_rate"]
        ),
        "worst_category_false_usable_rate": (
            same["worst_category_false_usable_rate"]
            <= FROZEN_GATES["maximum_worst_category_false_usable_rate"]
        ),
        "packet_accuracy_gain_vs_budget": (
            accuracy_gain
            >= FROZEN_GATES["minimum_packet_accuracy_gain_vs_budget"]
        ),
        "same_split_call_multiplier": (
            same["call_multiplier"]
            <= FROZEN_GATES["maximum_same_split_call_multiplier"]
        ),
        "complete_prediction_surface": complete,
    }
    hetero_gates = _heterogeneous_profile_gates(
        hetero=hetero, budget=budget, complete=complete,
    )
    passed = all(same_gates.values())
    safety_without_gain = all(
        value for key, value in same_gates.items()
        if key != "packet_accuracy_gain_vs_budget"
    )
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "frozen_gates": FROZEN_GATES,
        "corpus_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "reference_artifact_hash": reference_artifact["artifact_hash"],
        "comparisons": comparisons,
        "arm_metrics": metrics,
        "same_split_false_usable_reduction_vs_budget": false_usable_reduction,
        "same_split_packet_accuracy_gain_vs_budget": accuracy_gain,
        "same_split_usable_recall_harm_vs_budget": recall_harm,
        "same_model_gate_results": same_gates,
        "heterogeneous_gate_results": hetero_gates,
        "candidate_state": (
            "ROLE_STRUCTURE_GENERALIZATION_CANDIDATE"
            if passed else
            "ROLE_STRUCTURE_GAIN_NOT_IDENTIFIED"
            if safety_without_gain else
            "ROLE_STRUCTURE_GENERALIZATION_GATE_FAILED"
        ),
        "evidence_coordinate": "INTERNAL_MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_generalization_calibration(artifact, *, corpus_artifact,
                                        candidate_run, reference_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_generalization_calibration_hash_invalid")
    expected = build_generalization_calibration(
        corpus_artifact=corpus_artifact,
        candidate_run=candidate_run,
        reference_artifact=reference_artifact,
    )
    if artifact != expected:
        raise ValueError("negative_generalization_calibration_semantics_invalid")


def _arm_metrics(arm, comparisons, accounting):
    nonusable = [
        item for item in comparisons if item["reference_packet_state"] != "USABLE"
    ]
    usable = [
        item for item in comparisons if item["reference_packet_state"] == "USABLE"
    ]
    false_usable = _rate(
        nonusable, lambda item: item[arm] == "USABLE",
    )
    category_rates = {}
    for category in sorted({item["construction_category"] for item in comparisons}):
        category_nonusable = [
            item for item in nonusable if item["construction_category"] == category
        ]
        if category_nonusable:
            category_rates[category] = _rate(
                category_nonusable, lambda item: item[arm] == "USABLE",
            )
    baseline_calls = len(comparisons) / 2
    calls = accounting["attributed_provider_calls"]
    total_tokens = (
        accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    )
    return {
        "packet_accuracy": _rate(
            comparisons, lambda item: item[arm] == item["reference_packet_state"],
        ),
        "false_usable_rate": false_usable,
        "usable_recall": _rate(usable, lambda item: item[arm] == "USABLE"),
        "unresolved_rate": _rate(
            comparisons, lambda item: item[arm] == "UNRESOLVED",
        ),
        "category_false_usable_rates": category_rates,
        "worst_category_false_usable_rate": max(category_rates.values(), default=0.0),
        "attributed_provider_calls": calls,
        "attributed_tokens": total_tokens,
        "call_multiplier": calls / baseline_calls if baseline_calls else float("inf"),
        "tokens_per_item": total_tokens / len(comparisons),
    }


def _heterogeneous_profile_gates(*, hetero, budget, complete):
    return {
        "false_usable_rate": (
            hetero["false_usable_rate"]
            <= FROZEN_GATES["maximum_same_split_false_usable_rate"]
        ),
        "usable_recall": (
            hetero["usable_recall"]
            >= FROZEN_GATES["minimum_same_split_usable_recall"]
        ),
        "unresolved_rate": (
            hetero["unresolved_rate"]
            <= FROZEN_GATES["maximum_same_split_unresolved_rate"]
        ),
        "worst_category_false_usable_rate": (
            hetero["worst_category_false_usable_rate"]
            <= FROZEN_GATES["maximum_worst_category_false_usable_rate"]
        ),
        "packet_accuracy_gain_vs_budget": (
            hetero["packet_accuracy"] - budget["packet_accuracy"]
            >= FROZEN_GATES["minimum_packet_accuracy_gain_vs_budget"]
        ),
        "call_multiplier": (
            hetero["call_multiplier"]
            <= FROZEN_GATES["maximum_same_split_call_multiplier"]
        ),
        "complete_prediction_surface": complete,
    }


def _reference_states(reference, corpus_artifact):
    commitment = {key: value for key, value in reference.items() if key != "artifact_hash"}
    expected_ids = set(corpus_artifact["blind_surface"]["bindings"])
    labels = reference.get("labels") or []
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("candidate_state") != "MODEL_PANEL_REFERENCE_CANDIDATE"
        or reference.get("ground_truth_claim") is not False
        or reference.get("selection_authority") is not False
        or reference.get("retention_authority") is not False
        or {item.get("blind_candidate_id") for item in labels} != expected_ids
        or len(labels) != len(expected_ids)
    ):
        raise ValueError("negative_generalization_reference_surface_invalid")
    states = {}
    for item in labels:
        criteria = item.get("criteria", {})
        if (
            set(criteria) != set(JUDGE_CRITERIA)
            or any(value not in JUDGE_STATES for value in criteria.values())
        ):
            raise ValueError("negative_generalization_reference_criteria_invalid")
        states[item["blind_candidate_id"]] = _packet_state(criteria)
    return states


def _packet_state(criteria):
    states = set(criteria.values())
    if states == {"PRESENT"}:
        return "USABLE"
    if "ABSENT" in states:
        return "UNUSABLE"
    return "UNRESOLVED"


def _rate(items, predicate):
    return sum(predicate(item) for item in items) / len(items) if items else 0.0
