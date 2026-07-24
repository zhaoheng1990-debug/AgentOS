"""Frozen dual admission gates for v0.4 replication and structured defer."""

from __future__ import annotations

from .negative_evidence_structured_fusion import ARMS
from .negative_evidence_structured_holdout import validate_structured_corpus_artifact
from .negative_evidence_structured_runtime import validate_structured_candidate_run
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


CALIBRATION_VERSION = "negative_evidence_structured_calibration_v0_4"
STATE_KEYS = {
    "SINGLE_MONOLITHIC": "single_monolithic_state",
    "BUDGET_MATCHED_MONOLITHIC": "budget_matched_monolithic_state",
    "NAIVE_REPLICATION": "naive_replication_state",
    "STRUCTURED_DEFER": "structured_defer_state",
}
FROZEN_GATES = {
    "naive": {
        "maximum_false_usable_rate": 0.20, "minimum_usable_recall": 0.90,
        "maximum_unresolved_rate": 0.10, "maximum_worst_category_false_usable_rate": 0.25,
        "minimum_accuracy_gain_vs_budget": 0.10, "maximum_call_multiplier": 3.20,
    },
    "structured": {
        "maximum_false_usable_rate": 0.10, "minimum_usable_recall": 0.90,
        "maximum_unresolved_rate": 0.10, "maximum_worst_category_false_usable_rate": 0.25,
        "minimum_accuracy_gain_vs_budget": 0.10, "minimum_accuracy_gain_vs_naive": 0.04,
        "maximum_false_usable_increase_vs_naive": 0.0,
        "maximum_usable_recall_harm_vs_naive": 0.05, "maximum_call_multiplier": 3.20,
    },
    "complete_prediction_surface_required": True,
}


