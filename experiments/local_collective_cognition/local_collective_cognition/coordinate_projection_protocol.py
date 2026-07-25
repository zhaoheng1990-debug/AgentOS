"""Frozen v0.72 coordinate projection protocol."""

from hashlib import sha256
from pathlib import Path

from .provider_telemetry import hash_payload


HOLDOUT_HASH = (
    "5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1"
)


def build_preregistration(*, panel, holdout, source_run):
    if holdout["artifact_hash"] != HOLDOUT_HASH:
        raise ValueError("coordinate_projection_holdout_changed")
    value = {
        "preregistration_version": "coordinate_projection_v0_72",
        "source_panel_hash": panel["artifact_hash"],
        "source_baseline_run_hash": panel["baseline_projection"]["run_hash"],
        "source_candidate_run_hash": source_run["run_hash"],
        "frozen_fresh_holdout_hash": holdout["artifact_hash"],
        "mechanism_source_hash": source_hash(),
        "projection_rules": {
            "UNCONSTRAINED": "ALLOWED_BY_UNCONSTRAINED",
            "EXACT": "PRESERVE_PROVIDER_BINDING",
            "IMPLICIT": "PRESERVE_PROVIDER_BINDING",
            "UNRESOLVED": "PRESERVE_PROVIDER_BINDING",
        },
        "calibration_gate": {
            "valid_receipts_min": 12,
            "label_accuracy_min": 11 / 12,
            "effective_cbit_above_baseline": True,
            "harms_max": 0,
            "required_labels": {
                "EI-CAL-6743": "INCREASED",
                "EI-CAL-8861": "NO_DIFFERENCE",
            },
        },
        "provider_calls_added_max": 0,
        "fresh_holdout_authorized_only_after_prospective_reexecution": True,
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
        raise ValueError("coordinate_projection_preregistration_hash_invalid")
    if value.get("mechanism_source_hash") != source_hash():
        raise ValueError("coordinate_projection_mechanism_changed")


def source_hash():
    path = Path(__file__).with_name("coordinate_projection_replay.py")
    return sha256(path.read_bytes()).hexdigest()
