"""Frozen test-split protocol and decision for v0.65."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .evidence_inference_bridge import validate_panel
from .provider_telemetry import hash_payload


def build_holdout_preregistration(
    *,
    panel: dict[str, Any],
    calibration_decision: dict[str, Any],
) -> dict[str, Any]:
    validate_panel(panel)
    _validate_hash(calibration_decision)
    if calibration_decision.get("external_holdout_authorized") is not True:
        raise ValueError("benchmark_bridge_holdout_not_authorized")
    commitment = {
        "preregistration_version": "benchmark_bridge_holdout_v0_65",
        "source_panel_hash": panel["artifact_hash"],
        "source_calibration_decision_hash": calibration_decision[
            "artifact_hash"
        ],
        "mechanism_source_hashes": _mechanism_source_hashes(),
        "arms": ["A0_ONE_PASS", "A1_STAGED_ADMISSION_BINDING"],
        "case_count": panel["case_count"],
        "label_balance": panel["label_balance"],
        "prompt_or_contract_tuning_allowed": False,
        "holdout_gate": {
            "a1_contract_failure_count_max": 0,
            "a1_cross_type_overlap_count_max": 0,
            "a1_label_accuracy_min": 0.85,
            "a1_evidence_f1_min": 0.80,
            "a1_rationale_token_f1_min": 0.80,
            "a1_effective_cbit_above_a0": True,
        },
        "maximum_provider_tasks": panel["case_count"] * 3,
        "maximum_physical_attempts": panel["case_count"] * 6,
        "hard_token_ceiling": 600000,
        "benchmark_native_claim": False,
        "test_split_transfer_claim_only": True,
        "fresh_generalization_claim": False,
        "pretraining_contamination_excluded": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def holdout_decision(
    *,
    preregistration: dict[str, Any],
    one_pass_score: dict[str, Any],
    staged_score: dict[str, Any],
) -> dict[str, Any]:
    _validate_hash(preregistration)
    gate = preregistration["holdout_gate"]
    conditions = {
        "a1_contract_failures": staged_score["contract_failure_count"]
        <= gate["a1_contract_failure_count_max"],
        "a1_cross_type_overlap": staged_score["cross_type_overlap_count"]
        <= gate["a1_cross_type_overlap_count_max"],
        "a1_label_accuracy": staged_score["label_accuracy"]
        >= gate["a1_label_accuracy_min"],
        "a1_evidence_f1": staged_score["evidence_f1"]
        >= gate["a1_evidence_f1_min"],
        "a1_rationale_token_f1": staged_score["rationale_token_f1"]
        >= gate["a1_rationale_token_f1_min"],
        "a1_effective_cbit_above_a0": (
            staged_score["effective_cbit"]
            > one_pass_score["effective_cbit"]
        ),
        "provider_task_budget": (
            staged_score["provider_task_count"]
            + one_pass_score["provider_task_count"]
            <= preregistration["maximum_provider_tasks"]
        ),
        "physical_attempt_budget": (
            staged_score["physical_attempt_count"]
            + one_pass_score["physical_attempt_count"]
            <= preregistration["maximum_physical_attempts"]
        ),
        "hard_token_ceiling": (
            staged_score["physical_total_tokens"]
            + one_pass_score["physical_total_tokens"]
            <= preregistration["hard_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "decision_version": "benchmark_bridge_holdout_decision_v0_65",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_one_pass_score_hash": one_pass_score["artifact_hash"],
        "source_staged_score_hash": staged_score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_BENCHMARK_BRIDGE_TEST_SPLIT_TRANSFER"
            if passed
            else "REJECT_BENCHMARK_BRIDGE_TEST_SPLIT_TRANSFER"
        ),
        "test_split_transfer_supported": passed,
        "fresh_generalization_claim": False,
        "benchmark_native_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_holdout_preregistration(value: dict[str, Any]) -> None:
    _validate_hash(value)
    if value.get("prompt_or_contract_tuning_allowed") is not False:
        raise ValueError("benchmark_bridge_holdout_tuning_boundary_invalid")
    if value.get("mechanism_source_hashes") != _mechanism_source_hashes():
        raise ValueError("benchmark_bridge_mechanism_source_changed")


def _mechanism_source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    names = (
        "benchmark_bridge_contracts.py",
        "benchmark_bridge_tasks.py",
        "benchmark_bridge_runtime.py",
        "benchmark_bridge_metrics.py",
    )
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in names
    }


def _validate_hash(value: dict[str, Any]) -> None:
    key = "artifact_hash"
    commitment = {name: item for name, item in value.items() if name != key}
    if value.get(key) != hash_payload(commitment):
        raise ValueError("benchmark_bridge_holdout_hash_mismatch")
