"""Frozen protocol for v0.71 surface candidate binding."""

from hashlib import sha256
from pathlib import Path

from .provider_telemetry import hash_payload


FILES = (
    "surface_candidate_catalog.py",
    "surface_binding_schemas.py",
    "surface_binding_contracts.py",
    "surface_binding_tasks.py",
    "surface_binding_compiler.py",
    "surface_binding_runtime.py",
)
HOLDOUT_HASH = (
    "5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1"
)


def build_preregistration(*, panel, holdout, frame_run):
    if holdout["artifact_hash"] != HOLDOUT_HASH:
        raise ValueError("surface_binding_holdout_changed")
    value = {
        "preregistration_version": "surface_binding_v0_71",
        "source_panel_hash": panel["artifact_hash"],
        "source_baseline_run_hash": panel["baseline_projection"]["run_hash"],
        "source_frame_run_hash": frame_run["run_hash"],
        "frozen_fresh_holdout_hash": holdout["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "provider_free_text_witness_allowed": False,
        "provider_compiler_override_allowed": False,
        "calibration_gate": {
            "valid_receipts_min": 12,
            "failures_max": 0,
            "label_accuracy_min": 11 / 12,
            "evidence_f1_not_below_baseline": True,
            "effective_cbit_above_baseline": True,
            "harms_max": 0,
            "required_labels": {
                "EI-CAL-5842": "DECREASED",
                "EI-CAL-8555": "NO_DIFFERENCE",
            },
        },
        "maximum_provider_tasks": 24,
        "maximum_physical_attempts": 48,
        "hard_token_ceiling": 200000,
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
        raise ValueError("surface_binding_preregistration_hash_invalid")
    if value.get("mechanism_source_hashes") != source_hashes():
        raise ValueError("surface_binding_mechanism_changed")


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in FILES
    }
