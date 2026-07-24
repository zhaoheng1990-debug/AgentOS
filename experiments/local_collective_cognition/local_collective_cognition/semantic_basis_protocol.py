"""Frozen preregistration and mechanism source lock for v0.66."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .provider_telemetry import hash_payload
from .semantic_basis_calibration import validate_calibration_projection
from .semantic_basis_holdout import validate_semantic_basis_holdout


MECHANISM_FILES = (
    "semantic_basis_types.py",
    "semantic_basis_schemas.py",
    "semantic_basis_contracts.py",
    "semantic_basis_consistency.py",
    "semantic_basis_tasks.py",
    "semantic_basis_runtime.py",
    "semantic_basis_metrics.py",
)


def build_calibration_preregistration(
    *,
    panel: dict[str, Any],
) -> dict[str, Any]:
    validate_calibration_projection(panel)
    commitment = {
        "preregistration_version": "semantic_basis_calibration_v0_66",
        "source_panel_hash": panel["artifact_hash"],
        "source_baseline_run_hash": panel["baseline_projection"][
            "run_hash"
        ],
        "mechanism_source_hashes": mechanism_source_hashes(),
        "shared_admission_required": True,
        "prompt_change_after_first_basis_receipt_allowed": False,
        "calibration_gate": {
            "candidate_valid_receipt_count_min": 12,
            "candidate_total_failure_count_max": 0,
            "candidate_label_accuracy_min": 11 / 12,
            "candidate_evidence_f1_not_below_baseline": True,
            "candidate_effective_cbit_above_baseline": True,
            "known_significance_failure_corrected": "EI-CAL-11179",
            "known_orientation_failure_corrected": "EI-CAL-5842",
            "known_ambiguity_not_forced_effect": "EI-CAL-13793",
            "harmful_regression_count_max": 0,
        },
        "maximum_candidate_provider_tasks": 24,
        "maximum_candidate_physical_attempts": 48,
        "hard_candidate_token_ceiling": 150000,
        "fresh_holdout_authorized_only_after_full_pass": True,
        "semantic_coordinate_gold_available": False,
        "benchmark_native_claim": False,
        "fresh_generalization_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_holdout_preregistration(
    *,
    panel: dict[str, Any],
    calibration_decision: dict[str, Any],
) -> dict[str, Any]:
    validate_semantic_basis_holdout(panel)
    _validate_hash(calibration_decision)
    if calibration_decision.get("fresh_holdout_authorized") is not True:
        raise ValueError("semantic_basis_holdout_not_authorized")
    commitment = {
        "preregistration_version": "semantic_basis_holdout_v0_66",
        "source_panel_hash": panel["artifact_hash"],
        "source_calibration_decision_hash": calibration_decision[
            "artifact_hash"
        ],
        "mechanism_source_hashes": mechanism_source_hashes(),
        "shared_admission_required": True,
        "prompt_or_contract_tuning_allowed": False,
        "holdout_gate": {
            "candidate_valid_receipt_count_min": 36,
            "candidate_total_failure_count_max": 0,
            "candidate_label_accuracy_above_baseline": True,
            "candidate_effective_cbit_above_baseline": True,
            "candidate_evidence_f1_floor_vs_baseline": -0.01,
            "correction_surplus_min": 1,
        },
        "maximum_total_provider_tasks": 144,
        "maximum_total_physical_attempts": 288,
        "hard_total_token_ceiling": 600000,
        "semantic_coordinate_gold_available": False,
        "benchmark_native_claim": False,
        "fresh_generalization_claim": False,
        "pretraining_contamination_excluded": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_semantic_basis_preregistration(value: dict[str, Any]) -> None:
    _validate_hash(value)
    if value.get("mechanism_source_hashes") != mechanism_source_hashes():
        raise ValueError("semantic_basis_mechanism_source_changed")
    if value.get("core_write_allowed") is not False:
        raise ValueError("semantic_basis_core_boundary_invalid")
    if value.get("retention_write_allowed") is not False:
        raise ValueError("semantic_basis_retention_boundary_invalid")


def mechanism_source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in MECHANISM_FILES
    }


def _validate_hash(value: dict[str, Any]) -> None:
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("semantic_basis_preregistration_hash_invalid")