def build_structured_calibration(*, corpus_artifact, candidate_run, reference_artifact):
    validate_structured_corpus_artifact(corpus_artifact)
    validate_structured_candidate_run(candidate_run, corpus_artifact=corpus_artifact)
    reference = _reference_states(reference_artifact, corpus_artifact)
    bindings = corpus_artifact["blind_surface"]["bindings"]
    records = {x["blind_candidate_id"]: x for x in candidate_run["fusion"]["records"]}
    ids = sorted(bindings)
    complete = set(reference) == set(records) == set(ids)
    comparisons = [
        {"blind_candidate_id": item_id, "construction_category": bindings[item_id]["construction_category"], "surface_style": bindings[item_id]["surface_style"], "reference_packet_state": reference[item_id], **{arm: records[item_id][key] for arm, key in STATE_KEYS.items()}}
        for item_id in ids
    ]
    metrics = {arm: _metrics(arm, comparisons, candidate_run["fusion"]["arm_accounting"][arm]) for arm in ARMS}
    budget, naive, structured = (metrics[x] for x in ("BUDGET_MATCHED_MONOLITHIC", "NAIVE_REPLICATION", "STRUCTURED_DEFER"))
    ng = FROZEN_GATES["naive"]
    naive_gates = {
        "false_usable_rate": naive["false_usable_rate"] <= ng["maximum_false_usable_rate"],
        "usable_recall": naive["usable_recall"] >= ng["minimum_usable_recall"],
        "unresolved_rate": naive["unresolved_rate"] <= ng["maximum_unresolved_rate"],
        "worst_category_false_usable_rate": naive["worst_category_false_usable_rate"] <= ng["maximum_worst_category_false_usable_rate"],
        "accuracy_gain_vs_budget": naive["packet_accuracy"] - budget["packet_accuracy"] >= ng["minimum_accuracy_gain_vs_budget"],
        "call_multiplier": naive["call_multiplier"] <= ng["maximum_call_multiplier"],
        "complete_prediction_surface": complete,
    }
    sg = FROZEN_GATES["structured"]
    structured_gates = {
        "false_usable_rate": structured["false_usable_rate"] <= sg["maximum_false_usable_rate"],
        "usable_recall": structured["usable_recall"] >= sg["minimum_usable_recall"],
        "unresolved_rate": structured["unresolved_rate"] <= sg["maximum_unresolved_rate"],
        "worst_category_false_usable_rate": structured["worst_category_false_usable_rate"] <= sg["maximum_worst_category_false_usable_rate"],
        "accuracy_gain_vs_budget": structured["packet_accuracy"] - budget["packet_accuracy"] >= sg["minimum_accuracy_gain_vs_budget"],
        "accuracy_gain_vs_naive": structured["packet_accuracy"] - naive["packet_accuracy"] >= sg["minimum_accuracy_gain_vs_naive"],
        "false_usable_increase_vs_naive": structured["false_usable_rate"] - naive["false_usable_rate"] <= sg["maximum_false_usable_increase_vs_naive"],
        "usable_recall_harm_vs_naive": max(0.0, naive["usable_recall"] - structured["usable_recall"]) <= sg["maximum_usable_recall_harm_vs_naive"],
        "call_multiplier": structured["call_multiplier"] <= sg["maximum_call_multiplier"],
        "complete_prediction_surface": complete,
    }
    naive_pass, structured_pass = all(naive_gates.values()), all(structured_gates.values())
    state = (
        "NAIVE_AND_STRUCTURED_DEFER_CANDIDATES" if naive_pass and structured_pass
        else "STRUCTURED_DEFER_CANDIDATE" if structured_pass
        else "NAIVE_THREE_ROLE_REPLICATION_CANDIDATE" if naive_pass
        else "STRUCTURED_REPLICATION_GATE_FAILED"
    )
    commitment = {
        "calibration_version": CALIBRATION_VERSION, "frozen_gates": FROZEN_GATES,
        "corpus_artifact_hash": corpus_artifact["artifact_hash"], "candidate_run_hash": candidate_run["candidate_run_hash"],
        "reference_artifact_hash": reference_artifact["artifact_hash"], "comparisons": comparisons,
        "arm_metrics": metrics, "naive_gate_results": naive_gates,
        "structured_gate_results": structured_gates, "candidate_state": state,
        "evidence_coordinate": "INTERNAL_MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False, "selection_authority": False,
        "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_structured_calibration(artifact, *, corpus_artifact, candidate_run, reference_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_structured_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run, reference_artifact=reference_artifact):
        raise ValueError("negative_structured_calibration_invalid")


def _metrics(arm, rows, accounting):
    unusable = [x for x in rows if x["reference_packet_state"] != "USABLE"]
    usable = [x for x in rows if x["reference_packet_state"] == "USABLE"]
    category_rates = {}
    for category in sorted({x["construction_category"] for x in rows}):
        subset = [x for x in unusable if x["construction_category"] == category]
        if subset: category_rates[category] = _rate(subset, lambda x: x[arm] == "USABLE")
    calls = accounting["attributed_provider_calls"]
    tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    return {
        "packet_accuracy": _rate(rows, lambda x: x[arm] == x["reference_packet_state"]),
        "false_usable_rate": _rate(unusable, lambda x: x[arm] == "USABLE"),
        "usable_recall": _rate(usable, lambda x: x[arm] == "USABLE"),
        "unresolved_rate": _rate(rows, lambda x: x[arm] == "UNRESOLVED"),
        "category_false_usable_rates": category_rates,
        "worst_category_false_usable_rate": max(category_rates.values(), default=0.0),
        "attributed_provider_calls": calls, "attributed_tokens": tokens,
        "call_multiplier": calls / (len(rows) / 2), "tokens_per_item": tokens / len(rows),
    }


def _reference_states(reference, corpus):
    commitment = {key: value for key, value in reference.items() if key != "artifact_hash"}
    ids = set(corpus["blind_surface"]["bindings"]); labels = reference.get("labels") or []
    if reference.get("artifact_hash") != hash_payload(commitment) or reference.get("candidate_state") != "MODEL_PANEL_REFERENCE_CANDIDATE" or reference.get("ground_truth_claim") is not False or {x.get("blind_candidate_id") for x in labels} != ids or len(labels) != len(ids):
        raise ValueError("negative_structured_reference_invalid")
    result = {}
    for item in labels:
        criteria = item.get("criteria", {})
        if set(criteria) != set(JUDGE_CRITERIA) or any(x not in JUDGE_STATES for x in criteria.values()): raise ValueError("negative_structured_reference_criteria_invalid")
        states = set(criteria.values()); result[item["blind_candidate_id"]] = "USABLE" if states == {"PRESENT"} else "UNUSABLE" if "ABSENT" in states else "UNRESOLVED"
    return result


def _rate(items, predicate):
    return sum(predicate(x) for x in items) / len(items) if items else 0.0
