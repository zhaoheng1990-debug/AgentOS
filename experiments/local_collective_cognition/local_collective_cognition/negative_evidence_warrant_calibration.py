"""Frozen post-reference gates for v0.5 execution-warranted vetoes."""

from __future__ import annotations

from .negative_evidence_warrant_fusion import ARMS
from .negative_evidence_warrant_holdout import validate_warrant_corpus_artifact
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


CALIBRATION_VERSION = "negative_evidence_warrant_calibration_v0_5"
STATE_KEYS = {
    "SINGLE_MONOLITHIC": "single_monolithic_state",
    "BUDGET_MATCHED_MONOLITHIC": "budget_matched_monolithic_state",
    "NAIVE_REPLICATION": "naive_replication_state",
    "WARRANTED_VETO": "warranted_veto_state",
}
FROZEN_GATES = {
    "naive": {
        "maximum_false_usable_rate": 0.20,
        "minimum_usable_recall": 0.90,
        "maximum_unresolved_rate": 0.10,
        "maximum_worst_category_false_usable_rate": 0.25,
        "minimum_accuracy_gain_vs_budget": 0.10,
        "maximum_call_multiplier": 3.20,
    },
    "warranted": {
        "maximum_false_usable_rate": 0.20,
        "minimum_usable_recall": 0.85,
        "maximum_unresolved_rate": 0.10,
        "maximum_worst_category_false_usable_rate": 0.25,
        "minimum_accuracy_gain_vs_budget": 0.15,
        "minimum_accuracy_gain_vs_naive": 0.04,
        "maximum_false_usable_increase_vs_naive": 0.0,
        "minimum_usable_recall_gain_vs_naive": 0.15,
        "maximum_call_multiplier": 3.20,
    },
    "complete_prediction_surface_required": True,
}


def build_warrant_calibration(*, corpus_artifact, candidate_run, reference_artifact):
    from .negative_evidence_warrant_runtime import validate_warrant_candidate_run

    validate_warrant_corpus_artifact(corpus_artifact)
    validate_warrant_candidate_run(candidate_run, corpus_artifact=corpus_artifact)
    reference = _reference_states(reference_artifact, corpus_artifact)
    bindings = corpus_artifact["blind_surface"]["bindings"]
    records = {item["blind_candidate_id"]: item for item in candidate_run["fusion"]["records"]}
    ids = sorted(bindings)
    complete = set(reference) == set(records) == set(ids)
    comparisons = [
        {
            "blind_candidate_id": item_id,
            "construction_category": bindings[item_id]["construction_category"],
            "surface_style": bindings[item_id]["surface_style"],
            "reference_packet_state": reference[item_id],
            **{arm: records[item_id][key] for arm, key in STATE_KEYS.items()},
        }
        for item_id in ids
    ]
    metrics = {arm: _metrics(arm, comparisons, candidate_run["fusion"]["arm_accounting"][arm]) for arm in ARMS}
    budget, naive, warranted = (metrics[arm] for arm in ("BUDGET_MATCHED_MONOLITHIC", "NAIVE_REPLICATION", "WARRANTED_VETO"))
    naive_gates = _absolute_gates(metrics=naive, budget=budget, gates=FROZEN_GATES["naive"], complete=complete)
    wg = FROZEN_GATES["warranted"]
    warranted_gates = {
        **_absolute_gates(metrics=warranted, budget=budget, gates=wg, complete=complete),
        "accuracy_gain_vs_naive": warranted["packet_accuracy"] - naive["packet_accuracy"] >= wg["minimum_accuracy_gain_vs_naive"],
        "false_usable_increase_vs_naive": warranted["false_usable_rate"] - naive["false_usable_rate"] <= wg["maximum_false_usable_increase_vs_naive"],
        "usable_recall_gain_vs_naive": warranted["usable_recall"] - naive["usable_recall"] >= wg["minimum_usable_recall_gain_vs_naive"],
    }
    naive_pass, warranted_pass = all(naive_gates.values()), all(warranted_gates.values())
    state = (
        "NAIVE_AND_WARRANTED_VETO_CANDIDATES" if naive_pass and warranted_pass
        else "WARRANTED_VETO_CANDIDATE" if warranted_pass
        else "NAIVE_THREE_ROLE_REPLICATION_CANDIDATE" if naive_pass
        else "VETO_WARRANT_GATE_FAILED"
    )
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "frozen_gates": FROZEN_GATES,
        "corpus_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "reference_artifact_hash": reference_artifact["artifact_hash"],
        "comparisons": comparisons,
        "arm_metrics": metrics,
        "naive_gate_results": naive_gates,
        "warranted_gate_results": warranted_gates,
        "candidate_state": state,
        "evidence_coordinate": "INTERNAL_MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_warrant_calibration(artifact, *, corpus_artifact, candidate_run, reference_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_warrant_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run, reference_artifact=reference_artifact):
        raise ValueError("negative_warrant_calibration_invalid")


