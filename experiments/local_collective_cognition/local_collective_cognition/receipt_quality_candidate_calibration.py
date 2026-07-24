"""Score frozen receipt-quality predictions against a later model-panel reference."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .receipt_quality_candidate_runtime import validate_receipt_quality_candidate_run
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


CALIBRATION_VERSION = "receipt_quality_candidate_calibration_v0_1"
FROZEN_GATES = {
    "minimum_criterion_agreement": 0.85,
    "minimum_packet_state_accuracy": 0.85,
    "maximum_false_usable_rate": 0.10,
    "maximum_candidate_unresolved_rate": 0.15,
    "complete_prediction_surface_required": True,
}


def build_receipt_quality_calibration(*, corpus_artifact, candidate_run,
                                      reference_artifact):
    validate_receipt_quality_candidate_run(
        candidate_run, corpus_artifact=corpus_artifact,
    )
    _validate_reference_surface(reference_artifact, corpus_artifact)
    candidate = _candidate_labels(candidate_run)
    reference = {
        item["blind_candidate_id"]: item["criteria"]
        for item in reference_artifact["labels"]
    }
    blind_ids = sorted(corpus_artifact["blind_surface"]["bindings"])
    complete = set(candidate) == set(reference) == set(blind_ids)
    criterion_records = []
    packet_records = []
    for blind_id in blind_ids:
        candidate_criteria = candidate.get(blind_id, {})
        reference_criteria = reference.get(blind_id, {})
        for criterion in JUDGE_CRITERIA:
            predicted = candidate_criteria.get(criterion, "MISSING")
            expected = reference_criteria.get(criterion, "MISSING")
            criterion_records.append({
                "blind_candidate_id": blind_id,
                "criterion": criterion,
                "candidate_state": predicted,
                "reference_state": expected,
                "matched": predicted == expected,
            })
        predicted_packet = _packet_state(candidate_criteria)
        reference_packet = _packet_state(reference_criteria)
        packet_records.append({
            "blind_candidate_id": blind_id,
            "candidate_packet_state": predicted_packet,
            "reference_packet_state": reference_packet,
            "matched": predicted_packet == reference_packet,
        })
    criterion_agreement = (
        sum(item["matched"] for item in criterion_records) / len(criterion_records)
    )
    packet_accuracy = sum(item["matched"] for item in packet_records) / len(packet_records)
    reference_nonusable = [
        item for item in packet_records if item["reference_packet_state"] != "USABLE"
    ]
    false_usable_rate = (
        sum(
            item["candidate_packet_state"] == "USABLE"
            for item in reference_nonusable
        ) / len(reference_nonusable)
        if reference_nonusable else 0.0
    )
    candidate_unresolved_rate = sum(
        item["candidate_packet_state"] == "UNRESOLVED" for item in packet_records
    ) / len(packet_records)
    gate_results = {
        "criterion_agreement": (
            criterion_agreement >= FROZEN_GATES["minimum_criterion_agreement"]
        ),
        "packet_state_accuracy": (
            packet_accuracy >= FROZEN_GATES["minimum_packet_state_accuracy"]
        ),
        "false_usable_rate": (
            false_usable_rate <= FROZEN_GATES["maximum_false_usable_rate"]
        ),
        "candidate_unresolved_rate": (
            candidate_unresolved_rate
            <= FROZEN_GATES["maximum_candidate_unresolved_rate"]
        ),
        "complete_prediction_surface": complete,
    }
    passed = all(gate_results.values())
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "frozen_gates": FROZEN_GATES,
        "corpus_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["judge_run_hash"],
        "reference_artifact_hash": reference_artifact["artifact_hash"],
        "criterion_records": criterion_records,
        "packet_records": packet_records,
        "criterion_agreement": criterion_agreement,
        "packet_state_accuracy": packet_accuracy,
        "false_usable_rate": false_usable_rate,
        "candidate_unresolved_rate": candidate_unresolved_rate,
        "gate_results": gate_results,
        "candidate_state": (
            "RECEIPT_QUALITY_JUDGE_CALIBRATION_CANDIDATE"
            if passed else "RECEIPT_QUALITY_JUDGE_CALIBRATION_GATE_FAILED"
        ),
        "evidence_coordinate": "INTERNAL_MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_receipt_quality_calibration(artifact, *, corpus_artifact,
                                         candidate_run, reference_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("receipt_quality_calibration_artifact_hash_invalid")
    expected = build_receipt_quality_calibration(
        corpus_artifact=corpus_artifact,
        candidate_run=candidate_run,
        reference_artifact=reference_artifact,
    )
    if artifact != expected:
        raise ValueError("receipt_quality_calibration_artifact_semantics_invalid")


def _candidate_labels(candidate_run):
    labels = {}
    for judgment in candidate_run["judgments"]:
        for assessment in judgment["payload"]["assessments"]:
            labels[assessment["blind_candidate_id"]] = assessment["criteria"]
    return labels


def _packet_state(criteria):
    if set(criteria) != set(JUDGE_CRITERIA):
        return "MISSING"
    states = set(criteria.values())
    if not states.issubset(set(JUDGE_STATES)):
        return "MISSING"
    if states == {"PRESENT"}:
        return "USABLE"
    if "ABSENT" in states:
        return "UNUSABLE"
    return "UNRESOLVED"


def _validate_reference_surface(reference, corpus_artifact):
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
        or any(
            set(item.get("criteria", {})) != set(JUDGE_CRITERIA)
            or any(state not in JUDGE_STATES for state in item["criteria"].values())
            for item in labels
        )
    ):
        raise ValueError("receipt_quality_reference_surface_invalid")
