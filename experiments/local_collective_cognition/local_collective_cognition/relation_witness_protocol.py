"""Frozen v0.69 witness protocol."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .provider_telemetry import hash_payload


FILES = (
    "relation_witness_schemas.py",
    "relation_witness_contracts.py",
    "relation_witness_tasks.py",
    "relation_witness_compiler.py",
    "relation_witness_runtime.py",
    "relation_witness_metrics.py",
)
HOLDOUT_HASH = (
    "5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1"
)


def build_preregistration(*, panel, holdout):
    if panel["case_count"] != 12 or holdout["artifact_hash"] != HOLDOUT_HASH:
        raise ValueError("witness_source_window_invalid")
    value = {
        "preregistration_version": "relation_witness_v0_69",
        "source_panel_hash": panel["artifact_hash"],
        "source_baseline_run_hash": panel["baseline_projection"]["run_hash"],
        "frozen_fresh_holdout_hash": holdout["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "span_anchored_subject_required": True,
        "span_anchored_relation_required": True,
        "provider_compiler_override_allowed": False,
        "calibration_gate": {
            "valid_receipts_min": 12,
            "failure_count_max": 0,
            "label_accuracy_min": 11 / 12,
            "evidence_f1_not_below_baseline": True,
            "effective_cbit_above_baseline": True,
            "harmed_cases_max": 0,
            "required_labels": {
                "EI-CAL-5842": "DECREASED",
                "EI-CAL-8555": "NO_DIFFERENCE",
            },
        },
        "maximum_provider_tasks": 24,
        "maximum_physical_attempts": 48,
        "hard_token_ceiling": 160000,
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
        raise ValueError("witness_preregistration_hash_invalid")
    if value.get("mechanism_source_hashes") != source_hashes():
        raise ValueError("witness_mechanism_changed")
    if value.get("provider_compiler_override_allowed") is not False:
        raise ValueError("witness_authority_invalid")


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in FILES
    }
