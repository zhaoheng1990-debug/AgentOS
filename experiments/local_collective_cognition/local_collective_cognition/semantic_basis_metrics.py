"""Private outcome scoring and frozen gates for v0.66."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_metrics import score_arm
from .provider_telemetry import hash_payload
from .semantic_basis_protocol import (
    validate_semantic_basis_preregistration,
)


def score_semantic_basis(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    baseline_run: dict[str, Any],
    candidate_run: dict[str, Any],
) -> dict[str, Any]:
    validate_semantic_basis_preregistration(preregistration)
    baseline = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=baseline_run,
    )
    candidate = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=candidate_run,
    )
    baseline_cases = {
        value["case_id"]: value for value in baseline["cases"]
    }
    candidate_cases = {
        value["case_id"]: value for value in candidate["cases"]
    }
    corrections: list[str] = []
    harms: list[str] = []
    for case_id, observed in candidate_cases.items():
        previous = baseline_cases[case_id]
        if not previous["label_correct"] and observed["label_correct"]:
            corrections.append(case_id)
        if previous["label_correct"] and not observed["label_correct"]:
            harms.append(case_id)
    unresolved = sorted(
        case_id
        for case_id, receipt in candidate_run["receipts"].items()
        if receipt["predicted_label"]
        == "UNRESOLVED_MATERIAL_AMBIGUITY"
    )
    total_failures = (
        len(candidate_run["contract_failures"])
        + len(candidate_run["semantic_consistency_failures"])
    )
    commitment = {
        "score_version": "semantic_basis_score_v0_66",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "baseline": baseline,
        "candidate": candidate,
        "basis_receipt_count": len(candidate_run["basis_receipts"]),
        "candidate_total_failure_count": total_failures,
        "semantic_consistency_failure_count": len(
            candidate_run["semantic_consistency_failures"]
        ),
        "corrected_case_ids": sorted(corrections),
        "harmed_case_ids": sorted(harms),
        "unresolved_case_ids": unresolved,
        "correction_surplus": len(corrections) - len(harms),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def calibration_decision(
    *,
    preregistration: dict[str, Any],
    score: dict[str, Any],
) -> dict[str, Any]:
    validate_semantic_basis_preregistration(preregistration)
    gate = preregistration["calibration_gate"]
    candidate = score["candidate"]
    baseline = score["baseline"]
    receipts = candidate["cases"]
    observed = {
        value["case_id"]: value["predicted_label"] for value in receipts
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
            gate["known_significance_failure_corrected"]
        )
        == "NO_DIFFERENCE",
        "known_orientation_corrected": observed.get(
            gate["known_orientation_failure_corrected"]
        )
        == "DECREASED",
        "known_ambiguity_not_forced_effect": observed.get(
            gate["known_ambiguity_not_forced_effect"]
        )
        in {"NO_DIFFERENCE", "UNRESOLVED_MATERIAL_AMBIGUITY"},
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
        "decision_version": "semantic_basis_calibration_decision_v0_66",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_TYPED_SEMANTIC_BASIS_CALIBRATION"
            if passed
            else "REJECT_TYPED_SEMANTIC_BASIS_CALIBRATION"
        ),
        "fresh_holdout_authorized": passed,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def holdout_decision(
    *,
    preregistration: dict[str, Any],
    score: dict[str, Any],
) -> dict[str, Any]:
    validate_semantic_basis_preregistration(preregistration)
    gate = preregistration["holdout_gate"]
    candidate = score["candidate"]
    baseline = score["baseline"]
    total_tasks = (
        candidate["provider_task_count"]
        + baseline["provider_task_count"]
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
        "decision_version": "semantic_basis_holdout_decision_v0_66",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_TYPED_SEMANTIC_BASIS_FRESH_TRANSFER"
            if passed
            else "REJECT_TYPED_SEMANTIC_BASIS_FRESH_TRANSFER"
        ),
        "fresh_transfer_supported": passed,
        "benchmark_native_claim": False,
        "pretraining_contamination_excluded": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}
