"""Frozen scoring gates for the split negative-evidence candidate."""

from __future__ import annotations

from .negative_evidence_candidate_runtime import (
    validate_negative_evidence_candidate_run,
)
from .negative_evidence_holdout import validate_negative_evidence_corpus_artifact
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


CALIBRATION_VERSION = "negative_evidence_split_calibration_v0_1"
FROZEN_GATES = {
    "maximum_fused_false_usable_rate": 0.15,
    "minimum_false_usable_reduction_when_baseline_unsafe": 0.25,
    "minimum_fused_usable_recall": 0.80,
    "maximum_usable_recall_harm": 0.10,
    "maximum_fused_unresolved_rate": 0.15,
    "maximum_provider_call_multiplier": 3.20,
    "complete_prediction_surface_required": True,
}


def build_negative_evidence_calibration(*, corpus_artifact, candidate_run,
                                        reference_artifact):
    validate_negative_evidence_corpus_artifact(corpus_artifact)
    validate_negative_evidence_candidate_run(
        candidate_run, corpus_artifact=corpus_artifact,
    )
    reference = _reference_states(reference_artifact, corpus_artifact)
    records = {
        item["blind_candidate_id"]: item
        for item in candidate_run["fusion"]["records"]
    }
    blind_ids = sorted(corpus_artifact["blind_surface"]["bindings"])
    complete = set(reference) == set(records) == set(blind_ids)
    comparisons = []
    for blind_id in blind_ids:
        item = records[blind_id]
        comparisons.append({
            "blind_candidate_id": blind_id,
            "reference_packet_state": reference[blind_id],
            "baseline_packet_state": item["baseline_packet_state"],
            "fused_packet_state": item["fused_packet_state"],
            "live_ambiguity_audit_state": item["live_ambiguity_audit_state"],
            "fabrication_audit_state": item["fabrication_audit_state"],
        })
    nonusable = [
        item for item in comparisons if item["reference_packet_state"] != "USABLE"
    ]
    usable = [
        item for item in comparisons if item["reference_packet_state"] == "USABLE"
    ]
    baseline_false_usable = _rate(
        nonusable, lambda item: item["baseline_packet_state"] == "USABLE",
    )
    fused_false_usable = _rate(
        nonusable, lambda item: item["fused_packet_state"] == "USABLE",
    )
    false_usable_reduction = baseline_false_usable - fused_false_usable
    baseline_usable_recall = _rate(
        usable, lambda item: item["baseline_packet_state"] == "USABLE",
    )
    fused_usable_recall = _rate(
        usable, lambda item: item["fused_packet_state"] == "USABLE",
    )
    usable_recall_harm = max(0.0, baseline_usable_recall - fused_usable_recall)
    fused_unresolved_rate = _rate(
        comparisons, lambda item: item["fused_packet_state"] == "UNRESOLVED",
    )
    baseline_calls = candidate_run["lanes"]["BASELINE"]["provider_calls"]
    provider_call_multiplier = (
        candidate_run["total_provider_calls"] / baseline_calls
        if baseline_calls else float("inf")
    )
    gain_required = (
        baseline_false_usable
        > FROZEN_GATES["maximum_fused_false_usable_rate"]
    )
    gain_gate = (
        false_usable_reduction
        >= FROZEN_GATES["minimum_false_usable_reduction_when_baseline_unsafe"]
        if gain_required else True
    )
    gates = {
        "fused_false_usable_rate": (
            fused_false_usable
            <= FROZEN_GATES["maximum_fused_false_usable_rate"]
        ),
        "false_usable_reduction_when_required": gain_gate,
        "fused_usable_recall": (
            fused_usable_recall >= FROZEN_GATES["minimum_fused_usable_recall"]
        ),
        "usable_recall_harm": (
            usable_recall_harm <= FROZEN_GATES["maximum_usable_recall_harm"]
        ),
        "fused_unresolved_rate": (
            fused_unresolved_rate
            <= FROZEN_GATES["maximum_fused_unresolved_rate"]
        ),
        "provider_call_multiplier": (
            provider_call_multiplier
            <= FROZEN_GATES["maximum_provider_call_multiplier"]
        ),
        "complete_prediction_surface": complete,
    }
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "frozen_gates": FROZEN_GATES,
        "corpus_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "reference_artifact_hash": reference_artifact["artifact_hash"],
        "comparisons": comparisons,
        "baseline_false_usable_rate": baseline_false_usable,
        "fused_false_usable_rate": fused_false_usable,
        "false_usable_reduction": false_usable_reduction,
        "split_gain_required": gain_required,
        "split_gain_observed": false_usable_reduction > 0,
        "baseline_usable_recall": baseline_usable_recall,
        "fused_usable_recall": fused_usable_recall,
        "usable_recall_harm": usable_recall_harm,
        "fused_unresolved_rate": fused_unresolved_rate,
        "provider_call_multiplier": provider_call_multiplier,
        "gate_results": gates,
        "candidate_state": (
            "NEGATIVE_EVIDENCE_SPLIT_CALIBRATION_CANDIDATE"
            if all(gates.values())
            else "NEGATIVE_EVIDENCE_SPLIT_CALIBRATION_GATE_FAILED"
        ),
        "evidence_coordinate": "INTERNAL_MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_negative_evidence_calibration(artifact, *, corpus_artifact,
                                           candidate_run, reference_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_evidence_calibration_hash_invalid")
    expected = build_negative_evidence_calibration(
        corpus_artifact=corpus_artifact,
        candidate_run=candidate_run,
        reference_artifact=reference_artifact,
    )
    if artifact != expected:
        raise ValueError("negative_evidence_calibration_semantics_invalid")


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
        raise ValueError("negative_evidence_reference_surface_invalid")
    states = {}
    for item in labels:
        criteria = item.get("criteria", {})
        if (
            set(criteria) != set(JUDGE_CRITERIA)
            or any(value not in JUDGE_STATES for value in criteria.values())
        ):
            raise ValueError("negative_evidence_reference_criteria_invalid")
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
