"""Private calibration scoring for v0.68."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_metrics import score_arm
from .provider_telemetry import hash_payload
from .relational_contrast_protocol import (
    validate_relational_preregistration,
)


def score_relational_contrast(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    baseline_run: dict[str, Any],
    candidate_run: dict[str, Any],
) -> dict[str, Any]:
    validate_relational_preregistration(preregistration)
    baseline = score_arm(
        panel=panel, preregistration=preregistration, run=baseline_run
    )
    candidate = score_arm(
        panel=panel, preregistration=preregistration, run=candidate_run
    )
    old = {value["case_id"]: value for value in baseline["cases"]}
    new = {value["case_id"]: value for value in candidate["cases"]}
    corrections = sorted(
        case_id for case_id in new
        if not old[case_id]["label_correct"] and new[case_id]["label_correct"]
    )
    harms = sorted(
        case_id for case_id in new
        if old[case_id]["label_correct"] and not new[case_id]["label_correct"]
    )
    unresolved = sorted(
        case_id for case_id, receipt in candidate_run["receipts"].items()
        if receipt["predicted_label"]
        == "UNRESOLVED_MATERIAL_AMBIGUITY"
    )
    commitment = {
        "score_version": "relational_contrast_score_v0_68",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "baseline": baseline,
        "candidate": candidate,
        "frame_receipt_count": len(candidate_run["frame_receipts"]),
        "basis_receipt_count": len(candidate_run["basis_receipts"]),
        "candidate_total_failure_count": (
            len(candidate_run["contract_failures"])
            + len(candidate_run["compiler_failures"])
        ),
        "compiler_failure_count": len(candidate_run["compiler_failures"]),
        "corrected_case_ids": corrections,
        "harmed_case_ids": harms,
        "unresolved_case_ids": unresolved,
        "correction_surplus": len(corrections) - len(harms),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def calibration_decision(
    *, preregistration: dict[str, Any], score: dict[str, Any]
) -> dict[str, Any]:
    validate_relational_preregistration(preregistration)
    gate = preregistration["calibration_gate"]
    candidate, baseline = score["candidate"], score["baseline"]
    observed = {
        value["case_id"]: value["predicted_label"]
        for value in candidate["cases"]
    }
    known = all(
        observed.get(case_id) == label
        for case_id, label in gate["known_case_labels"].items()
    )
    conditions = {
        "candidate_receipt_count": candidate["valid_receipt_count"]
        >= gate["candidate_valid_receipt_count_min"],
        "candidate_failures": score["candidate_total_failure_count"]
        <= gate["candidate_total_failure_count_max"],
        "candidate_label_accuracy": candidate["label_accuracy"]
        >= gate["candidate_label_accuracy_min"],
        "candidate_evidence_f1": candidate["evidence_f1"]
        >= baseline["evidence_f1"],
        "candidate_effective_cbit": candidate["effective_cbit"]
        > baseline["effective_cbit"],
        "known_relational_cases": known,
        "known_measurement_not_forced_effect": observed.get(
            gate["known_measurement_case"]
        ) in {"NO_DIFFERENCE", "UNRESOLVED_MATERIAL_AMBIGUITY"},
        "harmful_regressions": len(score["harmed_case_ids"])
        <= gate["harmful_regression_count_max"],
        "provider_task_budget": candidate["provider_task_count"]
        <= preregistration["maximum_candidate_provider_tasks"],
        "physical_attempt_budget": candidate["physical_attempt_count"]
        <= preregistration["maximum_candidate_physical_attempts"],
        "hard_token_ceiling": candidate["physical_total_tokens"]
        <= preregistration["hard_candidate_token_ceiling"],
    }
    passed = all(conditions.values())
    commitment = {
        "decision_version": "relational_calibration_decision_v0_68",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_RELATIONAL_CONTRAST_CALIBRATION"
            if passed else "REJECT_RELATIONAL_CONTRAST_CALIBRATION"
        ),
        "fresh_holdout_authorized": passed,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}
