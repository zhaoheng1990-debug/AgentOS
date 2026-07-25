"""Frozen v0.75 one-shot fresh holdout protocol."""

from hashlib import sha256
from pathlib import Path

from .provider_telemetry import hash_payload


HOLDOUT_HASH = (
    "5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1"
)
CALIBRATION_DECISION_HASH = (
    "c6f42188058b4f242c650c03c030d260dd26e9093d33f7fcb12a8ea3c645e9c7"
)
FILES = (
    "benchmark_bridge_runtime.py",
    "benchmark_bridge_tasks.py",
    "benchmark_bridge_contracts.py",
    "benchmark_bridge_metrics.py",
    "grouped_alias_surface_runtime.py",
    "prospective_surface_pipeline.py",
    "grouped_arm_aliases.py",
    "relation_witness_tasks.py",
    "relation_witness_contracts.py",
    "surface_candidate_catalog.py",
    "surface_binding_tasks.py",
    "surface_binding_contracts.py",
    "coordinate_projection_replay.py",
    "surface_binding_compiler.py",
    "fresh_holdout_metrics.py",
)


def build_preregistration(
    *, panel, calibration_preregistration, calibration_decision
):
    if panel["artifact_hash"] != HOLDOUT_HASH:
        raise ValueError("fresh_holdout_panel_changed")
    if calibration_decision["artifact_hash"] != CALIBRATION_DECISION_HASH:
        raise ValueError("fresh_holdout_calibration_decision_changed")
    if calibration_decision["decision"] != (
        "PASS_GROUPED_ALIAS_SURFACE_CALIBRATION"
    ):
        raise ValueError("fresh_holdout_not_authorized")
    if calibration_decision["source_preregistration_hash"] != (
        calibration_preregistration["artifact_hash"]
    ):
        raise ValueError("fresh_holdout_calibration_lineage_invalid")
    value = {
        "preregistration_version": "fresh_holdout_v0_75",
        "source_panel_hash": panel["artifact_hash"],
        "source_calibration_preregistration_hash": (
            calibration_preregistration["artifact_hash"]
        ),
        "source_calibration_decision_hash": (
            calibration_decision["artifact_hash"]
        ),
        "mechanism_source_hashes": source_hashes(),
        "case_count": 36,
        "label_balance": {
            "INCREASED": 12,
            "DECREASED": 12,
            "NO_DIFFERENCE": 12,
        },
        "arms": [
            "A1_STAGED_ADMISSION_BINDING",
            "A10_GROUPED_ALIAS_SURFACE_PROJECTION",
        ],
        "shared_admission_receipts_required": True,
        "prompt_or_contract_tuning_after_freeze_allowed": False,
        "holdout_reexecution_allowed": False,
        "primary_gate": {
            "admission_receipts_min": 36,
            "candidate_valid_receipts_min": 34,
            "candidate_failures_max": 2,
            "label_accuracy_not_below_baseline": True,
            "evidence_f1_not_below_baseline": True,
            "rationale_token_f1_not_below_baseline": True,
            "effective_cbit_above_baseline": True,
            "net_label_corrections_min": 1,
        },
        "confidence_gate": {
            "effective_cbit_bootstrap_lower_above_zero": True,
        },
        "maximum_baseline_tasks": 72,
        "maximum_candidate_incremental_tasks": 72,
        "maximum_candidate_path_tasks": 108,
        "maximum_total_experiment_tasks": 144,
        "maximum_total_physical_attempts": 288,
        "hard_total_token_ceiling": 1800000,
        "claim_ceiling": "BOUNDED_FRESH_HOLDOUT_TRANSFER",
        "benchmark_native_claim": False,
        "pretraining_contamination_excluded": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def validate_preregistration(value):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("fresh_holdout_preregistration_hash_invalid")
    if value.get("mechanism_source_hashes") != source_hashes():
        raise ValueError("fresh_holdout_mechanism_changed")


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in FILES
    }
