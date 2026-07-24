"""Frozen v0.65 benchmark-bridge preregistration."""

from __future__ import annotations

from typing import Any

from .evidence_inference_bridge import BRIDGE_VERSION, validate_panel
from .provider_telemetry import hash_payload


def build_preregistration(panel: dict[str, Any]) -> dict[str, Any]:
    validate_panel(panel)
    commitment = {
        "preregistration_version": BRIDGE_VERSION,
        "source_panel_hash": panel["artifact_hash"],
        "research_object": "EVIDENCE_OBJECTIFICATION_MECHANISM",
        "arms": ["A0_ONE_PASS", "A1_STAGED_ADMISSION_BINDING"],
        "development_calibration": True,
        "prompt_change_after_first_semantic_receipt_allowed": False,
        "primary_metrics": [
            "label_accuracy",
            "evidence_precision",
            "evidence_recall",
            "evidence_f1",
            "rationale_token_f1",
            "receipt_contract_failure_count",
            "cross_type_overlap_count",
        ],
        "calibration_gate": {
            "a1_contract_failure_count_max": 0,
            "a1_cross_type_overlap_count_max": 0,
            "a1_label_accuracy_min": 8 / 9,
            "a1_evidence_f1_min": 0.80,
            "a1_rationale_token_f1_min": 0.80,
            "a1_effective_cbit_per_1k_tokens_min": 0.0,
            "a1_label_accuracy_not_below_a0": True,
            "a1_rationale_token_f1_not_below_a0": True,
            "a1_mechanism_delta_positive": True,
        },
        "effective_cbit_definition": (
            "mean(label_correct + evidence_f1 + rationale_token_f1) "
            "across cases"
        ),
        "token_cost_secondary_to_stable_positive_cbit": True,
        "maximum_provider_tasks": 27,
        "maximum_physical_attempts": 54,
        "hard_token_ceiling": 180000,
        "external_holdout_authorized_only_after_calibration_pass": True,
        "benchmark_native_claim": False,
        "fresh_generalization_claim": False,
        "pretraining_contamination_excluded": False,
        "raw_source_repository_write_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_preregistration(value: dict[str, Any]) -> None:
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("benchmark_bridge_preregistration_hash_mismatch")
    if value.get("core_write_allowed") is not False:
        raise ValueError("benchmark_bridge_core_write_boundary_invalid")