def _absolute_gates(*, metrics, budget, gates, complete):
    return {
        "false_usable_rate": metrics["false_usable_rate"] <= gates["maximum_false_usable_rate"],
        "usable_recall": metrics["usable_recall"] >= gates["minimum_usable_recall"],
        "unresolved_rate": metrics["unresolved_rate"] <= gates["maximum_unresolved_rate"],
        "worst_category_false_usable_rate": metrics["worst_category_false_usable_rate"] <= gates["maximum_worst_category_false_usable_rate"],
        "accuracy_gain_vs_budget": metrics["packet_accuracy"] - budget["packet_accuracy"] >= gates["minimum_accuracy_gain_vs_budget"],
        "call_multiplier": metrics["call_multiplier"] <= gates["maximum_call_multiplier"],
        "complete_prediction_surface": complete,
    }


def _metrics(arm, rows, accounting):
    unusable = [item for item in rows if item["reference_packet_state"] != "USABLE"]
    usable = [item for item in rows if item["reference_packet_state"] == "USABLE"]
    category_rates = {}
    for category in sorted({item["construction_category"] for item in rows}):
        subset = [item for item in unusable if item["construction_category"] == category]
        if subset:
            category_rates[category] = _rate(subset, lambda item: item[arm] == "USABLE")
    calls = accounting["attributed_provider_calls"]
    tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    return {
        "packet_accuracy": _rate(rows, lambda item: item[arm] == item["reference_packet_state"]),
        "false_usable_rate": _rate(unusable, lambda item: item[arm] == "USABLE"),
        "usable_recall": _rate(usable, lambda item: item[arm] == "USABLE"),
        "unresolved_rate": _rate(rows, lambda item: item[arm] == "UNRESOLVED"),
        "category_false_usable_rates": category_rates,
        "worst_category_false_usable_rate": max(category_rates.values(), default=0.0),
        "attributed_provider_calls": calls,
        "attributed_tokens": tokens,
        "call_multiplier": calls / (len(rows) / 2),
        "tokens_per_item": tokens / len(rows),
    }


def _reference_states(reference, corpus):
    commitment = {key: value for key, value in reference.items() if key != "artifact_hash"}
    ids = set(corpus["blind_surface"]["bindings"])
    labels = reference.get("labels") or []
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("candidate_state") != "MODEL_PANEL_REFERENCE_CANDIDATE"
        or reference.get("ground_truth_claim") is not False
        or {item.get("blind_candidate_id") for item in labels} != ids
        or len(labels) != len(ids)
    ):
        raise ValueError("negative_warrant_reference_invalid")
    result = {}
    for item in labels:
        criteria = item.get("criteria", {})
        if set(criteria) != set(JUDGE_CRITERIA) or any(state not in JUDGE_STATES for state in criteria.values()):
            raise ValueError("negative_warrant_reference_criteria_invalid")
        states = set(criteria.values())
        result[item["blind_candidate_id"]] = "USABLE" if states == {"PRESENT"} else "UNUSABLE" if "ABSENT" in states else "UNRESOLVED"
    return result


def _rate(items, predicate):
    return sum(predicate(item) for item in items) / len(items) if items else 0.0
