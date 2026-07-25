"""Frozen unused-source holdout for witness admission v0.78."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .evidence_inference_bridge import (
    build_selected_panel,
    public_panel,
    validate_panel,
)
from .provider_telemetry import hash_payload


SELECTED_PROMPT_IDS = (
    "3727",
    "9224",
    "4232",
    "7397",
    "11659",
    "10178",
    "7399",
    "5844",
    "5361",
    "7207",
    "1000",
    "11804",
)
PRIOR_TEST_PROMPT_IDS = (
    "9128",
    "8986",
    "8985",
    "6743",
    "13790",
    "3293",
    "8984",
    "3146",
    "1782",
    "2819",
    "4236",
    "9333",
    "5842",
    "13092",
    "11995",
    "3782",
    "8434",
    "5791",
    "9330",
    "10177",
    "12291",
    "3189",
    "11675",
    "5362",
    "771",
    "213",
    "11803",
    "8615",
    "11806",
    "13793",
    "8861",
    "11179",
    "6436",
    "8555",
    "8834",
    "6314",
)
V077_DEVELOPMENT_PROMPT_IDS = (
    "8984",
    "9554",
    "9333",
    "8986",
    "11995",
    "5362",
    "10177",
    "9748",
    "6857",
    "8615",
    "6165",
    "11806",
)
SOURCE_FILES = (
    "admission_v2_compiler.py",
    "admission_v2_contracts.py",
    "admission_v2_runtime.py",
    "admission_v2_schemas.py",
    "admission_v2_tasks.py",
    "admission_v3_compiler.py",
    "admission_v3_contracts.py",
    "admission_v3_runtime.py",
    "admission_v3_schemas.py",
    "admission_v3_tasks.py",
    "effect_basis_admission.py",
    "outcome_separability_witness.py",
)


def build_fresh_holdout(paths, *, source_manifest):
    panel = build_selected_panel(
        paths=paths,
        selected_prompt_ids=SELECTED_PROMPT_IDS,
        split_ids_name="test_article_ids.txt",
        benchmark_id="evidence-inference-admission-v3-fresh-holdout",
        split="unused_test_split_hash_selection_v0_78",
        manifest=source_manifest,
        external_transfer_claim=True,
    )
    value = {
        key: item for key, item in panel.items()
        if key != "artifact_hash"
    }
    value.update({
        "bridge_version": "admission_v3_fresh_holdout_v0_78",
        "selection_version": "sha256_unused_test_objects_v0_78",
        "selected_prompt_ids": list(SELECTED_PROMPT_IDS),
        "prior_test_prompt_ids_hash": hash_payload(
            list(PRIOR_TEST_PROMPT_IDS)
        ),
        "v0_77_development_prompt_ids_hash": hash_payload(
            list(V077_DEVELOPMENT_PROMPT_IDS)
        ),
        "local_pipeline_object_fresh": True,
        "v0_75_holdout_reused": False,
        "v0_77_development_reused": False,
        "typed_reference_available": False,
        "benchmark_gold_role": "SECONDARY_COVERAGE_GUARD_ONLY",
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    })
    return {**value, "artifact_hash": hash_payload(value)}


def validate_fresh_holdout(panel):
    validate_panel(panel)
    selected = set(panel.get("selected_prompt_ids", []))
    if (
        tuple(panel.get("selected_prompt_ids", []))
        != SELECTED_PROMPT_IDS
        or selected & set(PRIOR_TEST_PROMPT_IDS)
        or selected & set(V077_DEVELOPMENT_PROMPT_IDS)
        or panel.get("case_count") != 12
        or panel.get("label_balance") != {
            "INCREASED": 4,
            "DECREASED": 4,
            "NO_DIFFERENCE": 4,
        }
        or panel.get("local_pipeline_object_fresh") is not True
        or panel.get("typed_reference_available") is not False
    ):
        raise ValueError("admission_v3_fresh_holdout_invalid")


def build_preregistration(panel):
    validate_fresh_holdout(panel)
    value = {
        "preregistration_version": "admission_v3_fresh_holdout_v0_78",
        "source_panel_hash": panel["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "arms": [
            "A11_TYPED_EVIDENCE_ADMISSION",
            "A12_WITNESS_BACKED_ADMISSION",
        ],
        "case_count": 12,
        "label_balance": panel["label_balance"],
        "prompt_or_contract_tuning_after_freeze_allowed": False,
        "holdout_reexecution_allowed": False,
        "benchmark_gold_role": "SECONDARY_COVERAGE_GUARD_ONLY",
        "primary_semantic_gate": "EXTERNAL_TYPED_REFERENCE_REQUIRED",
        "operational_gate": {
            "valid_receipts_min_per_arm": 11,
            "failures_max_per_arm": 1,
            "complete_partitions_min_per_arm": 11,
        },
        "maximum_provider_tasks_per_arm": 12,
        "maximum_total_provider_tasks": 24,
        "maximum_total_physical_attempts": 48,
        "hard_total_token_ceiling": 250000,
        "freshness_scope": "LOCAL_PIPELINE_UNSEEN_SOURCE_OBJECTS",
        "pretraining_contamination_excluded": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def validate_preregistration(value, *, panel):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if (
        value.get("artifact_hash") != hash_payload(commitment)
        or value.get("source_panel_hash") != panel.get("artifact_hash")
        or value.get("mechanism_source_hashes") != source_hashes()
        or value.get("prompt_or_contract_tuning_after_freeze_allowed")
        is not False
        or value.get("primary_semantic_gate")
        != "EXTERNAL_TYPED_REFERENCE_REQUIRED"
    ):
        raise ValueError("admission_v3_preregistration_invalid")


def public_fresh_holdout(panel):
    public = public_panel(panel)
    return {
        **public,
        "selection_version": panel["selection_version"],
        "case_count": panel["case_count"],
        "local_pipeline_object_fresh": True,
        "typed_reference_available": False,
    }


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }
