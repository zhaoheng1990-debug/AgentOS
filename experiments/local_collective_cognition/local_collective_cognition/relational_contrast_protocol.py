"""Frozen v0.68 protocol and source lock."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .evidence_inference_bridge import validate_panel
from .provider_telemetry import hash_payload


MECHANISM_FILES = (
    "relational_contrast_types.py",
    "relational_contrast_objects.py",
    "relational_contrast_schemas.py",
    "relational_contrast_contracts.py",
    "relational_contrast_tasks.py",
    "relational_basis_compiler.py",
    "relational_contrast_runtime.py",
    "relational_contrast_metrics.py",
)
FROZEN_HOLDOUT_HASH = (
    "5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1"
)


def build_calibration_preregistration(
    *, panel: dict[str, Any], frozen_holdout: dict[str, Any]
) -> dict[str, Any]:
    validate_panel(panel)
    validate_panel(frozen_holdout)
    if panel.get("case_count") != 12:
        raise ValueError("relational_calibration_count_invalid")
    if frozen_holdout.get("artifact_hash") != FROZEN_HOLDOUT_HASH:
        raise ValueError("relational_holdout_changed")
    commitment = {
        "preregistration_version": "relational_calibration_v0_68",
        "source_panel_hash": panel["artifact_hash"],
        "source_baseline_run_hash": panel["baseline_projection"]["run_hash"],
        "frozen_fresh_holdout_hash": frozen_holdout["artifact_hash"],
        "mechanism_source_hashes": mechanism_source_hashes(),
        "shared_admission_required": True,
        "stable_local_arm_ids_required": True,
        "orientation_enum_allowed": False,
        "significance_can_exclude_exact_evidence": False,
        "free_provider_synthesis_allowed": False,
        "provider_compiler_override_allowed": False,
        "prompt_change_after_first_frame_receipt_allowed": False,
        "calibration_gate": {
            "candidate_valid_receipt_count_min": 12,
            "candidate_total_failure_count_max": 0,
            "candidate_label_accuracy_min": 11 / 12,
            "candidate_evidence_f1_not_below_baseline": True,
            "candidate_effective_cbit_above_baseline": True,
            "known_case_labels": {
                "EI-CAL-11179": "NO_DIFFERENCE",
                "EI-CAL-5842": "DECREASED",
                "EI-CAL-3189": "DECREASED",
                "EI-CAL-9330": "DECREASED",
            },
            "known_measurement_case": "EI-CAL-13793",
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


def validate_relational_preregistration(value: dict[str, Any]) -> None:
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("relational_preregistration_hash_invalid")
    if value.get("mechanism_source_hashes") != mechanism_source_hashes():
        raise ValueError("relational_mechanism_source_changed")
    boundaries = (
        ("orientation_enum_allowed", False),
        ("significance_can_exclude_exact_evidence", False),
        ("free_provider_synthesis_allowed", False),
        ("provider_compiler_override_allowed", False),
        ("core_write_allowed", False),
        ("retention_write_allowed", False),
    )
    if any(value.get(field) is not expected for field, expected in boundaries):
        raise ValueError("relational_authority_boundary_invalid")


def mechanism_source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in MECHANISM_FILES
    }
