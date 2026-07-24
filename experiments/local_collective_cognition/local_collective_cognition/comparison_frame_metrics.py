"""Private scoring and frozen decisions for v0.67."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_metrics import score_arm
from .provider_telemetry import hash_payload
from .comparison_frame_protocol import (
    validate_comparison_frame_preregistration,
)


def score_comparison_frame(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    baseline_run: dict[str, Any],
    candidate_run: dict[str, Any],
) -> dict[str, Any]:
    validate_comparison_frame_preregistration(preregistration)
    baseline = score_arm(
        panel=panel, preregistration=preregistration, run=baseline_run
    )
    candidate = score_arm(
        panel=panel, preregistration=preregistration, run=candidate_run
    )
    previous = {
        value["case_id"]: value for value in baseline["cases"]
    }
    observed = {
        value["case_id"]: value for value in candidate["cases"]
    }
    corrections = sorted(
        case_id for case_id in observed
        if not previous[case_id]["label_correct"]
        and observed[case_id]["label_correct"]
    )
    harms = sorted(
        case_id for case_id in observed
        if previous[case_id]["label_correct"]
        and not observed[case_id]["label_correct"]
    )
    unresolved = sorted(
        case_id for case_id, receipt in candidate_run["receipts"].items()
        if receipt["predicted_label"]
        == "UNRESOLVED_MATERIAL_AMBIGUITY"
    )
    total_failures = (
        len(candidate_run["contract_failures"])
        + len(candidate_run["compiler_failures"])
    )
    commitment = {
        "score_version": "comparison_frame_score_v0_67",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "baseline": baseline,
        "candidate": candidate,
        "frame_receipt_count": len(candidate_run["frame_receipts"]),
        "basis_receipt_count": len(candidate_run["basis_receipts"]),
        "candidate_total_failure_count": total_failures,
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
    validate_comparison_frame_preregistration(preregistration)
    gate = preregistration["calibration_gate"]
    candidate = score["candidate"]
    baseline = score["baseline"]
    observed = {
        value["case_id"]: value["predicted_label"]
        for value in candidate["cases"]
    }
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
        "known_significance_corrected": observed.get(
            gate["known_significance_case"]
        ) == "NO_DIFFERENCE",
        "known_orientation_corrected": observed.get(
            gate["known_orientation_case"]
        ) == "DECREASED",
        "known_multi_arm_preserved": observed.get(
            gate["known_multi_arm_case"]
        ) == "DECREASED",
        "known_unconstrained_timepoint_preserved": observed.get(
            gate["known_unconstrained_timepoint_case"]
        ) == "DECREASED",
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
        "decision_version": "comparison_frame_calibration_decision_v0_67",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_COMPARISON_FRAME_CALIBRATION"
            if passed else "REJECT_COMPARISON_FRAME_CALIBRATION"
        ),
        "fresh_holdout_authorized": passed,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def holdout_decision(
    *, preregistration: dict[str, Any], score: dict[str, Any]
) -> dict[str, Any]:
    validate_comparison_frame_preregistration(preregistration)
    gate = preregistration["holdout_gate"]
    candidate = score["candidate"]
    baseline = score["baseline"]
    total_tasks = (
        candidate["provider_task_count"] + baseline["provider_task_count"]
    )
    total_attempts = (
        candidate["physical_attempt_count"]
        + baseline["physical_attempt_count"]
    )
    total_tokens = (
        candidate["physical_total_tokens"]
        + baseline["physical_total_tokens"]
    )
    conditions = {
        "candidate_receipt_count": candidate["valid_receipt_count"]
        >= gate["candidate_valid_receipt_count_min"],
        "candidate_failures": score["candidate_total_failure_count"]
        <= gate["candidate_total_failure_count_max"],
        "candidate_label_accuracy_above_baseline": (
            candidate["label_accuracy"] > baseline["label_accuracy"]
        ),
        "candidate_effective_cbit_above_baseline": (
            candidate["effective_cbit"] > baseline["effective_cbit"]
        ),
        "candidate_evidence_f1_floor": (
            candidate["evidence_f1"] - baseline["evidence_f1"]
            >= gate["candidate_evidence_f1_floor_vs_baseline"]
        ),
        "correction_surplus": score["correction_surplus"]
        >= gate["correction_surplus_min"],
        "provider_task_budget": total_tasks
        <= preregistration["maximum_total_provider_tasks"],
        "physical_attempt_budget": total_attempts
        <= preregistration["maximum_total_physical_attempts"],
        "hard_token_ceiling": total_tokens
        <= preregistration["hard_total_token_ceiling"],
    }
    passed = all(conditions.values())
    commitment = {
        "decision_version": "comparison_frame_holdout_decision_v0_67",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_COMPARISON_FRAME_FRESH_TRANSFER"
            if passed else "REJECT_COMPARISON_FRAME_FRESH_TRANSFER"
        ),
        "fresh_transfer_supported": passed,
        "benchmark_native_claim": False,
        "pretraining_contamination_excluded": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}
