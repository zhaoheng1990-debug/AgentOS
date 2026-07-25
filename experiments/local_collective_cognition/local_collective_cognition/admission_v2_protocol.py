"""Frozen v0.76 typed evidence admission protocol."""

from hashlib import sha256
from pathlib import Path

from .provider_telemetry import hash_payload


SOURCE_BLOCK_HASH = (
    "6ee6a4a4bd0610e437a45a63ef9dbfa9ba81419a9e0aa0faedc937340e3533bc"
)
FILES = (
    "admission_v2_types.py",
    "admission_v2_schemas.py",
    "admission_v2_contracts.py",
    "admission_v2_compiler.py",
    "admission_v2_tasks.py",
    "admission_v2_runtime.py",
    "admission_v2_calibration.py",
    "benchmark_bridge_tasks.py",
)


def build_preregistration(*, panel, source_block):
    if source_block["artifact_hash"] != SOURCE_BLOCK_HASH:
        raise ValueError("admission_v2_source_block_changed")
    if source_block["decision"] != "BLOCKED_BY_ADMISSION_CONTRACT":
        raise ValueError("admission_v2_source_problem_invalid")
    if panel.get("v0_75_holdout_reused") is not False:
        raise ValueError("admission_v2_holdout_reuse_invalid")
    value = {
        "preregistration_version": "admission_v2_v0_76",
        "source_panel_hash": panel["artifact_hash"],
        "source_problem_decision_hash": source_block["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "research_object": "TYPED_EVIDENCE_ADMISSION_ONTOLOGY",
        "axes": [
            "OBJECT_RELATION",
            "EVIDENCE_UTILITY",
            "DISPOSITION",
        ],
        "null_evidence_is_valid_state": True,
        "context_partition_required": True,
        "provider_label_authority": False,
        "calibration_gate": {
            "valid_receipts_min": 12,
            "failures_max": 0,
            "complete_partitions_min": 12,
            "false_no_applicable_max": 0,
            "context_spans_min": 1,
            "evidence_precision_not_below_baseline": True,
            "evidence_recall_not_below_baseline": True,
            "evidence_f1_not_below_baseline": True,
            "harmed_cases_max": 0,
        },
        "maximum_provider_tasks": 12,
        "maximum_physical_attempts": 24,
        "hard_token_ceiling": 180000,
        "new_holdout_design_authorized_only_after_full_pass": True,
        "v0_75_holdout_reexecution_allowed": False,
        "fresh_generalization_claim": False,
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
        raise ValueError("admission_v2_preregistration_hash_invalid")
    if value.get("mechanism_source_hashes") != source_hashes():
        raise ValueError("admission_v2_mechanism_changed")


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in FILES
    }
