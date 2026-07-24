"""Frozen post-reference gates for precision-confirmed vetoes."""

from __future__ import annotations

from .negative_evidence_precision_fusion import ARMS
from .negative_evidence_precision_holdout import validate_precision_corpus_artifact
from .negative_evidence_precision_runtime import validate_precision_candidate_run
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


CALIBRATION_VERSION = "negative_evidence_precision_calibration_v0_3"
ARM_STATE_KEYS = {
    "SINGLE_MONOLITHIC": "single_monolithic_state",
    "BUDGET_CEILING_MONOLITHIC": "budget_ceiling_monolithic_state",
    "NAIVE_VETO": "naive_veto_state",
    "CONFIRMED_VETO": "confirmed_veto_state",
}
FROZEN_GATES = {
    "maximum_confirmed_false_usable_rate": 0.10,
    "minimum_confirmed_usable_recall": 0.90,
    "maximum_confirmed_unresolved_rate": 0.05,
    "maximum_worst_category_false_usable_rate": 0.25,
    "minimum_accuracy_gain_vs_budget_ceiling": 0.10,
    "minimum_usable_recall_gain_vs_naive": 0.04,
    "maximum_false_usable_increase_vs_naive": 0.0,
    "maximum_confirmed_call_multiplier": 4.0,
    "complete_prediction_surface_required": True,
}


def build_precision_calibration(*, corpus_artifact, candidate_run, reference_artifact):
    validate_precision_corpus_artifact(corpus_artifact)
    validate_precision_candidate_run(candidate_run, corpus_artifact=corpus_artifact)
    reference = _reference_states(reference_artifact, corpus_artifact)
    bindings = corpus_artifact["blind_surface"]["bindings"]
    records = {item["blind_candidate_id"]: item for item in candidate_run["fusion"]["records"]}
    blind_ids = sorted(bindings)
    complete = set(reference) == set(records) == set(blind_ids)
    comparisons = [
        {
            "blind_candidate_id": blind_id,
            "construction_category": bindings[blind_id]["construction_category"],
            "surface_style": bindings[blind_id]["surface_style"],
            "reference_packet_state": reference[blind_id],
            **{arm: records[blind_id][key] for arm, key in ARM_STATE_KEYS.items()},
        }
        for blind_id in blind_ids
    ]
    metrics = {
        arm: _arm_metrics(arm, comparisons, candidate_run["fusion"]["arm_accounting"][arm])
        for arm in ARMS
    }
    budget = metrics["BUDGET_CEILING_MONOLITHIC"]
    naive = metrics["NAIVE_VETO"]
    confirmed = metrics["CONFIRMED_VETO"]
    accuracy_gain = confirmed["packet_accuracy"] - budget["packet_accuracy"]
    recall_gain = confirmed["usable_recall"] - naive["usable_recall"]
    false_usable_increase = confirmed["false_usable_rate"] - naive["false_usable_rate"]
    gates = {
        "confirmed_false_usable_rate": confirmed["false_usable_rate"] <= FROZEN_GATES["maximum_confirmed_false_usable_rate"],
        "confirmed_usable_recall": confirmed["usable_recall"] >= FROZEN_GATES["minimum_confirmed_usable_recall"],
        "confirmed_unresolved_rate": confirmed["unresolved_rate"] <= FROZEN_GATES["maximum_confirmed_unresolved_rate"],
        "worst_category_false_usable_rate": confirmed["worst_category_false_usable_rate"] <= FROZEN_GATES["maximum_worst_category_false_usable_rate"],
        "accuracy_gain_vs_budget_ceiling": accuracy_gain >= FROZEN_GATES["minimum_accuracy_gain_vs_budget_ceiling"],
        "usable_recall_gain_vs_naive": recall_gain >= FROZEN_GATES["minimum_usable_recall_gain_vs_naive"],
        "false_usable_increase_vs_naive": false_usable_increase <= FROZEN_GATES["maximum_false_usable_increase_vs_naive"],
        "confirmed_call_multiplier": confirmed["call_multiplier"] <= FROZEN_GATES["maximum_confirmed_call_multiplier"],
        "complete_prediction_surface": complete,
    }
    safety_without_gain = all(
        value for key, value in gates.items()
        if key != "usable_recall_gain_vs_naive"
    )
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "frozen_gates": FROZEN_GATES,
        "corpus_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "reference_artifact_hash": reference_artifact["artifact_hash"],
        "comparisons": comparisons,
        "arm_metrics": metrics,
        "confirmed_accuracy_gain_vs_budget_ceiling": accuracy_gain,
        "confirmed_usable_recall_gain_vs_naive": recall_gain,
        "confirmed_false_usable_increase_vs_naive": false_usable_increase,
        "gate_results": gates,
        "candidate_state": (
            "PRECISION_CONFIRMED_VETO_CANDIDATE" if all(gates.values())
            else "PRECISION_CONFIRMATION_GAIN_NOT_IDENTIFIED" if safety_without_gain
            else "PRECISION_CONFIRMED_VETO_GATE_FAILED"
        ),
        "evidence_coordinate": "INTERNAL_MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_precision_calibration(artifact, *, corpus_artifact, candidate_run, reference_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_precision_calibration_hash_invalid")
    expected = build_precision_calibration(
        corpus_artifact=corpus_artifact,
        candidate_run=candidate_run,
        reference_artifact=reference_artifact,
    )
    if artifact != expected:
        raise ValueError("negative_precision_calibration_semantics_invalid")


def _arm_metrics(arm, comparisons, accounting):
    nonusable = [item for item in comparisons if item["reference_packet_state"] != "USABLE"]
    usable = [item for item in comparisons if item["reference_packet_state"] == "USABLE"]
    category_rates = {}
    for category in sorted({item["construction_category"] for item in comparisons}):
        category_nonusable = [item for item in nonusable if item["construction_category"] == category]
        if category_nonusable:
            category_rates[category] = _rate(category_nonusable, lambda item: item[arm] == "USABLE")
    calls = accounting["attributed_provider_calls"]
    total_tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    baseline_calls = len(comparisons) / 2
    return {
        "packet_accuracy": _rate(comparisons, lambda item: item[arm] == item["reference_packet_state"]),
        "false_usable_rate": _rate(nonusable, lambda item: item[arm] == "USABLE"),
        "usable_recall": _rate(usable, lambda item: item[arm] == "USABLE"),
        "unresolved_rate": _rate(comparisons, lambda item: item[arm] == "UNRESOLVED"),
        "category_false_usable_rates": category_rates,
        "worst_category_false_usable_rate": max(category_rates.values(), default=0.0),
        "attributed_provider_calls": calls,
        "attributed_tokens": total_tokens,
        "call_multiplier": calls / baseline_calls if baseline_calls else float("inf"),
        "tokens_per_item": total_tokens / len(comparisons),
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
        raise ValueError("negative_precision_reference_surface_invalid")
    states = {}
    for item in labels:
        criteria = item.get("criteria", {})
        if set(criteria) != set(JUDGE_CRITERIA) or any(value not in JUDGE_STATES for value in criteria.values()):
            raise ValueError("negative_precision_reference_criteria_invalid")
        values = set(criteria.values())
        states[item["blind_candidate_id"]] = (
            "USABLE" if values == {"PRESENT"}
            else "UNUSABLE" if "ABSENT" in values else "UNRESOLVED"
        )
    return states


def _rate(items, predicate):
    return sum(predicate(item) for item in items) / len(items) if items else 0.0
