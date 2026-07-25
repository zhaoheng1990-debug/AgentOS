"""Frozen v0.74 grouped-object alias protocol."""

from hashlib import sha256
from pathlib import Path

from .provider_telemetry import hash_payload


FILES = (
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
)
HOLDOUT_HASH = (
    "5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1"
)


def build_preregistration(*, panel, holdout):
    if holdout["artifact_hash"] != HOLDOUT_HASH:
        raise ValueError("grouped_alias_surface_holdout_changed")
    value = {
        "preregistration_version": "grouped_alias_surface_v0_74",
        "source_panel_hash": panel["artifact_hash"],
        "source_baseline_run_hash": panel["baseline_projection"]["run_hash"],
        "frozen_fresh_holdout_hash": holdout["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "prospective_provider_reexecution_required": True,
        "grouped_alias_contract": {
            "source": "IMMUTABLE_ARM_CATALOG_ONLY",
            "delimiters": [",", ";", "|"],
            "maximum_members": 8,
            "semantic_synonyms_allowed": False,
            "provider_alias_expansion_allowed": False,
        },
        "free_text_witness_allowed": False,
        "provider_compiler_override_allowed": False,
        "calibration_gate": {
            "valid_receipts_min": 12,
            "failures_max": 0,
            "label_accuracy_min": 11 / 12,
            "evidence_f1_not_below_baseline": True,
            "effective_cbit_above_baseline": True,
            "harms_max": 0,
            "required_labels": {
                "EI-CAL-11179": "NO_DIFFERENCE",
                "EI-CAL-13793": "NO_DIFFERENCE",
                "EI-CAL-3189": "DECREASED",
                "EI-CAL-5842": "DECREASED",
                "EI-CAL-6743": "INCREASED",
                "EI-CAL-8861": "NO_DIFFERENCE",
            },
        },
        "maximum_provider_tasks": 24,
        "maximum_physical_attempts": 48,
        "hard_token_ceiling": 320000,
        "fresh_holdout_authorized_only_after_full_pass": True,
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
        raise ValueError("grouped_alias_surface_preregistration_hash_invalid")
    if value.get("mechanism_source_hashes") != source_hashes():
        raise ValueError("grouped_alias_surface_mechanism_changed")


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in FILES
    }
